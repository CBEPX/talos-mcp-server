"""Pinned talosctl client with one code-owned policy gate and bounded subprocesses."""

import asyncio
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, cast

import anyio
import yaml
from loguru import logger

from talos_mcp.core.artifacts import has_reparse_component, windows_private_acl
from talos_mcp.core.policy import ALIASES, FORMS, OPERATIONS, _matches, validate_argv


class TalosExecutionError(Exception):
    """Sanitized operational error; raw talosctl output is never embedded."""

    def __init__(
        self,
        code: str,
        *,
        outcome: str = "failed",
        exit_code: int | None = None,
        truncated: bool = False,
    ) -> None:
        """Store one sanitized command failure."""
        self.code = code
        self.outcome = outcome
        self.exit_code = exit_code
        self.truncated = truncated
        super().__init__(code)


class TalosClient:
    """Execution context pinned at server startup."""

    def __init__(
        self,
        config_path: str | None = None,
        *,
        profile: str = "readonly",
        allow_tools: list[str] | None = None,
        talosctl: str | None = None,
        context: str | None = None,
        artifact_root: str | None = None,
        output_limit: int = 256 * 1024,
        timeout: float = 60,
        artifact_timeout: float = 600,
        upgrade_timeout: float = 600,
        artifact_limit: int = 512 * 1024 * 1024,
        root_limit: int = 4 * 1024 * 1024 * 1024,
        audit_enabled: bool = False,
    ) -> None:
        """Pin profile, credentials, binary, and bounded call limits at startup."""
        if profile not in {"readonly", "write"}:
            raise ValueError("INVALID_ARGUMENT: profile must be readonly or write")
        if (
            not 0 < timeout <= 600
            or not 0 < artifact_timeout <= 600
            or not 0 < upgrade_timeout <= 600
        ):
            raise ValueError("INVALID_ARGUMENT: timeout outside operator cap")
        if output_limit < 1 or artifact_limit < 1 or root_limit < artifact_limit:
            raise ValueError(
                "INVALID_ARGUMENT: artifact/output limits must be positive and root >= call"
            )
        self.profile = profile
        self.audit_enabled = audit_enabled
        self.allow_tools = frozenset(allow_tools) if allow_tools is not None else None
        if allow_tools is not None and (
            len(set(allow_tools)) != len(allow_tools)
            or any(
                name not in OPERATIONS
                or name.startswith("_")
                or (profile == "readonly" and OPERATIONS[name].kind != "READ")
                for name in allow_tools
            )
        ):
            raise ValueError(
                "INVALID_ARGUMENT: allow-tools requires unique canonical names permitted by profile"
            )
        self.output_limit = output_limit
        self.timeout = timeout
        self.artifact_timeout = artifact_timeout
        self.upgrade_timeout = upgrade_timeout
        self.artifact_limit = artifact_limit
        self.root_limit = root_limit
        self._mutation_lock = asyncio.Lock()
        self._deadline: ContextVar[float | None] = ContextVar("talos_call_deadline", default=None)
        self._active: set[asyncio.subprocess.Process] = set()
        self._stop_tasks: dict[asyncio.subprocess.Process, asyncio.Task[None]] = {}
        self.talosctl_path = self._resolve_binary(talosctl)
        self.config_path, self.config, self.current_context = self._load_config(
            config_path, context
        )
        self.artifact_root = self._resolve_artifact_root(artifact_root)

    @staticmethod
    def _load_config(
        config_path: str | None, context: str | None
    ) -> tuple[str | None, dict[str, Any] | None, str | None]:
        """Resolve and parse only the selected Talos context at startup."""
        selected = config_path if config_path is not None else os.environ.get("TALOSCONFIG")
        try:
            path = str(Path(selected).expanduser().resolve(strict=True)) if selected else None
        except (OSError, RuntimeError):
            raise ValueError("CONFIG_INVALID: selected talosconfig does not exist") from None
        if path:
            config_file = Path(path)
            if not config_file.is_file():
                raise ValueError("CONFIG_INVALID: talosconfig is not a regular file")
            try:
                parsed = yaml.safe_load(config_file.read_text())
            except (yaml.YAMLError, UnicodeError, OSError):
                raise ValueError("CONFIG_INVALID: talosconfig could not be parsed") from None
            if not isinstance(parsed, dict) or not isinstance(parsed.get("contexts"), dict):
                raise ValueError("CONFIG_INVALID: talosconfig has no contexts")
            selected_context = context or parsed.get("context")
            if not isinstance(selected_context, str) or selected_context not in parsed["contexts"]:
                raise ValueError("CONFIG_INVALID: selected context does not exist")
            return path, parsed, selected_context
        if context is not None:
            raise ValueError("CONFIG_INVALID: context requires talosconfig")
        return None, None, None

    @staticmethod
    def _resolve_artifact_root(artifact_root: str | None) -> Path | None:
        """Check ownership and privacy of an operator-selected artifact root."""
        if artifact_root:
            raw_root = Path(artifact_root).expanduser().absolute()
            if has_reparse_component(raw_root):
                raise ValueError("ARTIFACT_ROOT_INVALID: reparse point in root path")
            try:
                root = raw_root.resolve(strict=True)
            except (OSError, RuntimeError):
                raise ValueError("ARTIFACT_ROOT_INVALID: root does not exist") from None
        else:
            return None
        if not root.is_dir():
            raise ValueError("ARTIFACT_ROOT_INVALID: root is not a directory")
        if os.name == "posix":
            root_info = root.stat()
            if root_info.st_uid != os.geteuid():
                raise ValueError("ARTIFACT_ROOT_INVALID: root must belong to this account")
            if root_info.st_mode & 0o077:
                raise ValueError("ARTIFACT_ROOT_INVALID: root must be private")
        if os.name == "nt" and not windows_private_acl(root):
            raise ValueError("ARTIFACT_ROOT_INVALID: Windows ACL is not private")
        return root

    @staticmethod
    def _resolve_binary(value: str | None) -> str | None:
        if value is None:
            found = shutil.which("talosctl")
            return str(Path(found).resolve(strict=True)) if found else None
        try:
            path = Path(value).expanduser().resolve(strict=True)
        except (OSError, RuntimeError):
            raise ValueError("TALOSCTL_INVALID: binary does not exist") from None
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError("TALOSCTL_INVALID: binary is not executable")
        return str(path)

    def enabled(self, name: str) -> bool:
        """Return whether a canonical tool may be exposed and called."""
        operation = OPERATIONS.get(name)
        return bool(
            operation
            and (name.startswith("_") or self.profile == "write" or operation.kind == "READ")
            and (name.startswith("_") or self.allow_tools is None or name in self.allow_tools)
        )

    @contextmanager
    def call_budget(self, name: str) -> Iterator[None]:
        """Share one monotonic budget across a public call and its native preflights."""
        if self._deadline.get() is not None:
            yield
            return
        operation = OPERATIONS.get(ALIASES.get(name, name))
        limit = (
            self.upgrade_timeout
            if name == "talos_upgrade"
            else (
                self.artifact_timeout
                if operation and operation.kind == "LOCAL_ARTIFACT"
                else self.timeout
            )
        )
        token = self._deadline.set(time.monotonic() + limit)
        try:
            yield
        finally:
            self._deadline.reset(token)

    def _remaining(self) -> float:
        expiry = self._deadline.get()
        return max(0.0, expiry - time.monotonic()) if expiry is not None else self.timeout

    def check_operation(self, name: str, args: list[str]) -> None:
        """Enforce a canonical operation before every subprocess spawn."""
        canonical = ALIASES.get(name, name)
        if not self.enabled(canonical):
            raise TalosExecutionError("TOOL_NOT_ENABLED")
        try:
            operation = validate_argv(canonical, args)
        except ValueError as exc:
            raise TalosExecutionError("INVALID_ARGUMENT") from exc
        form = next(form for form in FORMS[canonical] if _matches(form, args))
        for expected, actual in zip(form, args, strict=True):
            if expected == "@input":
                if self.artifact_root is None:
                    raise TalosExecutionError("ARTIFACT_ROOT_REQUIRED")
                try:
                    relative = Path(actual).relative_to(self.artifact_root)
                    self.artifact_input(str(relative))
                except (ValueError, OSError) as exc:
                    raise TalosExecutionError("INVALID_ARGUMENT") from exc
            elif expected == "@output":
                if self.artifact_root is None or self.profile != "write":
                    raise TalosExecutionError("ARTIFACT_ROOT_REQUIRED")
                path = Path(actual)
                if not path.is_absolute() or not path.resolve().is_relative_to(self.artifact_root):
                    raise TalosExecutionError("INVALID_ARGUMENT")
                parent = path if canonical == "talos_gen_config" else path.parent
                if (
                    parent.parent != self.artifact_root
                    or not parent.name.startswith("talos-mcp-")
                    or not parent.is_dir()
                    or parent.is_symlink()
                ):
                    raise TalosExecutionError("INVALID_ARGUMENT")
                if canonical != "talos_gen_config" and path.exists():
                    raise TalosExecutionError("INVALID_ARGUMENT")
        if (
            operation.authenticated
            and not self.config_path
            and not (canonical == "talos_version" and "--client" in args)
            and not (canonical == "talos_apply_config" and "--insecure" in args)
        ):
            raise TalosExecutionError("CONFIG_REQUIRED")

    @staticmethod
    def _version_minor(output: str) -> tuple[str, str]:
        """Read either native short or full Client section and the Server Tag."""
        sections = re.search(r"(?ms)^Client:\s*\n(.*?)^Server:\s*\n(.*)$", output)
        if not sections:
            raise TalosExecutionError("UNSUPPORTED_VERSION")
        client = re.search(r"(?m)^(?:Talos\s+|\s*Tag:\s*)v(1\.\d+)\.\d+\s*$", sections.group(1))
        server = re.search(r"(?m)^\s*Tag:\s*v(1\.\d+)\.\d+\s*$", sections.group(2))
        if not client or not server:
            raise TalosExecutionError("UNSUPPORTED_VERSION")
        return client.group(1), server.group(1)

    async def client_minor(self) -> str:
        """Read the pinned binary's minor without using cluster credentials."""
        readback = await self.execute_talosctl(
            ["version", "--client", "--short"], operation="_client_version"
        )
        match = re.search(r"(?m)^Talos v(1\.\d+)\.\d+\s*$", readback["stdout"])
        if not match:
            raise TalosExecutionError("UNSUPPORTED_VERSION")
        return match.group(1)

    def get_context_info(self) -> dict[str, Any]:
        """Return sanitized context metadata without certificates or endpoints."""
        return {"context": self.current_context, "configured": self.config is not None}

    @staticmethod
    def _tree_size(root: Path) -> int:
        """Count live regular files, tolerating only concurrent deletion races."""

        def on_error(error: OSError) -> None:
            if not isinstance(error, FileNotFoundError):
                raise error

        total = 0
        for directory, _, names in os.walk(root, followlinks=False, onerror=on_error):
            for name in names:
                try:
                    info = (Path(directory) / name).lstat()
                except FileNotFoundError:
                    continue
                if stat.S_ISREG(info.st_mode):
                    total += info.st_size
        return total

    def artifact_input(self, relative: str) -> Path:
        """Resolve a reviewed regular input without traversal or symlinks."""
        if self.artifact_root is None:
            raise TalosExecutionError("ARTIFACT_ROOT_REQUIRED")
        candidate = Path(relative)
        if (
            candidate.is_absolute()
            or not candidate.parts
            or any(part in {"..", "."} for part in candidate.parts)
        ):
            raise TalosExecutionError("INVALID_ARGUMENT")
        current = self.artifact_root
        for part in candidate.parts:
            current = current / part
            if current.is_symlink():
                raise TalosExecutionError("INVALID_ARGUMENT")
        if not current.is_file() or not current.resolve().is_relative_to(self.artifact_root):
            raise TalosExecutionError("INVALID_ARGUMENT")
        if os.name == "nt" and not windows_private_acl(current):
            raise TalosExecutionError("ARTIFACT_INVALID")
        if (
            current.stat().st_size > self.artifact_limit
            or self._tree_size(self.artifact_root) > self.root_limit
        ):
            raise TalosExecutionError("ARTIFACT_QUOTA")
        return current

    def new_artifact_dir(self) -> Path:
        """Create a unique private output directory owned by this invocation."""
        if self.artifact_root is None:
            raise TalosExecutionError("ARTIFACT_ROOT_REQUIRED")
        if self.profile != "write":
            raise TalosExecutionError("TOOL_NOT_ENABLED")
        used = self._tree_size(self.artifact_root)
        if used >= self.root_limit:
            raise TalosExecutionError("ARTIFACT_QUOTA")
        directory = Path(tempfile.mkdtemp(prefix="talos-mcp-", dir=self.artifact_root))
        if os.name == "posix":
            directory.chmod(0o700)
        elif os.name == "nt" and not windows_private_acl(directory):
            directory.rmdir()
            raise TalosExecutionError("ARTIFACT_ROOT_INVALID")
        return directory

    def artifact_metadata(self, path: Path) -> dict[str, Any]:
        """Report only path, size, digest, and locality for a completed artifact."""
        if (
            self.artifact_root is None
            or not path.is_file()
            or path.is_symlink()
            or not path.resolve().is_relative_to(self.artifact_root)
        ):
            raise TalosExecutionError("ARTIFACT_INVALID")
        if os.name == "nt" and not windows_private_acl(path):
            raise TalosExecutionError("ARTIFACT_INVALID")
        size = path.stat().st_size
        call_size = self._tree_size(path.parent)
        root_size = self._tree_size(self.artifact_root)
        if call_size > self.artifact_limit or root_size > self.root_limit:
            raise TalosExecutionError("ARTIFACT_QUOTA")
        if os.name == "posix":
            path.chmod(0o600)
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return {"path": str(path), "size": size, "sha256": digest.hexdigest(), "locality": "server"}

    def get_nodes(self) -> list[str]:
        """Return nodes from the startup snapshot of the selected context."""
        if not self.config or not self.current_context:
            return []
        context = self.config["contexts"][self.current_context]
        if not isinstance(context, dict):
            return []
        nodes = context.get("nodes") or context.get("endpoints") or []
        if not isinstance(nodes, list):
            return []
        return [value for value in nodes if isinstance(value, str)]

    async def health_check(self) -> dict[str, Any]:
        """Check the configured cluster without leaking raw errors."""
        if not self.config:
            return {"healthy": False, "error": "No Talos configuration loaded"}
        try:
            nodes = self.get_nodes()
            if not nodes:
                return {"healthy": False, "error": "No Talos nodes configured"}
            result = await self.execute_talosctl(
                ["version", "-n", nodes[0], "--short"], operation="_preflight_version"
            )
            return {"healthy": True, "version": result["stdout"].splitlines()[0][:100]}
        except TalosExecutionError as exc:
            return {"healthy": False, "error": exc.code, "code": exc.code}

    async def close(self) -> None:
        """Stop all server-owned direct children on EOF or server shutdown."""
        with anyio.CancelScope(shield=True):
            await asyncio.gather(*(self._stop(child) for child in tuple(self._active)))

    async def _stop(self, child: asyncio.subprocess.Process) -> None:
        """Await one shared termination task even when EOF and call cleanup race."""
        if child not in self._active:
            return
        task = self._stop_tasks.get(child)
        if task is None:
            task = asyncio.create_task(self._terminate(child))
            self._stop_tasks[child] = task
        await asyncio.shield(task)

    async def _terminate(self, child: asyncio.subprocess.Process) -> None:
        """Terminate and reap a direct child without signalling reused group IDs."""
        # A paused full pipe can keep asyncio's process wait pending after exit.
        # No caller needs further output once termination has begun.
        for fd in (1, 2):
            pipe_transport = cast("Any", child)._transport.get_pipe_transport(fd)
            if pipe_transport is not None:
                pipe_transport.close()
        if child.returncode is not None:
            await child.wait()
            return
        try:
            if os.name == "posix":
                os.killpg(child.pid, signal.SIGTERM)
            else:
                child.terminate()
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(child.wait(), 5)
        except asyncio.TimeoutError:
            if child.returncode is not None:
                return
            try:
                if os.name == "posix":
                    os.killpg(child.pid, signal.SIGKILL)
                else:
                    child.kill()
            except ProcessLookupError:
                pass
            await child.wait()

    async def execute_talosctl(
        self,
        args: list[str],
        *,
        operation: str | None = None,
        artifact_stdout: Path | None = None,
        target_version: str | None = None,
        observation_window: int | None = None,
    ) -> dict[str, Any]:
        """Execute one validated, bounded talosctl child with no retry."""
        if operation is None:
            raise TalosExecutionError("UNKNOWN_TOOL")
        with self.call_budget(operation):
            return await self._execute_talosctl(
                args,
                operation=operation,
                artifact_stdout=artifact_stdout,
                target_version=target_version,
                observation_window=observation_window,
            )

    # The approved lifecycle keeps one dispatch/cleanup boundary for every child.
    async def _execute_talosctl(  # noqa: PLR0912, PLR0915
        self,
        args: list[str],
        *,
        operation: str,
        artifact_stdout: Path | None,
        target_version: str | None,
        observation_window: int | None,
    ) -> dict[str, Any]:
        name = ALIASES.get(operation, operation)
        self.check_operation(name, args)
        if observation_window is not None and (
            name != "talos_events" or not 1 <= observation_window <= 30
        ):
            raise TalosExecutionError("INVALID_ARGUMENT")
        if name in {"talos_cat", "talos_cp"} and artifact_stdout is None:
            raise TalosExecutionError("ARTIFACT_ROOT_REQUIRED")
        if artifact_stdout is not None:
            if name not in {"talos_cat", "talos_cp"} or self.artifact_root is None:
                raise TalosExecutionError("INVALID_ARGUMENT")
            if (
                artifact_stdout.parent.parent != self.artifact_root
                or not artifact_stdout.parent.name.startswith("talos-mcp-")
                or artifact_stdout.exists()
                or artifact_stdout.parent.is_symlink()
            ):
                raise TalosExecutionError("INVALID_ARGUMENT")
        if not self.talosctl_path:
            raise TalosExecutionError("TALOSCTL_NOT_FOUND")
        spec = OPERATIONS[name]
        if self._remaining() <= 0:
            raise TalosExecutionError("TIMEOUT")
        form = next(form for form in FORMS[name] if _matches(form, args))
        output_paths = [
            Path(value) for kind, value in zip(form, args, strict=True) if kind == "@output"
        ]
        artifact_dir = (
            artifact_stdout.parent
            if artifact_stdout
            else (
                (output_paths[0] if name == "talos_gen_config" else output_paths[0].parent)
                if output_paths
                else None
            )
        )
        command = [self.talosctl_path, *args]
        if (
            spec.authenticated
            and self.config_path
            and not (name == "talos_version" and "--client" in args)
        ):
            command.extend(
                ["--talosconfig", self.config_path, "--context", self.current_context or ""]
            )
        env = os.environ.copy()
        env.pop("TALOSCONFIG", None)

        async def run() -> dict[str, Any]:  # noqa: PLR0912, PLR0915
            if self.audit_enabled:
                node_flag = "--nodes" if "--nodes" in args else "-n"
                node = args[args.index(node_flag) + 1] if node_flag in args else ""
                logger.bind(audit=True).info(
                    json.dumps(
                        {
                            "phase": "dispatch",
                            "tool": name,
                            "profile": self.profile,
                            "node": node,
                            "class": spec.kind,
                            "code": "DISPATCH",
                            "outcome": "pending",
                            "duration_ms": 0,
                            "exit_code": None,
                            "response_bytes": 0,
                        },
                        separators=(",", ":"),
                    )
                )
            spawn_options: dict[str, Any] = {"umask": 0o077} if os.name == "posix" else {}
            try:
                child = await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        *command,
                        stdin=asyncio.subprocess.DEVNULL,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env,
                        start_new_session=os.name == "posix",
                        **spawn_options,
                    ),
                    self._remaining(),
                )
            except asyncio.TimeoutError as exc:
                raise TalosExecutionError("TIMEOUT") from exc
            self._active.add(child)
            output = bytearray()
            errors = bytearray()
            captured = 0

            async def read(pipe: asyncio.StreamReader, target: bytearray) -> None:
                nonlocal captured
                sink = None
                if target is output and artifact_stdout is not None:
                    descriptor = os.open(
                        artifact_stdout,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                        0o600,
                    )
                    sink = os.fdopen(descriptor, "wb")
                try:
                    while chunk := await pipe.read(8192):
                        if sink:
                            if sink.tell() + len(chunk) > self.artifact_limit:
                                raise TalosExecutionError("ARTIFACT_QUOTA", truncated=True)
                            sink.write(chunk)
                        else:
                            captured += len(chunk)
                            if captured > self.output_limit:
                                raise TalosExecutionError(
                                    "OUTPUT_LIMIT",
                                    outcome="unknown" if spec.kind == "CLUSTER_WRITE" else "failed",
                                    truncated=True,
                                )
                            target.extend(chunk)
                finally:
                    if sink:
                        sink.close()

            if child.stdout is None or child.stderr is None:
                raise TalosExecutionError("INTERNAL_ERROR")
            readers = [
                asyncio.create_task(read(child.stdout, output)),
                asyncio.create_task(read(child.stderr, errors)),
            ]

            async def monitor() -> None:
                while child.returncode is None:
                    if artifact_dir:
                        size = self._tree_size(artifact_dir)
                        if size > self.artifact_limit:
                            raise TalosExecutionError("ARTIFACT_QUOTA", truncated=True)
                        if (
                            self.artifact_root
                            and self._tree_size(self.artifact_root) > self.root_limit
                        ):
                            raise TalosExecutionError("ARTIFACT_QUOTA", truncated=True)
                    await asyncio.sleep(0.05)

            watcher = asyncio.create_task(monitor()) if artifact_dir else None
            waiter = asyncio.create_task(child.wait())
            window_end = (
                time.monotonic() + observation_window if observation_window is not None else None
            )
            try:
                remaining = self._remaining()
                if observation_window is not None:
                    remaining = min(remaining, observation_window)
                await asyncio.wait_for(
                    asyncio.gather(*readers, waiter, *([watcher] if watcher else [])), remaining
                )
                code = child.returncode
                if code:
                    diagnostic = errors.decode("utf-8", "replace").lower()
                    if (
                        "permission denied" in diagnostic
                        or "permissiondenied" in diagnostic
                        or "forbidden" in diagnostic
                    ):
                        category = "PERMISSION_DENIED"
                    elif "x509" in diagnostic or "certificate" in diagnostic:
                        category = "TLS_ERROR"
                    elif "connection refused" in diagnostic or "no route to host" in diagnostic:
                        category = "CONNECTION_ERROR"
                    else:
                        category = "COMMAND_FAILED"
                    logger.warning("talosctl {} exited {} ({})", name, code, category)
                    if spec.kind == "CLUSTER_WRITE":
                        raise TalosExecutionError(
                            "OUTCOME_UNKNOWN", outcome="unknown", exit_code=code
                        )
                    raise TalosExecutionError(category, exit_code=code)
                return {
                    "stdout": output.decode("utf-8", "replace").strip(),
                    "stderr": errors.decode("utf-8", "replace").strip(),
                    "complete_window": False,
                }
            except asyncio.TimeoutError as exc:
                if window_end is not None and window_end <= (self._deadline.get() or 0):
                    return {
                        "stdout": output.decode("utf-8", "replace").strip(),
                        "stderr": errors.decode("utf-8", "replace").strip(),
                        "complete_window": True,
                    }
                raise TalosExecutionError(
                    "OUTCOME_UNKNOWN" if spec.kind == "CLUSTER_WRITE" else "TIMEOUT",
                    outcome="unknown" if spec.kind == "CLUSTER_WRITE" else "failed",
                ) from exc
            except asyncio.CancelledError:
                raise
            finally:
                interrupted = False
                with anyio.CancelScope(shield=True):
                    while True:
                        try:
                            await asyncio.shield(self._stop(child))
                            break
                        except asyncio.CancelledError:
                            interrupted = True
                    tasks = [*readers, waiter, *([watcher] if watcher else [])]
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await asyncio.sleep(0)
                    self._active.discard(child)
                    self._stop_tasks.pop(child, None)
                if interrupted:
                    raise asyncio.CancelledError

        if spec.kind == "CLUSTER_WRITE":
            try:
                await asyncio.wait_for(self._mutation_lock.acquire(), self._remaining())
            except asyncio.TimeoutError as exc:
                raise TalosExecutionError("TIMEOUT") from exc
            try:
                if name == "talos_apply_config" and "--insecure" in args:
                    readback = await self.execute_talosctl(
                        ["version", "--client", "--short"], operation="_client_version"
                    )
                    match = re.search(r"(?m)^Talos v(1\.(?:13|14))\.\d+\s*$", readback["stdout"])
                    target_match = re.fullmatch(r"v?(1\.(?:13|14))\.\d+", target_version or "")
                    if not match or not target_match or match.group(1) != target_match.group(1):
                        raise TalosExecutionError("UNSUPPORTED_VERSION")
                else:
                    node = args[args.index("-n") + 1]
                    readback = await self.execute_talosctl(
                        ["version", "-n", node, "--short"], operation="_preflight_version"
                    )
                    client_minor, node_minor = self._version_minor(readback["stdout"])
                    if client_minor not in {"1.13", "1.14"} or node_minor != client_minor:
                        raise TalosExecutionError("UNSUPPORTED_VERSION")
                    if name == "talos_upgrade":
                        target_match = re.fullmatch(r"v?(1\.(?:13|14))\.\d+", target_version or "")
                        if not target_match or (client_minor, target_match.group(1)) not in {
                            ("1.13", "1.13"),
                            ("1.13", "1.14"),
                            ("1.14", "1.14"),
                        }:
                            raise TalosExecutionError("UNSUPPORTED_VERSION")
                floor = (
                    self.upgrade_timeout * 0.9
                    if name == "talos_upgrade"
                    else min(5.0, self.timeout / 2)
                )
                if self._remaining() < floor:
                    raise TalosExecutionError("TIMEOUT")
                return await run()
            finally:
                self._mutation_lock.release()
        warning = ""
        if spec.authenticated and name not in {"talos_version", "_preflight_version"}:
            node_flag = "--nodes" if "--nodes" in args else "-n"
            for node in args[args.index(node_flag) + 1].split(","):
                readback = await self.execute_talosctl(
                    ["version", "-n", node, "--short"], operation="_preflight_version"
                )
                client_minor, node_minor = self._version_minor(readback["stdout"])
                if node_minor == "1.12":
                    if name not in {"talos_health", "talos_get"}:
                        raise TalosExecutionError("UNSUPPORTED_VERSION")
                elif node_minor not in {"1.13", "1.14"}:
                    raise TalosExecutionError("UNSUPPORTED_VERSION")
                if spec.kind != "READ" and client_minor != node_minor:
                    raise TalosExecutionError("UNSUPPORTED_VERSION")
                if client_minor != node_minor:
                    warning = (
                        f"Version skew: client {client_minor}, node {node_minor}; diagnostic only"
                    )
        result = await run()
        if name == "talos_version" and "--client" not in args:
            try:
                client_minor, node_minor = self._version_minor(result["stdout"])
                if client_minor != node_minor:
                    warning = (
                        f"Version skew: client {client_minor}, node {node_minor}; diagnostic only"
                    )
            except TalosExecutionError:
                pass
        if warning:
            result["warning"] = warning
        return result

"""Canonical operation policy applied before every talosctl spawn."""

import base64
import binascii
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Operation:
    """Execution class and native command prefix for one public tool."""

    kind: str
    prefix: tuple[str, ...]
    authenticated: bool = True


# This table is the code-owned boundary; tool flags and caller-supplied labels confer no rights.
OPERATIONS: dict[str, Operation] = {
    "_preflight_version": Operation("READ", ("version",)),
    "_client_version": Operation("READ", ("version",), False),
    "talos_version": Operation("READ", ("version",)),
    "talos_health": Operation("READ", ("health",)),
    "talos_stats": Operation("READ", ("stats",)),
    "talos_containers": Operation("READ", ("containers",)),
    "talos_processes": Operation("READ", ("processes",)),
    "talos_memory": Operation("READ", ("memory",)),
    "talos_time": Operation("READ", ("time",)),
    "talos_disks": Operation("READ", ("get", "disks")),
    "talos_devices": Operation("READ", ("get", "devices")),
    "talos_ls": Operation("READ", ("ls",)),
    "talos_du": Operation("READ", ("usage",)),
    "talos_mounts": Operation("READ", ("mounts",)),
    "talos_interfaces": Operation("READ", ("get", "addresses")),
    "talos_routes": Operation("READ", ("get", "routes")),
    "talos_netstat": Operation("READ", ("netstat",)),
    "talos_service": Operation("READ", ("service",)),
    "talos_logs": Operation("READ", ("logs",)),
    "talos_dmesg": Operation("READ", ("dmesg",)),
    "talos_events": Operation("READ", ("events",)),
    "talos_etcd_members": Operation("READ", ("etcd", "members")),
    "talos_etcd_alarm": Operation("READ", ("etcd", "alarm", "list")),
    "talos_get": Operation("READ", ("get",)),
    "talos_definitions": Operation("READ", ("get", "rd")),
    "talos_volume_status": Operation("READ", ("get", "volumestatus")),
    "talos_kernel_param_status": Operation("READ", ("get", "kernelparamstatus")),
    "talos_cgroups": Operation("READ", ("cgroups",)),
    "talos_config_info": Operation("READ", (), False),
    "talos_validate_config": Operation("READ", ("validate",), False),
    "talos_cat": Operation("SENSITIVE_READ", ("read",)),
    "talos_cp": Operation("LOCAL_ARTIFACT", ("cp",)),
    "talos_kubeconfig": Operation("LOCAL_ARTIFACT", ("kubeconfig",)),
    "talos_etcd_snapshot": Operation("LOCAL_ARTIFACT", ("etcd", "snapshot")),
    "talos_support": Operation("LOCAL_ARTIFACT", ("support",)),
    "talos_gen_config": Operation("LOCAL_ARTIFACT", ("gen", "config"), False),
    "talos_service_action": Operation("CLUSTER_WRITE", ("service",)),
    "talos_image": Operation("READ", ("image", "list")),
    "talos_image_pull": Operation("CLUSTER_WRITE", ("image", "pull")),
    "talos_etcd_alarm_disarm": Operation("CLUSTER_WRITE", ("etcd", "alarm", "disarm")),
    "talos_etcd_defrag": Operation("CLUSTER_WRITE", ("etcd", "defrag")),
    "talos_apply_config": Operation("CLUSTER_WRITE", ("apply-config",)),
    "talos_machineconfig_patch": Operation("CLUSTER_WRITE", ("patch", "machineconfig")),
    "talos_bootstrap": Operation("CLUSTER_WRITE", ("bootstrap",)),
    "talos_reboot": Operation("CLUSTER_WRITE", ("reboot",)),
    "talos_shutdown": Operation("CLUSTER_WRITE", ("shutdown",)),
    "talos_reset": Operation("CLUSTER_WRITE", ("reset",)),
    "talos_upgrade": Operation("CLUSTER_WRITE", ("upgrade",)),
}

ALIASES = {"talos_apply": "talos_apply_config", "talos_patch": "talos_machineconfig_patch"}
UNSUPPORTED = {"talos_volumes", "talos_pcap", "talos_dashboard", "talos_cluster_show"}


FORMS: dict[str, tuple[tuple[str, ...], ...]] = {
    "_preflight_version": (("version", "-n", "@node", "--short"),),
    "_client_version": (("version", "--client", "--short"),),
    "talos_version": (("version", "-n", "@nodes"), ("version", "--client")),
    "talos_health": (("health", "-n", "@node", "--wait-timeout", "@duration"),),
    "talos_stats": (("stats", "-n", "@nodes"),),
    "talos_containers": (("containers", "-n", "@nodes"),),
    "talos_processes": (("processes", "-n", "@nodes"),),
    "talos_memory": (("memory", "-n", "@nodes"),),
    "talos_time": (("time", "-n", "@nodes"),),
    "talos_disks": (("get", "disks", "-n", "@nodes"),),
    "talos_devices": (("get", "devices", "-n", "@nodes"),),
    "talos_ls": (("ls", "@path", "-n", "@nodes"),),
    "talos_du": (("usage", "@path", "-n", "@nodes"),),
    "talos_mounts": (("mounts", "-n", "@nodes"),),
    "talos_interfaces": (("get", "addresses", "-n", "@nodes"),),
    "talos_routes": (("get", "routes", "-n", "@nodes"),),
    "talos_netstat": (("netstat", "-n", "@nodes"),),
    "talos_service": (("service", "-n", "@nodes"), ("service", "@text", "-n", "@nodes")),
    "talos_service_action": (
        ("service", "@text", "start", "-n", "@node"),
        ("service", "@text", "stop", "-n", "@node"),
        ("service", "@text", "restart", "-n", "@node"),
    ),
    "talos_logs": (("logs", "@text", "-n", "@nodes", "--tail", "@int"),),
    "talos_dmesg": (("dmesg", "-n", "@nodes", "--follow=false"),),
    "talos_events": (
        ("events", "-n", "@nodes", "--tail", "@int"),
        ("events", "-n", "@nodes", "--duration", "@duration"),
    ),
    "talos_etcd_members": (("etcd", "members", "-n", "@node"),),
    "talos_etcd_alarm": (("etcd", "alarm", "list", "-n", "@node"),),
    "talos_etcd_alarm_disarm": (("etcd", "alarm", "disarm", "-n", "@node"),),
    "talos_etcd_defrag": (("etcd", "defrag", "-n", "@node"),),
    "talos_get": (
        ("get", "machinestatus", "--namespace", "runtime", "-n", "@nodes", "-o", "@format"),
        ("get", "volumestatus", "--namespace", "runtime", "-n", "@nodes", "-o", "@format"),
    ),
    "talos_definitions": (("get", "rd", "-n", "@nodes"),),
    "talos_volume_status": (
        ("get", "volumestatus", "-n", "@nodes", "-o", "@format"),
        ("get", "volumestatus", "@text", "-n", "@nodes", "-o", "@format"),
    ),
    "talos_kernel_param_status": (("get", "kernelparamstatus", "-n", "@nodes", "-o", "@format"),),
    "talos_cgroups": (("cgroups", "--nodes", "@nodes", "--preset", "@cgroups_preset"),),
    "talos_validate_config": (
        ("validate", "-c", "@input", "--mode", "@validate_mode"),
        ("validate", "-c", "@input", "--mode", "@validate_mode", "--strict"),
    ),
    "talos_cat": (("read", "@path", "-n", "@node"),),
    "talos_cp": (("cp", "@path", "-", "-n", "@node"),),
    "talos_kubeconfig": (("kubeconfig", "@output", "--merge=false", "-n", "@node"),),
    "talos_etcd_snapshot": (("etcd", "snapshot", "@output", "-n", "@node"),),
    "talos_support": (
        ("support", "--output", "@output", "-n", "@node", "--no-encryption"),
        ("support", "--output", "@output", "-n", "@node"),
        (
            "support",
            "--output",
            "@output",
            "-n",
            "@node",
            "--encryption-no-default-recipients",
            "--encryption-recipients",
            "@text",
        ),
    ),
    "talos_gen_config": (
        ("gen", "config", "@text", "@endpoint", "--output", "@output"),
        (
            "gen",
            "config",
            "@text",
            "@endpoint",
            "--output",
            "@output",
            "--kubernetes-version",
            "@version",
        ),
    ),
    "talos_image": (("image", "list", "--namespace", "@namespace", "-n", "@node"),),
    "talos_image_pull": (("image", "pull", "@text", "--namespace", "@namespace", "-n", "@node"),),
    "talos_apply_config": (
        ("apply-config", "-f", "@input", "-n", "@node", "--mode", "@mode"),
        (
            "apply-config",
            "-f",
            "@input",
            "-n",
            "@node",
            "--mode",
            "@mode",
            "--insecure",
            "--cert-fingerprint",
            "@fingerprint",
        ),
    ),
    "talos_machineconfig_patch": (
        ("patch", "machineconfig", "--patch-file", "@input", "-n", "@node", "--mode", "@mode"),
    ),
    "talos_bootstrap": (("bootstrap", "-n", "@node"),),
    "talos_reboot": (("reboot", "-n", "@node", "--wait=false"),),
    "talos_shutdown": (("shutdown", "-n", "@node", "--wait=false"),),
    "talos_reset": (
        (
            "reset",
            "-n",
            "@node",
            "--system-labels-to-wipe",
            "@labels",
            "--graceful=true",
            "--reboot=true",
            "--wait=false",
        ),
    ),
    "talos_upgrade": (
        ("upgrade", "-n", "@node", "--image", "@digest_image", "--wait=true", "--drain=true"),
    ),
}
FORMS["talos_support"] += tuple(
    ("support", "--output", "@output", "-n", "@node", "--encryption-no-default-recipients")
    + ("--encryption-recipients", "@text") * count
    for count in range(2, 17)
)


def _matches(pattern: tuple[str, ...], args: list[str]) -> bool:
    return len(pattern) == len(args) and all(
        _valid_arg(expected, actual) for expected, actual in zip(pattern, args, strict=True)
    )


def _valid_arg(expected: str, actual: str) -> bool:
    if not isinstance(actual, str) or not actual or any(c in actual for c in "\x00\n\r"):
        return False
    if not expected.startswith("@"):
        return expected == actual
    return not actual.startswith("-") and _valid_placeholder(expected[1:], actual)


def _valid_placeholder(kind: str, actual: str) -> bool:
    choices = {
        "format": {"yaml", "json"},
        "validate_mode": {"metal", "cloud", "container"},
        "namespace": {"system", "cri", "inmem", "taloscontainers"},
        "cgroups_preset": {"cpu", "cpuset", "io", "memory", "process", "psi", "swap"},
        "mode": {"auto", "no-reboot", "staged", "try"},
    }
    valid = True
    if kind in choices:
        valid = actual in choices[kind]
    elif kind == "node":
        valid = actual.lower() not in {"all", "cluster", "default"} and "," not in actual
    elif kind == "nodes":
        valid = all(node and not node.startswith("-") for node in actual.split(","))
    elif kind == "int":
        valid = actual.isdecimal() and int(actual) >= 1
    elif kind == "duration":
        valid = re.fullmatch(r"(?:[1-9]\d{0,3})s", actual) is not None
    elif kind == "labels":
        valid = set(actual.split(",")).issubset({"STATE", "EPHEMERAL"})
    elif kind == "fingerprint":
        try:
            valid = len(base64.b64decode(actual, validate=True)) == 32
        except (ValueError, binascii.Error):
            valid = False
    elif kind == "digest_image":
        valid = re.fullmatch(r"[^\s@]+@sha256:[a-fA-F0-9]{64}", actual) is not None
    elif kind == "endpoint":
        valid = re.fullmatch(r"https://[^\s/]+(?::\d+)?", actual) is not None
    return valid


def validate_argv(name: str, args: list[str]) -> Operation:
    """Reject every argv outside an operation's complete native command forms."""
    operation = OPERATIONS.get(name)
    if operation is None or tuple(args[: len(operation.prefix)]) != operation.prefix:
        raise ValueError("INVALID_ARGUMENT: operation/argv mismatch")
    if name not in FORMS or not any(_matches(form, args) for form in FORMS[name]):
        raise ValueError("INVALID_ARGUMENT: native argv outside operation contract")
    if name == "talos_logs" and int(args[args.index("--tail") + 1]) > 2000:
        raise ValueError("INVALID_ARGUMENT: logs tail exceeds cap")
    if name == "talos_events":
        if "--tail" in args and int(args[args.index("--tail") + 1]) > 500:
            raise ValueError("INVALID_ARGUMENT: events tail exceeds cap")
        if "--duration" in args and int(args[args.index("--duration") + 1][:-1]) > 3600:
            raise ValueError("INVALID_ARGUMENT: events history exceeds cap")
    return operation

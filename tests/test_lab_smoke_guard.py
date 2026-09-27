"""The lab runner must reject a target without exact disposable ownership."""

import json
import subprocess
import sys
from pathlib import Path


def test_lab_runner_rejects_unconfirmed_node(tmp_path: Path) -> None:
    manifest = tmp_path / "lab.json"
    manifest.write_text(json.dumps({"disposable": True, "owner": "fixture", "node": "lab-node"}))
    runner = Path(__file__).resolve().parents[1] / "scripts/lab_smoke.py"
    result = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--manifest",
            str(manifest),
            "--confirm-disposable",
            "other-node",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0
    assert "confirmation does not match disposable node" in result.stderr


def test_lab_runner_requires_explicit_context(tmp_path: Path) -> None:
    """A selected talosconfig cannot silently choose its default context."""
    manifest = tmp_path / "lab.json"
    manifest.write_text(json.dumps({"disposable": True, "owner": "fixture", "node": "lab-node"}))
    runner = Path(__file__).resolve().parents[1] / "scripts/lab_smoke.py"
    result = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--manifest",
            str(manifest),
            "--confirm-disposable",
            "lab-node",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0
    assert "manifest requires an explicit context" in result.stderr


def test_lab_runner_rejects_mutating_readback(tmp_path: Path) -> None:
    """A mistaken manifest must not dispatch a second write as a readback."""
    for name in ("server", "talosctl", "talosconfig", "artifact_root"):
        (tmp_path / name).touch()
    manifest = tmp_path / "lab.json"
    manifest.write_text(
        json.dumps(
            {
                "disposable": True,
                "owner": "fixture",
                "node": "lab-node",
                "context": "disposable-lab",
                **{
                    name: str(tmp_path / name)
                    for name in ("server", "talosctl", "talosconfig", "artifact_root")
                },
                "operation": {"tool": "talos_reboot", "arguments": {"node": "lab-node"}},
                "readback": {"tool": "talos_reset", "arguments": {"node": "lab-node"}},
            }
        )
    )
    runner = Path(__file__).resolve().parents[1] / "scripts/lab_smoke.py"
    result = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--manifest",
            str(manifest),
            "--confirm-disposable",
            "lab-node",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0
    assert "readback must be a read tool" in result.stderr

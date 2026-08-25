from __future__ import annotations

import shlex
import subprocess
from pathlib import Path


class AdapterError(RuntimeError):
    pass


def _base_command(configured: str | None, name: str) -> list[str]:
    if not configured:
        raise AdapterError(f"{name} is not configured")
    command = shlex.split(configured)
    if not command:
        raise AdapterError(f"{name} command is empty")
    return command


def run_lucida(configured: str | None, source: Path, destination: Path) -> None:
    command = _base_command(configured, "Lucida")
    command.extend(["remove", str(source), "-o", str(destination), "--model", "lucida"])
    _run(command, "Lucida")


def run_ai_upscaler(configured: str | None, source: Path, destination: Path, scale: int) -> None:
    """Run InkLathe's narrow adapter protocol: COMMAND INPUT OUTPUT SCALE."""
    command = _base_command(configured, "AI upscaler")
    command.extend([str(source), str(destination), str(scale)])
    _run(command, "AI upscaler")


def _run(command: list[str], name: str) -> None:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=60 * 60, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AdapterError(f"{name} failed to start: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise AdapterError(f"{name} exited with {result.returncode}: {detail}")

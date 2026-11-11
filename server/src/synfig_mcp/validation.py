"""
Document validation against the real Synfig engine.

Every mutation performed by the MCP must produce a document that the *real*
Synfig binary can load without errors.  This module runs the ``synfig`` CLI
against a saved document and classifies the engine output so that tests and
the ``verify`` tooling can assert on it instead of trusting the writer.

It is intentionally dependency free (no Pillow / numpy) so it can be used
from the server, the CLI scripts and the test-suite alike.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from synfig_mcp.logging import get_logger

logger = get_logger("synfig_mcp.validation")

_ERROR_RE = re.compile(r"\berror:\s*(?P<message>.+)$", re.IGNORECASE)
_WARNING_RE = re.compile(r"\bwarning:\s*(?P<message>.+)$", re.IGNORECASE)
_LOAD_FAILURE_RE = re.compile(r"Unable to load file", re.IGNORECASE)
_MODULE_WARNING_RE = re.compile(r"Unable to find module", re.IGNORECASE)
_UNIT_WARNING_RE = re.compile(r"No unit provided in time code", re.IGNORECASE)


@dataclass(slots=True)
class ValidationResult:
    """Outcome of validating a document with the real Synfig engine."""

    valid: bool
    exit_code: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rendered: bool = False
    output_path: str | None = None

    def summary(self) -> str:
        if self.valid:
            return f"VALID (exit={self.exit_code}, rendered={self.rendered})"
        return f"INVALID (exit={self.exit_code}): " + "; ".join(self.errors[:5])


def find_synfig_binary() -> Path | None:
    """Locate a usable ``synfig`` CLI binary without importing the runner."""
    from synfig_mcp.config import settings

    if settings.synfig_cli_path and settings.synfig_cli_path.is_file():
        return settings.synfig_cli_path

    for name in ("synfig", "synfig.exe"):
        found = shutil.which(name)
        if found:
            return Path(found)

    candidates = [
        Path.cwd() / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfig.exe",
        Path("C:/Program Files/Synfig/bin/synfig.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _classify(stderr: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for raw_line in stderr.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _MODULE_WARNING_RE.search(line) or _UNIT_WARNING_RE.search(line):
            continue
        if _ERROR_RE.search(line) or _LOAD_FAILURE_RE.search(line):
            errors.append(line)
            continue
        if _WARNING_RE.search(line):
            warnings.append(line)
    return errors, warnings


async def validate_document(
    document_path: str | Path,
    *,
    binary: Path | None = None,
    timeout_seconds: float = 180.0,
    render: bool = True,
) -> ValidationResult:
    """
    Load ``document_path`` with the real Synfig engine and report errors.

    The document is loaded by asking Synfig to render a single frame, which
    exercises the full load path (canvas, layers, parameters, value nodes).
    """
    doc = Path(document_path)
    if not doc.is_file():
        return ValidationResult(valid=False, exit_code=-1, errors=[f"Missing file: {doc}"])

    exe = binary or find_synfig_binary()
    if exe is None or not exe.is_file():
        return ValidationResult(
            valid=False, exit_code=-2, errors=["Synfig CLI binary not available for validation"]
        )

    with tempfile.TemporaryDirectory(prefix="synfig_validate_") as tmp:
        out_path = Path(tmp) / "frame.png"
        cmd = [
            str(exe),
            "-q",
            str(doc),
            "-t",
            "png",
            "-o",
            str(out_path),
            "--time",
            "0s",
        ]
        env = dict(os.environ)
        # Avoid Synfig picking up a user renderer configuration that could
        # change the outcome of the validation.
        env.setdefault("SYNFIG_DISABLE_RENDERER", "1")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            return ValidationResult(
                valid=False,
                exit_code=-3,
                errors=[f"Synfig timed out after {timeout_seconds}s while validating {doc.name}"],
            )

        errors, warnings = _classify(stderr.decode("utf-8", errors="replace"))
        stdout_text = stdout.decode("utf-8", errors="replace")
        if stdout_text.strip():
            logger.debug("synfig validation stdout: %s", stdout_text.strip()[:500])

        rendered = out_path.is_file() and out_path.stat().st_size > 0
        exit_code = proc.returncode if proc.returncode is not None else -1
        valid = not errors and exit_code == 0 and (rendered or not render)

        return ValidationResult(
            valid=valid,
            exit_code=exit_code,
            errors=errors,
            warnings=warnings,
            rendered=rendered,
            output_path=str(out_path) if rendered else None,
        )


def validate_document_sync(
    document_path: str | Path,
    *,
    binary: Path | None = None,
    timeout_seconds: float = 180.0,
) -> ValidationResult:
    """Blocking convenience wrapper around :func:`validate_document`."""
    return asyncio.run(
        validate_document(document_path, binary=binary, timeout_seconds=timeout_seconds)
    )

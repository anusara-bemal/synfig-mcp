"""
Filesystem sandbox validator preventing directory traversal attacks.
"""

from pathlib import Path

from synfig_mcp.errors import SecuritySandboxError


def validate_path(target_path: Path, allowed_roots: list[Path]) -> Path:
    """
    Ensure target_path resolves inside one of the allowed_roots.
    Raises SecuritySandboxError if path attempts to escape.
    """
    resolved_target = target_path.resolve()
    for root in allowed_roots:
        resolved_root = root.resolve()
        if resolved_target == resolved_root or resolved_root in resolved_target.parents:
            return resolved_target

    raise SecuritySandboxError(f"Access to path '{target_path}' is denied by workspace sandbox")

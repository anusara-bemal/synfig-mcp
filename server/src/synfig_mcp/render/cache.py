"""
Disk-backed render cache keyed by document state and render parameters.
"""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from synfig_mcp.config import settings


class RenderCache:
    """Caches rendered frame and preview artifacts on disk."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is not None:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = settings.bridge_token_path.parent / "mcp_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def compute_key(self, doc_state: str, render_params: dict[str, Any]) -> str:
        """Generate deterministic SHA-256 hash representing document state and render parameters."""
        serialized_params = json.dumps(render_params, sort_keys=True, default=str)
        payload = f"{doc_state}::{serialized_params}".encode()
        return hashlib.sha256(payload).hexdigest()

    def get(self, key: str, ext: str = ".png") -> Path | None:
        """Lookup cached file by key."""
        target = self.cache_dir / f"{key}{ext}"
        if target.is_file() and target.stat().st_size > 0:
            return target
        return None

    def put(self, key: str, file_path: Path | str, ext: str = ".png") -> Path:
        """Store rendered artifact into the cache."""
        src = Path(file_path)
        dest = self.cache_dir / f"{key}{ext}"
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        return dest

    def clear(self) -> int:
        """Clear all cached artifacts."""
        count = 0
        for item in self.cache_dir.glob("*"):
            if item.is_file():
                item.unlink(missing_ok=True)
                count += 1
        return count

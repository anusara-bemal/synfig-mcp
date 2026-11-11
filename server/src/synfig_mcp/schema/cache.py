"""
Cache manager for introspected Synfig schemas.
"""

import json
import time
from pathlib import Path
from typing import Any


class SchemaCache:
    """Disk cache for introspected schemas to avoid repeated CLI spawning."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path.home() / ".synfig" / "mcp_cache"

    def save(self, key: str, data: dict[str, Any]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        target = self.cache_dir / f"{key}.json"
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, key: str) -> dict[str, Any] | None:
        target = self.cache_dir / f"{key}.json"
        if target.is_file():
            return json.loads(target.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
        return None

    def path_for(self, key: str) -> Path:
        """Return the on-disk location of a cache entry."""
        return self.cache_dir / f"{key}.json"

    def is_fresh(self, key: str, max_age_seconds: float = 7 * 24 * 3600) -> bool:
        """Check whether a cache entry exists and is younger than ``max_age_seconds``."""
        target = self.path_for(key)
        if not target.is_file():
            return False
        return (time.time() - target.stat().st_mtime) < max_age_seconds

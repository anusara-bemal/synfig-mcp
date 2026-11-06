"""
Cache manager for introspected Synfig schemas.
"""

import json
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

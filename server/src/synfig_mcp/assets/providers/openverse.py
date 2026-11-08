"""
Openverse API Provider Adapter (Phase A5).
Searches CC-licensed media via https://api.openverse.org/v1/images/.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from synfig_mcp.assets.models import AssetMetadata
from synfig_mcp.assets.providers.base import BaseAssetProvider
from synfig_mcp.assets.security.url_validator import validate_asset_url

OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"


class OpenverseAssetProvider(BaseAssetProvider):
    """Adapter for searching and retrieving open-licensed assets from Openverse."""

    @property
    def name(self) -> str:
        return "openverse"

    async def search(
        self,
        query: str,
        license_type: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> list[dict[str, Any]]:
        params = {
            "q": query,
            "page": str(page),
            "page_size": str(min(page_size, 20)),
        }
        if license_type:
            params["license"] = license_type.lower()

        url = f"{OPENVERSE_API_URL}?{urllib.parse.urlencode(params)}"
        validate_asset_url(url)

        req = urllib.request.Request(
            url, headers={"User-Agent": "SynfigMCP/0.8.0 (Studio-Grade Animation)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("results", []):
            results.append(
                {
                    "id": f"ov_{item.get('id', '')}",
                    "title": item.get("title", "Untitled"),
                    "creator": item.get("creator", "Unknown"),
                    "license": item.get("license", "unknown"),
                    "provider": self.name,
                    "filesize": item.get("filesize", 0),
                }
            )
        return results

    async def get_details(self, asset_id: str) -> AssetMetadata | None:
        clean_id = asset_id.replace("ov_", "")
        url = f"{OPENVERSE_API_URL}{clean_id}/"
        validate_asset_url(url)

        req = urllib.request.Request(
            url, headers={"User-Agent": "SynfigMCP/0.8.0 (Studio-Grade Animation)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

        return AssetMetadata(
            id=asset_id,
            provider=self.name,
            title=data.get("title", "Untitled"),
            creator=data.get("creator", "Unknown"),
            license_code=data.get("license", "unknown"),
            license_url=data.get("license_url", ""),
            attribution_text=data.get("attribution", ""),
            download_url=data.get("url", ""),
            thumbnail_url=data.get("thumbnail", None),
            filesize_bytes=data.get("filesize", 0),
            mature=bool(data.get("mature", False)),
        )

    async def fetch_preview(self, asset_id: str) -> bytes | None:
        meta = await self.get_details(asset_id)
        if not meta or not meta.thumbnail_url:
            return None

        validate_asset_url(meta.thumbnail_url)
        req = urllib.request.Request(meta.thumbnail_url, headers={"User-Agent": "SynfigMCP/0.8.0"})
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = resp.read()
                return bytes(data) if isinstance(data, (bytes, bytearray)) else None
        except Exception:
            return None

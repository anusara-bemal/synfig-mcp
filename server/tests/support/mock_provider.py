"""
Offline Mock Asset Provider: Serves deterministic licensed fixtures for air-gapped CI and testing.
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.assets.models import AssetMetadata
from synfig_mcp.assets.providers.base import BaseAssetProvider

# 1x1 valid PNG bytes
MOCK_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf"
    b"\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
)

MOCK_FIXTURES: dict[str, dict[str, Any]] = {
    "mock_cloud_01": {
        "id": "mock_cloud_01",
        "provider": "mock",
        "title": "Stylized Vector Cloud",
        "creator": "OpenArtist",
        "license_code": "cc0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution_text": "Stylized Vector Cloud by OpenArtist is dedicated to the public domain via CC0 1.0.",
        "download_url": "https://raw.githubusercontent.com/synfig/assets/cloud.png",
        "thumbnail_url": "https://raw.githubusercontent.com/synfig/assets/cloud_thumb.png",
        "filesize_bytes": len(MOCK_PNG_BYTES),
        "mature": False,
    },
    "mock_tree_02": {
        "id": "mock_tree_02",
        "provider": "mock",
        "title": "Silhouette Pine Tree",
        "creator": "CommonsUser",
        "license_code": "by",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution_text": "Silhouette Pine Tree by CommonsUser, used under CC BY 4.0.",
        "download_url": "https://raw.githubusercontent.com/synfig/assets/tree.png",
        "thumbnail_url": "https://raw.githubusercontent.com/synfig/assets/tree_thumb.png",
        "filesize_bytes": len(MOCK_PNG_BYTES),
        "mature": False,
    },
    "mock_nd_restricted": {
        "id": "mock_nd_restricted",
        "provider": "mock",
        "title": "Restricted Photo",
        "creator": "StrictPhotographer",
        "license_code": "by-nd",
        "license_url": "https://creativecommons.org/licenses/by-nd/4.0/",
        "attribution_text": "Restricted Photo by StrictPhotographer (CC BY-ND 4.0)",
        "download_url": "https://raw.githubusercontent.com/synfig/assets/photo.png",
        "filesize_bytes": len(MOCK_PNG_BYTES),
        "mature": False,
    },
}


class MockAssetProvider(BaseAssetProvider):
    """In-memory fixture provider for testing license filtering and pipeline execution."""

    @property
    def name(self) -> str:
        return "mock"

    async def search(
        self,
        query: str,
        license_type: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> list[dict[str, Any]]:
        del page, page_size
        results: list[dict[str, Any]] = []
        q = query.lower()

        for f in MOCK_FIXTURES.values():
            if q in f["title"].lower() or q in f["id"].lower():
                if license_type and f["license_code"] != license_type.lower():
                    continue
                results.append(
                    {
                        "id": f["id"],
                        "title": f["title"],
                        "creator": f["creator"],
                        "license": f["license_code"],
                        "provider": self.name,
                    }
                )
        return results

    async def get_details(self, asset_id: str) -> AssetMetadata | None:
        raw = MOCK_FIXTURES.get(asset_id)
        if not raw:
            return None
        return AssetMetadata(**raw)

    async def fetch_preview(self, asset_id: str) -> bytes | None:
        if asset_id in MOCK_FIXTURES:
            return MOCK_PNG_BYTES
        return None

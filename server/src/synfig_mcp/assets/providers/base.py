"""
Abstract base class for Asset Provider adapters (Phase A5).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from synfig_mcp.assets.models import AssetMetadata


class BaseAssetProvider(ABC):
    """Abstract interface for external media and asset providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    async def search(
        self,
        query: str,
        license_type: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> list[dict[str, Any]]:
        """Search provider for media assets, returning compact text descriptors."""

    @abstractmethod
    async def get_details(self, asset_id: str) -> AssetMetadata | None:
        """Fetch complete licensing and provenance details for an asset."""

    @abstractmethod
    async def fetch_preview(self, asset_id: str) -> bytes | None:
        """Fetch small thumbnail image bytes for LLM preview."""

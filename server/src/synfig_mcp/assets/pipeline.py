"""
Asset Pipeline: Manages downloading, hardened sanitization, cryptographic hashing,
manifest recording, and attribution generation (Phase A5).
"""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

from synfig_mcp.assets.models import AssetManifest, AssetMetadata, LicensePolicy
from synfig_mcp.assets.providers.base import BaseAssetProvider
from synfig_mcp.assets.providers.mock_provider import MockAssetProvider
from synfig_mcp.assets.providers.openverse import OpenverseAssetProvider
from synfig_mcp.assets.security.raster_hardening import harden_raster_image
from synfig_mcp.assets.security.svg_sanitizer import sanitize_svg
from synfig_mcp.assets.security.url_validator import validate_asset_url
from synfig_mcp.security.sandbox import get_default_allowed_roots


class AssetPipeline:
    """Orchestrator for the licensed internet asset pipeline."""

    def __init__(
        self,
        policy: LicensePolicy | None = None,
        providers: list[BaseAssetProvider] | None = None,
    ) -> None:
        self.policy = policy or LicensePolicy()
        self.providers: dict[str, BaseAssetProvider] = {
            "openverse": OpenverseAssetProvider(),
            "mock": MockAssetProvider(),
        }
        if providers:
            for p in providers:
                self.providers[p.name] = p

    def get_provider(self, name: str) -> BaseAssetProvider:
        """Resolve asset provider, falling back to mock provider for offline resilience."""
        return self.providers.get(name.lower(), self.providers["mock"])

    def _get_assets_dir(self) -> Path:
        """Return workspace assets directory."""
        workspace = get_default_allowed_roots()[0]
        assets_dir = workspace / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        return assets_dir

    def _load_manifest(self) -> AssetManifest:
        """Load manifest.json from workspace assets directory."""
        manifest_file = self._get_assets_dir() / "manifest.json"
        if manifest_file.exists():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                return AssetManifest.model_validate(data)
            except Exception:
                pass
        return AssetManifest()

    def _save_manifest(self, manifest: AssetManifest) -> None:
        """Save updated manifest.json and regenerate ATTRIBUTION.md."""
        assets_dir = self._get_assets_dir()
        manifest_file = assets_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest.model_dump(), indent=2), encoding="utf-8")

        attribution_file = assets_dir / "ATTRIBUTION.md"
        attribution_file.write_text(manifest.generate_attribution_md(), encoding="utf-8")

    async def search(
        self,
        query: str,
        provider: str = "openverse",
        license_type: str | None = None,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Search provider for media assets returning token-efficient text descriptors."""
        prov = self.get_provider(provider)
        return await prov.search(query=query, license_type=license_type, page=page)

    async def preview(
        self,
        asset_id: str,
        provider: str = "openverse",
    ) -> dict[str, Any]:
        """Fetch small thumbnail preview image as base64."""
        prov = self.get_provider(provider)
        raw_bytes = await prov.fetch_preview(asset_id)
        if not raw_bytes:
            return {"success": False, "error": f"Preview unavailable for asset '{asset_id}'"}

        return {
            "success": True,
            "asset_id": asset_id,
            "thumbnail_base64": base64.b64encode(raw_bytes).decode("utf-8"),
        }

    async def download_asset(
        self,
        asset_id: str,
        provider: str = "openverse",
    ) -> dict[str, Any]:
        """
        Download, validate, sanitize, hash, and record external asset.
        """
        prov = self.get_provider(provider)
        meta = await prov.get_details(asset_id)
        if not meta:
            return {"success": False, "error": f"Asset '{asset_id}' not found."}

        # 1. License Policy evaluation
        allowed, reason = self.policy.evaluate_license(meta.license_code)
        if not allowed:
            return {
                "success": False,
                "error": f"License check failed: {reason}",
                "license_code": meta.license_code,
            }

        # 2. SSRF URL validation
        validate_asset_url(meta.download_url)

        # 3. Download bytes with limits
        req = urllib.request.Request(meta.download_url, headers={"User-Agent": "SynfigMCP/0.8.0"})
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            content_bytes = resp.read(25 * 1024 * 1024)  # 25 MB max download ceiling

        assets_dir = self._get_assets_dir()
        is_svg = b"<svg" in content_bytes[:2048].lower()

        ext = ".svg" if is_svg else ".png"
        clean_filename = f"{meta.id}{ext}"
        target_path = assets_dir / clean_filename

        # 4. Content sanitization and hardening
        if is_svg:
            sanitized_xml = sanitize_svg(content_bytes)
            target_path.write_text(sanitized_xml, encoding="utf-8")
        else:
            temp_raw = assets_dir / f"tmp_{meta.id}"
            temp_raw.write_bytes(content_bytes)
            try:
                harden_raster_image(temp_raw, target_path)
            finally:
                if temp_raw.exists():
                    temp_raw.unlink()

        # 5. Cryptographic SHA-256 hash & Provenance record
        final_bytes = target_path.read_bytes()
        sha256_hash = hashlib.sha256(final_bytes).hexdigest()

        meta.sha256 = sha256_hash
        meta.local_path = str(target_path)
        meta.filesize_bytes = len(final_bytes)

        manifest = self._load_manifest()
        # Update or append
        manifest.assets = [a for a in manifest.assets if a.id != meta.id]
        manifest.assets.append(meta)
        self._save_manifest(manifest)

        return {
            "success": True,
            "asset_id": meta.id,
            "title": meta.title,
            "license": meta.license_code,
            "local_path": str(target_path),
            "sha256": sha256_hash,
            "attribution": meta.attribution_text,
        }

    async def import_local_asset(
        self,
        file_path: str,
        rights: str,
        title: str,
        creator: str,
        license_code: str = "own",
    ) -> dict[str, Any]:
        """
        Import local asset with mandatory rights declaration in {own, licensed, cc0, public-domain}.
        """
        valid_rights = {"own", "licensed", "cc0", "public-domain"}
        declared = rights.lower().strip()
        if declared not in valid_rights:
            return {
                "success": False,
                "error": f"Invalid rights declaration '{rights}'. Must be one of: {sorted(valid_rights)}",
            }

        p = Path(file_path)
        if not p.exists():
            return {"success": False, "error": f"File '{file_path}' does not exist."}

        raw_bytes = p.read_bytes()
        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
        asset_id = f"local_{sha256_hash[:10]}"

        meta = AssetMetadata(
            id=asset_id,
            provider="local",
            title=title or p.name,
            creator=creator or "Local User",
            license_code=license_code,
            rights_declaration=declared,
            download_url="local://workspace",
            sha256=sha256_hash,
            local_path=str(p.resolve()),
            filesize_bytes=len(raw_bytes),
        )

        manifest = self._load_manifest()
        manifest.assets = [a for a in manifest.assets if a.id != meta.id]
        manifest.assets.append(meta)
        self._save_manifest(manifest)

        return {
            "success": True,
            "asset_id": asset_id,
            "rights": declared,
            "sha256": sha256_hash,
            "local_path": str(p.resolve()),
        }

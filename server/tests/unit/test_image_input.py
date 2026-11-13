"""
Image-content ingest adapter: uploaded MCP images are hardened and written into a
granted root, and local paths are validated like any other asset.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from synfig_mcp.characters.image_input import (
    decode_image_payload,
    ingest_image_content,
    require_authorized_output_dir,
    resolve_image_input,
)
from synfig_mcp.errors import SecuritySandboxError, ValidationError
from synfig_mcp.security.permissions import PermissionStore


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> PermissionStore:
    fresh = PermissionStore()
    fresh.clear()
    fresh.grant(tmp_path)
    monkeypatch.setattr("synfig_mcp.security.permissions.permissions", fresh)
    monkeypatch.setattr(
        "synfig_mcp.security.sandbox.get_default_allowed_roots",
        lambda: [g.path for g in fresh.grants()],
    )
    return fresh


def _png_b64(colour: tuple[int, int, int, int] = (10, 20, 30, 255)) -> str:
    img = Image.new("RGBA", (48, 32), colour)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_decode_accepts_data_url() -> None:
    raw = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()
    data, mime = decode_image_payload(f"data:image/png;base64,{raw}")
    assert data == b"\x89PNG\r\n\x1a\n"
    assert mime == "image/png"


def test_decode_rejects_empty_and_bad_base64() -> None:
    with pytest.raises(ValidationError, match="empty"):
        decode_image_payload("")
    with pytest.raises(ValidationError, match="base64"):
        decode_image_payload("not valid base64 @@")


def test_ingest_writes_hardened_png(store: PermissionStore, tmp_path: Path) -> None:  # noqa: ARG001
    result = ingest_image_content(_png_b64(), tmp_path, filename="sheet")
    target = Path(result["path"])
    assert target.is_file() and target.suffix == ".png"
    assert result["source"] == "image_content"
    assert (result["width"], result["height"]) == (48, 32)
    with Image.open(target) as img:
        assert img.size == (48, 32)


def test_ingest_rejects_non_image_bytes(store: PermissionStore, tmp_path: Path) -> None:  # noqa: ARG001
    payload = base64.b64encode(b"this is not an image at all").decode()
    with pytest.raises(ValidationError, match="rejected"):
        ingest_image_content(payload, tmp_path)


def test_ingest_outside_granted_root_is_denied(store: PermissionStore, tmp_path: Path) -> None:  # noqa: ARG001
    elsewhere = tmp_path.parent / "outside"
    elsewhere.mkdir(exist_ok=True)
    with pytest.raises(SecuritySandboxError):
        ingest_image_content(_png_b64(), elsewhere)


def test_resolve_requires_exactly_one_source(store: PermissionStore, tmp_path: Path) -> None:  # noqa: ARG001
    with pytest.raises(ValidationError, match="exactly one"):
        resolve_image_input(tmp_path)
    with pytest.raises(ValidationError, match="exactly one"):
        resolve_image_input(tmp_path, image_base64=_png_b64(), file_path="x.png")


def test_resolve_local_path_is_validated(store: PermissionStore, tmp_path: Path) -> None:  # noqa: ARG001
    sheet = tmp_path / "sheet.png"
    Image.new("RGBA", (16, 16), (0, 0, 0, 0)).save(sheet)
    resolved = resolve_image_input(tmp_path, file_path=str(sheet))
    assert resolved["source"] == "file_path"
    assert resolved["path"] == str(sheet.resolve())


def test_require_output_dir_defaults_to_granted_root(
    store: PermissionStore,  # noqa: ARG001 (grants tmp_path as a side effect)
    tmp_path: Path,
) -> None:
    assert require_authorized_output_dir(None) == tmp_path.resolve()


def test_require_output_dir_without_grants_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fresh = PermissionStore()
    fresh.clear()
    monkeypatch.setattr("synfig_mcp.security.permissions.permissions", fresh)
    monkeypatch.setattr("synfig_mcp.security.sandbox.get_default_allowed_roots", list)
    with pytest.raises(SecuritySandboxError, match="authorized"):
        require_authorized_output_dir(None)


def test_ingest_round_trips_through_rig_sheet_from_image(
    store: PermissionStore,  # noqa: ARG001 (grants tmp_path as a side effect)
    tmp_path: Path,
) -> None:
    """The ingested PNG is a valid input for slice_rig_sheet."""
    from synfig_mcp.characters.sheet import slice_rig_sheet

    img = Image.new("RGBA", (200, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 10, 90, 90), fill=(240, 200, 160, 255))
    draw.rectangle((120, 10, 190, 110), fill=(40, 90, 200, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    payload = base64.b64encode(buf.getvalue()).decode()

    ingested = ingest_image_content(payload, tmp_path, filename="ref")
    result = slice_rig_sheet(
        Path(ingested["path"]),
        tmp_path / "parts",
        names={"1": "head", "2": "torso"},
        source="image_content",
    )
    assert result["detected_parts"] == 2
    assert [p["name"] for p in result["parts"]] == ["head", "torso"]

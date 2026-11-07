"""
Writer for saving .sif (raw XML), .sifz (gzip), and .sfg (zip container) documents.
"""

import contextlib
import gzip
import zipfile
from io import BytesIO
from pathlib import Path

from synfig_mcp.sif.parser import SifDocument


def save_sif(doc: SifDocument, target_path: Path) -> None:
    """Save SifDocument to disk, automatically applying format based on file extension."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    xml_data = doc.to_xml_bytes()
    ext = target_path.suffix.lower()

    if ext == ".sifz":
        with gzip.open(target_path, "wb") as gz:
            gz.write(xml_data)
    elif ext == ".sfg":
        # ZIP container
        existing_assets: dict[str, bytes] = dict(doc._container_assets)
        if target_path.is_file():
            with contextlib.suppress(Exception), zipfile.ZipFile(target_path, "r") as zf:
                for name in zf.namelist():
                    if name not in ("project.sif", "project.sifz", "canvas.sif", "canvas.sifz"):
                        existing_assets.setdefault(name, zf.read(name))

        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Write project.sif
            zf.writestr("project.sif", xml_data)
            # Write other container assets
            for asset_name, asset_bytes in existing_assets.items():
                zf.writestr(asset_name, asset_bytes)

        target_path.write_bytes(buf.getvalue())
    else:
        # Default to raw .sif
        target_path.write_bytes(xml_data)

"""
Writer for .sif, .sifz (gzip), and .sfg (zip) documents.
"""

import gzip
from pathlib import Path

from synfig_mcp.sif.parser import SifDocument


def save_sif(doc: SifDocument, target_path: Path) -> None:
    """Save document to disk (.sif or .sifz)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    xml_data = doc.to_xml_bytes()

    if target_path.suffix.lower() == ".sifz":
        with gzip.open(target_path, "wb") as gz:
            gz.write(xml_data)
    else:
        target_path.write_bytes(xml_data)

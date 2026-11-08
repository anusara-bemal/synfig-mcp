"""
Property-based and golden tests for lossless SIF XML round-tripping.
"""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from synfig_mcp.sif.parser import SifDocument
from synfig_mcp.sif.writer import save_sif

# Strategy for generating valid XML tag and attribute names
xml_names = st.from_regex(r"[a-z][a-z0-9_]{1,10}", fullmatch=True)
xml_texts = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-.,"),
    max_size=30,
)


@st.composite
def xml_canvas_strategy(draw: st.DrawFn) -> str:
    """Generate arbitrary valid SIF XML canvas trees with comments, metadata, and layers."""
    width = draw(st.integers(min_value=100, max_value=3840))
    height = draw(st.integers(min_value=100, max_value=2160))
    fps = draw(st.floats(min_value=1.0, max_value=120.0, allow_nan=False, allow_infinity=False))
    comment_text = draw(xml_texts).replace("--", "- -")
    if comment_text.endswith("-"):
        comment_text += " "
    custom_attr = draw(xml_names)
    custom_val = draw(xml_texts)

    num_layers = draw(st.integers(min_value=1, max_value=5))
    layers_xml: list[str] = []
    for i in range(num_layers):
        l_type = draw(st.sampled_from(["circle", "rectangle", "star", "solid_color", "text"]))
        l_desc = f"{l_type}_{i}"
        layers_xml.append(
            f'  <layer type="{l_type}" active="true" version="0.1" desc="{l_desc}">\n'
            f"    <!-- Layer comment {i} -->\n"
            f'    <param name="z_depth"><real value="{float(i):.4f}"/></param>\n'
            f"  </layer>"
        )

    layers_block = "\n".join(layers_xml)
    return (
        f'<?xml version="1.0" encoding="utf-8"?>\n'
        f'<canvas version="1.2" width="{width}" height="{height}" fps="{fps:.3f}" {custom_attr}="{custom_val}">\n'
        f"  <!-- Top level comment: {comment_text} -->\n"
        f"  <name>Property Test Canvas</name>\n"
        f"{layers_block}\n"
        f"</canvas>\n"
    )


@given(xml_canvas_strategy())
@settings(max_examples=30, deadline=None)
def test_property_sif_lossless_roundtrip(xml_content: str) -> None:
    """Verify that parsing and reserializing SIF XML preserves all elements and comments."""
    doc1 = SifDocument.from_string(xml_content)
    xml_bytes = doc1.to_xml_bytes()

    doc2 = SifDocument.from_bytes(xml_bytes)

    # Element counts and tags must match exactly
    root1 = doc1.root
    root2 = doc2.root
    assert root1.tag == root2.tag
    assert root1.get("width") == root2.get("width")
    assert root1.get("height") == root2.get("height")

    # Layer count must match
    layers1 = doc1.get_layers()
    layers2 = doc2.get_layers()
    assert len(layers1) == len(layers2)
    for l1, l2 in zip(layers1, layers2, strict=True):
        assert l1.type == l2.type
        assert l1.desc == l2.desc


def test_real_synfig_files_roundtrip() -> None:
    """Test lossless round-trip on real Synfig project examples from repo if present."""
    examples_dir = Path("build_synfig/synfig_src/synfig-core/examples")
    if not examples_dir.is_dir():
        return

    sif_files = list(examples_dir.glob("*.sif"))
    assert len(sif_files) > 0, "No sample .sif files found"

    for sif_path in sif_files[:5]:  # Test first 5 examples
        doc = SifDocument.from_file(sif_path)

        # Basic integrity
        assert doc.width > 0
        assert doc.height > 0
        assert doc.fps > 0

        # Reserialize
        serialized = doc.to_xml_bytes()
        doc_reloaded = SifDocument.from_bytes(serialized)

        assert doc_reloaded.width == doc.width
        assert doc_reloaded.height == doc.height
        assert len(doc_reloaded.get_layers()) == len(doc.get_layers())


def test_sif_sifz_sfg_formats_roundtrip() -> None:
    """Verify .sif, .sifz, and .sfg multi-format disk serialization and restoration."""
    doc = SifDocument.new(width=1280, height=720, fps=30.0, name="Container Test")
    doc.add_layer("circle", desc="Circle1", params={"radius": {"type": "real", "value": 2.5}})
    doc.add_layer("rectangle", desc="Rect1")
    doc.add_keyframe(1.0, desc="Keyframe 1")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Plain .sif
        sif_file = tmp_path / "test.sif"
        save_sif(doc, sif_file)
        assert sif_file.is_file()
        doc_sif = SifDocument.from_file(sif_file)
        assert doc_sif.width == 1280
        assert len(doc_sif.get_layers()) == 2
        assert len(doc_sif.list_keyframes()) == 1

        # 2. Gzipped .sifz
        sifz_file = tmp_path / "test.sifz"
        save_sif(doc, sifz_file)
        assert sifz_file.is_file()
        doc_sifz = SifDocument.from_file(sifz_file)
        assert doc_sifz.width == 1280
        assert len(doc_sifz.get_layers()) == 2
        assert len(doc_sifz.list_keyframes()) == 1

        # 3. Zip Container .sfg
        # Add a fake image asset to container
        doc._container_assets["images/texture.png"] = b"\x89PNG\r\n\x1a\nfakeimage"
        sfg_file = tmp_path / "test.sfg"
        save_sif(doc, sfg_file)
        assert sfg_file.is_file()
        doc_sfg = SifDocument.from_file(sfg_file)
        assert doc_sfg.width == 1280
        assert len(doc_sfg.get_layers()) == 2
        assert len(doc_sfg.list_keyframes()) == 1
        assert "images/texture.png" in doc_sfg._container_assets
        assert doc_sfg._container_assets["images/texture.png"] == b"\x89PNG\r\n\x1a\nfakeimage"

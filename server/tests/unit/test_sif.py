"""Unit tests for SIF parser."""

from synfig_mcp.sif.parser import SifDocument


def test_sif_parse_and_serialize() -> None:
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<canvas version="1.2" width="1920" height="1080" xres="2834.645752" yres="2834.645752" fps="24.000" start-time="0f" end-time="5s">
  <name>Test Canvas</name>
</canvas>"""
    doc = SifDocument.from_string(sample_xml)
    serialized = doc.to_xml_bytes().decode("utf-8")
    assert "<canvas" in serialized
    assert 'width="1920"' in serialized
    assert "Test Canvas" in serialized

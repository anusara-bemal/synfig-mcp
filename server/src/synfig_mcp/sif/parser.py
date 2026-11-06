"""
[STUB - P1 Prototype] Lossless SIF XML parser using lxml.

NOTE: This is a P1 prototype stub preserving unknown tags and basic serialization.
The full lossless, non-destructive SIF/SIFZ/SFG round-trip engine with full
schema node preservation will be implemented in Phase P6.
"""

from pathlib import Path

from lxml import etree


class SifDocument:
    """[STUB - P1 Prototype] Represents a parsed .sif XML document tree."""

    def __init__(self, tree: etree._ElementTree) -> None:
        self.tree = tree

    @classmethod
    def from_string(cls, xml_text: str) -> "SifDocument":
        parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
        tree = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
        return cls(etree.ElementTree(tree))

    @classmethod
    def from_file(cls, path: Path) -> "SifDocument":
        parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
        tree = etree.parse(str(path), parser=parser)
        return cls(tree)

    def to_xml_bytes(self) -> bytes:
        return etree.tostring(
            self.tree,
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8",
        )

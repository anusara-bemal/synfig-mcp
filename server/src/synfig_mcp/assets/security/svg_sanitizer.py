"""
Hardened SVG DOM Sanitizer: Rebuilds SVG with strict tag/attribute allow-lists.
Prevents XSS, SSRF, XML entity expansion bombs, and malicious embedded scripts (Phase A5).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# Register standard SVG namespaces so serializer doesn't generate ns0: prefixes
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

# Disallow external entities and DOCTYPE entity expansions
DOCTYPE_ENTITY_PATTERN = re.compile(r"<!ENTITY", re.IGNORECASE)
XML_BOMB_PATTERN = re.compile(r"<!DOCTYPE[^>]*\[", re.IGNORECASE)

# Tag allow-list for static vector graphics
ALLOWED_TAGS = {
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "defs",
    "lineargradient",
    "radialgradient",
    "stop",
    "clippath",
    "mask",
    "pattern",
    "style",
    "text",
    "tspan",
}

# Attribute allow-list
ALLOWED_ATTRS = {
    "id",
    "class",
    "style",
    "transform",
    "width",
    "height",
    "viewbox",
    "xmlns",
    "xmlns:xlink",
    "version",
    "d",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "points",
    "fill",
    "fill-opacity",
    "fill-rule",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "stroke-dasharray",
    "stroke-dashoffset",
    "stroke-opacity",
    "opacity",
    "gradientunits",
    "gradienttransform",
    "spreadmethod",
    "offset",
    "stop-color",
    "stop-opacity",
    "clip-path",
    "clip-rule",
    "mask",
}

DANGEROUS_PROTOCOLS = re.compile(r"^\s*(javascript|data|vbscript):", re.IGNORECASE)


def sanitize_svg(svg_content: str | bytes) -> str:
    """
    Sanitize SVG markup, removing all active content, scripts, and entities.
    Returns: Cleaned SVG markup as valid XML string.
    Raises: ValueError if the SVG contains XML bomb patterns or cannot be parsed.
    """
    if isinstance(svg_content, bytes):
        text = svg_content.decode("utf-8", errors="replace")
    else:
        text = svg_content

    # Check for XML entities / Billion laughs bomb
    if DOCTYPE_ENTITY_PATTERN.search(text) or XML_BOMB_PATTERN.search(text):
        raise ValueError("Malicious SVG rejected: DOCTYPE entity expansion detected.")

    try:
        # Strip xmlns prefix namespaces for normalized tag checking
        root = ET.fromstring(text)
    except Exception as exc:
        raise ValueError(f"Invalid SVG markup: {exc}") from exc

    def clean_element(elem: ET.Element) -> None:
        # Clean attributes
        attrs_to_remove: list[str] = []
        for attr, val in list(elem.attrib.items()):
            clean_attr = attr.split("}")[-1].lower() if "}" in attr else attr.lower()

            # Remove event handlers (onload, onclick, onerror, etc.)
            if clean_attr.startswith("on"):
                attrs_to_remove.append(attr)
                continue

            # Remove hrefs with dangerous protocols or external links
            if "href" in clean_attr and DANGEROUS_PROTOCOLS.search(str(val)):
                attrs_to_remove.append(attr)
                continue

            # Attribute allow-list
            if clean_attr not in ALLOWED_ATTRS:
                attrs_to_remove.append(attr)

        for a in attrs_to_remove:
            del elem.attrib[a]

        # Clean children
        children_to_remove: list[ET.Element] = []
        for child in list(elem):
            c_tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
            if c_tag not in ALLOWED_TAGS:
                children_to_remove.append(child)
            else:
                clean_element(child)

        for c in children_to_remove:
            elem.remove(c)

    clean_element(root)

    raw_xml = ET.tostring(root, encoding="utf-8")
    return raw_xml.decode("utf-8") if isinstance(raw_xml, bytes) else str(raw_xml)

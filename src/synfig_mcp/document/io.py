# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Read/write .sif (XML), .sifz (gzip XML) and .sfg (zip container).

The lxml tree is kept verbatim end-to-end (unknown tags/attributes are
preserved), and writes are atomic (temp file + os.replace). A ``.bak`` copy
is made before overwriting when ``backup=True``.
"""

from __future__ import annotations

import contextlib
import gzip
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import cast

from lxml import etree

from ..errors import InvalidProjectError, LimitExceededError, UnsupportedFormatError
from ..security.limits import Limits
from ..security.paths import check_file_size

PROJECT_EXTENSIONS = {".sif", ".sifz", ".sfg"}

PARSER = etree.XMLParser(remove_blank_text=False, recover=False, huge_tree=True)


def read_sif_bytes(path: Path, limits: Limits | None = None) -> bytes:
    max_bytes = limits.settings.max_file_bytes if limits else 256 * 1024 * 1024
    check_file_size(path, max_bytes, "project")
    suffix = path.suffix.lower()
    raw = path.read_bytes()
    if suffix == ".sif":
        return raw
    if suffix == ".sifz":
        try:
            return gzip.decompress(raw)
        except OSError as exc:
            raise InvalidProjectError(
                f"{path.name} is not a valid gzip (.sifz) file: {exc}"
            ) from exc
    if suffix == ".sfg":
        return _read_sfg(path)
    raise UnsupportedFormatError(
        f"Unsupported project extension {suffix!r}. Use .sif, .sifz or .sfg."
    )


def _read_sfg(path: Path) -> bytes:
    try:
        with zipfile.ZipFile(path) as bundle:
            names = bundle.namelist()
            preferred = sorted(
                (n for n in names if n.lower().endswith(".sifz")), key=len
            ) or sorted((n for n in names if n.lower().endswith(".sif")), key=len)
            if not preferred:
                raise InvalidProjectError(
                    f"{path.name} contains no .sif or .sifz canvas (found: {', '.join(names[:8])})."
                )
            data = bundle.read(preferred[0])
            if preferred[0].lower().endswith(".sifz"):
                try:
                    return gzip.decompress(data)
                except OSError as exc:
                    raise InvalidProjectError(
                        f"Embedded .sifz in {path.name} is corrupt: {exc}"
                    ) from exc
            return data
    except zipfile.BadZipFile as exc:
        raise InvalidProjectError(
            f"{path.name} is not a valid .sfg (zip) container: {exc}"
        ) from exc


def parse_sif(xml_bytes: bytes, *, source: str = "<document>") -> etree._ElementTree:
    try:
        root = etree.fromstring(xml_bytes, parser=PARSER)
    except etree.XMLSyntaxError as exc:
        raise InvalidProjectError(f"{source} is not well-formed XML: {exc}") from exc
    if root.tag != "canvas":
        raise InvalidProjectError(f"{source} does not contain a <canvas> root (got <{root.tag}>).")
    return etree.ElementTree(root)


def read_project(path: Path, limits: Limits | None = None) -> etree._ElementTree:
    xml_bytes = read_sif_bytes(path, limits)
    tree = parse_sif(xml_bytes, source=str(path))
    if limits:
        count_layers(tree)
        if count_layers(tree) > limits.settings.max_layers:
            raise LimitExceededError(
                f"{path.name} has more than {limits.settings.max_layers} layers; refusing to load."
            )
    return tree


def count_layers(tree: etree._ElementTree) -> int:
    return sum(1 for _ in tree.getroot().iter("layer"))


def count_layers_in_root(root: etree._Element) -> int:
    return sum(1 for _ in root.iter("layer"))


def serialize(tree: etree._ElementTree) -> bytes:
    return cast(
        bytes,
        etree.tostring(
            tree,
            xml_declaration=True,
            encoding="UTF-8",
            pretty_print=False,
        ),
    )


def serialize_pretty(tree: etree._ElementTree) -> bytes:
    return cast(
        bytes,
        etree.tostring(
            tree,
            xml_declaration=True,
            encoding="UTF-8",
            pretty_print=True,
        ),
    )


def atomic_write(path: Path, payload: bytes, *, backup: bool = True) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        # A failed backup must never block a save.
        with contextlib.suppress(OSError):
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def write_project(
    tree: etree._ElementTree, path: Path, *, backup: bool = True, pretty: bool = False
) -> None:
    xml_bytes = serialize_pretty(tree) if pretty else serialize(tree)
    suffix = path.suffix.lower()
    if suffix == ".sif":
        atomic_write(path, xml_bytes, backup=backup)
        return
    if suffix == ".sifz":
        payload = gzip.compress(xml_bytes, compresslevel=9, mtime=0)
        atomic_write(path, payload, backup=backup)
        return
    if suffix == ".sfg":
        _write_sfg(path, xml_bytes, backup=backup)
        return
    raise UnsupportedFormatError(
        f"Unsupported project extension {suffix!r}. Use .sif, .sifz or .sfg."
    )


def _write_sfg(path: Path, xml_bytes: bytes, *, backup: bool) -> None:
    """Write a .sfg (zip) containing ``canvas.sifz``. Preserves other entries."""
    sifz_payload = gzip.compress(xml_bytes, compresslevel=9, mtime=0)
    existing: dict[str, bytes] = {}
    if path.exists():
        try:
            with zipfile.ZipFile(path) as bundle:
                for name in bundle.namelist():
                    if name.lower() in {"canvas.sifz", "canvas.sif"}:
                        continue
                    with contextlib.suppress(OSError):
                        existing[name] = bundle.read(name)
        except zipfile.BadZipFile:
            existing = {}

    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        with contextlib.suppress(OSError):
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as raw, zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("canvas.sifz", sifz_payload)
            for name, blob in existing.items():
                bundle.writestr(name, blob)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def new_project_xml(
    *,
    width: int,
    height: int,
    fps: float,
    begin_time: str,
    end_time: str,
    name: str,
    bgcolor: tuple[float, float, float, float],
    antialias: int = 1,
    xres: float = 2834.645910,
    yres: float = 2834.645910,
    view_box: tuple[float, float, float, float] | None = None,
    gamma: tuple[float, float, float] | None = None,
) -> etree._ElementTree:
    view = view_box or default_view_box(width, height)
    canvas = etree.Element(
        "canvas",
        attrib={
            "version": "1.0",
            "width": str(int(width)),
            "height": str(int(height)),
            "xres": f"{xres:.6f}",
            "yres": f"{yres:.6f}",
            "view-box": f"{view[0]:.6f} {view[1]:.6f} {view[2]:.6f} {view[3]:.6f}",
            "antialias": str(int(antialias)),
            "fps": f"{fps:.3f}",
            "begin-time": begin_time,
            "end-time": end_time,
            "bgcolor": " ".join(f"{c:.6f}" for c in bgcolor),
        },
    )
    if gamma is not None:
        canvas.set("gamma-r", f"{gamma[0]:.6f}")
        canvas.set("gamma-g", f"{gamma[1]:.6f}")
        canvas.set("gamma-b", f"{gamma[2]:.6f}")
    name_el = etree.SubElement(canvas, "name")
    name_el.text = name
    return etree.ElementTree(canvas)


def default_view_box(width: int, height: int) -> tuple[float, float, float, float]:
    """Same aspect-preserving default as Studio: ±1.5 units vertically."""
    half_h = 1.5
    half_w = half_h * (width / height) if height else half_h
    return (-half_w, half_h, half_w, -half_h)

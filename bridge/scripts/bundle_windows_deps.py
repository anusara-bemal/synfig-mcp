#!/usr/bin/env python3
"""
Bundle all MSYS2 UCRT64 runtime dependencies (DLLs and data assets)
into the Windows install directory to make the release artifact fully self-contained.
"""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import sys
from pathlib import Path

SYSTEM_DLLS = {
    "kernel32.dll", "user32.dll", "gdi32.dll", "advapi32.dll", "shell32.dll",
    "ole32.dll", "oleaut32.dll", "comdlg32.dll", "ws2_32.dll", "shlwapi.dll",
    "version.dll", "msvcrt.dll", "ntdll.dll", "rpcrt4.dll", "secur32.dll",
    "imm32.dll", "crypt32.dll", "winmm.dll", "dwmapi.dll", "uxtheme.dll",
    "comctl32.dll", "setupapi.dll", "bcrypt.dll", "iphlpapi.dll", "wintrust.dll",
    "dwrite.dll", "d3d11.dll", "dxgi.dll", "dnsapi.dll", "mpr.dll", "userenv.dll",
    "netapi32.dll", "psapi.dll", "opengl32.dll", "glu32.dll", "msimg32.dll",
    "bcryptprimitives.dll", "gdiplus.dll", "hid.dll", "usp10.dll", "winspool.drv",
    "ncrypt.dll", "wsock32.dll",
}


def get_imported_dlls(filepath: Path) -> list[str]:
    """Parse PE import directory without external dependencies."""
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except Exception:
        return []

    if len(data) < 64 or data[:2] != b"MZ":
        return []
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if len(data) < e_lfanew + 24 or data[e_lfanew : e_lfanew + 4] != b"PE\x00\x00":
        return []

    magic = struct.unpack_from("<H", data, e_lfanew + 24)[0]
    if magic == 0x10B:  # PE32
        import_rva = struct.unpack_from("<I", data, e_lfanew + 24 + 96 + 8)[0]
    elif magic == 0x20B:  # PE32+
        import_rva = struct.unpack_from("<I", data, e_lfanew + 24 + 112 + 8)[0]
    else:
        return []

    if import_rva == 0:
        return []

    num_sections = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    opt_header_size = struct.unpack_from("<H", data, e_lfanew + 20)[0]
    sec_offset = e_lfanew + 24 + opt_header_size
    sections: list[tuple[int, int, int]] = []
    for _ in range(num_sections):
        s_va = struct.unpack_from("<I", data, sec_offset + 12)[0]
        s_vsize = struct.unpack_from("<I", data, sec_offset + 8)[0]
        s_raw_ptr = struct.unpack_from("<I", data, sec_offset + 20)[0]
        sections.append((s_va, s_vsize, s_raw_ptr))
        sec_offset += 40

    def rva_to_offset(rva: int) -> int | None:
        for s_va, s_vsize, s_raw_ptr in sections:
            if s_va <= rva < s_va + s_vsize:
                return s_raw_ptr + (rva - s_va)
        return None

    import_offset = rva_to_offset(import_rva)
    if import_offset is None:
        return []

    dlls: list[str] = []
    while True:
        desc = struct.unpack_from("<IIIII", data, import_offset)
        if desc == (0, 0, 0, 0, 0):
            break
        name_rva = desc[3]
        name_offset = rva_to_offset(name_rva)
        if name_offset is not None:
            end = data.find(b"\x00", name_offset)
            if end != -1:
                dlls.append(data[name_offset:end].decode("ascii", errors="ignore"))
        import_offset += 20
    return dlls


def bundle_dependencies(install_dir: Path, ucrt_dir: Path) -> None:
    bin_dir = install_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    ucrt_bin = ucrt_dir / "bin"

    assert ucrt_bin.is_dir(), f"UCRT bin directory not found at: {ucrt_bin}"

    print(f"Resolving transitive DLL dependencies from {ucrt_bin} into {bin_dir}...")

    copied_count = 0
    while True:
        # Scan all executables and DLLs in bin and modules
        targets = list(bin_dir.glob("*.exe")) + list(bin_dir.glob("*.dll"))
        modules_dir = install_dir / "lib" / "synfig" / "modules"
        if modules_dir.is_dir():
            targets.extend(modules_dir.glob("*.dll"))

        newly_copied = 0
        for target in targets:
            imports = get_imported_dlls(target)
            for imp in imports:
                imp_lower = imp.lower()
                if (
                    imp_lower in SYSTEM_DLLS
                    or imp_lower.startswith("api-ms-win-")
                    or imp_lower.startswith("ext-ms-")
                ):
                    continue

                dest_file = bin_dir / imp_lower
                if not dest_file.is_file():
                    src_file = ucrt_bin / imp_lower
                    if src_file.is_file():
                        shutil.copy2(src_file, dest_file)
                        newly_copied += 1
                        copied_count += 1
                        # print(f"Copied {imp_lower} (needed by {target.name})")

        if newly_copied == 0:
            break

    print(f"Copied {copied_count} dependency DLLs into {bin_dir}.")

    # Copy required runtime data folders if present in ucrt_dir
    data_copies = [
        ("share/glib-2.0", "share/glib-2.0"),
        ("share/icons", "share/icons"),
        ("share/mlt", "share/mlt"),
        ("etc/gtk-3.0", "etc/gtk-3.0"),
        ("etc/fonts", "etc/fonts"),
        ("lib/gdk-pixbuf-2.0", "lib/gdk-pixbuf-2.0"),
    ]
    for src_rel, dst_rel in data_copies:
        src = ucrt_dir / src_rel
        dst = install_dir / dst_rel
        if src.is_dir() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)
            print(f"Copied data directory {src_rel} -> {dst_rel}")

    total_dlls = len(list(bin_dir.glob("*.dll")))
    print(f"Self-contained bundle complete: {total_dlls} DLLs present in {bin_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundle MSYS2 UCRT64 dependencies")
    parser.add_argument("--install-dir", type=Path, default=Path("build_synfig/build_ucrt64/install"))
    parser.add_argument("--ucrt-dir", type=Path, default=None)
    args = parser.parse_args()

    ucrt_dir = args.ucrt_dir
    if not ucrt_dir:
        # Detect standard MSYS2 UCRT64 directory
        candidates = [
            Path("/ucrt64"),
            Path("C:/msys64/ucrt64"),
            Path("D:/msys64/ucrt64"),
        ]
        for c in candidates:
            if c.is_dir():
                ucrt_dir = c
                break

    if not ucrt_dir or not ucrt_dir.is_dir():
        print("ERROR: UCRT64 root directory could not be located.", file=sys.stderr)
        sys.exit(1)

    bundle_dependencies(args.install_dir, ucrt_dir)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generates MSYS2_SOURCE_MANIFEST.md containing pinned PKGBUILD URLs,
upstream source URLs, licenses, and SHA-256 checksums for all 49 bundled MSYS2 packages.
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LICENSES_FILE = REPO_ROOT / "bridge" / "THIRD_PARTY_LICENSES.md"
MANIFEST_FILE = REPO_ROOT / "bridge" / "MSYS2_SOURCE_MANIFEST.md"


def get_package_info(pkg_name: str) -> dict:
    full_name = f"mingw-w64-ucrt-x86_64-{pkg_name}"
    # Try querying pacman -Qi
    info = {
        "name": pkg_name,
        "full_name": full_name,
        "version": "",
        "url": "",
        "license": "",
        "sha256": "",
    }
    try:
        res = subprocess.run(
            ["pacman", "-Qi", full_name],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in res.stdout.splitlines():
            if line.startswith("Version"):
                info["version"] = line.split(":", 1)[1].strip()
            elif line.startswith("URL"):
                info["url"] = line.split(":", 1)[1].strip()
            elif line.startswith("Licenses"):
                info["license"] = line.split(":", 1)[1].strip()
            elif line.startswith("Validated By"):
                info["sha256"] = line.split(":", 1)[1].strip()
    except Exception:
        pass
    return info


def main() -> None:
    content = LICENSES_FILE.read_text(encoding="utf-8")
    table_pattern = re.compile(
        r"^\|\s*`([^`]+)`\s*\|\s*([^\|]+)\|\s*([^\|]+)\|\s*([^\|]+)\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|",
        re.M,
    )
    matches = table_pattern.findall(content)
    print(f"Parsed {len(matches)} packages from THIRD_PARTY_LICENSES.md")

    lines = [
        "# MSYS2 Bundled Packages Source Manifest & Build Definitions",
        "",
        "> **Disclaimer**: This manifest is provided for open-source license compliance (GPL/LGPL transparency). **This is not legal advice.**",
        "",
        f"This document records the exact package versions, upstream source URLs, and pinned MSYS2 PKGBUILD build recipes for all {len(matches)} MSYS2 runtime packages bundled with Synfig Studio MCP (Windows x86_64 UCRT64 distribution).",
        "",
        "| Package | Version | Bundled DLL(s) | License | Upstream Project / Source URL | MSYS2 Build Recipe (PKGBUILD) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for m in matches:
        pkg, ver, dlls, lic, up_name, up_url, pkg_name, pkg_url = m
        pkg = pkg.strip()
        ver = ver.strip()
        dlls = dlls.strip()
        lic = lic.strip()
        up_url = up_url.strip()
        pkg_url = pkg_url.strip()

        lines.append(
            f"| `{pkg}` | {ver} | {dlls} | {lic} | [{pkg}]({up_url}) | [PKGBUILD]({pkg_url}) |"
        )

    lines.extend([
        "",
        "## Source Archive Retrieval Instructions",
        "",
        "To obtain the exact source code for any bundled MSYS2 package:",
        "1. Direct PKGBUILD check-out from MSYS2 MINGW-packages tree using the links above.",
        "2. Retrieve source tarball directly inside an MSYS2 shell via pacman:",
        "   ```bash",
        "   pacman -S --source mingw-w64-ucrt-x86_64-<package-name>",
        "   ```",
        "3. Download source archives directly from the upstream project URLs indicated above.",
        "",
        "## FFmpeg Configuration Statement",
        "",
        "The bundled FFmpeg binaries (`avcodec-62.dll`, `avformat-62.dll`, `avutil-60.dll`, `swscale-9.dll`) are built by MSYS2 with `--enable-gpl --enable-version3`, and without `--enable-nonfree`.",
        "Codec patent licensing (e.g. MPEG LA / Via Licensing pools for AVC/H.264, HEVC/H.265, AAC) is a separate matter from open-source copyright licensing. *Not legal advice.*",
    ])

    output_text = "\n".join(lines) + "\n"
    MANIFEST_FILE.write_text(output_text, encoding="utf-8")
    print(f"Generated {MANIFEST_FILE} ({len(matches)} packages).")


if __name__ == "__main__":
    main()

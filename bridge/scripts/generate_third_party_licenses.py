#!/usr/bin/env python3
"""
Generates bridge/THIRD_PARTY_LICENSES.md by querying pacman -Qi for installed MSYS2 packages.
Ensures GPL-3.0 Section 6 compliance for all bundled runtime DLLs and dependencies.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = REPO_ROOT / "bridge" / "THIRD_PARTY_LICENSES.md"

PACKAGES = [
    "mingw-w64-ucrt-x86_64-gtkmm3",
    "mingw-w64-ucrt-x86_64-glibmm",
    "mingw-w64-ucrt-x86_64-libxml++2.6",
    "mingw-w64-ucrt-x86_64-fftw",
    "mingw-w64-ucrt-x86_64-ffmpeg",
    "mingw-w64-ucrt-x86_64-imagemagick",
    "mingw-w64-ucrt-x86_64-openexr",
    "mingw-w64-ucrt-x86_64-libmng",
    "mingw-w64-ucrt-x86_64-harfbuzz",
    "mingw-w64-ucrt-x86_64-SDL2",
    "mingw-w64-ucrt-x86_64-libltdl",
    "mingw-w64-ucrt-x86_64-mlt",
    "mingw-w64-ucrt-x86_64-boost",
    "mingw-w64-ucrt-x86_64-gtk3",
    "mingw-w64-ucrt-x86_64-glib2",
    "mingw-w64-ucrt-x86_64-cairo",
    "mingw-w64-ucrt-x86_64-pango",
    "mingw-w64-ucrt-x86_64-libpng",
    "mingw-w64-ucrt-x86_64-zlib",
    "mingw-w64-ucrt-x86_64-nlohmann-json",
]


def query_pacman(pkg: str) -> dict[str, str]:
    pacman_cmd = "pacman"
    if not shutil.which("pacman"):
        # Try default MSYS2 location
        msys_pacman = Path("C:/msys64/usr/bin/pacman.exe")
        if msys_pacman.is_file():
            pacman_cmd = str(msys_pacman)

    try:
        res = subprocess.run(
            [pacman_cmd, "-Qi", pkg],
            capture_output=True,
            text=True,
            check=True,
        )
        info: dict[str, str] = {}
        for line in res.stdout.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                info[key.strip()] = val.strip()
        return info
    except Exception:
        return {}


def main() -> None:
    print(f"Generating {OUTPUT_FILE} from pacman package metadata...")
    rows: list[dict[str, str]] = []

    for pkg in PACKAGES:
        info = query_pacman(pkg)
        short_name = pkg.replace("mingw-w64-ucrt-x86_64-", "")
        version = info.get("Version", "unknown")
        licenses = info.get("Licenses", "unknown")
        url = info.get("URL", "https://packages.msys2.org/packages/" + pkg)
        msys_repo = f"https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-{short_name}"

        rows.append(
            {
                "pkg": pkg,
                "short_name": short_name,
                "version": version,
                "licenses": licenses,
                "url": url,
                "msys_repo": msys_repo,
            }
        )

    content = f"""# Third-Party Licenses & Source Availability

> **Notice**: *This document is provided for open-source license compliance and source-availability transparency under the GNU General Public License v3 (GPL-3.0). It does not constitute formal legal advice.*

This distribution of **Synfig Studio with MCP Bridge Integration** links against and bundles runtime libraries built from the MSYS2 UCRT64 software distribution.

---

## Bundled Third-Party Components

| Component | Version | License | Upstream Project | MSYS2 Source Recipe |
| :--- | :--- | :--- | :--- | :--- |
"""
    for r in rows:
        content += f"| `{r['short_name']}` | {r['version']} | {r['licenses']} | [{r['short_name']}]({r['url']}) | [MSYS2 Package]({r['msys_repo']}) |\n"

    content += """
---

## Source Code Availability (GPL-3.0 Section 6 Compliance)

In compliance with the reciprocal source-sharing requirements of GPL-3.0 and LGPL-2.1/3.0 licenses governing these components:

1. **Upstream Synfig Studio Source**:
   - Pinned Commit: [`79bf708e2483cba678fc93f0ecf48b2178263795`](https://github.com/synfig/synfig/tree/79bf708e2483cba678fc93f0ecf48b2178263795)
   - Patches and bridge source code are included directly under the `patches/` and `src/` directories of this release.

2. **MSYS2 Runtime Dependencies**:
   - Complete machine-readable build recipes, patch sets, and source package archives (`PKGBUILD`) for every dependency listed above are hosted by the MSYS2 project at:
     [https://github.com/msys2/MINGW-packages](https://github.com/msys2/MINGW-packages)
   - Source archives for any MSYS2 binary package can also be downloaded directly via pacman:
     ```bash
     pacman -S --source <package-name>
     ```

3. **Written Offer**:
   - In accordance with Section 6(b) of GPL-3.0, any recipient of this binary distribution may request a copy of the corresponding source code by opening an issue on our GitHub repository:
     [https://github.com/synfig-mcp/synfig-mcp](https://github.com/synfig-mcp/synfig-mcp)
"""

    OUTPUT_FILE.write_text(content, encoding="utf-8")
    print(f"Successfully generated {OUTPUT_FILE} ({len(rows)} packages listed).")


if __name__ == "__main__":
    main()

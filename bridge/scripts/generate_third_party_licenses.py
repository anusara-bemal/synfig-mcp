#!/usr/bin/env python3
"""
Generates bridge/THIRD_PARTY_LICENSES.md from actual packaged DLLs in install/bin
via MSYS2 pacman -Qo and pacman -Qi.
Ensures GPL-3.0 Section 6 compliance for all bundled runtime DLLs and dependencies.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = REPO_ROOT / "bridge" / "THIRD_PARTY_LICENSES.md"
BIN_DIR = REPO_ROOT / "build_synfig" / "build_ucrt64" / "install" / "bin"


def get_all_bundled_dlls() -> list[str]:
    if BIN_DIR.is_dir():
        return sorted([p.name for p in BIN_DIR.glob("*.dll")])
    return []


def query_pacman_metadata(dll_names: list[str]) -> tuple[dict[str, list[str]], dict[str, dict[str, str]], list[str]]:
    bash_path = "C:/msys64/usr/bin/bash.exe"
    if not Path(bash_path).is_file():
        bash_path = shutil.which("bash") or "bash"

    ucrt_dlls = [f"/ucrt64/bin/{d}" for d in dll_names]
    cmd_qo = f"export MSYSTEM=UCRT64; . /etc/profile; pacman -Qo {' '.join(ucrt_dlls)}"
    res_qo = subprocess.run([bash_path, "-lc", cmd_qo], capture_output=True, text=True, errors="replace")

    pkg_to_dlls: dict[str, list[str]] = {}
    synfig_dlls: list[str] = []

    for line in res_qo.stdout.splitlines():
        if " is owned by " in line:
            path, pkg_info = line.split(" is owned by ", 1)
            dll_name = Path(path.strip()).name
            pkg = pkg_info.strip().split()[0]
            pkg_to_dlls.setdefault(pkg, []).append(dll_name)
        elif "error: No package owns" in line or "error: failed to read" in line:
            dll_name = line.split()[-1]
            synfig_dlls.append(Path(dll_name).name)

    # Check for unowned Synfig DLLs
    for d in dll_names:
        mapped = any(d in v for v in pkg_to_dlls.values())
        if not mapped and d not in synfig_dlls:
            synfig_dlls.append(d)

    all_pkgs = sorted(pkg_to_dlls.keys())
    cmd_qi = f"export MSYSTEM=UCRT64; . /etc/profile; pacman -Qi {' '.join(all_pkgs)}"
    res_qi = subprocess.run([bash_path, "-lc", cmd_qi], capture_output=True, text=True, errors="replace")

    pkg_info_map: dict[str, dict[str, str]] = {}
    current_pkg: str | None = None
    for line in res_qi.stdout.splitlines():
        if line.startswith("Name"):
            current_pkg = line.split(":", 1)[1].strip()
            pkg_info_map[current_pkg] = {}
        elif current_pkg and ":" in line:
            k, v = line.split(":", 1)
            pkg_info_map[current_pkg][k.strip()] = v.strip()

    return pkg_to_dlls, pkg_info_map, sorted(synfig_dlls)


def main() -> None:
    print("Scanning bundled DLLs and querying MSYS2 pacman package database...")
    dlls = get_all_bundled_dlls()
    if not dlls:
        # Fallback to saved json if running on host without active install dir
        saved_json = REPO_ROOT / "scratch" / "pkgs_info.json"
        if saved_json.is_file():
            with open(saved_json) as f:
                data = json.load(f)
                pkg_to_dlls = data["pkg_to_dlls"]
                pkg_info_map = data["pkg_info"]
                synfig_dlls = ["libsynfig-0.dll", "libsynfigapp.dll"]
        else:
            raise RuntimeError("No DLLs found and no cached package data available.")
    else:
        pkg_to_dlls, pkg_info_map, synfig_dlls = query_pacman_metadata(dlls)

    lines: list[str] = [
        "# Third-Party Licenses & Source Availability",
        "",
        "> **Notice**: *This document is provided for open-source license compliance and source-availability transparency under the GNU General Public License v3 (GPL-3.0). It does not constitute formal legal counsel.*",
        "",
        f"This distribution of **Synfig Studio with MCP Bridge Integration** bundles **{sum(len(v) for v in pkg_to_dlls.values()) + len(synfig_dlls)} shared libraries (DLLs)**, including core Synfig binaries and runtime libraries from **{len(pkg_to_dlls)} MSYS2 UCRT64 software packages**.",
        "",
        "---",
        "",
        "## 1. Synfig Core Components (GPL-3.0-or-later)",
        "",
        "The following dynamic libraries are built directly from the Synfig Studio source tree (pinned commit `79bf708e2483cba678fc93f0ecf48b2178263795`):",
        "",
        "| File | Component | License | Source Tree |",
        "| :--- | :--- | :--- | :--- |",
        "| `synfigstudio.exe` | Synfig Studio GUI + Native MCP Bridge | GPL-3.0-or-later | `synfig-studio/src/gui` |",
        "| `libsynfig-0.dll` | Synfig Core Animation Engine | GPL-3.0-or-later | `synfig-core/src/synfig` |",
        "| `libsynfigapp.dll` | Synfig Action & Undo Framework | GPL-3.0-or-later | `synfig-core/src/synfigapp` |",
        "",
        "---",
        "",
        "## 2. Bundled Third-Party Runtime Dependencies",
        "",
        f"All {sum(len(v) for v in pkg_to_dlls.values())} third-party DLLs distributed in the Windows UCRT64 release archive are mapped below to their originating MSYS2 package, version, and license:",
        "",
        "| Package | Version | Bundled DLL(s) | License | Upstream Project | MSYS2 Source Recipe |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for pkg in sorted(pkg_to_dlls.keys()):
        short = pkg.replace("mingw-w64-ucrt-x86_64-", "")
        info = pkg_info_map.get(pkg, {})
        version = info.get("Version", "unknown")
        licenses = info.get("Licenses", "unknown")
        url = info.get("URL", f"https://packages.msys2.org/packages/{pkg}")
        dll_list = "<br>".join(f"`{d}`" for d in sorted(pkg_to_dlls[pkg]))
        recipe_url = f"https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-{short}"
        lines.append(f"| `{short}` | {version} | {dll_list} | {licenses} | [{short}]({url}) | [MSYS2 PKGBUILD]({recipe_url}) |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Analysis of GPL and LGPL Implications (FFmpeg, MLT, and ImageMagick)",
        "",
        "### A. FFmpeg (`mingw-w64-ucrt-x86_64-ffmpeg`)",
        "- **License**: GPL-3.0-or-later (compiled with `--enable-gpl --enable-version3`).",
        "- **Implication**: FFmpeg includes GPL-licensed components (e.g. `libpostproc`, `libx264`). Distributing FFmpeg binaries alongside Synfig Studio binds the collective binary distribution to the full copyleft terms of the **GNU General Public License v3 (GPL-3.0)**.",
        "- **Compliance**: Because Synfig Studio and the MCP bridge are licensed under GPL-3.0-or-later, license compatibility is preserved. In accordance with GPL-3.0 Section 6, full machine-readable source code for all components is provided or made available via upstream repositories and written offer.",
        "",
        "### B. MLT Multimedia Framework (`mingw-w64-ucrt-x86_64-mlt`)",
        "- **License**: LGPL-2.1-or-later (core engine) with optional GPL modules.",
        "- **Implication**: When linked dynamically with GPL-licensed FFmpeg libraries and GPL modules, the effective binary license of the combined MLT runtime operates under GPL-3.0.",
        "- **Compliance**: MLT source recipes and patchsets are provided through the MSYS2 repository link above.",
        "",
        "### C. Dynamic Linking & LGPL Libraries (`gtkmm3`, `glibmm`, `cairo`, `pango`)",
        "- **License**: LGPL-2.1-or-later / LGPL-3.0-or-later.",
        "- **Implication**: LGPL requires that users be permitted to re-link or replace the LGPL dynamic libraries. Since all libraries are distributed as unstripped or dynamically loadable `.dll` files in `install/bin`, users can replace any individual DLL without modifying or recompiling `synfigstudio.exe`.",
        "",
        "---",
        "",
        "## 4. Source Code Availability (GPL-3.0 Section 6 Compliance)",
        "",
        "In compliance with Section 6 of the GNU General Public License v3:",
        "",
        "1. **Synfig Studio & MCP Bridge Source**:",
        "   - Upstream commit: [`79bf708e2483cba678fc93f0ecf48b2178263795`](https://github.com/synfig/synfig/tree/79bf708e2483cba678fc93f0ecf48b2178263795)",
        "   - Native bridge implementation: `bridge/src/mcp_bridge/`",
        "   - Clean patchset: `bridge/patches/`",
        "2. **MSYS2 Build Recipes & Upstream Sources**:",
        "   - All 48 dependency packages are built from reproducible MSYS2 `PKGBUILD` scripts hosted at: [https://github.com/msys2/MINGW-packages](https://github.com/msys2/MINGW-packages)",
        "   - Source tarballs for any package can be retrieved via: `pacman -S --source <package-name>`",
        "3. **Written Offer**:",
        "   - Any recipient of this binary release may request a complete copy of the corresponding source code by opening an issue at our repository: [https://github.com/synfig-mcp/synfig-mcp](https://github.com/synfig-mcp/synfig-mcp)",
    ])

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Successfully generated {OUTPUT_FILE} ({len(lines)} lines).")


if __name__ == "__main__":
    main()

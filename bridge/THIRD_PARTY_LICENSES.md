# Third-Party Licenses & Source Availability

> **Notice**: *This document is provided for open-source license compliance and source-availability transparency under the GNU General Public License v3 (GPL-3.0). It does not constitute formal legal advice.*

This distribution of **Synfig Studio with MCP Bridge Integration** links against and bundles runtime libraries built from the MSYS2 UCRT64 software distribution.

---

## Bundled Third-Party Components

| Component | Version | License | Upstream Project | MSYS2 Source Recipe |
| :--- | :--- | :--- | :--- | :--- |
| `gtkmm3` | 3.24.10-3 | LGPL | [gtkmm3](https://www.gtkmm.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gtkmm3) |
| `glibmm` | 2.66.8-4 | spdx:LGPL-2.1-or-later | [glibmm](https://www.gtkmm.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-glibmm) |
| `libxml++2.6` | 2.42.3-5 | spdx:LGPL-2.1-or-later | [libxml++2.6](https://libxmlplusplus.github.io/libxmlplusplus/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libxml++2.6) |
| `fftw` | 3.3.11-1 | spdx:GPL-2.0-or-later | [fftw](https://www.fftw.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-fftw) |
| `ffmpeg` | 8.1.1-2 | spdx:GPL-3.0-or-later | [ffmpeg](https://ffmpeg.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-ffmpeg) |
| `imagemagick` | 7.1.2.25-1 | spdx:ImageMagick | [imagemagick](https://www.imagemagick.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-imagemagick) |
| `openexr` | 3.4.12-1 | spdx:BSD-3-Clause | [openexr](https://www.openexr.com/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-openexr) |
| `libmng` | 2.0.3-7 | spdx:Zlib | [libmng](https://sourceforge.net/projects/libmng) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libmng) |
| `harfbuzz` | 14.2.1-1 | spdx:MIT | [harfbuzz](https://harfbuzz.github.io/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-harfbuzz) |
| `SDL2` | 2.32.10-1 | spdx:Zlib | [SDL2](https://libsdl.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-SDL2) |
| `libltdl` | 2.5.4-4 | spdx:LGPL-2.0-or-later WITH Libtool-exception | [libltdl](https://www.gnu.org/software/libtool) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libltdl) |
| `mlt` | 7.36.1-1 | spdx:LGPL-2.1-or-later | [mlt](https://www.mltframework.org) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-mlt) |
| `boost` | 1.91.0-3 | spdx:BSL-1.0 | [boost](https://www.boost.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-boost) |
| `gtk3` | 3.24.52-1 | spdx:LGPL-2.1-or-later | [gtk3](https://www.gtk.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gtk3) |
| `glib2` | 2.88.1-1 | spdx:LGPL-2.1-or-later | [glib2](https://gitlab.gnome.org/GNOME/glib) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-glib2) |
| `cairo` | 1.18.4-4 | spdx:LGPL-2.1-or-later OR MPL-1.1 | [cairo](https://cairographics.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-cairo) |
| `pango` | 1.57.1-1 | spdx:LGPL-2.1 | [pango](https://www.pango.org/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-pango) |
| `libpng` | 1.6.58-1 | custom | [libpng](http://www.libpng.org/pub/png/libpng.html) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libpng) |
| `zlib` | 1.3.2-2 | spdx:Zlib | [zlib](https://www.zlib.net/) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-zlib) |
| `nlohmann-json` | 3.12.0-1 | MIT | [nlohmann-json](https://github.com/nlohmann/json) | [MSYS2 Package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-nlohmann-json) |

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

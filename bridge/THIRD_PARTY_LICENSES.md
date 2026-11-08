# Third-Party Licenses & Source Availability

> **Notice**: *This document is provided for open-source license compliance and source-availability transparency under the GNU General Public License v3 (GPL-3.0). It does not constitute formal legal counsel.*

This distribution of **Synfig Studio with MCP Bridge Integration** bundles **75 shared libraries (DLLs)**, including core Synfig binaries and runtime libraries from **48 MSYS2 UCRT64 software packages**.

---

## 1. Synfig Core Components (GPL-3.0-or-later)

The following dynamic libraries are built directly from the Synfig Studio source tree (pinned commit `79bf708e2483cba678fc93f0ecf48b2178263795`):

| File | Component | License | Source Tree |
| :--- | :--- | :--- | :--- |
| `synfigstudio.exe` | Synfig Studio GUI + Native MCP Bridge | GPL-3.0-or-later | `synfig-studio/src/gui` |
| `libsynfig-0.dll` | Synfig Core Animation Engine | GPL-3.0-or-later | `synfig-core/src/synfig` |
| `libsynfigapp.dll` | Synfig Action & Undo Framework | GPL-3.0-or-later | `synfig-core/src/synfigapp` |

---

## 2. Bundled Third-Party Runtime Dependencies

All 73 third-party DLLs distributed in the Windows UCRT64 release archive are mapped below to their originating MSYS2 package, version, and license:

| Package | Version | Bundled DLL(s) | License | Upstream Project | MSYS2 Source Recipe |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `atk` | 2.60.4-1 | `libatk-1.0-0.dll` | spdx:LGPL-2.1-or-later | [atk](https://gnome.pages.gitlab.gnome.org/at-spi2-core/atk/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-atk) |
| `atkmm` | 2.28.5-1 | `libatkmm-1.6-1.dll` | spdx:LGPL-2.1-or-later | [atkmm](https://www.gtkmm.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-atkmm) |
| `brotli` | 1.2.0-1 | `libbrotlicommon.dll`<br>`libbrotlidec.dll` | spdx:MIT | [brotli](https://github.com/google/brotli) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-brotli) |
| `bzip2` | 1.0.8-3 | `libbz2-1.dll` | custom | [bzip2](https://sourceware.org/bzip2/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-bzip2) |
| `cairo` | 1.18.4-4 | `libcairo-2.dll`<br>`libcairo-gobject-2.dll`<br>`libcairo-script-interpreter-2.dll` | spdx:LGPL-2.1-or-later OR MPL-1.1 | [cairo](https://cairographics.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-cairo) |
| `cairomm` | 1.14.6-1 | `libcairomm-1.0-1.dll` | spdx:GPL-2.0-or-later | [cairomm](https://cairographics.org/cairomm/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-cairomm) |
| `dlfcn` | 1.4.2-1 | `libdl.dll` | spdx:MIT | [dlfcn](https://github.com/dlfcn-win32/dlfcn-win32) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-dlfcn) |
| `expat` | 2.8.1-2 | `libexpat-1.dll` | spdx:MIT | [expat](https://libexpat.github.io/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-expat) |
| `fftw` | 3.3.11-1 | `libfftw3-3.dll`<br>`libfftw3f-3.dll` | spdx:GPL-2.0-or-later | [fftw](https://www.fftw.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-fftw) |
| `fontconfig` | 2.18.1-1 | `libfontconfig-1.dll` | custom | [fontconfig](https://wiki.freedesktop.org/www/Software/fontconfig/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-fontconfig) |
| `freetype` | 2.14.3-1 | `libfreetype-6.dll` | spdx:GPL-2.0-or-later OR FTL | [freetype](https://www.freetype.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-freetype) |
| `fribidi` | 1.0.16-1 | `libfribidi-0.dll` | spdx:LGPL-2.1-or-later | [fribidi](https://github.com/fribidi/fribidi/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-fribidi) |
| `gcc-libs` | 16.1.0-5 | `libgcc_s_seh-1.dll`<br>`libquadmath-0.dll`<br>`libstdc++-6.dll` | spdx:GPL-3.0-or-later WITH GCC-exception-3.1 AND LGPL-2.1-or-later | [gcc-libs](https://gcc.gnu.org) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gcc-libs) |
| `gdk-pixbuf2` | 2.44.6-1 | `libgdk_pixbuf-2.0-0.dll` | spdx:LGPL-2.1-or-later | [gdk-pixbuf2](https://gitlab.gnome.org/GNOME/gdk-pixbuf) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gdk-pixbuf2) |
| `gettext-runtime` | 1.0-1 | `libintl-8.dll` | spdx:GPL-3.0-or-later AND LGPL-2.1-or-later | [gettext-runtime](https://www.gnu.org/software/gettext/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gettext-runtime) |
| `glib2` | 2.88.1-1 | `libgio-2.0-0.dll`<br>`libglib-2.0-0.dll`<br>`libgmodule-2.0-0.dll`<br>`libgobject-2.0-0.dll`<br>`libgthread-2.0-0.dll` | spdx:LGPL-2.1-or-later | [glib2](https://gitlab.gnome.org/GNOME/glib) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-glib2) |
| `glibmm` | 2.66.8-4 | `libgiomm-2.4-1.dll`<br>`libglibmm-2.4-1.dll`<br>`libglibmm_generate_extra_defs-2.4-1.dll` | spdx:LGPL-2.1-or-later | [glibmm](https://www.gtkmm.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-glibmm) |
| `graphite2` | 1.3.15-1 | `libgraphite2.dll` | spdx:LGPL-2.1-or-later | [graphite2](https://github.com/silnrsi/graphite) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-graphite2) |
| `gtk3` | 3.24.52-1 | `libgailutil-3-0.dll`<br>`libgdk-3-0.dll`<br>`libgtk-3-0.dll` | spdx:LGPL-2.1-or-later | [gtk3](https://www.gtk.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gtk3) |
| `gtkmm3` | 3.24.10-3 | `libgdkmm-3.0-1.dll`<br>`libgtkmm-3.0-1.dll` | LGPL | [gtkmm3](https://www.gtkmm.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gtkmm3) |
| `harfbuzz` | 14.2.1-1 | `libharfbuzz-0.dll` | spdx:MIT | [harfbuzz](https://harfbuzz.github.io/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-harfbuzz) |
| `imagemagick` | 7.1.2.25-1 | `libMagick++-7.Q16HDRI-5.dll`<br>`libMagickCore-7.Q16HDRI-10.dll`<br>`libMagickWand-7.Q16HDRI-10.dll` | spdx:ImageMagick | [imagemagick](https://www.imagemagick.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-imagemagick) |
| `jbigkit` | 2.1-5 | `libjbig-0.dll` | spdx:GPL-2.0 | [jbigkit](https://www.cl.cam.ac.uk/~mgk25/jbigkit/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-jbigkit) |
| `lerc` | 4.1.0-1 | `libLerc.dll` | spdx:Apache-2.0 | [lerc](https://github.com/Esri/lerc) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-lerc) |
| `libdatrie` | 0.2.14-1 | `libdatrie-1.dll` | LGPL | [libdatrie](https://linux.thai.net/projects/datrie) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libdatrie) |
| `libdeflate` | 1.25-1 | `libdeflate.dll` | spdx:MIT | [libdeflate](https://github.com/ebiggers/libdeflate) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libdeflate) |
| `libepoxy` | 1.5.10-7 | `libepoxy-0.dll` | spdx:MIT | [libepoxy](https://github.com/anholt/libepoxy) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libepoxy) |
| `libffi` | 3.5.2-1 | `libffi-8.dll` | spdx:MIT | [libffi](https://sourceware.org/libffi) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libffi) |
| `libiconv` | 1.19-1 | `libiconv-2.dll` | spdx:LGPL-2.1-or-later  documentation:spdx:GPL-3.0-or-later | [libiconv](https://www.gnu.org/software/libiconv/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libiconv) |
| `libjpeg-turbo` | 3.1.4.1-3 | `libjpeg-8.dll` | custom:BSD-like | [libjpeg-turbo](https://libjpeg-turbo.virtualgl.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libjpeg-turbo) |
| `libltdl` | 2.5.4-4 | `libltdl-7.dll` | spdx:LGPL-2.0-or-later WITH Libtool-exception | [libltdl](https://www.gnu.org/software/libtool) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libltdl) |
| `libpng` | 1.6.58-1 | `libpng16-16.dll` | custom | [libpng](http://www.libpng.org/pub/png/libpng.html) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libpng) |
| `librsvg` | 2.62.3-1 | `librsvg-2-2.dll` | spdx:LGPL-2.1-or-later | [librsvg](https://wiki.gnome.org/Projects/LibRsvg) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-librsvg) |
| `libsigc++` | 2.12.2-1 | `libsigc-2.0-0.dll` | spdx:LGPL-2.1-or-later | [libsigc++](https://libsigcplusplus.github.io/libsigcplusplus/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libsigc++) |
| `libthai` | 0.1.30-1 | `libthai-0.dll` | spdx:LGPL-2.1-or-later | [libthai](https://linux.thai.net/projects/libthai) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libthai) |
| `libtiff` | 4.7.1-1 | `libtiff-6.dll`<br>`libtiffxx-6.dll` | spdx:MIT | [libtiff](https://libtiff.gitlab.io/libtiff/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libtiff) |
| `libwebp` | 1.6.0-1 | `libsharpyuv-0.dll`<br>`libwebp-7.dll` | spdx:BSD-3-Clause | [libwebp](https://developers.google.com/speed/webp/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libwebp) |
| `libwinpthread` | 14.0.0.r92.g818fa6510-1 | `libwinpthread-1.dll` | spdx:MIT AND BSD-3-Clause-Clear | [libwinpthread](https://www.mingw-w64.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libwinpthread) |
| `libxml++2.6` | 2.42.3-5 | `libxml++-2.6-2.dll` | spdx:LGPL-2.1-or-later | [libxml++2.6](https://libxmlplusplus.github.io/libxmlplusplus/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libxml++2.6) |
| `libxml2` | 2.15.3-1 | `libxml2-16.dll` | spdx:MIT | [libxml2](https://gitlab.gnome.org/GNOME/libxml2/-/wikis/home) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libxml2) |
| `mlt` | 7.36.1-1 | `libmlt++-7.dll`<br>`libmlt-7.dll` | spdx:LGPL-2.1-or-later | [mlt](https://www.mltframework.org) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-mlt) |
| `pango` | 1.57.1-1 | `libpango-1.0-0.dll`<br>`libpangocairo-1.0-0.dll`<br>`libpangoft2-1.0-0.dll`<br>`libpangowin32-1.0-0.dll` | spdx:LGPL-2.1 | [pango](https://www.pango.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-pango) |
| `pangomm` | 2.46.4-2 | `libpangomm-1.4-1.dll` | spdx:LGPL-2.1-or-later | [pangomm](https://www.gtkmm.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-pangomm) |
| `pcre2` | 10.47-1 | `libpcre2-16-0.dll`<br>`libpcre2-32-0.dll`<br>`libpcre2-8-0.dll` | spdx:BSD-3-Clause | [pcre2](https://pcre.org/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-pcre2) |
| `pixman` | 0.46.4-3 | `libpixman-1-0.dll` | spdx:MIT | [pixman](https://gitlab.freedesktop.org/pixman/pixman) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-pixman) |
| `xz` | 5.8.3-1 | `liblzma-5.dll` | spdx:0BSD AND LGPL-2.1-or-later AND GPL-2.0-or-later | [xz](https://tukaani.org/xz) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-xz) |
| `zlib` | 1.3.2-2 | `zlib1.dll` | spdx:Zlib | [zlib](https://www.zlib.net/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-zlib) |
| `zstd` | 1.5.7-2 | `libzstd.dll` | spdx:BSD-3-Clause OR GPL-2.0-or-later | [zstd](https://facebook.github.io/zstd/) | [MSYS2 PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-zstd) |

---

## 3. Analysis of GPL and LGPL Implications (FFmpeg, MLT, and ImageMagick)

### A. FFmpeg (`mingw-w64-ucrt-x86_64-ffmpeg`)
- **License**: GPL-3.0-or-later (compiled with `--enable-gpl --enable-version3`, without `--enable-nonfree`).
- **Implication**: FFmpeg includes GPL-licensed components (e.g. `libpostproc`, `libx264`). Distributing FFmpeg binaries alongside Synfig Studio binds the collective binary distribution to the copyleft terms of the **GNU General Public License v3 (GPL-3.0)**.
- **Compliance**: Because Synfig Studio and the MCP bridge are licensed under GPL-3.0-or-later, license compatibility is preserved. In accordance with GPL-3.0 Section 6, full machine-readable source code for all components is provided or made available via upstream repositories and written offer.
- **Patent Licensing Distinction**: Copyright licensing under GPL-3.0 and patent licensing for proprietary media codecs (such as MPEG LA / Via Licensing patent pools covering H.264/AVC, H.265/HEVC, or AAC) are separate legal and regulatory matters. Users and distributors deploying commercial video rendering solutions must independently verify their codec patent licensing obligations. *Not legal advice.*

### B. MLT Multimedia Framework (`mingw-w64-ucrt-x86_64-mlt`)
- **License**: LGPL-2.1-or-later (core engine) with optional GPL modules.
- **Implication**: When linked dynamically with GPL-licensed FFmpeg libraries and GPL modules, the effective binary license of the combined MLT runtime operates under GPL-3.0.
- **Compliance**: MLT source recipes and patchsets are provided through the MSYS2 repository link above.

### C. Dynamic Linking & LGPL Libraries (`gtkmm3`, `glibmm`, `cairo`, `pango`)
- **License**: LGPL-2.1-or-later / LGPL-3.0-or-later.
- **Implication**: LGPL requires that users be permitted to re-link or replace the LGPL dynamic libraries. Since all libraries are distributed as unstripped or dynamically loadable `.dll` files in `install/bin`, users can replace any individual DLL without modifying or recompiling `synfigstudio.exe`.

---

## 4. Source Code Availability (GPL-3.0 Section 6 Compliance)

In compliance with Section 6 of the GNU General Public License v3:

1. **Synfig Studio & MCP Bridge Source**:
   - Upstream commit: [`79bf708e2483cba678fc93f0ecf48b2178263795`](https://github.com/synfig/synfig/tree/79bf708e2483cba678fc93f0ecf48b2178263795)
   - Native bridge implementation: `bridge/src/mcp_bridge/`
   - Clean patchset: `bridge/patches/`
2. **MSYS2 Build Recipes & Upstream Sources**:
   - All 48 dependency packages are built from reproducible MSYS2 `PKGBUILD` scripts hosted at: [https://github.com/msys2/MINGW-packages](https://github.com/msys2/MINGW-packages)
   - Source tarballs for any package can be retrieved via: `pacman -S --source <package-name>`
3. **Written Offer**:
   - Any recipient of this binary release may request a complete copy of the corresponding source code by opening an issue at our repository: [https://github.com/synfig-mcp/synfig-mcp](https://github.com/synfig-mcp/synfig-mcp)
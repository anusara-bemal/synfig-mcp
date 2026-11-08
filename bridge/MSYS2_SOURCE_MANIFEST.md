# MSYS2 Bundled Packages Source Manifest & Build Definitions

> **Disclaimer**: This manifest is provided for open-source license compliance (GPL/LGPL transparency). **This is not legal advice.**

This document records the exact package versions, upstream source URLs, and pinned MSYS2 PKGBUILD build recipes for all 49 MSYS2 runtime packages bundled with Synfig Studio MCP (Windows x86_64 UCRT64 distribution).

| Package | Version | Bundled DLL(s) | License | Upstream Project / Source URL | MSYS2 Build Recipe (PKGBUILD) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `atk` | 2.60.4-1 | `libatk-1.0-0.dll` | spdx:LGPL-2.1-or-later | [atk](https://gnome.pages.gitlab.gnome.org/at-spi2-core/atk/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-atk) |
| `atkmm` | 2.28.5-1 | `libatkmm-1.6-1.dll` | spdx:LGPL-2.1-or-later | [atkmm](https://www.gtkmm.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-atkmm) |
| `brotli` | 1.2.0-1 | `libbrotlicommon.dll`<br>`libbrotlidec.dll` | spdx:MIT | [brotli](https://github.com/google/brotli) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-brotli) |
| `bzip2` | 1.0.8-3 | `libbz2-1.dll` | custom | [bzip2](https://sourceware.org/bzip2/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-bzip2) |
| `cairo` | 1.18.4-4 | `libcairo-2.dll`<br>`libcairo-gobject-2.dll`<br>`libcairo-script-interpreter-2.dll` | spdx:LGPL-2.1-or-later OR MPL-1.1 | [cairo](https://cairographics.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-cairo) |
| `cairomm` | 1.14.6-1 | `libcairomm-1.0-1.dll` | spdx:GPL-2.0-or-later | [cairomm](https://cairographics.org/cairomm/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-cairomm) |
| `dlfcn` | 1.4.2-1 | `libdl.dll` | spdx:MIT | [dlfcn](https://github.com/dlfcn-win32/dlfcn-win32) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-dlfcn) |
| `expat` | 2.8.1-2 | `libexpat-1.dll` | spdx:MIT | [expat](https://libexpat.github.io/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-expat) |
| `ffmpeg` | 8.1.1-2 | `avcodec-62.dll`<br>`avformat-62.dll`<br>`avutil-60.dll`<br>`swscale-9.dll` | spdx:GPL-3.0-or-later | [ffmpeg](https://ffmpeg.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-ffmpeg) |
| `fftw` | 3.3.11-1 | `libfftw3-3.dll`<br>`libfftw3f-3.dll` | spdx:GPL-2.0-or-later | [fftw](https://www.fftw.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-fftw) |
| `fontconfig` | 2.18.1-1 | `libfontconfig-1.dll` | custom | [fontconfig](https://wiki.freedesktop.org/www/Software/fontconfig/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-fontconfig) |
| `freetype` | 2.14.3-1 | `libfreetype-6.dll` | spdx:GPL-2.0-or-later OR FTL | [freetype](https://www.freetype.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-freetype) |
| `fribidi` | 1.0.16-1 | `libfribidi-0.dll` | spdx:LGPL-2.1-or-later | [fribidi](https://github.com/fribidi/fribidi/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-fribidi) |
| `gcc-libs` | 16.1.0-5 | `libgcc_s_seh-1.dll`<br>`libquadmath-0.dll`<br>`libstdc++-6.dll` | spdx:GPL-3.0-or-later WITH GCC-exception-3.1 AND LGPL-2.1-or-later | [gcc-libs](https://gcc.gnu.org) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gcc-libs) |
| `gdk-pixbuf2` | 2.44.6-1 | `libgdk_pixbuf-2.0-0.dll` | spdx:LGPL-2.1-or-later | [gdk-pixbuf2](https://gitlab.gnome.org/GNOME/gdk-pixbuf) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gdk-pixbuf2) |
| `gettext-runtime` | 1.0-1 | `libintl-8.dll` | spdx:GPL-3.0-or-later AND LGPL-2.1-or-later | [gettext-runtime](https://www.gnu.org/software/gettext/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gettext-runtime) |
| `glib2` | 2.88.1-1 | `libgio-2.0-0.dll`<br>`libglib-2.0-0.dll`<br>`libgmodule-2.0-0.dll`<br>`libgobject-2.0-0.dll`<br>`libgthread-2.0-0.dll` | spdx:LGPL-2.1-or-later | [glib2](https://gitlab.gnome.org/GNOME/glib) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-glib2) |
| `glibmm` | 2.66.8-4 | `libgiomm-2.4-1.dll`<br>`libglibmm-2.4-1.dll`<br>`libglibmm_generate_extra_defs-2.4-1.dll` | spdx:LGPL-2.1-or-later | [glibmm](https://www.gtkmm.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-glibmm) |
| `graphite2` | 1.3.15-1 | `libgraphite2.dll` | spdx:LGPL-2.1-or-later | [graphite2](https://github.com/silnrsi/graphite) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-graphite2) |
| `gtk3` | 3.24.52-1 | `libgailutil-3-0.dll`<br>`libgdk-3-0.dll`<br>`libgtk-3-0.dll` | spdx:LGPL-2.1-or-later | [gtk3](https://www.gtk.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gtk3) |
| `gtkmm3` | 3.24.10-3 | `libgdkmm-3.0-1.dll`<br>`libgtkmm-3.0-1.dll` | LGPL | [gtkmm3](https://www.gtkmm.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-gtkmm3) |
| `harfbuzz` | 14.2.1-1 | `libharfbuzz-0.dll` | spdx:MIT | [harfbuzz](https://harfbuzz.github.io/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-harfbuzz) |
| `imagemagick` | 7.1.2.25-1 | `libMagick++-7.Q16HDRI-5.dll`<br>`libMagickCore-7.Q16HDRI-10.dll`<br>`libMagickWand-7.Q16HDRI-10.dll` | spdx:ImageMagick | [imagemagick](https://www.imagemagick.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-imagemagick) |
| `jbigkit` | 2.1-5 | `libjbig-0.dll` | spdx:GPL-2.0 | [jbigkit](https://www.cl.cam.ac.uk/~mgk25/jbigkit/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-jbigkit) |
| `lerc` | 4.1.0-1 | `libLerc.dll` | spdx:Apache-2.0 | [lerc](https://github.com/Esri/lerc) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-lerc) |
| `libdatrie` | 0.2.14-1 | `libdatrie-1.dll` | LGPL | [libdatrie](https://linux.thai.net/projects/datrie) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libdatrie) |
| `libdeflate` | 1.25-1 | `libdeflate.dll` | spdx:MIT | [libdeflate](https://github.com/ebiggers/libdeflate) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libdeflate) |
| `libepoxy` | 1.5.10-7 | `libepoxy-0.dll` | spdx:MIT | [libepoxy](https://github.com/anholt/libepoxy) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libepoxy) |
| `libffi` | 3.5.2-1 | `libffi-8.dll` | spdx:MIT | [libffi](https://sourceware.org/libffi) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libffi) |
| `libiconv` | 1.19-1 | `libiconv-2.dll` | spdx:LGPL-2.1-or-later  documentation:spdx:GPL-3.0-or-later | [libiconv](https://www.gnu.org/software/libiconv/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libiconv) |
| `libjpeg-turbo` | 3.1.4.1-3 | `libjpeg-8.dll` | custom:BSD-like | [libjpeg-turbo](https://libjpeg-turbo.virtualgl.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libjpeg-turbo) |
| `libltdl` | 2.5.4-4 | `libltdl-7.dll` | spdx:LGPL-2.0-or-later WITH Libtool-exception | [libltdl](https://www.gnu.org/software/libtool) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libltdl) |
| `libpng` | 1.6.58-1 | `libpng16-16.dll` | custom | [libpng](http://www.libpng.org/pub/png/libpng.html) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libpng) |
| `librsvg` | 2.62.3-1 | `librsvg-2-2.dll` | spdx:LGPL-2.1-or-later | [librsvg](https://wiki.gnome.org/Projects/LibRsvg) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-librsvg) |
| `libsigc++` | 2.12.2-1 | `libsigc-2.0-0.dll` | spdx:LGPL-2.1-or-later | [libsigc++](https://libsigcplusplus.github.io/libsigcplusplus/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libsigc++) |
| `libthai` | 0.1.30-1 | `libthai-0.dll` | spdx:LGPL-2.1-or-later | [libthai](https://linux.thai.net/projects/libthai) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libthai) |
| `libtiff` | 4.7.1-1 | `libtiff-6.dll`<br>`libtiffxx-6.dll` | spdx:MIT | [libtiff](https://libtiff.gitlab.io/libtiff/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libtiff) |
| `libwebp` | 1.6.0-1 | `libsharpyuv-0.dll`<br>`libwebp-7.dll` | spdx:BSD-3-Clause | [libwebp](https://developers.google.com/speed/webp/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libwebp) |
| `libwinpthread` | 14.0.0.r92.g818fa6510-1 | `libwinpthread-1.dll` | spdx:MIT AND BSD-3-Clause-Clear | [libwinpthread](https://www.mingw-w64.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libwinpthread) |
| `libxml++2.6` | 2.42.3-5 | `libxml++-2.6-2.dll` | spdx:LGPL-2.1-or-later | [libxml++2.6](https://libxmlplusplus.github.io/libxmlplusplus/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libxml++2.6) |
| `libxml2` | 2.15.3-1 | `libxml2-16.dll` | spdx:MIT | [libxml2](https://gitlab.gnome.org/GNOME/libxml2/-/wikis/home) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-libxml2) |
| `mlt` | 7.36.1-1 | `libmlt++-7.dll`<br>`libmlt-7.dll` | spdx:LGPL-2.1-or-later | [mlt](https://www.mltframework.org) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-mlt) |
| `pango` | 1.57.1-1 | `libpango-1.0-0.dll`<br>`libpangocairo-1.0-0.dll`<br>`libpangoft2-1.0-0.dll`<br>`libpangowin32-1.0-0.dll` | spdx:LGPL-2.1 | [pango](https://www.pango.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-pango) |
| `pangomm` | 2.46.4-2 | `libpangomm-1.4-1.dll` | spdx:LGPL-2.1-or-later | [pangomm](https://www.gtkmm.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-pangomm) |
| `pcre2` | 10.47-1 | `libpcre2-16-0.dll`<br>`libpcre2-32-0.dll`<br>`libpcre2-8-0.dll` | spdx:BSD-3-Clause | [pcre2](https://pcre.org/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-pcre2) |
| `pixman` | 0.46.4-3 | `libpixman-1-0.dll` | spdx:MIT | [pixman](https://gitlab.freedesktop.org/pixman/pixman) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-pixman) |
| `xz` | 5.8.3-1 | `liblzma-5.dll` | spdx:0BSD AND LGPL-2.1-or-later AND GPL-2.0-or-later | [xz](https://tukaani.org/xz) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-xz) |
| `zlib` | 1.3.2-2 | `zlib1.dll` | spdx:Zlib | [zlib](https://www.zlib.net/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-zlib) |
| `zstd` | 1.5.7-2 | `libzstd.dll` | spdx:BSD-3-Clause OR GPL-2.0-or-later | [zstd](https://facebook.github.io/zstd/) | [PKGBUILD](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-zstd) |

## Source Archive Retrieval Instructions

To obtain the exact source code for any bundled MSYS2 package:
1. Direct PKGBUILD check-out from MSYS2 MINGW-packages tree using the links above.
2. Retrieve source tarball directly inside an MSYS2 shell via pacman:
   ```bash
   pacman -S --source mingw-w64-ucrt-x86_64-<package-name>
   ```
3. Download source archives directly from the upstream project URLs indicated above.

## FFmpeg Configuration Statement

The bundled FFmpeg binaries (`avcodec-62.dll`, `avformat-62.dll`, `avutil-60.dll`, `swscale-9.dll`) are built by MSYS2 with `--enable-gpl --enable-version3`, and without `--enable-nonfree`.
Codec patent licensing (e.g. MPEG LA / Via Licensing pools for AVC/H.264, HEVC/H.265, AAC) is a separate matter from open-source copyright licensing. *Not legal advice.*

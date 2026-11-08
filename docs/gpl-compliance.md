# GPL-3.0 Compliance & Bundled Dependencies

> **Disclaimer**: This document and the accompanying distribution materials are provided for open source licensing compliance and transparency purposes only. **This is not legal advice.**

---

## 1. Upstream Synfig Studio Source Availability

Synfig Studio is licensed under the **GNU General Public License version 3 (GPL-3.0-or-later)**.
In full compliance with Section 6 of the GPL-3.0 ("Conveying Non-Source Forms"), any binary release distribution of the patched Synfig Studio executable (`synfigstudio.exe`) includes complete and corresponding source code:

- **Pinned Upstream Commit**: `79bf708e2483cba678fc93f0ecf48b2178263795` (synfig/synfig repo, tag v1.5.5)
- **Patch Directory**: `bridge/patches/` contains the full git-compatible patches applied to upstream.
- **Bridge Source**: `bridge/src/mcp_bridge/` contains the full C++ source code of the embedded MCP bridge.
- **Build Scripts**: `bridge/scripts/` provides automated, reproducible build scripts for Windows (MSYS2 UCRT64) and Linux.
- **Source Bundle Archive**: Every GitHub release attaches `synfig-mcp-gpl-source-v0.7.0.tar.gz` containing the exact commit tree, applied patches, and build definitions.

---

## 2. Bundled FFmpeg Configuration & Verification

Synfig Studio links dynamically to FFmpeg libraries (`libavcodec`, `libavformat`, `libavutil`, `libswscale`, `libswresample`, `libavfilter`, `libavdevice`) for multimedia import and video export.

The bundled FFmpeg binary distributed in our Windows packages is built directly by the MSYS2 UCRT64 project. We have explicitly queried the configuration from the runtime binary (`ffmpeg -buildconf`):

```text
ffmpeg version 8.1.1 Copyright (c) 2000-2026 the FFmpeg developers
  built with gcc 16.1.0 (Rev5, Built by MSYS2 project)
  configuration: --prefix=/ucrt64 --target-os=mingw32 --arch=x86_64 --cc=gcc --cxx=g++ --disable-debug --disable-stripping --disable-doc --enable-dxva2 --enable-d3d11va --enable-d3d12va --enable-frei0r --enable-gmp --enable-gnutls --enable-gpl --enable-iconv --enable-libaom --enable-libass --enable-libbluray --enable-libcaca --enable-libdav1d --enable-libfontconfig --enable-libfreetype --enable-libfribidi --enable-libgme --enable-libgsm --enable-libharfbuzz --enable-libjxl --enable-libmodplug --enable-libmp3lame --enable-libopencore_amrnb --enable-libopencore_amrwb --enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libssh --enable-libsoxr --enable-libspeex --enable-libsrt --enable-libtheora --enable-libvidstab --enable-libvorbis --enable-libx264 --enable-libx265 --enable-libxvid --enable-libvpx --enable-libwebp --enable-libxml2 --enable-libzimg --enable-libzvbi --enable-openal --enable-pic --enable-runtime-cpudetect --enable-swresample --enable-version3 --enable-vulkan --enable-zlib --enable-libvpl --enable-liblc3 --enable-libplacebo --enable-librav1e --enable-librsvg --enable-libsvtav1 --enable-libshaderc --enable-whisper --enable-amf --enable-nvenc --logfile=config.log --enable-shared
  libavutil      60. 26.101 / 60. 26.101
  libavcodec     62. 28.101 / 62. 28.101
  libavformat    62. 12.101 / 62. 12.101
  libavdevice    62.  3.101 / 62.  3.101
  libavfilter    11. 14.101 / 11. 14.101
  libswscale      9.  5.101 /  9.  5.101
  libswresample   6.  3.101 /  6.  3.101
```

### Verification Findings:
1. **GPL-3.0 Compatibility**: `--enable-gpl` and `--enable-version3` are enabled; `--enable-nonfree` is NOT enabled. This confirms that all bundled codec libraries are fully compliant with GPL-3.0 redistribution.
2. **Shared Libraries**: `--enable-shared` is used; all components link dynamically against standard DLLs.
3. **Hardware Acceleration**: `--enable-nvenc` and `--enable-amf` are present as open header loaders without proprietary runtime blobs statically bundled.

---

## 3. Bundled Third-Party Dependencies and Licenses

The Windows distribution packages libraries from MSYS2 UCRT64. Full package details and licensing can be inspected in [`THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md). A summary of core dependencies and their licenses:

| Component / Library | Upstream License | Distribution Compatibility |
| :--- | :--- | :--- |
| **Synfig Core & Studio** | GPL-3.0-or-later | Primary application license |
| **GTK 3 & Gtkmm** | LGPL-2.1-or-later | Dynamic linking allowed |
| **FFmpeg** | GPL-3.0 (built with `--enable-gpl --enable-version3`) | GPL-3.0 compatible |
| **Cairo & Cairomm** | LGPL-2.1 / MPL-1.1 | Permissive / copyleft dynamic link |
| **Pango & Pangomm** | LGPL-2.1-or-later | Dynamic linking allowed |
| **ImageMagick** | Apache-2.0-style / ImageMagick License | Permissive |
| **libxml2** | MIT License | Permissive |
| **FreeType** | FreeType License / GPL-2.0 | Dual-licensed |
| **HarfBuzz** | MIT License | Permissive |
| **libpng / zlib** | libpng / zlib License | Permissive |
| **libjpeg-turbo** | BSD-3-Clause / IJG | Permissive |

---

## 4. Rebuilding From Source

To rebuild the exact binary artifact from source:

1. Clone or download the source bundle:
   ```bash
   tar -xzf synfig-mcp-gpl-source-v0.7.0.tar.gz
   cd synfig-mcp-gpl-source
   ```
2. In an MSYS2 UCRT64 shell:
   ```bash
   bash bridge/scripts/build-windows.sh
   ```
3. In a Linux shell (Ubuntu 22.04 / 24.04):
   ```bash
   bash bridge/scripts/build-linux.sh
   ```

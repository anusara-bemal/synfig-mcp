# Building Synfig Studio on Windows (MSYS2 UCRT64)

This document records the exact build steps, dependencies, and environment configurations for compiling Synfig Studio from source on Windows using the MSYS2 UCRT64 toolchain.

---

## 1. Environment & Pinned Versions

- **Host OS**: Windows 11 / 10 x86_64
- **MSYS2 Environment**: UCRT64 (`C:\msys64\ucrt64`)
- **Pinned Synfig Tag**: `v1.5.5`
- **Pinned Git Commit**: `79bf708e2483cba678fc93f0ecf48b2178263795`
- **Compilers**: GCC 16.1.0 (`x86_64-w64-mingw32`)
- **Build System**: CMake 4.3.3 + Ninja 1.13.2

---

## 2. Dependency Setup

Run the following commands inside the MSYS2 UCRT64 environment (`export MSYSTEM=UCRT64; . /etc/profile`):

```bash
pacman -S --needed --noconfirm \
    autoconf \
    automake-wrapper \
    intltool \
    libtool \
    make \
    patch \
    tar \
    mingw-w64-ucrt-x86_64-ccache \
    mingw-w64-ucrt-x86_64-cmake \
    mingw-w64-ucrt-x86_64-ninja \
    mingw-w64-ucrt-x86_64-pkgconf \
    mingw-w64-ucrt-x86_64-gcc \
    mingw-w64-ucrt-x86_64-gtkmm3 \
    mingw-w64-ucrt-x86_64-glibmm \
    mingw-w64-ucrt-x86_64-libxml++2.6 \
    mingw-w64-ucrt-x86_64-fftw \
    mingw-w64-ucrt-x86_64-ffmpeg \
    mingw-w64-ucrt-x86_64-imagemagick \
    mingw-w64-ucrt-x86_64-openexr \
    mingw-w64-ucrt-x86_64-libmng \
    mingw-w64-ucrt-x86_64-harfbuzz \
    mingw-w64-ucrt-x86_64-SDL2 \
    mingw-w64-ucrt-x86_64-libltdl \
    mingw-w64-ucrt-x86_64-mlt \
    mingw-w64-ucrt-x86_64-boost
```

> [!TIP]
> MLT is provided directly via the official MSYS2 UCRT64 package `mingw-w64-ucrt-x86_64-mlt` (`7.36.1`), eliminating the need to compile MLT manually.
> To prevent exhausting Drive `C:`, clear the package download cache after installation:
> `pacman -Scc --noconfirm`

---

## 3. CMake Configuration & Compilation

From the root of the cloned `synfig` repository:

```bash
mkdir -p build_ucrt64 && cd build_ucrt64

cmake -GNinja \
    -DMSYS=1 \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_TESTS=OFF \
    -DCMAKE_INSTALL_PREFIX=./install \
    ../synfig_src

ninja synfigstudio
cmake --install .
```

The output artifacts are placed in:
- `build_ucrt64/install/bin/synfigstudio.exe`
- `build_ucrt64/install/bin/synfig.exe`
- Dynamic libraries (`libsynfig.dll`, `libsynfigapp.dll`, GTKmm/Cairo DLLs, etc.)

---

## 4. Troubleshooting & Notes

1. **MSYS2 `/etc/profile` Registry Exit Error**:
   If `set -e` is invoked before `. /etc/profile`, MSYS2's default printer check in the Windows registry may return non-zero and abort the script. Ensure `. /etc/profile || true` is loaded before setting `set -e`.
2. **Path Quoting**:
   Directories containing spaces must be enclosed in quotes when passed from Windows shells to MSYS2 bash.
3. **Winsock Linkage**:
   When compiling socket bridge code on Windows MinGW/UCRT64, `ws2_32` must be linked:
   `target_link_libraries(synfigstudio PRIVATE ws2_32)`.

#!/usr/bin/env bash
# Reproducible build script for Synfig Studio on Windows (MSYS2 UCRT64)
export MSYSTEM=UCRT64
. /etc/profile || true
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC_DIR="${ROOT_DIR}/build_synfig/synfig_src"
BUILD_DIR="${ROOT_DIR}/build_synfig/build_ucrt64"

echo "=== Synfig Studio Windows Build (MSYS2 UCRT64) ==="
echo "Root:   ${ROOT_DIR}"
echo "Source: ${SRC_DIR}"
echo "Build:  ${BUILD_DIR}"

# 1. Ensure dependencies are installed
PACKAGES=(
    autoconf
    automake-wrapper
    intltool
    libtool
    make
    patch
    tar
    mingw-w64-ucrt-x86_64-ccache
    mingw-w64-ucrt-x86_64-cmake
    mingw-w64-ucrt-x86_64-ninja
    mingw-w64-ucrt-x86_64-pkgconf
    mingw-w64-ucrt-x86_64-gcc
    mingw-w64-ucrt-x86_64-gtkmm3
    mingw-w64-ucrt-x86_64-glibmm
    mingw-w64-ucrt-x86_64-libxml++2.6
    mingw-w64-ucrt-x86_64-fftw
    mingw-w64-ucrt-x86_64-ffmpeg
    mingw-w64-ucrt-x86_64-imagemagick
    mingw-w64-ucrt-x86_64-openexr
    mingw-w64-ucrt-x86_64-libmng
    mingw-w64-ucrt-x86_64-harfbuzz
    mingw-w64-ucrt-x86_64-SDL2
    mingw-w64-ucrt-x86_64-libltdl
    mingw-w64-ucrt-x86_64-mlt
    mingw-w64-ucrt-x86_64-boost
)

echo "=== Verifying MSYS2 packages ==="
pacman -S --needed --noconfirm --color=auto "${PACKAGES[@]}"

# 2. Ensure pinned source exists
if [ ! -d "${SRC_DIR}/.git" ]; then
    echo "=== Source directory not found, fetching pinned commit ==="
    bash "${SCRIPT_DIR}/fetch_synfig.sh" "${SRC_DIR}"
fi

# 3. Apply bridge patches if any exist
if [ -f "${SCRIPT_DIR}/apply_patches.sh" ]; then
    bash "${SCRIPT_DIR}/apply_patches.sh" "${SRC_DIR}"
fi

# 4. Configure with CMake
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

echo "=== Configuring CMake ==="
cmake -GNinja \
    -DMSYS=1 \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_TESTS=OFF \
    -DCMAKE_INSTALL_PREFIX=./install \
    "${SRC_DIR}"

# 5. Compile and install
echo "=== Compiling Synfig Studio ==="
ninja synfigstudio
cmake --install .

echo "=== Build Completed Successfully ==="
echo "Binary: ${BUILD_DIR}/install/bin/synfigstudio.exe"

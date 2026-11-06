#!/usr/bin/env bash
# Setup MSYS2 UCRT64 dependencies for building Synfig Studio
set -e

export MSYSTEM=UCRT64
. /etc/profile

echo "=== Updating pacman and installing Synfig dependencies for UCRT64 ==="

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

pacman -S --needed --noconfirm --color=auto "${PACKAGES[@]}"

echo "=== Cleaning pacman cache to conserve drive space ==="
pacman -Scc --noconfirm

echo "=== MSYS2 UCRT64 dependencies successfully configured ==="

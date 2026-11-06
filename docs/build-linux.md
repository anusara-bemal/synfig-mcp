# Building Synfig Studio on Linux (Ubuntu / Debian)

This document describes how to compile the patched Synfig Studio on Linux or in a Docker container.

---

## 1. Prerequisites & Dependencies

```bash
sudo apt-get update && sudo apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    ccache \
    intltool \
    libxml++2.6-dev \
    libsigc++-2.0-dev \
    libglibmm-2.4-dev \
    libgtkmm-3.0-dev \
    libmlt++-dev \
    libmlt-dev \
    libfftw3-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libmagick++-dev \
    libopenexr-dev \
    libboost-all-dev
```

---

## 2. Compilation

```bash
bash bridge/scripts/fetch_synfig.sh
bash bridge/scripts/apply_patches.sh
bash bridge/scripts/build_linux.sh
```

The resulting binary will be available at:
`build_synfig/build_linux/install/bin/synfigstudio`

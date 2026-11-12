#!/usr/bin/env bash
# Install the Synfig engine the project targets, without FUSE or root.
#
# The MCP is developed against Synfig 1.5.5 built from the commit recorded in
# bridge/PINNED_COMMIT.  Distributions ship older builds (Ubuntu 24.04 has
# 1.5.3) whose ValueNode and render-target sets differ, so the document
# validity gate must run against the pinned engine or it reports failures that
# the project's own engine does not have.
#
# The official AppImage is a type-1 image: an ISO9660 filesystem with
# zisofs-compressed files behind an ELF runtime.  Mounting it needs FUSE, which
# CI containers do not provide, so it is unpacked with bsdtar (libarchive
# decompresses zisofs) instead of being mounted.
#
# Usage:
#   bash scripts/install_pinned_synfig.sh [DEST_DIR]
#
# The engine is extracted into DEST_DIR (default: ./synfig-engine) and a
# ``synfig`` wrapper is created there.  Put DEST_DIR on PATH to use it.

set -euo pipefail

VERSION="1.5.5"
ASSET="SynfigStudio-1.5.5-2026.03.15-linux64-79bf7.appimage"
SHA256="b85aabc26f690a0c150d2143c656c17f358b73abbedf8d01007f15a7a95740e9"
URL="https://github.com/synfig/synfig/releases/download/v${VERSION}/${ASSET}"

DEST="${1:-$PWD/synfig-engine}"
APPIMAGE="${DEST}/${ASSET}"

if ! command -v bsdtar >/dev/null 2>&1; then
    echo "ERROR: bsdtar is required to unpack the AppImage (install libarchive-tools)." >&2
    exit 1
fi

mkdir -p "${DEST}"

echo "=== Downloading pinned Synfig ${VERSION} engine ==="
curl -fL --retry 3 --retry-delay 2 -o "${APPIMAGE}" "${URL}"

echo "=== Verifying SHA256 ==="
echo "${SHA256}  ${APPIMAGE}" | sha256sum -c -

echo "=== Extracting (FUSE-free) ==="
bsdtar -xf "${APPIMAGE}" -C "${DEST}"
rm -f "${APPIMAGE}"

# The extracted files lose the executable bit, and the binary has no RPATH, so
# a wrapper exposes the bundled libraries and the binary as ``synfig``.
chmod +x "${DEST}"/usr/bin/* 2>/dev/null || true
cat > "${DEST}/synfig" <<'WRAPPER'
#!/usr/bin/env bash
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$HERE/usr/lib:$HERE/usr/lib/x86_64-linux-gnu:$HERE/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SYNFIG_MODULE_DIR="$HERE/usr/lib/synfig/modules"
# The bundled fontconfig looks for its configuration under the path it was
# built with, which does not exist here; point it at the AppImage's own copy.
export FONTCONFIG_FILE="$HERE/usr/etc/fonts/fonts.conf"
export FONTCONFIG_PATH="$HERE/usr/etc/fonts"
exec "$HERE/usr/bin/synfig" "$@"
WRAPPER
chmod +x "${DEST}/synfig"

echo "=== Synfig engine ready: ${DEST}/synfig ==="
"${DEST}/synfig" --version

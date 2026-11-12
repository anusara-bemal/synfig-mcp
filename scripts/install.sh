#!/usr/bin/env bash
#
# One-command installer for synfig-mcp.
#
#   curl -fsSL https://raw.githubusercontent.com/anusara-bemal/synfig-mcp/main/scripts/install.sh | bash
#
# It installs the Python server (preferred: uv, fallback: pip), verifies the
# installation with `synfig-mcp doctor` and prints the client configuration.
set -euo pipefail

BLUE="\033[1;34m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
NC="\033[0m"

info()  { printf "%b\n" "${BLUE}==>${NC} $*"; }
ok()    { printf "%b\n" "${GREEN}✔${NC} $*"; }
warn()  { printf "%b\n" "${YELLOW}!${NC} $*"; }
fail()  { printf "%b\n" "${RED}✘${NC} $*" >&2; exit 1; }

printf "%b\n" "${BLUE}synfig-mcp installer${NC}"
printf "%b\n" "   author: ABM · license: MIT (server) / GPL-3.0 (bridge)"
printf "\n"

# --- prerequisites -----------------------------------------------------------
command -v python3 >/dev/null 2>&1 || fail "python3 is required (3.12 or newer)"
PY_OK=$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 12) else 0)')
[ "$PY_OK" = "1" ] || fail "python 3.12 or newer is required (found: $(python3 --version))"

INSTALL_DIR="${SYNFIG_MCP_HOME:-$HOME/.synfig-mcp}"
mkdir -p "$INSTALL_DIR"

# --- install -----------------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
  info "Installing with uv into $INSTALL_DIR"
  uv tool install synfig-mcp --with "pillow>=10.3.0" --force 2>/dev/null \
    || uv tool install --force synfig-mcp
  BIN_DIR="$(uv tool dir --bin 2>/dev/null || printf '%s' "$HOME/.local/bin")"
  BIN="$BIN_DIR/synfig-mcp"
else
  warn "uv not found - falling back to pip"
  info "Installing with pip into $INSTALL_DIR"
  python3 -m pip install --upgrade pip >/dev/null
  python3 -m pip install --user --upgrade synfig-mcp
  BIN="$HOME/.local/bin/synfig-mcp"
  [ -x "$BIN" ] || BIN="$(command -v synfig-mcp || true)"
fi

[ -n "$BIN" ] && [ -x "$BIN" ] || fail "the synfig-mcp executable was not found after installation"

ok "installed: $BIN"

# --- verify ------------------------------------------------------------------
info "Running synfig-mcp doctor"
if "$BIN" doctor; then
  ok "doctor finished"
else
  warn "doctor reported issues - see the output above"
fi

# --- client configuration ----------------------------------------------------
cat <<'EOF'

Add this to your MCP client configuration:

  {
    "mcpServers": {
      "synfig": {
        "command": "synfig-mcp",
        "env": {
          "SYNFIG_MCP_PROFILE": "all",
          "SYNFIG_MCP_BACKEND": "auto"
        }
      }
    }
  }

Live mode additionally needs the patched Synfig Studio:
  1. Download it from https://github.com/anusara-bemal/synfig-mcp/releases
  2. Start it and enable "Tools -> MCP Bridge"

EOF

ok "done. Start the server with: synfig-mcp"

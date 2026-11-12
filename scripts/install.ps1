<#
.SYNOPSIS
    One-command installer for synfig-mcp (Windows / PowerShell).

.EXAMPLE
    irm https://raw.githubusercontent.com/anusara-bemal/synfig-mcp/main/scripts/install.ps1 | iex

.DESCRIPTION
    Installs the Python server (preferred: uv, fallback: pip), verifies the
    installation with `synfig-mcp doctor` and prints the client configuration.
#>

$ErrorActionPreference = "Stop"

function Write-Info($Message) { Write-Host "==> $Message" -ForegroundColor Blue }
function Write-Ok($Message)    { Write-Host "OK  $Message" -ForegroundColor Green }
function Write-Warn($Message)  { Write-Host "!   $Message" -ForegroundColor Yellow }
function Write-Fail($Message)  { Write-Host "X   $Message" -ForegroundColor Red; exit 1 }

Write-Host "synfig-mcp installer" -ForegroundColor Blue
Write-Host "   author: ABM - license: MIT (server) / GPL-3.0 (bridge)"
Write-Host ""

# --- prerequisites -----------------------------------------------------------
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { Write-Fail "python is required (3.12 or newer)" }

$version = & python -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]($version -replace '[^0-9.].*$', '') -lt 3) {
    Write-Fail "python 3.12 or newer is required (found $version)"
}

# --- install -----------------------------------------------------------------
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    Write-Info "Installing with uv"
    & uv tool install --force synfig-mcp
    if ($LASTEXITCODE -ne 0) { Write-Fail "uv tool install failed" }
    $binDir = (& uv tool dir --bin 2>$null)
    if (-not $binDir) { $binDir = Join-Path $env:USERPROFILE ".local\bin" }
} else {
    Write-Warn "uv not found - falling back to pip"
    Write-Info "Installing with pip"
    & python -m pip install --upgrade pip | Out-Null
    & python -m pip install --user --upgrade synfig-mcp
    if ($LASTEXITCODE -ne 0) { Write-Fail "pip install failed" }
    $binDir = Join-Path $env:USERPROFILE "AppData\Roaming\Python\Python312\Scripts"
}

$mcpExe = Get-Command synfig-mcp -ErrorAction SilentlyContinue
if (-not $mcpExe) {
    $candidate = Join-Path $binDir "synfig-mcp.exe"
    if (Test-Path $candidate) { $mcpExe = $candidate }
}
if (-not $mcpExe) { Write-Fail "the synfig-mcp executable was not found after installation" }

Write-Ok "installed: $($mcpExe.Source)"

# --- verify ------------------------------------------------------------------
Write-Info "Running synfig-mcp doctor"
& $mcpExe.Source doctor
Write-Ok "doctor finished"

# --- client configuration ----------------------------------------------------
Write-Host ""
Write-Host "Add this to your MCP client configuration:" -ForegroundColor Blue
Write-Host @'
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
'@
Write-Host ""
Write-Host "Live mode additionally needs the patched Synfig Studio:" -ForegroundColor Blue
Write-Host "  1. Download it from https://github.com/anusara-bemal/synfig-mcp/releases"
Write-Host "  2. Start it and enable 'Tools -> MCP Bridge'"
Write-Host ""
Write-Ok "done. Start the server with: synfig-mcp"

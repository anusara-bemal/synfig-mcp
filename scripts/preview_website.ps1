# Synfig MCP Website Preview
$WebsiteDir = Join-Path $PSScriptRoot "..\website"
Write-Host "Opening Synfig MCP website preview..." -ForegroundColor Cyan
Start-Process (Join-Path $WebsiteDir "index.html")

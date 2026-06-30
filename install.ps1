# Hermes Agent — install the MiniMax image-generation provider plugin
# (Windows native, PowerShell).
#
# This script does NOT touch your API key. If your `minimax-cn` chat provider
# is already configured, that key is picked up automatically (Token Plan
# covers image on the same quota). Otherwise set MINIMAX_CN_API_KEY later.

$ErrorActionPreference = "Stop"

$RepoRaw = "https://raw.githubusercontent.com/Upstream17/hermes-minimax-image-plugin/main"

# Per official Hermes docs, user plugins live under
#   %LOCALAPPDATA%\hermes\plugins\image_gen\<name>\
# (NOT under plugins\minimax — that's a legacy path).
if ($env:HERMES_HOME) {
    $PluginDir = Join-Path $env:HERMES_HOME "plugins\image_gen\minimax"
} else {
    $PluginDir = Join-Path $env:LOCALAPPDATA "hermes\plugins\image_gen\minimax"
}

Write-Host "Installing plugin to: $PluginDir"
New-Item -ItemType Directory -Force -Path $PluginDir | Out-Null

Invoke-WebRequest -Uri "$RepoRaw/plugin/__init__.py" -OutFile (Join-Path $PluginDir "__init__.py") -UseBasicParsing
Invoke-WebRequest -Uri "$RepoRaw/plugin/plugin.yaml" -OutFile (Join-Path $PluginDir "plugin.yaml") -UseBasicParsing

Write-Host ""
Write-Host "Plugin files installed:"
Get-ChildItem $PluginDir
Write-Host ""

# --- Enable the plugin and route image_generate to it ---
# The official `hermes plugins enable` command is the recommended way
# (per https://hermes-agent.nousresearch.com/docs/developer-guide/image-gen-provider-plugin).
$hermes = Get-Command hermes -ErrorAction SilentlyContinue
if ($hermes) {
    Write-Host "Enabling the 'minimax' plugin and switching image_gen.provider..."
    try {
        & hermes plugins enable minimax
        Write-Host "Plugin enabled via `hermes plugins enable`."
    } catch {
        Write-Host "WARN: 'hermes plugins enable minimax' failed. Run it manually after this script."
    }
    try {
        & hermes config set image_gen.provider minimax | Out-Null
    } catch {
        Write-Host "WARN: 'hermes config set image_gen.provider minimax' failed. Run it manually."
    }
} else {
    Write-Host "WARN: 'hermes' is not on PATH — you'll need to enable the plugin manually:"
    Write-Host "      hermes plugins enable minimax"
    Write-Host "      hermes config set image_gen.provider minimax"
}

Write-Host ""
Write-Host "============================================"
Write-Host "Done. Verify the install:"
Write-Host "============================================"
Write-Host ""
Write-Host "  \$env:HERMES_PLUGINS_DEBUG=1; hermes chat -q 'ping' --yolo -Q 2>&1 | Select-String minimax"
Write-Host "  # Expected: Plugin 'minimax' registered image_gen provider: minimax"
Write-Host ""
Write-Host "If the minimax-cn chat provider is already configured, the same key is"
Write-Host "used automatically (Token Plan shares one quota). Otherwise, set the key:"
Write-Host ""
Write-Host "  Add-Content '$env:LOCALAPPDATA\hermes\.env' 'MINIMAX_CN_API_KEY=eyJhbGc...'"
Write-Host ""
Write-Host "Real test:"
Write-Host "  hermes chat -q 'Generate an image: a small red apple on a white background' --yolo -Q"
Write-Host ""

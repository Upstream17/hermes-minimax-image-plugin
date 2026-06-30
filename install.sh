#!/usr/bin/env bash
# Hermes Agent — install the MiniMax image-generation provider plugin
# (macOS / Linux / WSL).
#
# This script does NOT touch your API key. If your `minimax-cn` chat provider
# is already configured, that key is picked up automatically (Token Plan
# covers image on the same quota). Otherwise set MINIMAX_CN_API_KEY later.

set -e

REPO_RAW="https://raw.githubusercontent.com/Upstream17/hermes-minimax-image-plugin/main"

# --- Detect plugin install directory (per official Hermes docs) ---
# Hermes scans ~/.hermes/plugins/image_gen/<name>/ for user plugins.
if [[ -n "$HERMES_HOME" ]]; then
    PLUGIN_DIR="$HERMES_HOME/plugins/image_gen/minimax"
elif [[ "$OSTYPE" == "darwin"* || "$OSTYPE" == "linux-gnu"* ]]; then
    PLUGIN_DIR="$HOME/.hermes/plugins/image_gen/minimax"
elif [[ -n "$WSL_DISTRO_NAME" || -n "$WSLENV" ]]; then
    # WSL: HOME points to the Linux user dir, but Hermes on WSL uses the
    # Linux-style path. Fall back to ~/.hermes (NOT /mnt/c/... — that's
    # the Windows-side config, not the WSL one).
    PLUGIN_DIR="$HOME/.hermes/plugins/image_gen/minimax"
else
    echo "ERROR: this script supports macOS / Linux / WSL."
    echo "On Windows native, run install.ps1 from PowerShell instead."
    exit 1
fi

# --- Download plugin files ---
echo "Installing plugin to: $PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"

fetch() {
    local url=$1
    local out=$2
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url" -o "$out"
    elif command -v wget >/dev/null 2>&1; then
        wget -q "$url" -O "$out"
    else
        echo "ERROR: neither curl nor wget is installed."
        exit 1
    fi
}

fetch "$REPO_RAW/plugin/__init__.py" "$PLUGIN_DIR/__init__.py"
fetch "$REPO_RAW/plugin/plugin.yaml" "$PLUGIN_DIR/plugin.yaml"

echo ""
echo "Plugin files installed:"
ls -la "$PLUGIN_DIR"
echo ""

# --- Enable the plugin and route image_generate to it ---
# The official `hermes plugins enable` command is the recommended way
# (per https://hermes-agent.nousresearch.com/docs/developer-guide/image-gen-provider-plugin).
# It registers the plugin in plugins.enabled and avoids the
# list-as-string malformation that the older `hermes config set` approach hit.
if command -v hermes >/dev/null 2>&1; then
    echo "Enabling the 'minimax' plugin and switching image_gen.provider..."
    if hermes plugins enable minimax 2>&1; then
        echo ""
        echo "Plugin enabled via `hermes plugins enable`."
    else
        echo ""
        echo "WARN: 'hermes plugins enable minimax' returned non-zero."
        echo "      Run it manually after this script if needed."
    fi

    if command -v hermes >/dev/null 2>&1; then
        # Set the active provider (model defaults to image-01 inside the plugin).
        hermes config set image_gen.provider minimax 2>/dev/null || \
            echo "WARN: 'hermes config set image_gen.provider minimax' failed; run manually."
    fi
else
    echo "WARN: 'hermes' is not on PATH — you'll need to enable the plugin manually:"
    echo "      hermes plugins enable minimax"
    echo "      hermes config set image_gen.provider minimax"
fi

echo ""
echo "============================================"
echo "Done. Verify the install:"
echo "============================================"
echo ""
echo "  HERMES_PLUGINS_DEBUG=1 hermes chat -q 'ping' --yolo -Q 2>&1 | grep minimax"
echo "  # Expected: Plugin 'minimax' registered image_gen provider: minimax"
echo ""
echo "If the minimax-cn chat provider is already configured, the same key is"
echo "used automatically (Token Plan shares one quota). Otherwise, set the key:"
echo ""
echo "  echo 'MINIMAX_CN_API_KEY=eyJhbGc...' >> ~/.hermes/.env"
echo ""
echo "Real test:"
echo "  hermes chat -q 'Generate an image: a small red apple on a white background' --yolo -Q"
echo ""

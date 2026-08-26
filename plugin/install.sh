#!/bin/bash
# LazyBlend Omarchy plugin installer
# Run this from the lazyblend repo directory

set -euo pipefail

PLUGIN_DIR="$HOME/.config/omarchy/plugins/lazyblend"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "Installing LazyBlend Omarchy plugin..."

# Install lazyblend Python package
echo "Installing Python package..."
cd "$REPO_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Create plugin directory
mkdir -p "$PLUGIN_DIR"

# Link files
chmod +x "$SCRIPT_DIR/omarchy-lazyblend"
ln -sf "$SCRIPT_DIR/omarchy-lazyblend" "$PLUGIN_DIR/omarchy-lazyblend"
ln -sf "$SCRIPT_DIR/omarchy-menu.jsonc" "$PLUGIN_DIR/omarchy-menu.jsonc"

echo "Done! LazyBlend is now available in your Omarchy app launcher."
echo "Run 'omarchy restart shell' to reload the shell if needed."

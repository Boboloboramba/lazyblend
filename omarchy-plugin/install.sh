#!/bin/bash
# Install LazyBlend as an Omarchy bar widget
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$HOME/.config/omarchy/plugins/lazyblend"

echo "Installing LazyBlend bar widget..."

# Install Python package
cd "$SCRIPT_DIR/.."
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -e . --quiet

# Create plugin directory
mkdir -p "$PLUGIN_DIR"

# Symlink plugin files
ln -sf "$SCRIPT_DIR/manifest.json" "$PLUGIN_DIR/manifest.json"
ln -sf "$SCRIPT_DIR/LazyBlendWidget.qml" "$PLUGIN_DIR/LazyBlendWidget.qml"

# Add to shell.json if not already present
SHELL_JSON="$HOME/.config/omarchy/shell.json"
if ! grep -q '"lazyblend"' "$SHELL_JSON" 2>/dev/null; then
  echo "Adding lazyblend to bar layout..."
  # Use python to safely modify JSON
  python3 -c "
import json
with open('$SHELL_JSON') as f:
    cfg = json.load(f)
right = cfg.get('bar', {}).get('layout', {}).get('right', [])
# Insert after tray
insert_idx = next((i for i, w in enumerate(right) if w.get('id') == 'omarchy.tray'), 0)
right.insert(insert_idx + 1, {'id': 'lazyblend'})
with open('$SHELL_JSON', 'w') as f:
    json.dump(cfg, f, indent=2)
print('Added lazyblend to bar layout')
"
fi

echo "Done! Run 'omarchy restart shell' to see the widget."

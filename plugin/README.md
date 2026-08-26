# LazyBlend Omarchy Plugin

This plugin adds LazyBlend to your Omarchy Quattro shell, making it accessible from the app launcher and status bar.

## Installation

### Quick Install (recommended)

```bash
# From the lazyblend repo directory
./plugin/install.sh
```

### Manual Install

```bash
# 1. Install lazyblend to your system
cd ~/lazyblend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Create the Omarchy plugin directory
mkdir -p ~/.config/omarchy/plugins/lazyblend

# 3. Link the launcher script
ln -s ~/lazyblend/plugin/omarchy-lazyblend ~/.config/omarchy/plugins/lazyblend/omarchy-lazyblend

# 4. Link the menu entry
ln -s ~/lazyblend/plugin/omarchy-menu.jsonc ~/.config/omarchy/plugins/lazyblend/omarchy-menu.jsonc
```

## What It Does

- Adds "LazyBlend" to the Omarchy app launcher menu
- Creates an `omarchy-lazyblend` command on PATH
- Launches LazyBlend in a terminal when selected

## Uninstall

```bash
rm -rf ~/.config/omarchy/plugins/lazyblend
```

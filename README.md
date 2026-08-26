# LazyBlend

A fast, fuzzy-searching TUI for browsing and launching Blender `.blend` files. Built with [Textual](https://textual.textualize.io/) and inspired by [LazyGit](https://github.com/jesseduffield/lazygit) and [LazyDocker](https://github.com/jesseduffield/lazydocker).

![LazyBlend](https://img.shields.io/badge/status-alpha-blue) ![Python](https://img.shields.io/badge/python-3.10+-green) ![License](https://img.shields.io/badge/license-MIT-yellow)

## Features

- **Fuzzy search** — quickly find blend files with scoring-based matching
- **File metadata** — shows file size, modification date, and Blender version from the file header
- **Favorites** — bookmark frequently used blend files
- **Recent files** — tracks recently opened files
- **Directory scanning** — recursively scans configured directories for blend files
- **Batch open** — open multiple files in Blender at once
- **Clipboard integration** — copy file paths with `c`
- **File manager integration** — open containing folder with `d`
- **Delete with confirmation** — safely delete blend files
- **Vim-style navigation** — `j`/`k` to move, `/` to search, `enter` to open
- **Omarchy plugin** — install as an Omarchy Quattro shell plugin

## Install

```bash
# Clone the repo
git clone https://github.com/Boboloboramba/lazyblend.git
cd lazyblend

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Or install directly
pip install .
```

## Usage

```bash
# Run from anywhere
lazyblend

# Or run with Python module
python -m lazyblend

# Or run directly
python src/lazyblend/app.py
```

### Keybindings

| Key | Action |
|-----|--------|
| `j` / `k` or `↑` / `↓` | Navigate up/down |
| `enter` or `o` | Open selected file in Blender |
| `/` | Focus search filter |
| `escape` | Clear search / close help |
| `f` | Toggle favorite |
| `d` | Open containing folder in file manager |
| `c` | Copy file path to clipboard |
| `x` | Delete file (with confirmation) |
| `b` | Batch open all filtered files |
| `r` | Rescan directories |
| `1` | Show all files |
| `2` | Show favorites only |
| `3` | Show recent only |
| `?` | Toggle help overlay |
| `q` | Quit |

## Configuration

LazyBlend stores its configuration in `~/.config/lazyblend/`:

- `config.json` — scan directories, Blender path, preferences
- `favorites.json` — bookmarked blend files
- `recent.json` — recently opened files

### Config options

```json
{
  "scan_dirs": [
    "~/Documents",
    "~/Projects",
    "~/Desktop",
    "~"
  ],
  "blender_path": "blender",
  "max_recent": 50,
  "show_hidden": false,
  "sort_by": "name",
  "sort_reverse": false
}
```

## Omarchy Bar Widget

LazyBlend can be installed as an Omarchy Quattro bar widget. Run the installer:

```bash
cd ~/lazyblend
./omarchy-plugin/install.sh
omarchy restart shell
```

This adds a Blender icon (󰚩) to your status bar. Click it to launch LazyBlend in a terminal.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run with dev tools
textual run lazyblend.app:LazyBlendApp --dev
```

## License

MIT

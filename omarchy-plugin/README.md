# LazyBlend

A fast, fuzzy-searching TUI for browsing and launching Blender `.blend` files, available as an Omarchy bar widget.

## Features

- Fuzzy search by filename, objects, materials, collections, and scenes
- Deep file inspection via Blender's Python API
- Thumbnail previews rendered as Unicode block art
- Favorites, recent files, and multi-select batch open
- Metadata caching for instant loading
- Vim-style navigation

## Install (Marketplace)

```sh
omarchy plugin add https://github.com/Boboloboramba/lazyblend.git --enable
```

## Install (Manual)

```sh
cd ~/lazyblend
./omarchy-plugin/install.sh
omarchy restart shell
```

## Usage

Click the Blender icon (󰚩) in the bar to open LazyBlend in a terminal.

## Remove

```sh
omarchy plugin remove io.github.Boboloboramba.lazyblend
```

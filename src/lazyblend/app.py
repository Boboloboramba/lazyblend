"""Main LazyBlend TUI application."""

import subprocess
import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Input,
    Static,
    Label,
    Button,
    SelectionList,
)
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual import on, work
from textual.worker import get_current_worker
from rapidfuzz import fuzz

from lazyblend.blend_parser import BlendInfo
from lazyblend.scanner import scan_for_blends
from lazyblend.config import (
    Config,
    load_favorites,
    save_favorites,
    load_recent,
    save_recent,
)


HELP_TEXT = """\
[bold]LazyBlend[/bold] - Blender File Manager

[bold cyan]Navigation[/bold cyan]
  j/k or ↑/↓     Move up/down
  enter           Open selected file in Blender
  /               Focus search filter
  escape          Clear search / close panel
  tab             Switch between panels

[bold cyan]Actions[/bold cyan]
  o               Open in Blender
  d               Show file in file manager
  f               Toggle favorite
  r               Rescan directories
  c               Copy file path to clipboard
  x               Delete file (with confirmation)
  b               Batch open selected files

[bold cyan]Views[/bold cyan]
  1               All files
  2               Favorites only
  3               Recent only

[bold cyan]Other[/bold cyan]
  ?               Toggle this help
  q               Quit
"""


class LazyBlendApp(App):
    """A TUI for browsing and launching Blender blend files."""

    TITLE = "LazyBlend"
    SUB_TITLE = "Blender File Manager"

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 30fr;
        grid-rows: 1fr;
    }

    #sidebar {
        width: 100%;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #sidebar Button {
        width: 100%;
        margin: 0 0 1 0;
    }

    #main-panel {
        width: 100%;
        height: 100%;
    }

    #search {
        dock: top;
        margin: 0 0 1 0;
    }

    #file-table {
        width: 100%;
        height: 1fr;
    }

    #info-panel {
        dock: bottom;
        height: auto;
        max-height: 12;
        border: solid $accent;
        padding: 1;
        margin: 1 0 0 0;
        background: $surface;
    }

    #help-overlay {
        layer: overlay;
        width: 60;
        height: auto;
        max-height: 90%;
        margin: 4 4;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
        display: none;
    }

    #help-overlay.visible {
        display: block;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $primary-background-lighten-2;
        color: $text;
        padding: 0 1;
    }

    DataTable > .datatable--header {
        background: $primary-background-lighten-1;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("question_mark", "toggle_help", "Help", show=False),
        Binding("slash", "focus_search", "Search", show=False),
        Binding("escape", "clear_search", "Clear", show=False),
        Binding("o", "open_blender", "Open", show=False),
        Binding("enter", "open_blender", "Open", show=False),
        Binding("f", "toggle_favorite", "Favorite", show=False),
        Binding("r", "rescan", "Rescan", show=False),
        Binding("d", "open_in_fm", "File Manager", show=False),
        Binding("c", "copy_path", "Copy Path", show=False),
        Binding("x", "delete_file", "Delete", show=False),
        Binding("b", "batch_open", "Batch Open", show=False),
        Binding("1", "show_all", "All Files", show=False),
        Binding("2", "show_favorites", "Favorites", show=False),
        Binding("3", "show_recent", "Recent", show=False),
        Binding("j", "cursor_down", "Down", show=False, key_display="j"),
        Binding("k", "cursor_up", "Up", show=False, key_display="k"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = Config.load()
        self.all_files: list[BlendInfo] = []
        self.filtered_files: list[BlendInfo] = []
        self.favorites: list[str] = load_favorites()
        self.recent: list[str] = load_recent()
        self.current_filter: str = ""
        self.current_view: str = "all"  # all, favorites, recent
        self._help_visible = False

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[bold]LazyBlend[/bold]", id="title")
                yield Button("All Files [1]", id="btn-all", variant="primary")
                yield Button("Favorites [2]", id="btn-favs")
                yield Button("Recent [3]", id="btn-recent")
                yield Button("Rescan [r]", id="btn-rescan")
                yield Button("Help [?]", id="btn-help")
                yield Static("", id="stats-label")

            with Vertical(id="main-panel"):
                yield Input(placeholder="Type to filter blend files... [↑↓ navigate, enter to open]", id="search")
                yield DataTable(id="file-table")
                yield Static("Select a file to see details", id="info-panel")

        yield Footer()
        yield Static("", id="status-bar")
        yield Static(HELP_TEXT, id="help-overlay")

    def on_mount(self) -> None:
        table = self.query_one("#file-table", DataTable)
        table.add_columns("File", "Size", "Modified", "Version")
        table.cursor_type = "row"
        table.zebra_stripes = True

        self._update_stats()
        self.action_rescan()

    def _update_stats(self) -> None:
        stats = self.query_one("#stats-label", Static)
        total = len(self.all_files)
        favs = len(self.favorites)
        recs = len(self.recent)
        stats.update(f"[dim]{total} files[/dim]\n[dim]{favs} favorites[/dim]\n[dim]{recs} recent[/dim]")

    def _update_status(self, msg: str) -> None:
        bar = self.query_one("#status-bar", Static)
        bar.update(msg)

    def _update_info_panel(self, info: BlendInfo | None) -> None:
        panel = self.query_one("#info-panel", Static)
        if info is None:
            panel.update("Select a file to see details")
            return

        path = Path(info.path)
        lines = [
            f"[bold]{path.name}[/bold]",
            f"Path: {info.path}",
            f"Size: {info.size_str}",
            f"Modified: {info.modified_str}",
        ]
        if info.valid:
            lines.append(f"Version: {info.version}")
            lines.append(f"Pointer: {info.pointer_size} | {info.endianness}")
        else:
            lines.append("[dim]Not a valid .blend file header[/dim]")

        if info.path in self.favorites:
            lines.append("[yellow]★ Favorite[/yellow]")

        panel.update("\n".join(lines))

    def _populate_table(self) -> None:
        table = self.query_one("#file-table", DataTable)
        table.clear()

        for info in self.filtered_files:
            path = Path(info.path)
            is_fav = info.path in self.favorites
            name = f"★ {path.name}" if is_fav else path.name
            parent = path.parent.name
            display = f"{name} [dim]({parent})[/dim]"

            table.add_row(
                display,
                info.size_str,
                info.modified_str,
                info.version if info.valid else "[dim]unknown[/dim]",
            )

        count = len(self.filtered_files)
        self._update_status(f"Showing {count} file{'s' if count != 1 else ''}")

    def _apply_filter(self) -> None:
        query = self.current_filter.lower().strip()

        if self.current_view == "favorites":
            pool = [f for f in self.all_files if f.path in self.favorites]
        elif self.current_view == "recent":
            pool = [f for f in self.all_files if f.path in self.recent]
        else:
            pool = self.all_files

        if not query:
            self.filtered_files = pool
        else:
            scored = []
            for info in pool:
                name = Path(info.path).name.lower()
                # Use token_set_ratio for better multi-word matching
                score = max(
                    fuzz.partial_ratio(query, name),
                    fuzz.token_set_ratio(query, name),
                )
                if score > 40:
                    scored.append((score, info))
            scored.sort(key=lambda x: x[0], reverse=True)
            self.filtered_files = [info for _, info in scored]

        self._populate_table()

    @on(Input.Changed, "#search")
    def on_search_changed(self, event: Input.Changed) -> None:
        self.current_filter = event.value
        self._apply_filter()

    @on(DataTable.RowSelected, "#file-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_index is not None and 0 <= event.row_index < len(self.filtered_files):
            info = self.filtered_files[event.row_index]
            self._update_info_panel(info)

    @on(Button.Pressed, "#btn-all")
    def on_btn_all(self) -> None:
        self.action_show_all()

    @on(Button.Pressed, "#btn-favs")
    def on_btn_favs(self) -> None:
        self.action_show_favorites()

    @on(Button.Pressed, "#btn-recent")
    def on_btn_recent(self) -> None:
        self.action_show_recent()

    @on(Button.Pressed, "#btn-rescan")
    def on_btn_rescan(self) -> None:
        self.action_rescan()

    @on(Button.Pressed, "#btn-help")
    def on_btn_help(self) -> None:
        self.action_toggle_help()

    def _get_selected_file(self) -> BlendInfo | None:
        table = self.query_one("#file-table", DataTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self.filtered_files):
            return self.filtered_files[table.cursor_row]
        return None

    # --- Actions ---

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_clear_search(self) -> None:
        search = self.query_one("#search", Input)
        if search.value:
            search.value = ""
        elif self._help_visible:
            self.action_toggle_help()

    def action_toggle_help(self) -> None:
        overlay = self.query_one("#help-overlay", Static)
        self._help_visible = not self._help_visible
        if self._help_visible:
            overlay.add_class("visible")
        else:
            overlay.remove_class("visible")

    def action_open_blender(self) -> None:
        info = self._get_selected_file()
        if info is None:
            return

        self._update_status(f"Opening {Path(info.path).name} in Blender...")
        self._launch_blender(info.path)

    @work(thread=True, group="blender")
    def _launch_blender(self, filepath: str) -> None:
        worker = get_current_worker()
        try:
            subprocess.Popen(
                [self.config.blender_path, filepath],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            # Track as recent
            self.call_from_thread(self._track_recent, filepath)
            self.call_from_thread(self._update_status, f"Launched {Path(filepath).name}")
        except FileNotFoundError:
            self.call_from_thread(
                self._update_status, f"Error: Blender not found at '{self.config.blender_path}'"
            )
        except Exception as e:
            self.call_from_thread(self._update_status, f"Error launching Blender: {e}")

    def _track_recent(self, filepath: str) -> None:
        if filepath in self.recent:
            self.recent.remove(filepath)
        self.recent.insert(0, filepath)
        save_recent(self.recent, self.config.max_recent)

    def action_toggle_favorite(self) -> None:
        info = self._get_selected_file()
        if info is None:
            return

        if info.path in self.favorites:
            self.favorites.remove(info.path)
            self._update_status(f"Removed from favorites: {Path(info.path).name}")
        else:
            self.favorites.append(info.path)
            self._update_status(f"Added to favorites: {Path(info.path).name}")

        save_favorites(self.favorites)
        self._update_stats()
        self._apply_filter()

    def action_rescan(self) -> None:
        self._update_status("Scanning for blend files...")
        self._run_scan()

    @work(thread=True, group="scan")
    def _run_scan(self) -> None:
        worker = get_current_worker()
        files = scan_for_blends(
            self.config.scan_dirs,
            show_hidden=self.config.show_hidden,
        )
        self.call_from_thread(self._on_scan_complete, files)

    def _on_scan_complete(self, files: list[BlendInfo]) -> None:
        self.all_files = files
        self._update_stats()
        self._apply_filter()
        self._update_status(f"Found {len(files)} blend files")

    def action_open_in_fm(self) -> None:
        info = self._get_selected_file()
        if info is None:
            return
        dir_path = str(Path(info.path).parent)
        try:
            subprocess.Popen(["xdg-open", dir_path], start_new_session=True)
        except Exception:
            self._update_status("Could not open file manager")

    def action_copy_path(self) -> None:
        info = self._get_selected_file()
        if info is None:
            return
        try:
            subprocess.run(
                ["wl-copy", info.path],
                check=True,
                capture_output=True,
            )
            self._update_status(f"Copied: {info.path}")
        except (FileNotFoundError, subprocess.CalledProcessError):
            self._update_status("Could not copy to clipboard (install wl-clipboard)")

    def action_delete_file(self) -> None:
        info = self._get_selected_file()
        if info is None:
            return
        self._pending_delete = info
        self.push_screen(DeleteConfirmScreen(info))

    def confirm_delete(self, confirmed: bool) -> None:
        info = getattr(self, "_pending_delete", None)
        if not confirmed or info is None:
            self._update_status("Delete cancelled")
            return

        try:
            Path(info.path).unlink()
            if info.path in self.favorites:
                self.favorites.remove(info.path)
                save_favorites(self.favorites)
            if info.path in self.recent:
                self.recent.remove(info.path)
                save_recent(self.recent, self.config.max_recent)
            self._update_status(f"Deleted: {Path(info.path).name}")
            self.action_rescan()
        except Exception as e:
            self._update_status(f"Error deleting: {e}")

    def action_batch_open(self) -> None:
        selected = []
        table = self.query_one("#file-table", DataTable)
        for row_idx in table.cursor_type == "row" and range(len(self.filtered_files)) or []:
            # In row mode, we just open all filtered files
            pass

        # Open all currently filtered files
        if not self.filtered_files:
            self._update_status("No files to open")
            return

        for info in self.filtered_files[:10]:  # Limit to 10
            try:
                subprocess.Popen(
                    [self.config.blender_path, info.path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception:
                pass

        self._update_status(f"Launched {min(len(self.filtered_files), 10)} files in Blender")

    def action_show_all(self) -> None:
        self.current_view = "all"
        self.query_one("#btn-all", Button).variant = "primary"
        self.query_one("#btn-favs", Button).variant = "default"
        self.query_one("#btn-recent", Button).variant = "default"
        self._apply_filter()

    def action_show_favorites(self) -> None:
        self.current_view = "favorites"
        self.query_one("#btn-all", Button).variant = "default"
        self.query_one("#btn-favs", Button).variant = "primary"
        self.query_one("#btn-recent", Button).variant = "default"
        self._apply_filter()

    def action_show_recent(self) -> None:
        self.current_view = "recent"
        self.query_one("#btn-all", Button).variant = "default"
        self.query_one("#btn-favs", Button).variant = "default"
        self.query_one("#btn-recent", Button).variant = "primary"
        self._apply_filter()

    def action_cursor_down(self) -> None:
        table = self.query_one("#file-table", DataTable)
        table.move_cursor(row=min(table.cursor_row + 1, len(self.filtered_files) - 1) if self.filtered_files else 0)

    def action_cursor_up(self) -> None:
        table = self.query_one("#file-table", DataTable)
        table.move_cursor(row=max(table.cursor_row - 1, 0))


class DeleteConfirmScreen(Screen):
    """Confirm deletion of a blend file."""

    CSS = """
    DeleteConfirmScreen {
        align: center middle;
    }
    #dialog {
        width: 50;
        height: auto;
        padding: 1 2;
        border: thick $error;
        background: $surface;
    }
    #dialog Static {
        width: 100%;
        margin: 0 0 1 0;
    }
    #dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, info: BlendInfo) -> None:
        super().__init__()
        self.info = info

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"[bold red]Delete {Path(self.info.path).name}?[/bold red]")
            yield Static(f"[dim]{self.info.path}[/dim]")
            yield Static("This cannot be undone.")
            with Horizontal():
                yield Button("Delete", variant="error", id="confirm")
                yield Button("Cancel", variant="default", id="cancel")

    @on(Button.Pressed, "#confirm")
    def on_confirm(self) -> None:
        self.app.pop_screen()
        self.app.confirm_delete(True)

    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.app.pop_screen()
        self.app.confirm_delete(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
            self.app.confirm_delete(False)


def main() -> None:
    """CLI entry point."""
    LazyBlendApp().run()


if __name__ == "__main__":
    main()

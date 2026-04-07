"""
Interactive filesystem tree TUI using Textual.

Keybindings:
    arrows / j/k  - navigate
    enter / space  - expand / collapse directory
    s             - cycle sort (size → name → size)
    o             - toggle sort order (asc ↔ desc)
    h             - toggle hidden files
    f             - toggle files shown
    /             - focus filter input
    escape        - clear filter / unfocus filter
    r             - refresh (rescan from disk)
    q             - quit
    [custom]      - user-defined commands (if any)
"""

from __future__ import annotations

import os
from threading import Timer
from typing import Callable
from dataclasses import dataclass

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Tree as TextualTree
from textual.widgets.tree import TreeNode
from textual.reactive import reactive

__version__ = "0.1.0"


class NodeMeta(dict):
    """Metadata stored for each tree node."""
    name: str
    path: str
    is_dir: bool
    is_symlink: bool
    size: int | None
    depth: int
    children: list[NodeMeta]


class Command:
    """Represents a user-defined command that can be executed on a tree node."""
    app: FileTreeApp
    key: str
    name: str
    description: str

    def exec_fn(self, node_data: NodeMeta):
        """Override this method to define what the command does."""
        raise NotImplementedError("Command exec_fn must be implemented by subclass")


class FileTreeApp(App):
    """Full-screen interactive file tree."""

    TITLE = "File Tree"
    CSS = """
    #filter-bar {
        dock: bottom;
        height: 3;
        display: none;
    }
    #filter-bar.visible {
        display: block;
    }
    #tree-view {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("o", "toggle_order", "Order"),
        Binding("h", "toggle_hidden", "Hidden"),
        Binding("f", "toggle_files", "Files"),
        Binding("r", "refresh", "Refresh"),
        Binding("slash", "show_filter", "Filter", key_display="/"),
    ]

    sort_by: reactive[str] = reactive("size")
    sort_order: reactive[str] = reactive("asc")
    ignore_hidden: reactive[bool] = reactive(True)
    show_files: reactive[bool] = reactive(True)
    filter_text: reactive[str] = reactive("")

    def __init__(
        self,
        root_path: str,
        max_depth: int = 3,
        size_threshold: int | None = None,
        size_flag_threshold: int | None = None,
        sort_by: str = "size",
        sort_order: str = "asc",
        ignore_hidden: bool = True,
        show_files: bool = True,
        get_size_fn=None,
        humanize_fn=None,
        known_extensions_cls=None,
        commands: list[Command] = [],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.root_path = os.path.abspath(root_path)
        self.max_depth = max_depth
        self.size_threshold = size_threshold
        self.size_flag_threshold = size_flag_threshold

        # Store init values - applied in on_mount
        self._init_sort_by = sort_by
        self._init_sort_order = sort_order
        self._init_ignore_hidden = ignore_hidden
        self._init_show_files = show_files

        # Injected dependencies
        self._get_size = get_size_fn or (lambda p, ignore_hidden=False: 0)
        self._humanize = humanize_fn
        self._icons = known_extensions_cls

        # In-memory tree data - populated by _scan_tree, re-rendered on setting changes
        self._tree_data: dict | None = None
        # Maps textual node id -> tree data dict
        self._node_meta: dict[int, dict] = {}

        # Debounce timer for rebuilds
        self._rebuild_timer: Timer | None = None
        self._rebuild_debounce_secs = 0.15

        # Additional bindings
        self.commands = commands
        for cmd in self.commands:
            cmd.app = self
            self._bindings._add_binding(Binding(cmd.key, cmd.name, cmd.description))

        # Guards
        self._mount_complete = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield TextualTree(self.root_path, id="tree-view")
        yield Input(placeholder="Type to filter...", id="filter-bar")
        yield Footer()

    def on_mount(self) -> None:
        tree = self.query_one("#tree-view", TextualTree)
        tree.show_root = True
        tree.root.set_label(f"{self.root_path} [dim](scanning...)[/dim]")
        tree.root.expand()

        # Set reactives - watchers won't rebuild because _mount_complete is False
        self.sort_by = self._init_sort_by
        self.sort_order = self._init_sort_order
        self.ignore_hidden = self._init_ignore_hidden
        self.show_files = self._init_show_files
        self._update_title()

        # Kick off background scan
        self._do_scan()

    @work(thread=True)
    def _do_scan(self) -> None:
        """Scan filesystem on background thread, then render on main thread."""
        tree_data = self._scan_tree(self.root_path, 0)
        self._tree_data = tree_data
        self.call_from_thread(self._render_from_data)
        self.call_from_thread(self._finish_mount)

    def _finish_mount(self) -> None:
        self._mount_complete = True

    # ------------------------------------------------------------------
    # Filesystem scan - pure data, no UI. Runs on worker thread.
    # ------------------------------------------------------------------

    def _scan_tree(self, dir_path: str, depth: int) -> dict | None:
        """Recursively scan directory and compute sizes. Returns a plain dict tree."""
        if depth > self.max_depth:
            return None

        name = os.path.basename(dir_path) or dir_path
        is_symlink = os.path.islink(dir_path)
        size = self._get_size(dir_path, ignore_hidden=self.ignore_hidden)

        if self.size_threshold is not None and size < self.size_threshold:
            return None

        node = {
            "name": name,
            "path": dir_path,
            "is_dir": True,
            "is_symlink": is_symlink,
            "size": size,
            "depth": depth,
            "children": [],
        }

        if depth >= self.max_depth:
            return node

        try:
            entries = list(os.scandir(dir_path))
        except PermissionError:
            return node

        for entry in entries:
            if self.ignore_hidden and entry.name.startswith("."):
                continue

            if entry.is_dir(follow_symlinks=False):
                child = self._scan_tree(entry.path, depth + 1)
                if child:
                    node["children"].append(child)

            elif entry.is_file(follow_symlinks=False) and self.show_files:
                try:
                    fsize = entry.stat().st_size
                except OSError:
                    fsize = 0
                if self.size_threshold is not None and fsize < self.size_threshold:
                    continue
                node["children"].append({
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": False,
                    "is_symlink": entry.is_symlink(),
                    "size": fsize,
                    "depth": depth + 1,
                    "children": [],
                })

        self._sort_data_children(node)
        return node

    def _sort_data_children(self, node: dict) -> None:
        """Sort a data node's children according to current settings."""
        reverse = self.sort_order == "desc"
        if self.sort_by == "size":
            node["children"].sort(key=lambda c: c.get("size") or 0, reverse=reverse)
        else:
            node["children"].sort(key=lambda c: c["name"].lower(), reverse=reverse)

    # ------------------------------------------------------------------
    # Rendering - takes in-memory data and builds Textual tree nodes.
    # Always runs on main thread. No IO.
    # ------------------------------------------------------------------

    def _render_from_data(self) -> None:
        """Render the in-memory tree data into the Textual tree widget."""
        tree = self.query_one("#tree-view", TextualTree)
        tree.clear()
        self._node_meta.clear()

        data = self._tree_data
        if not data:
            tree.root.set_label("No files found matching criteria.")
            return

        # Apply current sort to the entire data tree
        self._resort_data(data)

        # Apply filter if active
        render_data = data
        if self.filter_text.strip():
            render_data = self._filter_data(data, self.filter_text.strip().lower())
            if not render_data:
                tree.root.set_label("No files match filter.")
                return

        tree.root.set_label(self._make_label(
            render_data["name"],
            is_dir=True,
            is_symlink=render_data["is_symlink"],
            size=render_data["size"],
            has_children=bool(render_data["children"]),
        ))
        self._node_meta[id(tree.root)] = render_data
        self._render_children(tree.root, render_data)
        tree.root.expand()

    def _render_children(self, parent_node: TreeNode, data: dict) -> None:
        """Recursively add children to a Textual tree node from data."""
        for child_data in data["children"]:
            label = self._make_label(
                child_data["name"],
                is_dir=child_data["is_dir"],
                is_symlink=child_data["is_symlink"],
                size=child_data["size"],
                has_children=bool(child_data["children"]),
            )
            if child_data["is_dir"]:
                child_node = parent_node.add(label, expand=False, allow_expand=True)
            else:
                child_node = parent_node.add_leaf(label)
            self._node_meta[id(child_node)] = child_data
            if child_data["children"]:
                self._render_children(child_node, child_data)

    def _resort_data(self, node: dict) -> None:
        """Recursively re-sort the entire data tree in place."""
        self._sort_data_children(node)
        for child in node["children"]:
            if child["is_dir"]:
                self._resort_data(child)

    def _filter_data(self, node: dict, filter_lower: str) -> dict | None:
        """Return a filtered copy of the data tree. None if nothing matches."""
        name_matches = filter_lower in node["name"].lower()

        if node["is_dir"]:
            filtered_children = []
            for child in node["children"]:
                filtered = self._filter_data(child, filter_lower)
                if filtered:
                    filtered_children.append(filtered)

            if name_matches or filtered_children:
                return {**node, "children": filtered_children}
            return None
        else:
            return node if name_matches else None

    # ------------------------------------------------------------------
    # Label formatting
    # ------------------------------------------------------------------

    def _make_label(
        self,
        name: str,
        is_dir: bool,
        is_symlink: bool,
        size: int | None,
        has_children: bool = False,
    ) -> str:
        icon = ""
        if self._icons:
            ext = os.path.splitext(name)[1] if not is_dir else None
            icon = (
                self._icons.get_icon(
                    ext, is_dir=is_dir, is_symlink=is_symlink, has_children=has_children
                )
                + " "
            )

        label = f"{icon}{name}"

        if size is not None and size > 1024 and self._humanize:
            size_str = self._humanize(size)
            if self.size_flag_threshold is not None and size >= self.size_flag_threshold:
                label += f" [bold red]({size_str})[/bold red]"
            else:
                label += f" [green]({size_str})[/green]"

        return label

    # ------------------------------------------------------------------
    # Debounced rebuild - coalesces rapid reactive changes into one render
    # ------------------------------------------------------------------

    def _schedule_rebuild(self) -> None:
        if self._rebuild_timer is not None:
            self._rebuild_timer.cancel()
        self._rebuild_timer = Timer(
            self._rebuild_debounce_secs,
            lambda: self.call_from_thread(self._render_from_data),
        )
        self._rebuild_timer.daemon = True
        self._rebuild_timer.start()

    # ------------------------------------------------------------------
    # Reactive watchers
    # ------------------------------------------------------------------

    def watch_sort_by(self) -> None:
        if self.is_mounted and self._mount_complete:
            self._schedule_rebuild()
            self._update_title()

    def watch_sort_order(self) -> None:
        if self.is_mounted and self._mount_complete:
            self._schedule_rebuild()
            self._update_title()

    def watch_ignore_hidden(self) -> None:
        if self.is_mounted and self._mount_complete:
            # Hidden toggle changes what's on disk - rescan needed
            self._do_scan()
            self._update_title()

    def watch_show_files(self) -> None:
        if self.is_mounted and self._mount_complete:
            # File toggle changes what's scanned - rescan needed
            self._do_scan()
            self._update_title()

    def watch_filter_text(self) -> None:
        if self.is_mounted and self._mount_complete:
            self._schedule_rebuild()

    def _update_title(self) -> None:
        parts = [
            f"Sort: {self.sort_by} {self.sort_order}",
            f"Hidden: {'off' if self.ignore_hidden else 'on'}",
            f"Files: {'on' if self.show_files else 'off'}",
        ]
        self.sub_title = " | ".join(parts)

    # ------------------------------------------------------------------
    # Actions (keybindings)
    # ------------------------------------------------------------------

    def action_cycle_sort(self) -> None:
        self.sort_by = "name" if self.sort_by == "size" else "size"

    def action_toggle_order(self) -> None:
        self.sort_order = "desc" if self.sort_order == "asc" else "asc"

    def action_toggle_hidden(self) -> None:
        self.ignore_hidden = not self.ignore_hidden

    def action_toggle_files(self) -> None:
        self.show_files = not self.show_files

    def action_refresh(self) -> None:
        """Force rescan from disk."""
        tree = self.query_one("#tree-view", TextualTree)
        tree.clear()
        tree.root.set_label(f"{self.root_path} [dim](scanning...)[/dim]")
        self._do_scan()

    def action_show_filter(self) -> None:
        filter_bar = self.query_one("#filter-bar", Input)
        if filter_bar.has_class("visible"):
            filter_bar.remove_class("visible")
            filter_bar.value = ""
            self.filter_text = ""
            self.query_one("#tree-view", TextualTree).focus()
        else:
            filter_bar.add_class("visible")
            filter_bar.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-bar":
            self.filter_text = event.value

    def on_key(self, event) -> None:
        # Dismiss Error
        if self.screen and isinstance(self.screen, MessageScreen):
            self.pop_screen()

        # Dismiss filter
        elif event.key == "escape":
            filter_bar = self.query_one("#filter-bar", Input)
            if filter_bar.has_class("visible"):
                filter_bar.remove_class("visible")
                filter_bar.value = ""
                self.filter_text = ""
                self.query_one("#tree-view", TextualTree).focus()

        # Handle custom commands
        else:
            selected_node = self.query_one("#tree-view", TextualTree).cursor_node
            this_command  = next((cmd for cmd in self.commands if cmd.key == event.key), None)

            if selected_node and this_command:
                node_data = self._node_meta.get(id(selected_node))
                if node_data:
                    try:
                        result = this_command.exec_fn(node_data) # type: ignore
                        if result is True:
                            self.action_refresh()
                    except Exception as e:
                        self.bell()
                        self.push_screen(MessageScreen(f"Error executing command: {e}"))


class MessageScreen(Screen):
    """Simple screen to show a message and wait for a key press."""

    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        yield Header(name="Message")
        yield Input(value=self.message, id="message-input", disabled=True)
        yield Input("Press any key to continue...", id="prompt-input", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#message-input", Input).focus()

class ConfirmScreen(Screen):
    """Screen to ask user to confirm an action."""

    def __init__(self, message: str, on_confirm: Callable[[], None], **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.on_confirm = on_confirm

    def compose(self) -> ComposeResult:
        yield Header(name="Confirm")
        yield Input(value=self.message, id="confirm-input", disabled=True)
        yield Input("Press 'y' to confirm, any other key to cancel.", id="prompt-input", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#confirm-input", Input).focus()

    def on_key(self, event) -> None:
        try:
            app: FileTreeApp = self.app # type: ignore
            if event.key.lower() == "y":
                self.on_confirm()
            app.pop_screen()
            app.action_refresh()
        except Exception as e:
            app.pop_screen()
            app.bell()
            app.push_screen(MessageScreen(f"Error executing command: {e}"))

def launch_interactive_tree(
    path: str,
    max_depth: int = 3,
    size_threshold: int | None = None,
    size_flag_threshold: int | None = None,
    sort_by: str = "size",
    sort_order: str = "asc",
    ignore_hidden: bool = True,
    show_files: bool = True,
    get_size_fn=None,
    humanize_fn=None,
    known_extensions_cls=None,
    commands=[],
):
    """Entry point to launch the interactive tree from your click command."""
    app = FileTreeApp(
        root_path=path,
        max_depth=max_depth,
        size_threshold=size_threshold,
        size_flag_threshold=size_flag_threshold,
        sort_by=sort_by,
        sort_order=sort_order,
        ignore_hidden=ignore_hidden,
        show_files=show_files,
        get_size_fn=get_size_fn,
        humanize_fn=humanize_fn,
        known_extensions_cls=known_extensions_cls,
        commands=commands,
    )
    app.run()
import click
import humanize

from ptools.lib.flow.decorators import output_flavor

@click.group()
def cli():
    """Filesystem manipulation tools."""
    pass

@click.command()
@click.argument('path', type=click.Path(exists=True), default=".")
def info(path):
    """Display information about a file or directory."""
    import os
    import time
    path  = os.path.abspath(path)
    stats = os.stat(path)
    click.echo(f"Path: {path}")
    click.echo(f"Size: {humanize.naturalsize(stats.st_size)} ({stats.st_size} bytes)")
    click.echo(f"Last modified: {time.ctime(stats.st_mtime)}")
    click.echo(f"Last accessed: {time.ctime(stats.st_atime)}")
    click.echo(f"Creation time: {time.ctime(stats.st_ctime)}")
    click.echo(f"Is directory: {os.path.isdir(path)}")
    click.echo(f"Is file: {os.path.isfile(path)}")
    click.echo(f"Permissions: {oct(stats.st_mode)}")

# walkdir
@click.command()
@click.argument('query', required=False, default=None, nargs=1)
@click.option('--path', '-i', type=click.Path(exists=True), default=".")
@click.option('--max-depth', type=int, default=3)
@click.option('--no-files/--files', '-f/-F', is_flag=True, default=False)
@click.option('--no-dirs/--dirs', '-d/-D', is_flag=True, default=False)
@click.option('--symlinks/--no-symlinks', '-s/-S', is_flag=True, default=False)
@click.option('--regex', '-g', is_flag=True, default=False, help="Use regex for filtering")
@click.option('--ignore-hidden', is_flag=True, default=True, help="Ignore hidden files and directories")
@output_flavor.decorate()
def walkdir(
    path: str,
    max_depth: int,
    no_files: bool,
    no_dirs: bool,
    symlinks: bool,
    ignore_hidden: bool,
    query: str,
    regex: bool,
    flavor,
):
    """Recursively list files and directories."""
    import os
    from ptools.lib.flow.values import OutputValue
    from ptools.utils.re import test


    """
    Result: {
        kind: 'dir' | 'file',
        children: List[Result] (if dir)
    }
    """
    result = []

    test_file = test(query, regex) if query else lambda x: True

    def _walk(current_path, depth):
        if depth < 0:
            return
        try:
            with os.scandir(current_path) as it:
                for entry in it:

                    if ignore_hidden and entry.name.startswith('.'):
                        continue

                    if entry.is_symlink():
                        if not symlinks:
                            continue

                    if entry.is_dir():
                        if not no_dirs:
                            result.append({ 'kind': 'dir', 'name': entry.name, 'path': entry.path })
                        _walk(entry.path, depth - 1)
                    elif entry.is_file():
                        if test_file(entry.path):
                            if not no_files:
                                dirpath = os.path.dirname(entry.path)
                                result.append({ 'kind': 'file', 'name': entry.name, 'path': entry.path, 'dirpath': dirpath })
        except PermissionError:
            return

    path = os.path.abspath(path)
    max_depth = max_depth if max_depth is not None else 3
    no_files = no_files
    no_dirs = no_dirs
    symlinks = symlinks

    _walk(path, max_depth)

    click.echo(OutputValue(flavor=flavor).format(result))

@cli.command()
@click.argument('query', required=False, default=None, nargs=1)
@click.option('--path', '-i', type=click.Path(exists=True), default=".")
@click.option('--max-depth', type=int, default=3)
@click.option('--symlinks/--no-symlinks', '-s/-S', is_flag=True, default=False)
@click.option('--regex', '-g', is_flag=True, default=False, help="Use regex for filtering")
@click.option('--ignore-hidden', is_flag=True, default=True, help="Ignore hidden files and directories")
@output_flavor.decorate()
def findfiles(
    path,
    max_depth,
    symlinks,
    ignore_hidden,
    query,
    regex,
    flavor
):
    return walkdir.callback( # type: ignore
        path=path,
        max_depth=max_depth,
        no_files=False,
        no_dirs=True,
        symlinks=symlinks,
        ignore_hidden=ignore_hidden,
        query=query,
        regex=regex,
        flavor=flavor,
    )

# Print a tree structure of directory content with size
# Optionally take a size threshold to only show dirs/files larger than that size
@cli.command()
@click.argument('path', type=click.Path(exists=True), default=".")
@click.argument('sort', required=False, default='size', nargs=1, type=click.Choice(['size', 'name'], case_sensitive=False))
@click.argument('sort-order', required=False, default='asc', nargs=1, type=click.Choice(['asc', 'desc'], case_sensitive=False))
@click.option('--max-depth', type=int, default=3, help="Maximum depth to display in the tree")
@click.option('--size-threshold', '--size-t', type=str, default=None, help="Only show files larger than this size (e.g. 10MB)")
@click.option('--size-flag-threshold', '--size-ft', type=str, default=None, help="Highlight in red files larger than this size (e.g. 100MB)")
@click.option('--ignore-hidden', is_flag=True, default=True, help="Ignore hidden files and directories")
@click.option('--show-files/--no-files', '-f/-F', is_flag=True, default=True, help="Show files in the tree")
@click.option('--interactive', '-i', is_flag=True, default=False, help="Enable interactive mode with clickable file paths")
def tree(
    path,
    sort,
    sort_order,
    max_depth,
    size_threshold,
    size_flag_threshold,
    ignore_hidden,
    show_files,
    interactive,
):
    """Print a tree structure of directory content with size information."""
    # Example: ptools fs tree . --max-depth 2 --size-threshold 10MB
    import os
    from ptools.utils.files import get_size
    from ptools.utils.print import TreeText, KnownExtensions
    from ptools.utils.read import FromHumanized

    bytes_threshold = \
        FromHumanized.from_humanized_size(size_threshold) \
            if size_threshold \
            else None

    bytes_flag_threshold = \
        FromHumanized.from_humanized_size(size_flag_threshold) \
            if size_flag_threshold \
            else None

    if interactive:
        from ptools.lib.fs.file_tree_app import launch_interactive_tree, Command, NodeMeta, ConfirmScreen
        import humanize as humanize_mod

        class OpenCommand(Command):
            key = 'ctrl+o'
            name = 'open'
            description = 'Open'

            def exec_fn(self, node_data: NodeMeta):
                import subprocess
                path = node_data.get('path')
                if path:
                    if os.name == 'nt':  # Windows
                        os.startfile(path)
                    elif os.name == 'posix':
                        subprocess.run(['open', path])
                    else:
                        raise NotImplementedError("Unsupported OS for opening files")
                else:
                    raise ValueError("No path associated with this node")

        class DeleteCommand(Command):
            key = 'backspace'
            name = 'delete'
            description = 'Delete'

            def exec_fn(self, node_data: NodeMeta):
                import os
                path = node_data.get('path')
                if not path:
                    raise ValueError("No path associated with this node")
                fn   = os.removedirs if os.path.isdir(path) else os.remove
                exec = lambda: fn(path)
                self.app.push_screen(
                    ConfirmScreen(
                        message=f"Are you sure you want to delete '{path}'?",
                        on_confirm=exec
                    )
                )

        launch_interactive_tree(
            path=os.path.abspath(path),
            max_depth=max_depth,
            size_threshold=bytes_threshold,
            size_flag_threshold=bytes_flag_threshold,
            sort_by=sort,
            sort_order=sort_order,
            ignore_hidden=ignore_hidden,
            show_files=show_files,
            get_size_fn=get_size,
            humanize_fn=humanize_mod.naturalsize,
            known_extensions_cls=KnownExtensions,
            commands=[OpenCommand(), DeleteCommand()],
        )

        return

    def _build_tree(current_path, depth):
        if depth < 0:
            return None

        name = os.path.basename(current_path) or current_path
        size = get_size(current_path, ignore_hidden=ignore_hidden)
        if bytes_threshold is not None and size < bytes_threshold:
            return None

        node = TreeText.FileTreeNode(
            name,
            is_directory=os.path.isdir(current_path),
            is_symlink=os.path.islink(current_path),
            size=size
        )

        if bytes_flag_threshold is not None and size >= bytes_flag_threshold:
            node.size_color = 'red'

        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    if ignore_hidden and entry.name.startswith('.'):
                        continue

                    if entry.is_dir():
                        child_node = _build_tree(entry.path, depth - 1)
                        if child_node:
                            node.add_child(child_node)
                    elif entry.is_file() and show_files and depth > 0:
                        size = get_size(entry.path)
                        if bytes_threshold is None or size >= bytes_threshold:
                            file_node = TreeText.FileTreeNode(f"{entry.name}", is_directory=False, is_symlink=entry.is_symlink(), size=size)
                            if bytes_flag_threshold is not None and size >= bytes_flag_threshold:
                                file_node.size_color = 'red'
                            node.add_child(file_node)

        except PermissionError:
            pass

        if sort == 'size':
            node.children.sort(key=lambda x: x.size, reverse=(sort_order == 'desc'))
        elif sort == 'name':
            node.children.sort(key=lambda x: x.name.lower(), reverse=(sort_order == 'desc'))

        return node

    print(f"Building tree for {path} with max depth {max_depth} and size threshold {size_threshold}...")

    path = os.path.abspath(path)
    tree_root = _build_tree(path, max_depth)
    if tree_root:
        click.echo(TreeText.render_tree(tree_root))
    else:
        click.echo("No files or directories found.")

cli.add_command(info, name='info')
cli.add_command(walkdir, name='walkdir')
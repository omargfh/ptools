import click 
import humanize
from collections import defaultdict

from ptools.lib.flow.values import OutputValue
from ptools.lib.flow.decorators import output_flavor

from ptools.utils.re import test

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
@click.argument('path', type=click.Path(exists=True), default=".")
@click.option('--max-depth', type=int, default=3)
@click.option('--no-files/--files', is_flag=True, default=False)
@click.option('--no-dirs/--dirs', is_flag=True, default=False)
@click.option('--symlinks/--no-symlinks', is_flag=True, default=False)
@click.option('--query', default=None, help="Filter files by name")
@click.option('--regex/--no-regex', is_flag=True, default=False, help="Use regex for filtering")
@click.option('--ignore-hidden', is_flag=True, default=True, help="Ignore hidden files and directories")
@click.option('--as-dict', is_flag=True, default=False, help="Output as a flat list instead of a tree")
@output_flavor.decorate()
def walkdir(
    path,
    max_depth,
    no_files,
    no_dirs,
    symlinks,
    ignore_hidden,
    query,
    regex,
    flavor,
    as_dict
):
    """Recursively list files and directories."""
    import os
    
    """
    Result: {
        kind: 'dir' | 'file',
        children: List[Result] (if dir)
    }
    """
    result = defaultdict(lambda: { 'kind': 'dir', 'children': [] })
    result_list = []
    
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
                            result[entry.path] = { 'kind': 'dir', 'children': [] }
                            result_list.append({ 'kind': 'dir', 'name': entry.name, 'path': entry.path })
                        _walk(entry.path, depth - 1)
                    elif entry.is_file():
                        if test_file(entry.name):
                            if not no_files:
                                dirpath = os.path.dirname(entry.path)
                                result[dirpath]['children'].append({ 'kind': 'file', 'name': entry.name, 'path': entry.path })
                                result_list.append({ 'kind': 'file', 'name': entry.name, 'path': entry.path, 'dirpath': dirpath })
        except PermissionError:
            return

    path = os.path.abspath(path)
    max_depth = max_depth if max_depth is not None else 3
    no_files = no_files
    no_dirs = no_dirs
    symlinks = symlinks

    _walk(path, max_depth)

    result = dict(result) if as_dict else result_list
    click.echo(OutputValue(flavor=flavor).format(result))

cli.add_command(info, name='info')
cli.add_command(walkdir, name='walkdir')
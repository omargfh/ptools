from pathlib import Path

import click

from ptools.lib.node_workspaces import NodeWorkspace, NodeProject, __make_foreach__

@click.group()
@click.option('--path', '-p', default='.', help='Path to the workspace root directory.', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def cli(ctx, path):
    """Node.js workspaces management tools."""
    ctx.obj = {
        'workspace': NodeWorkspace(Path(path).resolve())
    }
    
@cli.command()
@click.pass_context
def list(ctx):
    """List all projects in the workspace."""
    workspace: NodeWorkspace = ctx.obj['workspace']
    print(workspace)

for name in NodeProject.reserved_names:
    __make_foreach__(cli, name)


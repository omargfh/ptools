import click

from ptools.utils.re import test

from .project import NodeProject 
from .workspace import NodeWorkspace
from .decorators import workspace_command

def __make_foreach__(cli, method_name: str):
    @cli.command(name=method_name, help=f"npm run {method_name}")
    @workspace_command.decorate()
    @click.pass_context
    def func(ctx, max_workers, query, regex):
        matcher = test(query, regex)
        workspace: NodeWorkspace = ctx.obj['workspace']
        workspace.each(
            lambda p: getattr(p, method_name)(),
            max_workers=max_workers,
            filter=lambda p: matcher(p.name)
        )
    return func
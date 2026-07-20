"""Git Powertools

The :command:`ptools git` subcommands provide utility functions for working
with Git repositories.
"""

__version__ = "0.1.0"

import click
import ptools.lib.git.decorators as git_decorators

@click.group()
def cli():
    """Git Powertools"""
    pass

@cli.command(name="prune", help="Prune commit message bodies in the specified range.")
@git_decorators.range.decorate()
def prune(commit_hashes):
    """Keep only the subject line of each commit message in the range."""
    import subprocess

    base = f"{commit_hashes[-1]}^"  # parent of oldest commit in range
    exec_cmd = 'git commit --amend -m "$(git log --format=%s -n1 HEAD)"'

    result = subprocess.run(
        ["git", "rebase", base, "--exec", exec_cmd],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise click.ClickException(f"rebase failed:\n{result.stderr.strip()}")
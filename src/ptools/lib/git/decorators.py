import click
from ptools.utils.decorator_compistor import DecoratorCompositor

def resolve_git_range(f):
    """Decorator to convert --since/--until into git hashes"""
    def wrapper(since, until, *args, **kwargs):
      import subprocess
      git_log_cmd = ["git", "rev-list", f"{since}..{until}"]

      # Execute the git log command and capture the output
      result = subprocess.run(git_log_cmd, capture_output=True, text=True)
      if result.returncode != 0:
          raise click.ClickException(f"Error executing git command: {result.stderr.strip()}")

      # Call the original function with the resolved commit hashes
      kwargs['commit_hashes'] = result.stdout.strip().splitlines()
      return f(*args, **kwargs)
    return wrapper

range = DecoratorCompositor.from_list([
  click.option('--since', default=None, help='Start date for the commit range (e.g., "2021-01-01", "HEAD~10", "v1.0.0").'),
  click.option('--until', default=None, help='End date for the commit range (e.g., "2021-12-31", "HEAD", "v2.0.0").'),
  resolve_git_range
])
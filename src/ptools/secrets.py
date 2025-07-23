import click
import re
import os 

from ptools.utils.print import FormatUtils
from ptools.utils.config import ConfigFile

config_instance = None
class SecretsConfig():
    def __init__(self, config_name='secrets'):
        """Initialize the secrets configuration."""
        global config_instance
        if config_instance is None:
            config_instance = self
        self.config = ConfigFile(config_name, quiet=True, encrypt=True)
        config_instance = self

    def get_secret(self, key, default=None):
        """Get a secret value from the configuration."""
        return self.config.get(key, default)

    def set_secret(self, key, value):
        """Set a secret value in the configuration."""
        return self.config.set(key, value)

    def delete_secret(self, key):
        """Delete a secret from the configuration."""
        return self.config.delete(key)
    
    def __iter__(self):
        """Iterate over all secrets in the configuration."""
        return iter(self.config.data.items())
    
def filter(dict, query, regex=False):
    """Filter a dictionary based on a query."""
    if regex:
        pattern = re.compile(query)
        return {k: v for k, v in dict.items() if pattern.search(k)}
    else:
        return {k: v for k, v in dict.items() if query in k}
    
@click.group()
def cli():
    """Manage secrets configuration."""
    pass

@click.command()
@click.argument('key')
@click.argument('value')
def set_secret(key, value):
    """Set a secret value."""
    secrets_config = SecretsConfig()
    secrets_config.set_secret(key, value)
    click.echo(FormatUtils.success(f"Secret '{key}' set to '{value}'"))

@click.command()
@click.argument('key')
@click.option('--quiet', is_flag=True, help="Suppress output messages")
def get_secret(key, quiet):
    """Get a secret value."""
    secrets_config = SecretsConfig()
    value = secrets_config.get_secret(key)
    if value is not None:
        if not quiet:
            click.echo(FormatUtils.success(f"Secret '{key}': {value}"))
        else:
            click.echo(value)
    else:
        if not quiet:
            click.echo(FormatUtils.warning(f"Secret '{key}' not found."))
            raise KeyError(f"Secret '{key}' not found.")

@click.command()
@click.option('--query', '-q', help="Query to filter secrets")
@click.option('--regex', is_flag=True, help="Use regex for filtering")
@click.argument('command', nargs=-1)
def with_secrets(query, regex, command):
    """Run a command with secrets."""
    secrets_config = SecretsConfig()
    if query:
        secrets = filter(dict(secrets_config), query, regex)
    else:
        secrets = dict(secrets_config)

    if not secrets:
        click.echo(FormatUtils.warning("No secrets found."))
        return

    # Set environment variables for the command
    for key, value in secrets.items():
        os.environ[key] = value

    # Execute the command
    if command:
        os.system(' '.join(command))
    else:
        click.echo(FormatUtils.info("No command provided to run with secrets."))
    
@click.command()
@click.option('--query', '-q', help="Query to filter secrets")
@click.option('--regex', is_flag=True, help="Use regex for filtering")
@click.option('--match', is_flag=True, help="Match query exactly")
@click.option('--show-values', is_flag=True, help="Show secret values")
def list_secrets(query, show_values, regex, match):
    """List all secrets."""
    secrets_config = SecretsConfig()
    secrets = secrets_config.config.list()
    if not secrets:
        click.echo(FormatUtils.warning("No secrets found."))
        return
    
    if not show_values:
        secrets = {k: '*' * len(v) for k, v in secrets.items()}

    if query:
        secrets = filter(secrets, query, regex)

    if not secrets:
        click.echo(FormatUtils.warning("No secrets found."))
    else:
        for key, value in secrets.items():
            click.echo(f"{key}: {value}")

@click.command()
@click.confirmation_option(prompt="Are you sure you want to delete all secrets?")
def delete_all_secrets():
    """Delete all secrets."""
    secrets_config = SecretsConfig()
    secrets_config.config.clear()
    click.echo(FormatUtils.success("All secrets have been deleted."))

cli.add_command(set_secret, name="set")
cli.add_command(get_secret, name="get")
cli.add_command(list_secrets, name="list")
cli.add_command(with_secrets, name="exec")
cli.add_command(delete_all_secrets, name="dangerous-delete-all-secrets")

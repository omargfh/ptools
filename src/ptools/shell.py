import click 
import re

from ptools.utils.config import ConfigFile

config_name = 'shell'

shell_instance = None
class Shell():
    def __init__(self, config_name):
        """Initialize the shell with a configuration."""
        global shell_instance
        if shell_instance is None:
            shell_instance = self
        self.config = ConfigFile(config_name, quiet=True)
        shell_instance = self

    def _get_shell_config_file(self):
        """Get the shell configuration file path."""
        shconfig = self.config.get('shell_config_file', None)
        if shconfig is None:
            raise ValueError("Shell configuration file is not set. Please set it using 'set_default_shell' command.")
        return shconfig

    def write_to_shell_config(self, value):
        """Write a value to the shell configuration."""
        shconfig = self._get_shell_config_file()
        with open(shconfig, 'w') as f:
            f.write(f"\n{value}\n")
        click.echo(f"Value '{value}' written to shell configuration file: {shconfig}")
        return self
    
    def set_default_shell(self, shell_config_file):
        """Set the default shell configuration."""
        self.config.upsert('shell_config_file', shell_config_file)
        click.echo(f"Default shell configuration set to: {shell_config_file}")

    def add_alias(self, alias_name, command):
        """Add an alias for a command."""
        code = f"alias {alias_name}='{command}'"
        self.write_to_shell_config(code)
        return self
    
    def add_export(self, var_name, value):
        """Add an export statement to the shell configuration."""
        code = f"export {var_name}='{value}'"
        self.write_to_shell_config(code)
        return self
    
    def extend_var(self, var_name, value):
        """Extend a shell variable with a new value."""
        # check if the variable is already set
        shconfig = self._get_shell_config_file()
        with open(shconfig, 'r') as f:
            lines = f.readlines()
        # Does the variable already exist?
        var_exists = False 
        var_pattern = re.compile(rf'^{var_name}=')
        for line in lines:
            if var_pattern.match(line):
                var_exists = True
                break
        
        if var_exists:
            # Extend the existing variable
            code = f"{var_name}=${var_name}:{value}"
        else:
            # Create a new variable
            code = f"{var_name}='{value}'"
        self.write_to_shell_config(code)
        return (self, var_exists)
    


@click.group()
def cli():
    """Shell commands for ptools."""
    pass

@click.command(name='set_default_shell')
@click.argument('shell_config_file', type=click.Path(exists=True))
def set_default_shell(shell_config_file):
    """Set the default shell for ptools."""
    shell_instance.set_default_shell(shell_config_file)
    
@click.command(name='alias')
@click.argument('alias_name', type=str)
@click.argument('command', type=str)
def add_alias(alias_name, command):
    """Add an alias for a command."""
    shell_instance.config.set(alias_name, command)
    click.echo(f"Alias '{alias_name}' added for command: {command}")

@click.command(name='x')
@click.argument('var_name', type=str)
@click.argument('value', type=str)
def add_export(var_name, value):
    """Add an export statement to the shell configuration."""
    shell_instance.add_export(var_name, value)
    click.echo(f"Export '{var_name}' set to: {value}")

@click.command(name='xvar')
@click.argument('var_name', type=str)
@click.argument('value', type=str)
def extend_var(var_name, value):
    """Extend a shell variable with a new value."""
    _, var_exists = shell_instance.extend_var(var_name, value)
    if var_exists:
        click.echo(f"Extended existing variable '{var_name}' with value: {value}")
    else:
        click.echo(f"Created new variable '{var_name}' with value: {value}")

@click.command(name='xpath')
@click.argument('path', type=click.Path(exists=True))
def extend_path(path):
    """Extend the PATH variable with a new path."""
    shell_instance.extend_var('PATH', path)
    click.echo(f"Extended PATH with: {path}")


cli.add_command(set_default_shell)
cli.add_command(add_alias)
cli.add_command(add_export)
cli.add_command(extend_var)
cli.add_command(extend_path)
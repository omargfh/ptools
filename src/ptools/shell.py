import click 
import re
import os
from datetime import datetime

from ptools.utils.config import ConfigFile
from ptools.utils.print import FormatUtils

shell_instance = None
class Shell():
    def __init__(self, config_name='shell'):
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
    
    def _var_exists(self, var_name):
        """Check if a shell variable exists in the configuration file."""
        shconfig = self._get_shell_config_file()
        with open(shconfig, 'r') as f:
            lines = f.readlines()
        var_pattern = re.compile(rf'^export {var_name}=[^\s]')
        for line in lines:
            if var_pattern.match(line):
                return True
        return False

    def append_to_shell_config(self, value):
        """Write a value to the shell configuration."""
        shconfig = self._get_shell_config_file()
        current_content = ""
        try:
            with open(shconfig, 'r') as f:
                current_content = f.read()
        except FileNotFoundError:
            # If the file does not exist, it will be created
            pass

        with open(shconfig, 'w') as f:
            f.write(current_content)
            if not current_content.endswith('\n'):
                f.write('\n')
            f.write(f"{value} # Added by ptools shell command\n")

        echo_info(f"Value '{FormatUtils.highlight(value)}'")
        return self
    
    def set_default_shell(self, shell_config_file):
        """Set the default shell configuration."""
        self.config.upsert('shell_config_file', shell_config_file)
        echo_info(f"Default shell configuration set to: {shell_config_file}")

    def add_alias(self, alias_name, command):
        """Add an alias for a command."""
        code = f"alias {alias_name}='{command}'"
        self.append_to_shell_config(code)
        return self
    
    def add_export(self, var_name, value, force=False):
        """Add an export statement to the shell configuration."""
        if self._var_exists(var_name) and not force:
            echo_info(f"Variable '{FormatUtils.highlight(var_name)}' already exists. Use 'xvar' to extend it if it is a list or pass --force to overwrite.")
            return self
        
        code = f"export {var_name}='{value}'"
        self.append_to_shell_config(code)
        return self
    
    def extend_var(self, var_name, value):
        """Extend a shell variable with a new value."""
        # check if the variable is already set
        var_exists = self._var_exists(var_name)
        
        if var_exists:
            # Extend the existing variable
            code = f"{var_name}=${var_name}:{value}"
        else:
            # Create a new variable
            code = f"{var_name}='{value}'"
        self.append_to_shell_config(code)
        return (self, var_exists)
    

def echo_info(*args, **kwargs):
    """Print an info message."""
    click.echo(FormatUtils.info(*args), **kwargs)

@click.group()
def cli():
    """Shell commands for ptools."""
    pass

@click.command(name='set-default-shell')
@click.argument('shell_config_file', type=click.Path(exists=True))
def set_default_shell(shell_config_file):
    """Set the default shell for ptools."""
    Shell().set_default_shell(shell_config_file)
    
@click.command(name='alias')
@click.argument('alias_name', type=str)
@click.argument('command', type=str)
def add_alias(alias_name, command):
    """Add an alias for a command."""
    Shell().add_alias(alias_name, command)
    echo_info(f"Alias '{FormatUtils.highlight(alias_name)}' added for command: {FormatUtils.highlight(command)}")

@click.command(name='x')
@click.argument('var_name', type=str)
@click.argument('value', type=str)
@click.option('--force', is_flag=True, help="Force overwrite if variable already exists.")
def add_export(var_name, value, force=False):
    """Add an export statement to the shell configuration."""
    Shell().add_export(var_name, value, force=force)
    echo_info(f"Variable '{FormatUtils.highlight(var_name)}' set to: {FormatUtils.highlight(value)}")

@click.command(name='xvar')
@click.argument('var_name', type=str)
@click.argument('value', type=str)
def extend_var(var_name, value):
    """Extend a shell variable with a new value."""
    _, var_exists = Shell().extend_var(var_name, value)
    if var_exists:
        echo_info(f"Extended existing variable '{FormatUtils.highlight(var_name)}' with value: {FormatUtils.highlight(value)}")
    else:
        echo_info(f"Created new variable '{FormatUtils.highlight(var_name)}' with value: {FormatUtils.highlight(value)}")

@click.command(name='xpath')
@click.argument('path', type=click.Path(exists=True))
def extend_path(path):
    """Extend the PATH variable with a new path."""
    Shell().extend_var('PATH', path)
    echo_info(f"Extended PATH with: {FormatUtils.highlight(path)}")


cli.add_command(set_default_shell)
cli.add_command(add_alias)
cli.add_command(add_export)
cli.add_command(extend_var)
cli.add_command(extend_path)
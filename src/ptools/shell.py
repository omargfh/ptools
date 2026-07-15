"""Shell configuration helpers.

Provides the :command:`ptools shell` CLI for managing a user's shell
configuration file (e.g. ``~/.zshrc`` or ``~/.bashrc``). The :class:`Shell`
class encapsulates the low-level append/extend operations and is driven
by a persistent :class:`~ptools.utils.config.ConfigFile` that remembers
which shell config file the user has chosen as the default target.
"""

import click
import re
import os
from datetime import datetime

from click.shell_completion import get_completion_class

from ptools.utils.config import ConfigFile
from ptools.utils.print import FormatUtils

COMPLETION_PROG_NAME = "ptools"
COMPLETION_SHELLS = ("bash", "zsh", "fish")


def _completion_env_var(prog_name: str = COMPLETION_PROG_NAME) -> str:
    """Derive the ``_<PROG>_COMPLETE`` env var name Click looks for.

    Mirrors the (private) derivation in
    ``click.core.BaseCommand._main_shell_completion``: uppercase the
    program name, replace ``-``/``.`` with ``_``, and wrap it in
    ``_..._COMPLETE``. For ``ptools`` this is ``_PTOOLS_COMPLETE``.
    """
    complete_name = prog_name.replace("-", "_").replace(".", "_")
    return f"_{complete_name}_COMPLETE".upper()


def _completion_script(shell: str, prog_name: str = COMPLETION_PROG_NAME) -> str:
    """Generate Click's shell completion script for *shell*.

    Uses Click's in-process :mod:`click.shell_completion` API against the
    real ``ptools`` root command. This is equivalent to running
    ``_PTOOLS_COMPLETE=<shell>_source ptools`` as a subprocess, but avoids
    the extra process spawn and any dependency on ``ptools`` being on
    ``PATH`` (the completion script itself never introspects subcommands,
    so it's safe to generate in-process).
    """
    from ptools.main import cli as root_cli

    comp_cls = get_completion_class(shell)
    if comp_cls is None:
        raise click.ClickException(f"Shell completion is not supported for '{shell}'.")

    complete_var = _completion_env_var(prog_name)
    comp = comp_cls(root_cli, {}, prog_name, complete_var)
    return comp.source()


def _completion_eval_line(shell: str, prog_name: str = COMPLETION_PROG_NAME) -> str:
    """The one-line ``eval "$(...)"`` snippet that enables completion in an rc file."""
    complete_var = _completion_env_var(prog_name)
    return f'eval "$({complete_var}={shell}_source {prog_name})"'


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

    def install_completion(self, shell, prog_name=COMPLETION_PROG_NAME):
        """Install the shell-completion ``eval`` line into the shell config file.

        Reuses :meth:`append_to_shell_config` as the actual write
        mechanism. Idempotent the same way ``add_export`` is: the file is
        checked first, and the line is only appended if it isn't already
        present, so running this twice does not duplicate the block.
        """
        value = _completion_eval_line(shell, prog_name)
        shconfig = self._get_shell_config_file()
        try:
            with open(shconfig, 'r') as f:
                already_installed = value in f.read()
        except FileNotFoundError:
            already_installed = False

        if already_installed:
            echo_info(f"Completion for '{FormatUtils.highlight(shell)}' is already installed in {shconfig}.")
            return self

        self.append_to_shell_config(value)
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
    """Shell commands for ptools.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools shell set-default-shell /tmp/ptools-doc-home/shellrc
      INFO Default shell configuration set to: /tmp/ptools-doc-home/shellrc
    """
    pass

@click.command(name='set-default-shell')
@click.argument('shell_config_file', type=click.Path(exists=True))
def set_default_shell(shell_config_file):
    """Set the default shell for ptools.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools shell set-default-shell /tmp/ptools-doc-home/shellrc
      INFO Default shell configuration set to: /tmp/ptools-doc-home/shellrc
    """
    Shell().set_default_shell(shell_config_file)
    
@click.command(name='alias')
@click.argument('alias_name', type=str)
@click.argument('command', type=str)
def add_alias(alias_name, command):
    """Add an alias for a command.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools shell alias ll 'ls -la'
      INFO Value 'alias ll='ls -la''
      INFO Alias 'll' added for command: ls -la
    """
    Shell().add_alias(alias_name, command)
    echo_info(f"Alias '{FormatUtils.highlight(alias_name)}' added for command: {FormatUtils.highlight(command)}")

@click.command(name='x')
@click.argument('var_name', type=str)
@click.argument('value', type=str)
@click.option('--force', is_flag=True, help="Force overwrite if variable already exists.")
def add_export(var_name, value, force=False):
    """Add an export statement to the shell configuration.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools shell x PTOOLS_DOC_EXAMPLE enabled --force
      INFO Value 'export PTOOLS_DOC_EXAMPLE='enabled''
      INFO Variable 'PTOOLS_DOC_EXAMPLE' set to: enabled
    """
    Shell().add_export(var_name, value, force=force)
    echo_info(f"Variable '{FormatUtils.highlight(var_name)}' set to: {FormatUtils.highlight(value)}")

@click.command(name='xvar')
@click.argument('var_name', type=str)
@click.argument('value', type=str)
def extend_var(var_name, value):
    """Extend a shell variable with a new value.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools shell xvar PTOOLS_DOC_PATH /tmp/example
      INFO Value 'PTOOLS_DOC_PATH='/tmp/example''
      INFO Created new variable 'PTOOLS_DOC_PATH' with value: /tmp/example
    """
    _, var_exists = Shell().extend_var(var_name, value)
    if var_exists:
        echo_info(f"Extended existing variable '{FormatUtils.highlight(var_name)}' with value: {FormatUtils.highlight(value)}")
    else:
        echo_info(f"Created new variable '{FormatUtils.highlight(var_name)}' with value: {FormatUtils.highlight(value)}")

@click.command(name='xpath')
@click.argument('path', type=click.Path(exists=True))
def extend_path(path):
    """Extend the PATH variable with a new path.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools shell xpath /tmp/ptools-doc-examples
      INFO Value 'PATH=$PATH:/tmp/ptools-doc-examples'
      INFO Extended PATH with: /tmp/ptools-doc-examples
    """
    Shell().extend_var('PATH', path)
    echo_info(f"Extended PATH with: {FormatUtils.highlight(path)}")

@click.command(name='completion')
@click.option(
    '--shell',
    type=click.Choice(COMPLETION_SHELLS),
    required=True,
    help="Shell to generate/install completion for.",
)
@click.option(
    '--install',
    is_flag=True,
    help="Append the completion eval line to the configured shell config file instead of printing the script.",
)
def completion(shell, install=False):
    """Print or install Click's shell completion script for ptools.

    Without --install, prints the completion script for SHELL to stdout
    (equivalent to running ``_PTOOLS_COMPLETE=<shell>_source ptools``).
    With --install, appends the corresponding
    ``eval "$(_PTOOLS_COMPLETE=<shell>_source ptools)"`` line to the
    configured shell config file (see 'set-default-shell'); running it
    again does not duplicate the line.

    \b
    Example:
      $ ptools shell completion --shell bash | head -1
      _ptools_completion() {

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools shell completion --shell zsh --install
      INFO Value 'eval "$(_PTOOLS_COMPLETE=zsh_source ptools)"'
    """
    if install:
        Shell().install_completion(shell)
    else:
        click.echo(_completion_script(shell))


cli.add_command(set_default_shell)
cli.add_command(add_alias)
cli.add_command(add_export)
cli.add_command(extend_var)
cli.add_command(extend_path)
cli.add_command(completion)

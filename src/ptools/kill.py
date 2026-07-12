import subprocess
import click

@click.group(name='kill')
def cli():
    """Kill tools.

    \b
    Example:
      $ ptools kill port 9
      No process is using port 9.
    """
    pass

@cli.command(name="port")
@click.argument('port', type=int, required=True, nargs=-1)
def kill_port(port):
    """Kill process by port number.

    \b
    Example:
      $ ptools kill port 9
      No process is using port 9.
    """
    for p in port:
        try:
            if subprocess.run(["lsof", "-i", f":{p}"], capture_output=True, text=True).stdout:
                pid = subprocess.run(
                    ["lsof", "-t", "-i", f":{p}"],
                    capture_output=True,
                    text=True
                ).stdout.strip()
                subprocess.run(["kill", "-9", pid])
                click.echo(f"Process on port {p} with PID {pid} has been killed.")
            else:
                click.echo(f"No process is using port {p}.")
        except Exception as e:
            click.echo(f"An error occurred while trying to kill process on port {p}: {e}")

@cli.command(name="process")
@click.argument('process_name', type=str, required=True, nargs=-1)
def kill_process(process_name):
    """Kill process by name.

    \b
    Example:
      $ ptools kill process definitely-not-running-ptools-example
      No process found with name 'definitely-not-running-ptools-example'.
    """
    for name in process_name:
        try:
            pids = subprocess.run(
                ["pgrep", name],
                capture_output=True,
                text=True
            ).stdout.strip().splitlines()
            if pids:
                for pid in pids:
                    subprocess.run(["kill", "-9", pid])
                    click.echo(f"Process '{name}' with PID {pid} has been killed.")
            else:
                click.echo(f"No process found with name '{name}'.")
        except Exception as e:
            click.echo(f"An error occurred while trying to kill process '{name}': {e}")

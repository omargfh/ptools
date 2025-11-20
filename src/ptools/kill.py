import subprocess
import click

@click.group(name='kill')
def cli():
    """kill tools"""
    pass

@cli.command(name="port")
@click.argument('port', type=int, required=True, nargs=-1)
def kill_port(port):
    """Kill process by port number"""
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
    """Kill process by name"""
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

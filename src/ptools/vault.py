import click

from ptools.utils.encrypt import Encryption, PasswordEncryption

@click.group()
def cli():
    """File encryption and decryption commands."""
    pass

@cli.command(name="seal")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_file", type=click.Path(dir_okay=False), required=False)
@click.option('-p', '--password', prompt=True, hide_input=True, confirmation_prompt=True, help="Password for encryption.")
def seal(input_file, output_file, password):
    """Encrypt a file and write the encrypted data to an output file.

    If OUTPUT_FILE is not provided, the encrypted data will be printed to stdout.
    """
    enc = PasswordEncryption(password)
    with open(input_file, "rb") as f:
        plaintext = f.read()
    encrypted_blob = enc.encrypt(plaintext)

    output_file = output_file or f"{input_file}"
    with open(output_file, "w") as f:
        f.write(str(encrypted_blob))

@cli.command(name="unseal")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_file", type=click.Path(dir_okay=False), required=False)
@click.option('-p', '--password', prompt=True, hide_input=True, help="Password for decryption.")
def unseal(input_file, output_file, password):
    """Decrypt a file and write the decrypted data to an output file.

    If OUTPUT_FILE is not provided, the decrypted data will be printed to stdout.
    """
    enc = PasswordEncryption(password)
    with open(input_file, "r") as f:
        encrypted_blob = eval(f.read())  # Use eval to convert string back to dict

    decrypted_data = enc.decrypt(encrypted_blob)

    output_file = output_file or f"{input_file}"
    with open(output_file, "wb") as f:
        f.write(decrypted_data.encode('utf-8'))

@cli.command(name="bury")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_file", type=click.Path(dir_okay=False), required=False)
def bury(input_file, output_file):
    """Encrypt a file using the system keyring and write the encrypted data to an output file.

    If OUTPUT_FILE is not provided, the encrypted data will be printed to stdout.
    """
    enc = Encryption(service_name="com.ptools.vault")
    with open(input_file, "rb") as f:
        plaintext = f.read()
    encrypted_blob = enc.encrypt(plaintext)

    output_file = output_file or f"{input_file}"
    with open(output_file, "w") as f:
        f.write(str(encrypted_blob))

@cli.command(name="dig")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_file", type=click.Path(dir_okay=False), required=False)
def dig(input_file, output_file):
    """Decrypt a file using the system keyring and write the decrypted data to an output file.

    If OUTPUT_FILE is not provided, the decrypted data will be printed to stdout.
    """
    enc = Encryption(service_name="com.ptools.vault")
    with open(input_file, "r") as f:
        encrypted_blob = eval(f.read())  # Use eval to convert string back to dict

    decrypted_data = enc.decrypt(encrypted_blob)

    output_file = output_file or f"{input_file}"
    with open(output_file, "wb") as f:
        f.write(decrypted_data.encode('utf-8'))
"""Keyring-backed AES-GCM encryption helpers used by the config module."""
import os
import keyring
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

__version__ = "0.1.0"


class EncryptionError(BaseException):
    """Raised when the keyring is unreachable or encryption/decryption fails."""
    pass

class Encryption:
    """AES-GCM encryptor that lazily fetches its key from the system keyring.

    A 32-byte key is read from (or created in) the keyring under
    ``service_name``/``user_name`` the first time encryption is needed.
    Each call to :meth:`encrypt` generates a fresh nonce.

    :param service_name: Keyring service identifier under which the key lives.
    :param user_name: Keyring account name. Defaults to ``$USER`` or
        ``"encryptionUser"`` if unset.
    """
    def __init__(self, service_name, user_name=None):
        self.service_name = service_name
        self.user_name = user_name if user_name else (os.getenv('USER') or "encryptionUser")
        self.key = None

    def _instantiate_encryption(self):
        """Initialize the encryption key from the keyring service (once)."""
        if self.key is not None:
            return

        try:
            self.key = keyring.get_password(self.service_name, self.user_name)
            if self.key is None:
                # Generate a new key if it doesn't exist
                self.key = get_random_bytes(32)
                keyring.set_password(self.service_name, self.user_name, bytes.hex(self.key))
            else:
                self.key = bytes.fromhex(self.key)

            if not self.key or len(self.key) != 32:
                raise ValueError("Invalid key length. Key must be 32 bytes long.")

            return
        except keyring.errors.KeyringError as e:
            raise EncryptionError(f"Failed to access keyring service: {e}")
        except Exception as e:
            raise EncryptionError(f"Failed to initialize encryption key: {e}")

    def encrypt(self, value):
        """Encrypt ``value`` and return a dict of hex-encoded nonce/ciphertext/tag.

        :param value: ``str`` or ``bytes`` payload to encrypt.
        """
        self._instantiate_encryption()
        cipher = AES.new(self.key, AES.MODE_GCM)

        if not isinstance(value, bytes):
            value = value.encode('utf-8')

        ciphertext, tag = cipher.encrypt_and_digest(value)
        nonce = cipher.nonce

        encrypted_data = {
            'nonce': bytes.hex(nonce),
            'ciphertext': bytes.hex(ciphertext),
            'tag': bytes.hex(tag)
        }

        return encrypted_data

    def decrypt(self, encrypted_data):
        """Decrypt the dict produced by :meth:`encrypt` and return the UTF-8 string."""
        self._instantiate_encryption()

        nonce = bytes.fromhex(encrypted_data['nonce'])
        ciphertext = bytes.fromhex(encrypted_data['ciphertext'])
        tag = bytes.fromhex(encrypted_data['tag'])

        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        decrypted_value = cipher.decrypt_and_verify(ciphertext, tag)

        return decrypted_value.decode('utf-8')

class DummyEncryption:
    """Pass-through encryption used in tests and unencrypted code paths."""
    def __init__(self, service_name=None, user_name=None):
        """Accept and ignore the same arguments as :class:`Encryption`."""
        pass

    def encrypt(self, value):
        """Return the value as is."""
        return value

    def decrypt(self, value):
        """Return the value as is."""
        return value


if __name__ == "__main__":
    # Example usage
    encryption = Encryption(service_name="com.ptools.secrets", user_name="testuser")

    message = r"{\"secret\": \"This is a secret message.\"}"
    encrypted = encryption.encrypt(message)
    print("Key:", encryption.key)
    print("Encrypted:", encrypted)

    decrypted = encryption.decrypt(encrypted)
    print("Decrypted:", decrypted)
"""AES-256-GCM com chaves externas, envelopes versionados e dados associados."""

import argparse
import base64
import csv
import json
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app

from exceptions.api_errors import APIError


class DataEncryptionError(APIError):
    def __init__(self):
        super().__init__(
            "Não foi possível validar os dados financeiros. Verifique as chaves e a integridade do banco.",
            500,
        )


class DataCipher:
    """A chave de escrita pode mudar, preservando as chaves anteriores para leitura."""

    def __init__(self, active_key, keys):
        if active_key not in keys or not keys:
            raise ValueError("Chave ativa de criptografia ausente.")
        if any(
            not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key_id)
            or not isinstance(key, bytes)
            or len(key) != 32
            for key_id, key in keys.items()
        ):
            raise ValueError("As chaves de dados devem conter 32 bytes aleatórios.")
        self.active_key = active_key
        self._keys = {key_id: AESGCM(key) for key_id, key in keys.items()}

    @classmethod
    def from_key_file(cls, path):
        try:
            path = Path(path)
            if path.stat().st_size > 65536:
                raise ValueError
            document = json.loads(path.read_text(encoding="utf-8"))
            keys = {
                key_id: base64.b64decode(value, validate=True)
                for key_id, value in document["keys"].items()
            }
            return cls(document["active_key"], keys)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise RuntimeError(
                "Configure DATA_ENCRYPTION_KEY_FILE com um arquivo de chaves válido. "
                "Não gere outra chave para substituir uma chave perdida."
            ) from error

    @staticmethod
    def _aad(context, key_id):
        return json.dumps(
            {"application": "FinanceHub", "version": 1, "key_id": key_id, "context": context},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def encrypt(self, plaintext, context):
        nonce = os.urandom(12)
        ciphertext = self._keys[self.active_key].encrypt(
            nonce, plaintext, self._aad(context, self.active_key)
        )
        encoded = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
        return f"fh1:{self.active_key}:{encoded}"

    def decrypt(self, envelope, context):
        try:
            version, key_id, encoded = envelope.split(":", 2)
            if version != "fh1" or key_id not in self._keys:
                raise ValueError
            packet = base64.b64decode(encoded, altchars=b"-_", validate=True)
            if len(packet) < 28:
                raise ValueError
            return self._keys[key_id].decrypt(packet[:12], packet[12:], self._aad(context, key_id))
        except (InvalidTag, ValueError, KeyError, TypeError, AttributeError) as error:
            raise DataEncryptionError() from error

    def encrypt_fields(self, fields, context):
        plaintext = json.dumps(
            {"version": 1, "fields": fields},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        # Reduz a informação exposta pelo comprimento exato de nomes e descrições.
        plaintext += b" " * (-len(plaintext) % 256)
        return self.encrypt(plaintext, context)

    def decrypt_fields(self, envelope, context):
        try:
            document = json.loads(self.decrypt(envelope, context))
            if document["version"] != 1 or not isinstance(document["fields"], dict):
                raise ValueError
            return document["fields"]
        except (ValueError, KeyError, TypeError) as error:
            raise DataEncryptionError() from error


def get_data_cipher():
    cipher = current_app.extensions.get("financial_data_cipher")
    if not isinstance(cipher, DataCipher):
        raise DataEncryptionError()
    return cipher


def restrict_secret_file(path):
    """Remove permissões herdadas no Windows; usa 0600 no POSIX."""
    if os.name != "nt":
        os.chmod(path, 0o600)
        return
    result = subprocess.run(
        ["whoami", "/user", "/fo", "csv", "/nh"],
        check=True,
        capture_output=True,
        text=True,
    )
    sid = next(csv.reader([result.stdout.strip()]))[1]
    subprocess.run(
        ["icacls", str(path), "/inheritance:r", "/grant:r", f"*{sid}:(F)", "*S-1-5-18:(F)"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def write_private_file(path, content):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # O arquivo ainda está vazio ao restringir as permissões.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        restrict_secret_file(path)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return path


def generate_key_file(path):
    key_id = uuid4().hex[:16]
    document = {
        "active_key": key_id,
        "keys": {key_id: base64.b64encode(AESGCM.generate_key(bit_length=256)).decode("ascii")},
    }
    return write_private_file(path, json.dumps(document, indent=2).encode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cria uma chave de dados sem exibi-la no terminal."
    )
    parser.add_argument("command", choices=["generate-key"])
    parser.add_argument("--file", required=True)
    arguments = parser.parse_args()
    try:
        generate_key_file(arguments.file)
    except (OSError, subprocess.SubprocessError):
        parser.exit(
            1,
            "Não foi possível criar o arquivo de chave; arquivos existentes não são sobrescritos.\n",
        )
    print("Arquivo de chave criado com acesso restrito. Guarde uma cópia protegida separadamente.")

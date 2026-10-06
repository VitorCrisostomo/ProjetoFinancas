"""Credenciais individuais no .env, com escrita privada e bloqueio entre processos."""

import os
import time
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from uuid import UUID, uuid4

from dotenv import dotenv_values
from dotenv.parser import parse_stream
from flask import current_app

from exceptions.api_errors import APIError, ValidationError
from services.data_encryption import restrict_secret_file, write_private_file


class PluggyCredentialsStore:
    def __init__(self, path=None):
        self.path = Path(path or current_app.config["PLUGGY_ENV_FILE"]).resolve()

    @staticmethod
    def validate(client_id, client_secret):
        for value, limit in ((client_id, 512), (client_secret, 4096)):
            if (
                not isinstance(value, str)
                or not 1 <= len(value) <= limit
                or any(not 33 <= ord(character) <= 126 for character in value)
            ):
                raise ValidationError(
                    "Informe Client ID e Client Secret válidos, sem espaços ou quebras de linha."
                )
        return client_id, client_secret

    @staticmethod
    def variable_names(reference):
        try:
            identifier = UUID(reference).hex.upper()
        except (ValueError, TypeError, AttributeError) as error:
            raise APIError("Identidade bancária inválida.", 500) from error
        prefix = f"PLUGGY_USER_{identifier}"
        return f"{prefix}_CLIENT_ID", f"{prefix}_CLIENT_SECRET"

    @contextmanager
    def _locked(self):
        lock_path = self.path.with_name(self.path.name + ".lock")
        try:
            descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
            stream = os.fdopen(descriptor, "r+b")
            with stream:
                restrict_secret_file(lock_path)
                if os.fstat(stream.fileno()).st_size == 0:
                    stream.write(b"0")
                    stream.flush()
                deadline = time.monotonic() + 10
                while True:
                    try:
                        if os.name == "nt":
                            import msvcrt

                            stream.seek(0)
                            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl

                            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise APIError("O arquivo .env está em uso. Tente novamente.", 503)
                        time.sleep(0.05)
                try:
                    yield
                finally:
                    if os.name == "nt":
                        stream.seek(0)
                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(stream, fcntl.LOCK_UN)
        except OSError as error:
            raise APIError("Não foi possível acessar as credenciais no .env.", 503) from error

    def _read(self):
        try:
            content = self.path.read_bytes().decode("utf-8") if self.path.exists() else ""
        except UnicodeError as error:
            raise APIError("O arquivo .env precisa estar no formato UTF-8.", 503) from error
        bindings = list(parse_stream(StringIO(content)))
        if any(binding.error for binding in bindings):
            raise APIError("Corrija a sintaxe do .env antes de configurar a integração.", 503)
        return content, bindings

    def _write(self, content):
        temporary = self.path.with_name(f"{self.path.name}.{uuid4().hex}.tmp")
        try:
            write_private_file(temporary, content.encode("utf-8"))
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def get(self, reference):
        names = self.variable_names(reference)
        with self._locked():
            content, _bindings = self._read()
            # O arquivo é a fonte de verdade; alterações não exigem reiniciar workers.
            values = dotenv_values(stream=StringIO(content), interpolate=False)
        pair = tuple(values.get(name) for name in names)
        try:
            return self.validate(*pair)
        except ValidationError as error:
            raise APIError(
                "A integração Pluggy deste usuário não está configurada. Contate o administrador.",
                503,
            ) from error

    @contextmanager
    def snapshot(self):
        """Mantém configuração e banco coordenados durante o snapshot de backup."""
        with self._locked():
            content, _bindings = self._read()
            yield content

    @contextmanager
    def change(self, reference, client_id, client_secret):
        """Confirma junto da operação administrativa; exceções restauram o .env anterior."""
        pair = self.validate(client_id, client_secret)
        names = self.variable_names(reference)
        with self._locked():
            existed = self.path.exists()
            previous, bindings = self._read()
            content = "".join(
                binding.original.string for binding in bindings if binding.key not in names
            )
            if content and not content.endswith("\n"):
                content += "\n"
            for name, value in zip(names, pair, strict=True):
                escaped = value.replace("\\", "\\\\").replace("'", "\\'")
                content += f"{name}='{escaped}'\n"
            self._write(content)
            try:
                yield
            except Exception:
                try:
                    if existed:
                        self._write(previous)
                    else:
                        self.path.unlink()
                except OSError as error:
                    raise APIError(
                        "Falha ao restaurar o .env. Confira as credenciais antes de retomar.", 500
                    ) from error
                raise

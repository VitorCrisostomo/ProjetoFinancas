"""Verifica o HTTP local sem carregar a aplicação ou decriptar registros."""

import http.client
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values


def configured_host():
    """Lê apenas a origem pública gerada pelo bootstrap no arquivo externo."""
    environment_file = Path(os.getenv("FINANCEHUB_ENV_FILE", "/state/config/app.env"))
    settings = dotenv_values(environment_file, interpolate=False)
    origin = urlsplit((settings.get("AUTH_ALLOWED_ORIGINS") or "").split(",", 1)[0].strip())
    if (
        origin.scheme == "https"
        and origin.hostname
        and not origin.hostname.startswith(".")
        and "*" not in origin.netloc
        and not origin.username
        and not origin.password
        and not origin.path
        and not origin.query
        and not origin.fragment
    ):
        return origin.netloc
    raise ValueError("Origem de produção inválida.")


def main():
    connection = None
    try:
        connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=3)
        connection.request("GET", "/healthz", headers={"Host": configured_host()})
        response = connection.getresponse()
        content = response.read(4096)
        return 0 if response.status == 200 and json.loads(content).get("status") == "ok" else 1
    except (OSError, ValueError, http.client.HTTPException, AttributeError):
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())

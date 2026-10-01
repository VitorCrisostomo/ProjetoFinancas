"""Exporta as exceções utilizadas pelas rotas e pelos serviços."""

from .api_errors import APIError, NotFoundError, ValidationError

# Interface pública das exceções do backend.
__all__ = ["APIError", "NotFoundError", "ValidationError"]

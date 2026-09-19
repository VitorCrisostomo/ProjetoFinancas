from .api_errors import APIError, NotFoundError, ValidationError

# O __all__ define o que é exportado quando alguém faz "from exceptions import *"
__all__ = [
    "APIError", 
    "NotFoundError", 
    "ValidationError"
]
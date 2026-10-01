"""Define erros da API com mensagem e status HTTP."""


class APIError(Exception):
    """Erro com mensagem e status que os handlers convertem em JSON."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(APIError):
    """Erro de recurso não encontrado, com status HTTP 404."""

    def __init__(self, message="Not found"):
        super().__init__(message, 404)


class ValidationError(APIError):
    """Erro de validação, com status HTTP 400."""

    def __init__(self, message="Invalid input"):
        super().__init__(message, 400)

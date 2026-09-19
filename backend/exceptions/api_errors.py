class APIError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class NotFoundError(APIError):
    def __init__(self, message="Not found"):
        super().__init__(message, 404)

class ValidationError(APIError):
    def __init__(self, message="Invalid input"):
        super().__init__(message, 400)
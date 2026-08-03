class AppException(Exception):
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None, status_code: int | None = None):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFoundException(AppException):
    status_code = 404
    detail = "Resource not found"


class ValidationException(AppException):
    status_code = 422
    detail = "Validation error"


class LLMException(AppException):
    status_code = 502
    detail = "LLM service error"


class ParsingException(AppException):
    status_code = 422
    detail = "Document parsing error"
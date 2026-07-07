class AppException(Exception):
    status_code = 500
    detail = "Internal error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class BadRequestException(AppException):
    status_code = 400
    detail = "Bad request"


class NotFoundException(AppException):
    status_code = 404
    detail = "Not found"


class ForbiddenException(AppException):
    status_code = 403
    detail = "Forbidden"


class UnauthorizedException(AppException):
    status_code = 401
    detail = "Not authenticated"


class ConflictException(AppException):
    status_code = 409
    detail = "Conflict"

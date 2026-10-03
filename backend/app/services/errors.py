"""Business-rule errors raised by services and turned into structured JSON."""

from typing import Any


class ServiceError(Exception):
    """{"detail": {"code": ..., "message": ..., **extra}} with the given status."""

    def __init__(self, status_code: int, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.extra = extra


def not_found(code: str, message: str) -> ServiceError:
    return ServiceError(404, code, message)

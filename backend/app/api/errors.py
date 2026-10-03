"""Structured API errors: {"detail": {"code": "...", "message": "..."}}."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.auth import AuthError


def api_error(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers=headers,
    )


def _field_name(loc: tuple) -> str:
    # ("body", "password") -> "password"; whole-body errors -> "body".
    parts = [str(part) for part in loc if part not in ("body", "query", "path")]
    return ".".join(parts) or "body"


def _clean_message(message: str) -> str:
    return message.removeprefix("Value error, ")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def auth_error(request: Request, exc: AuthError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": exc.message}},
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Same structured shape as other errors, plus one message per invalid field."""
        fields: dict[str, str] = {}
        for error in exc.errors():
            fields.setdefault(_field_name(tuple(error["loc"])), _clean_message(error["msg"]))
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "validation_error",
                    "message": "Some fields are invalid.",
                    "fields": fields,
                }
            },
        )

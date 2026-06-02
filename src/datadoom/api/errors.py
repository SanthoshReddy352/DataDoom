"""Consistent error envelope + exception handlers (08 §1, §12).

Every error response is ``{ "error": { code, message, locator? } }``. Spec
validation failures map to 422 with the offending field's ``locator``; other
engine errors to 400; anything unexpected to 500 (traceback logged, not leaked).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from datadoom.engine.errors import (
    DataDoomError,
    DistributionError,
    SpecValidationError,
)

log = logging.getLogger("datadoom.api")


def _envelope(code: str, message: str, locator: str | None = None) -> dict:
    detail = {"code": code, "message": message}
    if locator is not None:
        detail["locator"] = locator
    return {"error": detail}


# Status-code -> default error code for bare HTTPExceptions.
_CODE_FOR_STATUS = {400: "bad_request", 404: "not_found", 409: "conflict", 422: "validation_error"}


def http_error(status: int, code: str, message: str, locator: str | None = None):  # noqa: ANN201
    """Build an HTTPException whose detail carries our envelope fields."""
    from fastapi import HTTPException

    return HTTPException(status_code=status, detail={"code": code, "message": message, "locator": locator})


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SpecValidationError)
    async def _spec_invalid(_req: Request, exc: SpecValidationError):  # noqa: ANN202
        return JSONResponse(
            status_code=422,
            content=_envelope("validation_error", str(exc), getattr(exc, "locator", None)),
        )

    @app.exception_handler(DistributionError)
    async def _dist_error(_req: Request, exc: DistributionError):  # noqa: ANN202
        return JSONResponse(
            status_code=422,
            content=_envelope("distribution_error", str(exc), getattr(exc, "locator", None)),
        )

    @app.exception_handler(DataDoomError)
    async def _domain_error(_req: Request, exc: DataDoomError):  # noqa: ANN202
        return JSONResponse(
            status_code=400, content=_envelope("error", str(exc), getattr(exc, "locator", None))
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(_req: Request, exc: StarletteHTTPException):  # noqa: ANN202
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            content = _envelope(detail["code"], detail.get("message", ""), detail.get("locator"))
        else:
            code = _CODE_FOR_STATUS.get(exc.status_code, "error")
            content = _envelope(code, str(detail))
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def _req_invalid(_req: Request, exc: RequestValidationError):  # noqa: ANN202
        first = exc.errors()[0] if exc.errors() else {}
        locator = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        return JSONResponse(
            status_code=422,
            content=_envelope("validation_error", first.get("msg", "invalid request"), locator or None),
        )

    @app.exception_handler(Exception)
    async def _unexpected(_req: Request, exc: Exception):  # noqa: ANN202
        log.exception("unhandled server error")
        return JSONResponse(
            status_code=500, content=_envelope("internal_error", "internal server error")
        )

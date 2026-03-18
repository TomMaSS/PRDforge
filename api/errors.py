"""Structured error responses for the Python API.

Format: {"error": {"code": "...", "message": "...", "status": N, "details": {}}}

9 standard error codes matching the PRD spec.
"""

from fastapi.responses import JSONResponse


# Standard error codes
UNAUTHORIZED = "UNAUTHORIZED"
PERMISSION_DENIED = "PERMISSION_DENIED"
NOT_FOUND = "NOT_FOUND"
VALIDATION_ERROR = "VALIDATION_ERROR"
CONFLICT = "CONFLICT"
RATE_LIMITED = "RATE_LIMITED"
INTERNAL_ERROR = "INTERNAL_ERROR"
CHAT_DISABLED = "CHAT_DISABLED"
NO_API_KEY = "NO_API_KEY"


def error_response(
    code: str,
    message: str,
    status: int,
    details: dict | None = None,
) -> JSONResponse:
    """Create a structured error response."""
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "status": status,
                "details": details or {},
            }
        },
        status_code=status,
    )


def not_found(resource: str, identifier: str) -> JSONResponse:
    return error_response(
        NOT_FOUND,
        f"{resource} '{identifier}' not found",
        404,
    )


def validation_error(message: str, details: dict | None = None) -> JSONResponse:
    return error_response(VALIDATION_ERROR, message, 400, details)


def unauthorized(message: str = "Authentication required") -> JSONResponse:
    return error_response(UNAUTHORIZED, message, 401)


def permission_denied(message: str = "Insufficient permissions") -> JSONResponse:
    return error_response(PERMISSION_DENIED, message, 403)


def conflict(message: str, details: dict | None = None) -> JSONResponse:
    return error_response(CONFLICT, message, 409, details)


def internal_error(message: str = "Internal server error") -> JSONResponse:
    return error_response(INTERNAL_ERROR, message, 500)

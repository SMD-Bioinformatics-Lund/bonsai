"""API client error handling."""

class HTTPException(Exception):
    """Generic request error."""

class BadRequestError(HTTPException):
    """400 error"""

class UnauthorizedError(HTTPException):
    """401 error. Used if authentication failed."""

class ForbiddenError(HTTPException):
    """403 error."""

class NotFoundError(HTTPException):
    """404 error."""

class ConflictError(HTTPException):
    """409 error."""

class TooManyRequestsError(HTTPException):
    """429 error."""

class ServerError(HTTPException):
    """For 5xx errors."""

class ApiRequestError(Exception):
    """Something went wrong requesting the data."""


_STATUS_TO_ERROR = {
    400: BadRequestError, 401: UnauthorizedError, 403: ForbiddenError, 404: NotFoundError,
    409: ConflictError, 429: TooManyRequestsError,
}

def raise_for_status(status: int, body: str | None = None):
    """Raise granualar errors depending on the HTTP status code."""
    if 400 <= status < 500:
        raise _STATUS_TO_ERROR.get(status, HTTPException)(body or f"HTTP {status}")
    if 500 <= status:
        raise ServerError(body or f"HTTP {status}")

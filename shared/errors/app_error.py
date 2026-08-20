"""
shared/errors/app_error.py
───────────────────────────
Application error hierarchy.

Design
──────
All errors in this system are subclasses of AppError.
AppError carries an HTTP status_code so the error handler middleware
can map domain errors to HTTP responses without a big if/elif chain.

This follows the "make illegal states unrepresentable" principle:
if a service raises NotFoundError, the HTTP layer knows it's a 404 —
no coupling between business logic and HTTP status numbers.

Usage in services
─────────────────
    raise NotFoundError("Group", group_id)         # → 404
    raise ValidationError("amount must be > 0")   # → 400
    raise ConflictError("expense already settled") # → 409
    raise DomainError("splits do not sum to total") # → 422
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail  # optional machine-readable detail for API consumers

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload


class ValidationError(AppError):
    """
    400 Bad Request — client sent data that fails validation rules.
    Example: negative expense amount, email already in use.
    """

    status_code = 400
    error_code = "VALIDATION_ERROR"


class AuthenticationError(AppError):
    """401 Unauthorized — missing or invalid credentials."""

    status_code = 401
    error_code = "AUTHENTICATION_ERROR"


class ForbiddenError(AppError):
    """403 Forbidden — authenticated but not authorised for this resource."""

    status_code = 403
    error_code = "FORBIDDEN"


class NotFoundError(AppError):
    """404 Not Found — resource does not exist or is not visible to this user."""

    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, resource: str, resource_id: str | None = None) -> None:
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} '{resource_id}' not found"
        super().__init__(msg)


class ConflictError(AppError):
    """409 Conflict — request conflicts with current resource state."""

    status_code = 409
    error_code = "CONFLICT"


class UnprocessableError(AppError):
    """
    422 Unprocessable Entity — request is well-formed but semantically invalid.
    Used by the AI module when LLM output is ambiguous.
    Example: parsed expense names don't match any group member.
    """

    status_code = 422
    error_code = "UNPROCESSABLE"


class DomainError(AppError):
    """
    422 — business rule violation in the domain layer.
    Example: PercentSplitStrategy percentages don't sum to 100.
    """

    status_code = 422
    error_code = "DOMAIN_ERROR"


class ExternalServiceError(AppError):
    """
    502 — upstream service (Claude API, email provider) returned an error.
    Distinct from 500 so clients know the problem is external, not our bug.
    """

    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Shared error codes (../contracts.md "Trusted context and structured errors")."""

    INPUT_INVALID = "INPUT_INVALID"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    PAUSE_REQUESTED = "PAUSE_REQUESTED"
    PAUSED = "PAUSED"
    REVISION_CONFLICT = "REVISION_CONFLICT"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    ASSISTANT_UNAVAILABLE = "ASSISTANT_UNAVAILABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class DspError(Exception):
    """A structured failure with a stable code; messages never carry secrets or raw data."""

    code: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True)
class TrustedContext:
    """Who is acting, derived by the application from authentication, never from request content."""

    principal: str
    tenant: str
    scopes: frozenset[str]

    @classmethod
    def local(cls) -> "TrustedContext":
        """Return the single-user local owner, who holds every role in the local build."""
        return cls("owner-local", "tenant-local", frozenset({"*"}))

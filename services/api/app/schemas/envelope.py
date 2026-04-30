"""
Standard API response envelope per spec §7:

{
  "data": <payload | null>,
  "meta": {
    "request_id": "req_...",
    "next_cursor": "...",
    "total": 1247,
    "took_ms": 48
  },
  "errors": []
}
"""

import time
import uuid
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    next_cursor: str | None = None
    total: int | None = None
    took_ms: int | None = None


class APIError(BaseModel):
    code: str
    message: str
    field: str | None = None


class APIResponse(BaseModel):
    """Standard CloudVisor API response envelope."""
    data: Any = None
    meta: Meta = Field(default_factory=Meta)
    errors: list[APIError] = Field(default_factory=list)


def ok(
    data: Any,
    total: int | None = None,
    next_cursor: str | None = None,
    took_ms: int | None = None,
    request_id: str | None = None,
) -> dict:
    """Build a successful response envelope."""
    meta = Meta(
        total=total,
        next_cursor=next_cursor,
        took_ms=took_ms,
    )
    if request_id:
        meta.request_id = request_id
    return APIResponse(data=data, meta=meta).model_dump()


def error(
    code: str,
    message: str,
    field: str | None = None,
    status_code: int = 400,
) -> dict:
    """Build an error response envelope."""
    return APIResponse(
        data=None,
        errors=[APIError(code=code, message=message, field=field)],
    ).model_dump()

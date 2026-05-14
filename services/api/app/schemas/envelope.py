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
  "errors": [
    { "code": "...", "message": "...", "field": null }
  ]
}

Cursor-based pagination helpers:
  - encode_cursor / decode_cursor  — opaque base64 JSON cursors
  - parse_filter_params            — parse filter[field]=value query params
  - parse_sort_param               — parse sort=field,-other_field
  - parse_fields_param             — parse fields[resource]=id,name,severity
"""

import base64
import json
import time
import uuid
from typing import Any, Generic, TypeVar
from urllib.parse import parse_qs

from pydantic import BaseModel, Field

T = TypeVar("T")


# ─── Envelope models ──────────────────────────────────────────────────────────

class Meta(BaseModel):
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    page: int | None = None
    per_page: int | None = None
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


# ─── Envelope builders ────────────────────────────────────────────────────────

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


# ─── Cursor-based pagination ──────────────────────────────────────────────────

def encode_cursor(payload: dict[str, Any]) -> str:
    """Encode a cursor dict to an opaque base64 string."""
    raw = json.dumps(payload, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode an opaque cursor string back to a dict. Returns {} on error."""
    try:
        padded = cursor + "=" * (4 - len(cursor) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return {}


def cursor_to_offset(cursor: str | None, default_limit: int = 50) -> tuple[int, int]:
    """
    Convert a cursor to (offset, limit) for upstream services that use offset pagination.
    The cursor encodes {"offset": N, "limit": M}.
    Returns (0, default_limit) when cursor is None or invalid.
    """
    if not cursor:
        return 0, default_limit
    data = decode_cursor(cursor)
    return data.get("offset", 0), data.get("limit", default_limit)


def make_next_cursor(offset: int, limit: int, total: int | None) -> str | None:
    """
    Build the next_cursor for a list response.
    Returns None when there are no more pages.
    """
    next_offset = offset + limit
    if total is not None and next_offset >= total:
        return None
    return encode_cursor({"offset": next_offset, "limit": limit})


# ─── Query parameter parsers ──────────────────────────────────────────────────

def parse_filter_params(query_string: str) -> dict[str, str]:
    """
    Parse filter[field]=value query parameters from a raw query string.

    Example: "filter[severity]=HIGH&filter[status]=open"
    Returns: {"severity": "HIGH", "status": "open"}
    """
    filters: dict[str, str] = {}
    parsed = parse_qs(query_string, keep_blank_values=False)
    for key, values in parsed.items():
        if key.startswith("filter[") and key.endswith("]"):
            field = key[7:-1]
            if field and values:
                filters[field] = values[0]
    return filters


def parse_sort_param(sort: str | None) -> list[tuple[str, str]]:
    """
    Parse sort=field,-other_field into a list of (field, direction) tuples.

    Example: "severity,-created_at"
    Returns: [("severity", "asc"), ("created_at", "desc")]
    """
    if not sort:
        return []
    result: list[tuple[str, str]] = []
    for part in sort.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("-"):
            result.append((part[1:], "desc"))
        else:
            result.append((part, "asc"))
    return result


def parse_fields_param(fields_raw: str | None, resource: str) -> list[str] | None:
    """
    Parse fields[resource]=field1,field2 from a pre-extracted value.

    The caller should extract the value of the `fields[<resource>]` query param
    and pass it here.  Returns None when no field selection is requested.

    Example: fields_raw="id,severity,title", resource="findings"
    Returns: ["id", "severity", "title"]
    """
    if not fields_raw:
        return None
    return [f.strip() for f in fields_raw.split(",") if f.strip()]

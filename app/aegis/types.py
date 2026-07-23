"""Shared validation and canonicalization helpers."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, field_validator


def new_id() -> str:
    return uuid4().hex


def utc_now() -> datetime:
    return datetime.now(UTC)


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class CorrelationIds(BaseModel):
    trace_id: str | None = None
    span_id: str | None = None
    workflow_execution_id: str | None = None

    @field_validator("trace_id")
    @classmethod
    def validate_trace(cls, value: str | None) -> str | None:
        if value is not None and (len(value) != 32 or any(char not in "0123456789abcdef" for char in value)):
            raise ValueError("trace_id must be 32 lowercase hexadecimal characters")
        return value

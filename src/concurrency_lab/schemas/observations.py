"""Shared validation for actual observation timestamps."""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator


def _validate_timestamp(value: str) -> str:
    if datetime.fromisoformat(value).tzinfo is None:
        raise ValueError("A timezone-aware collection timestamp is required")
    return value


CollectionTimestamp = Annotated[str, AfterValidator(_validate_timestamp)]

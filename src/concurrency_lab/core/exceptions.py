"""Safe service failures; HTTP mappings belong to the API boundary."""

from enum import StrEnum


class FailureCode(StrEnum):
    INVALID = "invalid_input"
    DISABLED = "business_disabled"
    NOT_FOUND = "not_found"
    OWNERSHIP = "ownership_mismatch"
    DATABASE = "database_unavailable"
    POOL = "pool_timeout"
    BUDGET = "request_timeout"


class BusinessFailure(Exception):
    def __init__(self, code: FailureCode) -> None:
        self.code = code
        super().__init__(code.value)

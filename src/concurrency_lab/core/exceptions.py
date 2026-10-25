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
    WRITES_DISABLED = "write_lab_disabled"
    STOCK = "insufficient_stock"
    IDEMPOTENCY = "idempotency_conflict"
    TRANSITION = "invalid_order_transition"
    CONFLICT = "transaction_conflict"
    INVARIANT = "inventory_invariant_failure"


class BusinessFailure(Exception):
    def __init__(self, code: FailureCode) -> None:
        self.code = code
        super().__init__(code.value)

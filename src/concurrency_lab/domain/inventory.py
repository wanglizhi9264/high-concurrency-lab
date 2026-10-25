"""Single-product stock accounting and stable client intent identity."""

import hashlib
import json
from enum import StrEnum
from uuid import UUID


class OrderState(StrEnum):
    RESERVED = "reserved"
    PAID = "paid"
    CANCELLED = "cancelled"


class InvalidTransition(ValueError):
    pass


def transition_changes_state(current: OrderState, target: OrderState) -> bool:
    if current == target:
        return False
    if current != OrderState.RESERVED or target not in (OrderState.PAID, OrderState.CANCELLED):
        raise InvalidTransition("Only reserved orders can enter a terminal state")
    return True


def order_fingerprint(scenario_id: UUID, user_id: int, quantity: int) -> str:
    payload = {"scenario_id": scenario_id.hex, "user_id": user_id, "quantity": quantity}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def audit_checks(
    initial: int,
    available: int,
    reserved: int,
    sold: int,
    reserved_order_units: int,
    paid_order_units: int,
) -> dict[str, bool]:
    return {
        "nonnegative": min(initial, available, reserved, sold) >= 0,
        "balance": available + reserved + sold == initial,
        "reserved_matches": reserved == reserved_order_units,
        "paid_matches": sold == paid_order_units,
    }

"""Owned transactions, stable lock order and safe intent replay for inventory writes."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

from sqlalchemy import RowMapping
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.db.business import BusinessResources, ObservedDatabase, pool_gauges
from concurrency_lab.domain.inventory import (
    InvalidTransition,
    OrderState,
    audit_checks,
    order_fingerprint,
    transition_changes_state,
)
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.repositories.inventory_repository import InventoryRepository
from concurrency_lab.schemas.inventory import (
    InventoryAudit,
    OrderInput,
    OrderResult,
    PurchaseOrderDTO,
    ScenarioDTO,
    ScenarioInput,
    ScenarioResult,
)

SOURCE = "src/concurrency_lab/services/inventory_service.py"
T = TypeVar("T")


class UniqueIntentConflict(Exception):
    """An entire failed transaction must unwind before resolving the committed winner."""


def mysql_error_code(error: DBAPIError) -> int | None:
    arguments = getattr(error.orig, "args", ())
    return arguments[0] if arguments and isinstance(arguments[0], int) else None


def _order(row: RowMapping) -> PurchaseOrderDTO:
    return PurchaseOrderDTO.model_validate(
        {name: row[name] for name in PurchaseOrderDTO.model_fields}
    )


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class InventoryService:
    def __init__(
        self, resources: BusinessResources, observation: RequestObservation, budget: float
    ) -> None:
        self.resources, self.observation, self.budget = resources, observation, budget

    async def _bounded(self, operation: Callable[[], Awaitable[T]]) -> T:
        observation = self.observation
        observation.pool_before = pool_gauges(self.resources.engine)
        observation.pool_before_offset_ms = observation.elapsed()
        try:
            async with asyncio.timeout(self.budget):
                with observation.span("Inventory workflow", "service", SOURCE):
                    return await operation()
        except PoolTimeout as error:
            raise BusinessFailure(FailureCode.POOL) from error
        except TimeoutError as error:
            raise BusinessFailure(FailureCode.BUDGET) from error
        except DBAPIError as error:
            code = mysql_error_code(error)
            if code in (1205, 1213):
                raise BusinessFailure(FailureCode.CONFLICT) from error
            if code == 1452:
                raise BusinessFailure(FailureCode.INVALID) from error
            raise BusinessFailure(FailureCode.DATABASE) from error
        finally:
            observation.pool_after = pool_gauges(self.resources.engine)
            observation.pool_after_offset_ms = observation.elapsed()

    async def _transaction(self, operation: Callable[[InventoryRepository], Awaitable[T]]) -> T:
        try:
            async with self.resources.sessions() as session:
                with self.observation.span(
                    "Explicit transaction (includes exit/commit)", "transaction", SOURCE
                ):
                    async with session.begin():
                        with self.observation.span(
                            "Acquire business connection",
                            "acquire",
                            "src/concurrency_lab/db/business.py",
                        ):
                            await session.connection(
                                execution_options={"isolation_level": "REPEATABLE READ"}
                            )
                        database = ObservedDatabase(session, self.observation)
                        await database.verify_ownership(self.observation.database)
                        return await operation(InventoryRepository(database))
        except IntegrityError as error:
            if mysql_error_code(error) == 1062:
                raise UniqueIntentConflict() from error
            raise

    async def create_scenario(self, intent: ScenarioInput) -> ScenarioResult:
        async def existing(repository: InventoryRepository) -> ScenarioResult:
            row = await repository.scenario(intent.scenario_id.hex)
            if row is None:
                raise BusinessFailure(FailureCode.CONFLICT)
            if row["product_id"] != intent.product_id or row["initial"] != intent.initial:
                raise BusinessFailure(FailureCode.IDEMPOTENCY)
            return ScenarioResult(scenario=ScenarioDTO.model_validate(row), replayed=True)

        async def create(repository: InventoryRepository) -> ScenarioResult:
            await repository.create_scenario(intent, _now())
            row = await repository.scenario(intent.scenario_id.hex)
            if row is None:
                raise BusinessFailure(FailureCode.INVARIANT)
            return ScenarioResult(scenario=ScenarioDTO.model_validate(row))

        async def workflow() -> ScenarioResult:
            try:
                return await self._transaction(create)
            except UniqueIntentConflict:
                return await self._transaction(existing)

        return await self._bounded(workflow)

    async def get_scenario(self, identifier: UUID) -> ScenarioResult:
        async def read(repository: InventoryRepository) -> ScenarioResult:
            row = await repository.scenario(identifier.hex)
            if row is None:
                raise BusinessFailure(FailureCode.NOT_FOUND)
            return ScenarioResult(scenario=ScenarioDTO.model_validate(row))

        return await self._bounded(lambda: self._transaction(read))

    async def create_order(self, intent: OrderInput, key: UUID) -> OrderResult:
        fingerprint = order_fingerprint(intent.scenario_id, intent.user_id, intent.quantity)

        def replay(row: RowMapping) -> OrderResult:
            if row["payload_sha256"] != fingerprint:
                raise BusinessFailure(FailureCode.IDEMPOTENCY)
            return OrderResult(order=_order(row), replayed=True)

        async def create(repository: InventoryRepository) -> OrderResult:
            existing = await repository.order_by_key(str(key))
            if existing is not None:
                return replay(existing)  # Replay precedes stock or terminal-state checks.
            scenario = await repository.scenario(intent.scenario_id.hex, locked=True)
            if scenario is None:
                raise BusinessFailure(FailureCode.NOT_FOUND)
            price = await repository.price(scenario["product_id"])
            if price is None:
                raise BusinessFailure(FailureCode.INVARIANT)
            # A winner may have committed while this request waited for the scenario lock.
            # Try the unique INSERT before stock checks, then resolve1062 in a fresh transaction.
            identifier = await repository.create_order(intent, str(key), fingerprint, price, _now())
            if await repository.reserve(intent.scenario_id.hex, intent.quantity) != 1:
                raise BusinessFailure(FailureCode.STOCK)
            row = await repository.order(identifier) if identifier is not None else None
            if row is None:
                raise BusinessFailure(FailureCode.INVARIANT)
            return OrderResult(order=_order(row), applied=True)

        async def resolve(repository: InventoryRepository) -> OrderResult:
            row = await repository.order_by_key(str(key))
            if row is None:
                raise BusinessFailure(FailureCode.CONFLICT)
            return replay(row)

        async def workflow() -> OrderResult:
            try:
                return await self._transaction(create)
            except UniqueIntentConflict:
                return await self._transaction(resolve)

        return await self._bounded(workflow)

    async def get_order(self, identifier: int | UUID) -> OrderResult:
        async def read(repository: InventoryRepository) -> OrderResult:
            row = (
                await repository.order_by_key(str(identifier))
                if isinstance(identifier, UUID)
                else await repository.order(identifier)
            )
            if row is None:
                raise BusinessFailure(FailureCode.NOT_FOUND)
            return OrderResult(order=_order(row))

        return await self._bounded(lambda: self._transaction(read))

    async def transition(self, identifier: int, target: OrderState) -> OrderResult:
        async def change(repository: InventoryRepository) -> OrderResult:
            initial = await repository.order(identifier)
            if initial is None:
                raise BusinessFailure(FailureCode.NOT_FOUND)
            # Pre-read identifies the immutable scenario; state comes from the current lock read.
            scenario = await repository.scenario(initial["scenario_id"], locked=True)
            row = await repository.order(identifier, locked=True)
            if scenario is None or row is None:
                raise BusinessFailure(FailureCode.INVARIANT)
            try:
                changed = transition_changes_state(OrderState(row["status"]), target)
            except InvalidTransition as error:
                raise BusinessFailure(FailureCode.TRANSITION) from error
            if not changed:
                return OrderResult(order=_order(row), replayed=True)
            if await repository.settle(row["scenario_id"], row["quantity"], target) != 1:
                raise BusinessFailure(FailureCode.INVARIANT)
            if await repository.change_state(identifier, target, _now()) != 1:
                raise BusinessFailure(FailureCode.INVARIANT)
            current = await repository.order(identifier, locked=True)
            if current is None:
                raise BusinessFailure(FailureCode.INVARIANT)
            return OrderResult(order=_order(current), applied=True)

        return await self._bounded(lambda: self._transaction(change))

    async def audit(self, identifier: UUID) -> InventoryAudit:
        async def read(repository: InventoryRepository) -> InventoryAudit:
            row = await repository.scenario(identifier.hex)
            if row is None:
                raise BusinessFailure(FailureCode.NOT_FOUND)
            aggregates = await repository.aggregate_orders(identifier.hex)
            units = {state.value: 0 for state in OrderState}
            counts = dict(units)
            for aggregate in aggregates:
                units[aggregate["status"]] = int(aggregate["units"])
                counts[aggregate["status"]] = int(aggregate["orders"])
            checks = audit_checks(
                row["initial"],
                row["available"],
                row["reserved"],
                row["sold"],
                units[OrderState.RESERVED],
                units[OrderState.PAID],
            )
            return InventoryAudit(
                scenario=ScenarioDTO.model_validate(row),
                order_units=units,
                order_counts=counts,
                checks=checks,
                all_pass=all(checks.values()),
                observed_at=datetime.now(UTC).isoformat(),
            )

        return await self._bounded(lambda: self._transaction(read))

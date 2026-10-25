"""Redis7 transport only: fixed scenario keys, bounded commands and honest observations."""

import asyncio
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from concurrency_lab.db.business import validate_business_database


class TaskStream:
    group = "receipt-v1"

    def __init__(self, client: Redis, database: str, scenario: UUID) -> None:
        self.client, self.database, self.scenario = (
            client,
            validate_business_database(database),
            scenario,
        )
        self.key = f"hcl:tasks:v1:{{{database}:{scenario.hex}}}:stream"
        self.cursor = "0-0"

    async def ensure_group(self) -> None:
        async with asyncio.timeout(0.25):
            try:
                # EXEC runs expiry even if CREATE reports the already-existing group.
                async with self.client.pipeline(transaction=True) as pipeline:
                    pipeline.xgroup_create(self.key, self.group, id="0-0", mkstream=True)
                    pipeline.pexpire(self.key, 86400000)
                    await pipeline.execute()
            except ResponseError as error:
                if "BUSYGROUP" not in str(error):
                    raise

    async def publish(self, task_id: str) -> str:
        UUID(hex=task_id)
        async with asyncio.timeout(0.25):
            # Atomic retention setup: connection loss cannot leave XADD without its TTL.
            async with self.client.pipeline(transaction=True) as pipeline:
                pipeline.xadd(self.key, {"task_id": task_id}, maxlen=1000, approximate=True)
                pipeline.pexpire(self.key, 86400000)
                result = await pipeline.execute()
            return str(result[0])

    async def receive(self, consumer: str, lease_ms: int) -> tuple[str, dict[str, str]] | None:
        await self.ensure_group()
        async with asyncio.timeout(0.25):
            reclaimed = await self.client.xautoclaim(
                self.key,
                self.group,
                consumer,
                min_idle_time=lease_ms,
                start_id=self.cursor,
                count=1,
            )
            # Redis7: next cursor, claimed messages, deleted entry IDs. Continue cursor.
            self.cursor = str(reclaimed[0])
            if reclaimed[1]:
                message_id, fields = reclaimed[1][0]
                return str(message_id), dict(fields)
            messages = await self.client.xreadgroup(
                self.group, consumer, {self.key: ">"}, count=1, block=100
            )
            if messages:
                message_id, fields = messages[0][1][0]
                return str(message_id), dict(fields)
            return None

    async def acknowledge(self, message_id: str) -> int:
        async with asyncio.timeout(0.25):
            return int(await self.client.xack(self.key, self.group, message_id))

    async def snapshot(self) -> dict[str, Any]:
        async with asyncio.timeout(0.25):
            retained = int(await self.client.xlen(self.key))
            pttl = int(await self.client.pttl(self.key))
            if pttl == -2:
                return {
                    "group_ready": False,
                    "retained_entries": 0,
                    "pending": 0,
                    "group_lag": None,
                    "pttl_ms": -2,
                }
            groups = await self.client.xinfo_groups(self.key)
            group = next((g for g in groups if g["name"] == self.group), None)
            pending = await self.client.xpending(self.key, self.group) if group else None
            return {
                "group_ready": group is not None,
                "retained_entries": retained,
                "pending": int(pending["pending"]) if pending else 0,
                "group_lag": group.get("lag") if group else None,
                "pttl_ms": pttl,
            }

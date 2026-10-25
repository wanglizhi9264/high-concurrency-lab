"""Fixed monitoring statements on the already-owned business engine."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.db.business import BUSINESS_PURPOSE
from concurrency_lab.schemas.benchmarks import BusinessMetrics


async def read_business_metrics(connection: AsyncConnection, result: BusinessMetrics) -> None:
    row = (
        (
            await connection.execute(
                text(
                    "SELECT DATABASE() AS database_name, VERSION() AS mysql_version, o.purpose, "
                    "d.order_count,d.seed,d.digest,d.status FROM experiment_ownership o "
                    "JOIN experiment_dataset d ON d.id=o.id WHERE o.id=1"
                )
            )
        )
        .mappings()
        .one()
    )
    if (
        row["database_name"] != result.database
        or row["purpose"] != BUSINESS_PURPOSE
        or row["status"] != "ready"
    ):
        raise BusinessFailure(FailureCode.OWNERSHIP)
    result.mysql_version = str(row["mysql_version"])
    result.dataset = {
        key: row[key] for key in ("purpose", "order_count", "seed", "digest", "status")
    }
    rows = (
        await connection.execute(
            text(
                "SHOW GLOBAL STATUS WHERE Variable_name IN "
                "('Threads_connected','Threads_running','Questions','Queries','Com_select','Uptime')"
            )
        )
    ).all()
    result.mysql_status = {str(row[0]): int(row[1]) for row in rows}

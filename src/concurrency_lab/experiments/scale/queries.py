"""Fixed comparable SQL and actual optimizer observations, not inferred index labels."""

from datetime import datetime
from typing import Any

from concurrency_lab.models.scale import QUERY_TABLES


def query_cases(
    table: str, count: int, cursor: tuple[datetime, int]
) -> dict[str, tuple[str, dict[str, Any]]]:
    if table not in QUERY_TABLES or count < 1:
        raise ValueError("Fixed009query table/count required")
    order = " ORDER BY created_at DESC,id DESC LIMIT 20"
    offset = int(count * 0.8)
    return {
        "primary_key": (
            f"SELECT id,total FROM {table} WHERE id=:id AND created_at=:time",
            {"id": cursor[1], "time": cursor[0]},
        ),
        "by_user": (
            f"SELECT id FROM {table} WHERE user_id=:user ORDER BY id LIMIT 20",
            {"user": 500},
        ),
        "user_projection": (
            f"SELECT id,created_at,total,status FROM {table} WHERE user_id=:user" + order,
            {"user": 500},
        ),
        "offset": (
            f"SELECT id,created_at FROM {table}" + order + " OFFSET :offset",
            {"offset": offset},
        ),
        "keyset": (
            f"SELECT id,created_at FROM {table} WHERE created_at<:time "
            "OR (created_at=:time AND id<:id)" + order,
            {"time": cursor[0], "id": cursor[1]},
        ),
        "time_range": (
            f"SELECT COUNT(*) AS orders,SUM(total) AS total FROM {table} "
            "WHERE created_at>=:start AND created_at<:end",
            {"start": datetime(2025, 7, 1), "end": datetime(2025, 8, 1)},
        ),
        "id_without_time": (
            f"SELECT id,total FROM {table} WHERE id=:id",
            {"id": max(1, count // 2)},
        ),
    }


def partition_observation(plan: dict[str, Any]) -> dict[str, Any]:
    partitions: set[str] = set()
    found_partitions, covering = False, False

    def visit(value: Any) -> None:
        nonlocal found_partitions, covering
        if isinstance(value, dict):
            if "partitions" in value:
                found_partitions = True
                partitions.update(value["partitions"])
            covering = covering or value.get("using_index") is True
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(plan)
    return {
        "selected_partitions": sorted(partitions) if found_partitions else None,
        "covering_observed": covering,
    }

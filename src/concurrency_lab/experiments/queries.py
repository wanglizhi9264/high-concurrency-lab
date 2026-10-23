"""Fixed SQL cases and explicit EXPLAIN ANALYZE iterator interpretation."""

import math
import re
from datetime import datetime
from typing import Any

NUMBER = r"[0-9.+eE-]+"
ACTUAL = re.compile(
    r"actual time=("
    + NUMBER
    + r")\.\.("
    + NUMBER
    + r") rows=("
    + NUMBER
    + r") loops=("
    + NUMBER
    + r")"
)


def parse_tree(tree: str) -> list[dict[str, Any]]:
    nodes = []
    for line in tree.splitlines():
        match = ACTUAL.search(line)
        if not match:
            continue
        first, last, rows, loops = map(float, match.groups())
        label = line.split("(actual time=")[0].strip()
        access = any(
            token in label.lower()
            for token in (
                "table scan",
                "index scan",
                "index range scan",
                "index lookup",
                "index range lookup",
                "rows fetched before execution",
            )
        )
        nodes.append(
            {
                "operator": label,
                "first_row_ms": first,
                "iterator_ms_per_loop": last,
                "actual_rows_per_loop": rows,
                "loops": loops,
                "access_rows": rows * loops if access else None,
            }
        )
    return nodes


def percentile(samples: list[float], quantile: float) -> float:
    if not samples:
        raise ValueError("No timing samples")
    values = sorted(samples)
    position = (len(values) - 1) * quantile
    low, high = math.floor(position), math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def query_set(
    count: int, user_id: int, offset: int, cursor: tuple[datetime, int]
) -> dict[str, tuple[str, dict[str, Any]]]:
    order = " ORDER BY created_at DESC, id DESC LIMIT 20"
    cursor_time, cursor_id = cursor
    return {
        "primary_key": ("SELECT id, total FROM lab_order WHERE id=:id", {"id": count // 2}),
        "by_user": (
            "SELECT id FROM lab_order WHERE user_id=:user_id ORDER BY id LIMIT 20",
            {"user_id": user_id},
        ),
        "user_time": (
            "SELECT id, created_at FROM lab_order WHERE user_id=:user_id" + order,
            {"user_id": user_id},
        ),
        "offset": (
            "SELECT id, created_at FROM lab_order" + order + " OFFSET :offset",
            {"offset": offset},
        ),
        "keyset": (
            "SELECT id, created_at FROM lab_order WHERE created_at < :cursor_time "
            "OR (created_at = :cursor_time AND id < :cursor_id)" + order,
            {"cursor_time": cursor_time, "cursor_id": cursor_id},
        ),
        "email": (
            "SELECT id FROM lab_user WHERE email=:email",
            {"email": "user0500@example.invalid"},
        ),
    }

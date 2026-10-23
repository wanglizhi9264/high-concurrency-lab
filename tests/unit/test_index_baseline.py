from datetime import datetime

import pytest

from concurrency_lab.experiments.dataset import order_batches
from concurrency_lab.experiments.queries import parse_tree, percentile, query_set
from concurrency_lab.experiments.safety import validate_database


def test_database_allowlist():
    for bad in (
        "concurrency_lab",
        "mysql",
        "concurrency_lab_exp_002_test;DROP DATABASE mysql",
        "concurrency_lab_exp_002_other",
    ):
        with pytest.raises(ValueError):
            validate_database(bad)
    assert validate_database("concurrency_lab_exp_002_10000") == "concurrency_lab_exp_002_10000"


def test_deterministic_bounded_batches():
    first = list(order_batches(105, 42, 20))
    second = list(order_batches(105, 42, 31))
    assert all(len(orders) <= 20 and len(items) <= 40 for orders, items in first)
    assert [row for batch, _ in first for row in batch] == [
        row for batch, _ in second for row in batch
    ]
    assert [row for _, batch in first for row in batch] == [
        row for _, batch in second for row in batch
    ]
    assert len(first) == 6
    assert first != list(order_batches(105, 43, 20))


def test_reject_invalid_generation():
    for count, batch in ((0, 10), (10, 0), (10, 10001)):
        with pytest.raises(ValueError):
            next(order_batches(count, 42, batch))


def test_plan_actual_leaf_rows():
    tree = """-> Limit: 20 row(s) (actual time=0.1..2 rows=20 loops=1)
    -> Index range scan on lab_order using ix_order_time (actual time=0.1..1 rows=8e+2 loops=2)"""
    nodes = parse_tree(tree)
    assert len(nodes) == 2
    assert nodes[-1]["access_rows"] == 1600
    assert nodes[0]["access_rows"] is None
    assert percentile([1, 2, 3], 0.5) == 2


def test_stable_queries():
    queries = query_set(100, 1, 80, (datetime(2025, 1, 1), 5))
    assert "created_at DESC, id DESC" in queries["offset"][0]
    assert "id < :cursor_id" in queries["keyset"][0]
    assert "created_at = :cursor_time" in queries["keyset"][0]


async def test_ownership_guard_rejects_wrong_database_and_marker():
    from unittest.mock import AsyncMock

    from concurrency_lab.experiments.safety import assert_owned

    database = "concurrency_lab_exp_002_test"
    connection = AsyncMock()
    connection.scalar.side_effect = ["concurrency_lab"]
    with pytest.raises(ValueError, match="does not match"):
        await assert_owned(connection, database)
    connection.scalar.side_effect = [database, "wrong-purpose"]
    with pytest.raises(ValueError, match="ownership"):
        await assert_owned(connection, database)


def test_baseline_identity_gate():
    import json
    from pathlib import Path
    from unittest.mock import patch

    from concurrency_lab.experiments.runner import load_baseline

    with patch.object(
        Path,
        "read_text",
        return_value=json.dumps(
            {
                "phase": "baseline",
                "revision": "0002",
                "database": "concurrency_lab_exp_002_test",
                "dataset": {"digest": "wrong"},
            }
        ),
    ):
        with pytest.raises(ValueError, match="does not match"):
            load_baseline(Path("."), "concurrency_lab_exp_002_test", {"digest": "right"})


def test_hash_independent_of_batch_size():
    import hashlib

    from concurrency_lab.experiments.dataset import digest_batch

    hashes = []
    for size in (7, 100):
        hasher = hashlib.sha256()
        for orders, items in order_batches(100, 42, size):
            digest_batch(hasher, orders, items)
        hashes.append(hasher.hexdigest())
    assert hashes[0] == hashes[1]


def test_generated_order_totals_and_item_keys():
    from decimal import Decimal

    for orders, items in order_batches(53, 42, 11):
        for position, order in enumerate(orders):
            pair = items[position * 2 : position * 2 + 2]
            assert all(item["order_id"] == order["id"] for item in pair)
            assert pair[0]["product_id"] != pair[1]["product_id"]
            assert order["total"] == sum(
                (item["unit_price"] * item["quantity"] for item in pair), Decimal(0)
            )

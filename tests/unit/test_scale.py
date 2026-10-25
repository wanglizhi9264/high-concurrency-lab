import hashlib
from datetime import datetime

import pytest

from concurrency_lab.experiments.scale.dataset import canonical_row, row_batches
from concurrency_lab.experiments.scale.queries import partition_observation, query_cases
from concurrency_lab.experiments.scale.safety import validate_batch_budget, validate_target


def test_generator_sha_does_not_depend_on_batching_and_has_ties():
    def generate(batch):
        return [row for rows in row_batches(3000, 20261025, batch) for row in rows]

    first, second = generate(17), generate(1000)
    assert first == second
    assert (
        hashlib.sha256(b"".join(map(canonical_row, first))).hexdigest()
        == hashlib.sha256(b"".join(map(canonical_row, second))).hexdigest()
    )
    assert len({r["created_at"].month for r in first}) == 12
    assert len({r["created_at"] for r in first}) < len(first)
    assert all(datetime(2025, 1, 1) <= r["created_at"] < datetime(2026, 1, 1) for r in first)


def test_scale_targets_are_exact_and_ten_million_requires_explicit_opt_in():
    assert (
        validate_target("concurrency_lab_exp_009_10000", 10000) == "concurrency_lab_exp_009_10000"
    )
    for database, count in [
        ("concurrency_lab", 10000),
        ("concurrency_lab_exp_002_10000", 10000),
        ("concurrency_lab_exp_009_10000", 100000),
        ("concurrency_lab_exp_009_10000000", 10000000),
    ]:
        with pytest.raises(ValueError):
            validate_target(database, count)
    assert validate_target("concurrency_lab_exp_009_10000000", 10000000, True)
    for batch in (0, 10001):
        with pytest.raises(ValueError):
            next(row_batches(1, 20261025, batch))
    with pytest.raises(ValueError):
        validate_batch_budget(1000000, 1)
    validate_batch_budget(10000000, 1000)


def test_fixed_query_cases_expose_projection_and_do_not_accept_table_sql():
    cases = query_cases("scale_order", 10000, (datetime(2025, 3, 1), 5))
    assert "total" in cases["user_projection"][0] and "status" in cases["user_projection"][0]
    assert "id DESC" in cases["offset"][0] and "id DESC" in cases["keyset"][0]
    with pytest.raises(ValueError):
        query_cases("scale_order; DROP DATABASE anything", 10000, (datetime(2025, 3, 1), 5))
    assert partition_observation(
        {"query_block": {"table": {"table_name": "p", "partitions": ["p3"], "using_index": True}}}
    ) == {"selected_partitions": ["p3"], "covering_observed": True}
    assert partition_observation({"query_block": {"table": {"using_index_condition": True}}}) == {
        "selected_partitions": None,
        "covering_observed": False,
    }

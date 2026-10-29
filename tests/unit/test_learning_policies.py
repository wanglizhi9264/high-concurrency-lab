"""Business decisions have no clock, random source, database or broker dependency."""

from dataclasses import FrozenInstanceError

import pytest

from concurrency_lab.domain.cache import CacheTtl
from concurrency_lab.domain.tasks import failure_decision


@pytest.mark.parametrize("seconds", [1, 5, 60])
def test_ttl_retains_original_distribution_endpoints(seconds):
    ttl = CacheTtl(seconds)
    assert ttl.expiration_ms(0) == seconds * 1000
    assert ttl.expiration_ms(ttl.jitter_limit_ms) == seconds * 1100
    with pytest.raises(FrozenInstanceError):
        ttl.ttl_seconds = 2


@pytest.mark.parametrize("seconds", [0, 61, -1, True, 1.5])
def test_invalid_ttl_is_rejected(seconds):
    with pytest.raises(ValueError):
        CacheTtl(seconds)


@pytest.mark.parametrize("jitter", [-1, 101, True, 0.5])
def test_jitter_must_stay_inside_the_declared_integer_window(jitter):
    with pytest.raises(ValueError):
        CacheTtl(1).expiration_ms(jitter)


@pytest.mark.parametrize("attempt,delay", [(1, 0.2), (2, 0.4), (3, 0.8), (4, 1.6), (5, 2)])
def test_failure_preserves_backoff_and_attempt_limit(attempt, delay):
    decision = failure_decision(attempt, 5, "handler_timeout")
    assert decision.delay_seconds == delay
    assert decision.terminal is (attempt == 5)


def test_invalid_business_precondition_never_retries():
    assert failure_decision(1, 5, "invalid_paid_order").terminal
    assert not failure_decision(1, 5, "handler_database_unavailable").terminal
    assert failure_decision(1, 1, "controlled_failure").terminal


@pytest.mark.parametrize("attempt,limit", [(0, 5), (2, 1), (1, 6), (True, 5), (1, 1.5)])
def test_invalid_attempt_range_is_rejected(attempt, limit):
    with pytest.raises(ValueError):
        failure_decision(attempt, limit, "controlled_failure")

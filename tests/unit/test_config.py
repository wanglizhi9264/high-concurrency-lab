import pytest
from pydantic import ValidationError

from concurrency_lab.core.config import Settings


def test_required_passwords():
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_pool_and_redacted_input():
    with pytest.raises(ValidationError) as exc:
        Settings(mysql_password="private-value", redis_password="private-value", db_pool_size=0)
    assert "private-value" not in str(exc.value)

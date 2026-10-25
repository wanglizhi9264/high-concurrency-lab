"""Isolation guards before any container/process/clone acceptance is permitted."""

import importlib.util
import socket
from pathlib import Path

import pytest


@pytest.fixture
def runner():
    path = Path(__file__).resolve().parents[2] / "scripts/verify_end_to_end.py"
    spec = importlib.util.spec_from_file_location("isolated_acceptance_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rejects_existing_clone_paths_and_traversal(runner, tmp_path):
    name = "e2e-20261025T000000-1234abcd"
    target = runner.clone_target(tmp_path, name)
    assert target.parent == tmp_path.resolve()
    target.mkdir()
    with pytest.raises(FileExistsError):
        runner.clone_target(tmp_path, name)
    with pytest.raises(ValueError):
        runner.clone_target(tmp_path, "../anything")


def test_ports_must_be_free_distinct_and_disjoint_from_developer_defaults(runner):
    ports = {
        "mysql": 15006,
        "redis": 15379,
        "experiment": 15306,
        "api": 18004,
        "load": 18005,
        "frontend": 5175,
    }
    for modified in ({**ports, "api": 18002}, {**ports, "api": 15306}, {**ports, "api": 80}):
        with pytest.raises(ValueError):
            runner.validate_ports(modified)
    with socket.socket() as held:
        held.bind(("127.0.0.1", 0))
        with pytest.raises(ValueError):
            runner.validate_ports({**ports, "api": held.getsockname()[1]})


def test_isolated_env_overrides_config_and_redacts_generated_secrets(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("PYTHONPATH", "private-source")
    monkeypatch.setenv("COMPOSE_FILE", "private-compose")
    secrets = {
        key: f"fixture-{key}"
        for key in ("MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD", "REDIS_PASSWORD", "EXP_MYSQL_PASSWORD")
    }
    ports = {
        "mysql": 15006,
        "redis": 15379,
        "experiment": 15306,
        "api": 18004,
        "load": 18005,
        "frontend": 5175,
    }
    environment = runner.isolated_environment(tmp_path, "hcl-e2e-009-1234abcd", ports, secrets)
    assert "PYTHONPATH" not in environment and "COMPOSE_FILE" not in environment
    assert environment["CONCURRENCY_LAB_ROOT"] == str(tmp_path)
    assert environment["MYSQL_PORT"] == "15006" and environment["PLAYWRIGHT_API_PORT"] == "18004"
    assert environment["PLAYWRIGHT_REUSE_SERVER"] == "false"
    assert all(environment[key] == value for key, value in secrets.items())
    text = runner.redact(f"{tmp_path} {secrets['MYSQL_PASSWORD']}", secrets, tmp_path)
    assert secrets["MYSQL_PASSWORD"] not in text and str(tmp_path) not in text

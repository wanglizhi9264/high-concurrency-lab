"""Destructive-to-availability local acceptance; leaves dependencies running."""

import subprocess

import httpx


def run(*args):
    subprocess.run(args, check=True)


def probe(expected):
    with httpx.Client(timeout=6, trust_env=False) as client:
        live = client.get("http://127.0.0.1:18000/health/live")
        ready = client.get("http://127.0.0.1:18000/health/ready")
        assert live.status_code == 200
        assert ready.status_code == expected, ready.text
        print(f"live={live.status_code} ready={ready.status_code} {ready.text}", flush=True)


probe(200)
for service in ("redis", "mysql"):
    try:
        run("docker", "compose", "stop", service)
        probe(503)
    finally:
        run("docker", "compose", "start", "--wait", service)
    probe(200)
run("docker", "compose", "down")
run("docker", "compose", "up", "-d", "--wait")
run("uv", "run", "alembic", "current")
probe(200)

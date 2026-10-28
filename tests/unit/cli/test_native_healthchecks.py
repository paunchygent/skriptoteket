"""Native health contracts using real HTTP and storage writes with fake worker tools."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import uvicorn
import yaml
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

ROOT = Path(__file__).resolve().parents[3]
COMMANDS = ROOT / "src/skriptoteket/cli/commands"
WORKER = COMMANDS / "healthcheck_execution_worker.sh"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/timeout":
            time.sleep(0.4)
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
        elif self.path == "/loop":
            self.send_response(302)
            self.send_header("Location", "/loop")
        else:
            self.send_response({"/fail": 503, "/not-modified": 304}.get(self.path, 200))
        self.end_headers()

    def log_message(self, *args) -> None:
        pass


@contextmanager
def server():
    instance = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance.server_address[1]
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join()


@contextmanager
def recording_server():
    """Local HTTP server that records the `Host` header of every request."""
    recorded: list[str] = []

    class RecordingHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            recorded.append(self.headers.get("Host", ""))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args) -> None:
            pass

    instance = ThreadingHTTPServer(("127.0.0.1", 0), RecordingHandler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance.server_address[1], recorded
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join()


def healthcheck_script(tmp_path: Path, name: str) -> Path:
    script = tmp_path / name
    script.write_text((COMMANDS / "healthcheck_web.sh").read_text())
    return script


@pytest.mark.parametrize(
    ("endpoint", "success"),
    [
        ("/ok", True),
        ("/redirect", True),
        ("/fail", False),
        ("/not-modified", False),
        ("/loop", False),
        ("/timeout", False),
    ],
)
def test_web_http_contract(tmp_path: Path, endpoint: str, success: bool) -> None:
    with server() as port:
        script = tmp_path / "web.sh"
        script.write_text(
            (COMMANDS / "healthcheck_web.sh")
            .read_text()
            .replace("http://localhost:8000/healthz", f"http://127.0.0.1:{port}{endpoint}")
            .replace("--max-time 10", "--max-time 0.2")
        )
        result = subprocess.run(["/bin/sh", str(script)], capture_output=True, timeout=2)
    assert (result.returncode == 0) is success
    assert result.stdout == b""


def test_web_healthcheck_sends_the_configured_allowed_host(tmp_path: Path) -> None:
    """Production refuses loopback hosts, so the probe must name the public host."""
    with recording_server() as (port, recorded):
        result = subprocess.run(
            [
                "/bin/sh",
                str(healthcheck_script(tmp_path, "host-web.sh")),
                f"http://127.0.0.1:{port}/healthz/live",
                "skriptoteket.hule.education",
            ],
            capture_output=True,
            timeout=20,
        )

    assert result.returncode == 0
    assert recorded == ["skriptoteket.hule.education"]


def test_production_host_gate_accepts_the_healthcheck_request(tmp_path: Path) -> None:
    """The production probe passes the real TrustedHostMiddleware; a loopback probe does not.

    Serves a minimal liveness app behind `TrustedHostMiddleware` with the
    production allowed host, then runs the shipped healthcheck script against
    it with and without the allowed host.
    """

    async def liveness(scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b'{"status":"ok"}'})

    gate: ASGIApp = TrustedHostMiddleware(liveness, allowed_hosts=["skriptoteket.hule.education"])
    config = uvicorn.Config(
        app=gate, host="127.0.0.1", port=0, log_level="error", lifespan="off", access_log=False
    )
    instance = uvicorn.Server(config)
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not instance.started:
        assert time.monotonic() < deadline, "uvicorn did not start"
        time.sleep(0.01)

    port = instance.servers[0].sockets[0].getsockname()[1]
    script = healthcheck_script(tmp_path, "prod-web.sh")
    url = f"http://127.0.0.1:{port}/healthz/live"
    try:
        allowed = subprocess.run(
            ["/bin/sh", str(script), url, "skriptoteket.hule.education"],
            capture_output=True,
            timeout=20,
        )
        refused = subprocess.run(["/bin/sh", str(script), url], capture_output=True, timeout=20)
    finally:
        instance.should_exit = True
        thread.join(timeout=10)

    assert allowed.returncode == 0
    assert refused.returncode == 1


def executable(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


def worker_environment(tmp_path: Path) -> dict[str, str]:
    timeout = shutil.which("timeout") or shutil.which(
        "timeout", path="/usr/bin:/opt/homebrew/bin:/usr/local/bin"
    )
    if timeout is None:
        pytest.fail("Worker healthcheck tests require GNU timeout (install coreutils).")
    tools = tmp_path / "tools"
    tools.mkdir()
    executable(
        tools / "timeout",
        f'printf "%s\\n" "$@" > "$TIMEOUT_RECEIPT"\nexec {shlex.quote(timeout)} "$@"\n',
    )
    executable(
        tools / "psql",
        'printf "%s" "$PGDATABASE" > "$RECEIPT"\n'
        'printf "%s\\n" "$@" > "$QUERY_RECEIPT"\n'
        'exit "${DB_EXIT:-0}"\n',
    )
    executable(
        tools / "curl",
        'printf "%s" "$*" > "$SOCKET_RECEIPT"\n'
        'printf "%s" "${DOCKER_RESPONSE:-OK}"\n'
        'exit "${DOCKER_EXIT:-0}"\n',
    )
    return {
        **os.environ,
        "PATH": f"{tools}:/usr/bin:/bin",
        "DATABASE_URL": "postgresql+asyncpg://user:fake-secret@db/test",
        "ARTIFACTS_ROOT": str(tmp_path / "artifacts"),
        "RECEIPT": str(tmp_path / "database"),
        "QUERY_RECEIPT": str(tmp_path / "query"),
        "TIMEOUT_RECEIPT": str(tmp_path / "timeout"),
        "SOCKET_RECEIPT": str(tmp_path / "socket"),
        "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
    }


def run_worker(environment: dict[str, str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["/bin/sh", str(WORKER)], env=environment, capture_output=True, timeout=6)


def test_worker_queries_database_pings_selected_socket_and_cleans_write(tmp_path: Path) -> None:
    environment = worker_environment(tmp_path)
    executable(
        tmp_path / "tools/rm",
        'for argument in "$@"; do\n'
        '    if [ -f "$argument" ]; then cat "$argument" > "$WRITE_RECEIPT"; fi\n'
        'done\nexec /bin/rm "$@"\n',
    )
    environment["WRITE_RECEIPT"] = str(tmp_path / "write")
    result = run_worker(environment)
    assert result.returncode == 0
    assert result.stdout == result.stderr == b""
    database_url = "postgresql://user:fake-secret@db/test?connect_timeout=2"
    assert Path(environment["RECEIPT"]).read_text() == database_url
    query_arguments = [
        "--dbname",
        database_url,
        "--no-psqlrc",
        "--no-password",
        "--set",
        "ON_ERROR_STOP=1",
        "--tuples-only",
        "--no-align",
        "--command",
        "SELECT 1",
    ]
    assert Path(environment["QUERY_RECEIPT"]).read_text().splitlines() == query_arguments
    assert Path(environment["TIMEOUT_RECEIPT"]).read_text().splitlines() == [
        "4",
        "psql",
        *query_arguments,
    ]
    assert Path(environment["SOCKET_RECEIPT"]).read_text() == (
        "--silent --fail --noproxy * --max-time 3 "
        "--unix-socket /run/user/1000/docker.sock http://localhost/_ping"
    )
    assert Path(environment["WRITE_RECEIPT"]).read_text() == "ok"
    assert list(Path(environment["ARTIFACTS_ROOT"]).iterdir()) == []


@pytest.mark.parametrize("exit_code", ["2", "3"])
def test_database_authentication_or_query_failure_is_safe(tmp_path: Path, exit_code: str) -> None:
    environment = worker_environment(tmp_path)
    environment["DB_EXIT"] = exit_code
    result = run_worker(environment)
    assert result.returncode != 0
    assert result.stderr == b"Database healthcheck failed\n"
    assert Path(environment["RECEIPT"]).exists()
    assert not Path(environment["SOCKET_RECEIPT"]).exists()
    assert not Path(environment["ARTIFACTS_ROOT"]).exists()


@pytest.mark.parametrize(("response", "exit_code"), [("not OK", "0"), ("", "7"), ("OK", "22")])
def test_docker_transport_http_and_response_failures(
    tmp_path: Path, response: str, exit_code: str
) -> None:
    environment = worker_environment(tmp_path)
    environment.update(DOCKER_RESPONSE=response, DOCKER_EXIT=exit_code)
    result = run_worker(environment)
    assert result.returncode != 0
    expected_error = (
        b"Docker healthcheck response failed\n"
        if exit_code == "0"
        else b"Docker healthcheck failed\n"
    )
    assert result.stderr == expected_error
    assert Path(environment["RECEIPT"]).exists()
    assert Path(environment["SOCKET_RECEIPT"]).exists()
    assert not Path(environment["ARTIFACTS_ROOT"]).exists()


def test_artifact_create_failure(tmp_path: Path) -> None:
    environment = worker_environment(tmp_path)
    Path(environment["ARTIFACTS_ROOT"]).write_text("a file blocks mkdir")
    result = run_worker(environment)
    assert result.returncode != 0
    assert result.stderr == b"Artifacts healthcheck failed\n"
    assert Path(environment["RECEIPT"]).exists()
    assert Path(environment["SOCKET_RECEIPT"]).exists()
    assert Path(environment["ARTIFACTS_ROOT"]).read_text() == "a file blocks mkdir"


def test_actual_write_failure_removes_created_probe(tmp_path: Path) -> None:
    environment = worker_environment(tmp_path)
    probe = Path(environment["ARTIFACTS_ROOT"]) / ".healthcheck-worker-write-failure"
    executable(
        tmp_path / "tools/mktemp",
        f'ln -s "{tmp_path}" "{probe}"\nprintf "%s" "{probe}"\n',
    )
    result = run_worker(environment)
    assert result.returncode != 0
    assert result.stderr == b"Artifacts healthcheck write failed\n"
    assert Path(environment["RECEIPT"]).exists()
    assert Path(environment["SOCKET_RECEIPT"]).exists()
    assert not probe.is_symlink()
    assert list(probe.parent.iterdir()) == []


@pytest.mark.parametrize("proxy_name", ["http_proxy", "HTTP_PROXY"])
def test_web_preserves_http_proxy_case_and_ignores_all_proxy(
    tmp_path: Path, proxy_name: str
) -> None:
    with server() as port:
        script = tmp_path / "proxy-web.sh"
        script.write_text(
            (COMMANDS / "healthcheck_web.sh")
            .read_text()
            .replace("http://localhost:8000/healthz", "http://native-health.invalid/ok")
            .replace("--max-time 10", "--max-time 0.2")
        )
        environment = {
            name: value
            for name, value in os.environ.items()
            if "proxy" not in name.lower() and name != "REQUEST_METHOD"
        }
        environment.update(
            {proxy_name: f"http://127.0.0.1:{port}", "ALL_PROXY": "http://127.0.0.1:1"}
        )
        result = subprocess.run(
            ["/bin/sh", str(script)], env=environment, capture_output=True, timeout=2
        )
    assert result.returncode == 0


@pytest.mark.parametrize(
    ("compose_name", "interval", "url", "host"),
    [
        ("compose.yaml", "30s", "http://localhost:8000/healthz/live", None),
        ("compose.hemma-dev.yaml", "15s", "http://localhost:8000/healthz/live", None),
        # Production refuses loopback allowed hosts, so its probe names the public host.
        (
            "compose.prod.yaml",
            "30s",
            "http://127.0.0.1:8000/healthz/live",
            "skriptoteket.hule.education",
        ),
    ],
)
def test_recurring_web_checks_select_passive_liveness(
    compose_name: str, interval: str, url: str, host: str | None
) -> None:
    compose = yaml.safe_load((ROOT / compose_name).read_text())
    test_command = [
        "CMD",
        "/bin/sh",
        "/app/src/skriptoteket/cli/commands/healthcheck_web.sh",
        url,
    ]
    if host is not None:
        test_command.append(host)
    assert compose["services"]["web"]["healthcheck"] == {
        "test": test_command,
        "interval": interval,
        "timeout": "10s",
        "retries": 3,
        "start_period": "10s",
    }

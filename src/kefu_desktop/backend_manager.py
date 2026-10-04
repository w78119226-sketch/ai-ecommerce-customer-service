"""Lifecycle management for the local Decision API process.

The manager owns only the process it starts.  It never searches for or kills
other Python/uvicorn processes, which makes it safe to use from the desktop
client while a developer runs another service in parallel.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from collections import deque
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

LogCallback = Callable[[str, str], None]


class BackendManager:
    """Start, monitor, and stop the repository's Decision API.

    ``project_root`` is the repository root containing ``src``.  The manager
    uses the current Python interpreter by default, so a virtual environment
    selected to launch the desktop app is also used for the API process.
    """

    def __init__(
        self,
        project_root: str | Path | None = None,
        *,
        python_executable: str | Path | None = None,
        host: str = "127.0.0.1",
        port: int = 18080,
        env: Mapping[str, str] | None = None,
        health_timeout: float = 1.5,
        log_callback: LogCallback | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path(__file__).resolve().parents[2]).resolve()
        self.python_executable = str(python_executable or sys.executable)
        self.host = str(host or "127.0.0.1")
        self.port = int(port)
        self.health_timeout = max(0.1, float(health_timeout))
        self._extra_env = {str(k): str(v) for k, v in (env or {}).items()}
        self._log_callback = log_callback
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.RLock()
        self._logs: deque[tuple[str, str]] = deque(maxlen=2000)
        self._last_error = ""
        self._reader_threads: list[threading.Thread] = []

    @property
    def process(self) -> subprocess.Popen[str] | None:
        with self._lock:
            return self._process

    @property
    def pid(self) -> int | None:
        process = self.process
        return process.pid if process and process.poll() is None else None

    @property
    def last_error(self) -> str:
        with self._lock:
            return self._last_error

    @property
    def logs(self) -> list[tuple[str, str]]:
        with self._lock:
            return list(self._logs)

    @property
    def health_url(self) -> str:
        return f"http://{self.host}:{self.port}/health"

    def command(self) -> list[str]:
        return [
            self.python_executable,
            "-m",
            "uvicorn",
            "kefu_clawbot.main:app",
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]

    def _environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(self._extra_env)
        src_path = str((self.project_root / "src").resolve())
        existing = environment.get("PYTHONPATH", "")
        paths = [item for item in existing.split(os.pathsep) if item]
        if src_path not in paths:
            paths.insert(0, src_path)
        environment["PYTHONPATH"] = os.pathsep.join(paths)
        return environment

    def update_environment(self, env: Mapping[str, str]) -> None:
        """Replace desktop-managed environment values for the next start."""
        with self._lock:
            self._extra_env = {str(k): str(v) for k, v in env.items()}

    def _emit(self, stream: str, line: str) -> None:
        text = line.rstrip("\r\n")
        if not text:
            return
        with self._lock:
            self._logs.append((stream, text))
        callback = self._log_callback
        if callback:
            try:
                callback(stream, text)
            except Exception:
                # A UI callback must never stop process output collection.
                pass

    def _read_stream(self, stream_name: str, pipe: object) -> None:
        try:
            for line in pipe:  # type: ignore[union-attr]
                self._emit(stream_name, line)
        except (OSError, ValueError):
            return

    def start(self) -> bool:
        """Start the API and return whether a new process was created."""
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return False
            self._last_error = ""
            kwargs: dict[str, object] = {
                "cwd": str(self.project_root),
                "env": self._environment(),
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "bufsize": 1,
            }
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            else:
                kwargs["start_new_session"] = True
            try:
                process = subprocess.Popen(self.command(), **kwargs)  # type: ignore[arg-type]
            except OSError as exc:
                self._last_error = str(exc)
                self._emit("manager", f"启动后端失败: {exc}")
                self._process = None
                return False
            self._process = process
            self._reader_threads = []
            for stream_name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
                if pipe is None:
                    continue
                thread = threading.Thread(
                    target=self._read_stream,
                    args=(stream_name, pipe),
                    name=f"kefu-backend-{stream_name}",
                    daemon=True,
                )
                thread.start()
                self._reader_threads.append(thread)
            return True

    def health(self) -> bool:
        """Return whether the owned API responds successfully to ``/health``."""
        if self.pid is None:
            return False
        try:
            with urllib_request.urlopen(self.health_url, timeout=self.health_timeout) as response:
                return 200 <= int(response.status) < 300
        except (urllib_error.URLError, OSError, TimeoutError, ValueError):
            return False

    def status(self) -> str:
        """Return one of ``stopped``, ``starting``, ``running`` or ``error``."""
        process = self.process
        if process is None:
            return "stopped"
        returncode = process.poll()
        if returncode is not None:
            return "error" if returncode else "stopped"
        return "running" if self.health() else "starting"

    def stop(self, timeout: float = 5.0) -> bool:
        """Stop only the process started by this manager."""
        with self._lock:
            process = self._process
        if process is None:
            return False
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=max(0.1, float(timeout)))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
        with self._lock:
            if self._process is process:
                self._process = None
        return True

    def close(self) -> None:
        self.stop()

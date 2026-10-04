from __future__ import annotations

from pathlib import Path

from kefu_desktop.backend_manager import BackendManager


def test_manager_uses_pathlib_and_windows_safe_paths(tmp_path: Path) -> None:
    root = tmp_path / "中文 项目"
    root.mkdir()
    manager = BackendManager(root, python_executable=root / "venv" / "Scripts" / "python.exe")
    assert manager.project_root == root.resolve()
    assert manager.command()[-1] == "18080"
    environment = manager._environment()
    assert str((root / "src").resolve()) in environment["PYTHONPATH"].split(
        __import__("os").pathsep
    )


def test_status_without_owned_process_is_stopped(tmp_path: Path) -> None:
    manager = BackendManager(tmp_path)
    assert manager.pid is None
    assert manager.status() == "stopped"
    assert manager.health() is False
    assert manager.stop() is False


def test_log_callback_and_process_lifecycle_are_owned(monkeypatch, tmp_path: Path) -> None:
    events: list[tuple[str, str]] = []

    class FakePipe:
        def __iter__(self):
            return iter(["hello\\n"])

    class FakeProcess:
        pid = 4312
        stdout = FakePipe()
        stderr = FakePipe()

        def __init__(self) -> None:
            self.returncode = None
            self.terminated = False

        def poll(self):
            return self.returncode

        def terminate(self):
            self.terminated = True
            self.returncode = 0

        def wait(self, timeout=None):
            return self.returncode

    process = FakeProcess()
    monkeypatch.setattr(
        "kefu_desktop.backend_manager.subprocess.Popen",
        lambda *args, **kwargs: process,
    )
    manager = BackendManager(
        tmp_path, log_callback=lambda stream, line: events.append((stream, line))
    )
    assert manager.start() is True
    for thread in manager._reader_threads:
        thread.join(timeout=1)
    assert manager.pid == process.pid
    assert {stream for stream, _ in events} == {"stdout", "stderr"}
    assert manager.stop() is True
    assert process.terminated is True
    assert manager.pid is None

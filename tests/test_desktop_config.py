from pathlib import Path

from kefu_desktop.config import ConfigStore, read_env, update_env


def test_read_and_update_env_preserves_unknown_lines_and_windows_paths(tmp_path: Path) -> None:
    root = tmp_path / "中文 项目"
    root.mkdir()
    env = root / ".env"
    env.write_text("# keep this\nUNKNOWN=value\nCLAWBOT_DEEPSEEK_MODEL=old\n", encoding="utf-8")
    assert read_env(env)["UNKNOWN"] == "value"
    update_env(
        env, {"CLAWBOT_DEEPSEEK_MODEL": "deepseek-chat", "WINDOWS_PATH": r"C:\\Program Files\\Kefu"}
    )
    text = env.read_text(encoding="utf-8")
    assert "# keep this" in text and "UNKNOWN=value" in text
    assert read_env(env)["WINDOWS_PATH"] == r"C:\\Program Files\\Kefu"


def test_config_store_provider_and_backend_env(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "project")
    store.save_provider_settings("deepseek", "", "https://example.invalid", "model-name", 42)
    settings = store.get_provider_settings("deepseek")
    assert settings["base_url"] == "https://example.invalid"
    assert settings["timeout"] == "42"
    env = store.build_backend_env()
    assert env["CLAWBOT_DEEPSEEK_MODEL"] == "model-name"
    assert str((tmp_path / "project" / "src").resolve()) in env["PYTHONPATH"].split(
        __import__("os").pathsep
    )


def test_backend_env_has_first_run_deepseek_defaults(tmp_path: Path) -> None:
    env = ConfigStore(tmp_path / "empty-project").build_backend_env()
    assert env["CLAWBOT_DECISION_MODE"] == "deepseek"
    assert env["CLAWBOT_DEEPSEEK_BASE_URL"] == "https://api.deepseek.com"
    assert env["CLAWBOT_DEEPSEEK_MODEL"] == "deepseek-chat"
    assert env["CLAWBOT_DEEPSEEK_TIMEOUT_SEC"] == "60"

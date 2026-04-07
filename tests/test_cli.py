import io
import json
import logging
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from weibo_auto_signin import cli
from weibo_auto_signin.cli import build_summary_lines
from weibo_auto_signin.config import ConfigError
from weibo_auto_signin.logging import configure_logger
from weibo_auto_signin.models import AccountCheckinResult, TopicCheckinResult


def test_build_summary_lines_includes_account_and_topic_details() -> None:
    result = AccountCheckinResult(
        account_name="main",
        ok=True,
        screen_name="demo",
        topic_results=[
            TopicCheckinResult(
                title="Topic A",
                ok=True,
                message="ok",
                experience=4,
                rank=1,
            )
        ],
    )

    lines = build_summary_lines([result])

    assert any("main" in line for line in lines)
    assert any("Topic A" in line for line in lines)


def test_build_summary_lines_marks_cookie_invalid_accounts() -> None:
    result = AccountCheckinResult(
        account_name="broken",
        ok=False,
        cookie_invalid=True,
        error_message="missing SUBP",
    )

    lines = build_summary_lines([result])

    assert any("cookie invalid" in line.lower() for line in lines)


def test_build_summary_lines_includes_topic_details_for_partial_failures() -> None:
    result = AccountCheckinResult(
        account_name="main",
        ok=False,
        screen_name="demo",
        topic_results=[
            TopicCheckinResult(
                title="Topic A",
                ok=False,
                message="Failed to check in topic: HTTP request failed",
            ),
            TopicCheckinResult(
                title="Topic B",
                ok=True,
                message="ok",
                experience=4,
            ),
        ],
    )

    lines = build_summary_lines([result])

    assert lines[0] == "[FAILED] main (demo)"
    assert "Topic A: Failed to check in topic: HTTP request failed" in lines[1]
    assert "Topic B: +4 exp" in lines[2]


@pytest.mark.parametrize(
    "exception",
    [
        FileNotFoundError("missing config"),
        json.JSONDecodeError("bad json", "{}", 0),
        ConfigError("Config must include a non-empty 'accounts' array"),
    ],
)
def test_main_reports_config_load_failures_without_traceback(monkeypatch, exception) -> None:
    stream = io.StringIO()
    logger = logging.getLogger("test-weibo-auto-signin-cli")
    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    logger.propagate = False

    def fail_load_accounts_config(_path):
        raise exception

    def fail_run_accounts_checkin(_accounts):
        raise AssertionError("check-in should not run when config loading fails")

    monkeypatch.setattr(cli, "configure_logger", lambda _path: logger)
    monkeypatch.setattr(cli, "load_accounts_config", fail_load_accounts_config)
    monkeypatch.setattr(cli, "run_accounts_checkin", fail_run_accounts_checkin)

    try:
        result = cli.main(["--config", "accounts.json"])
    finally:
        logger.removeHandler(handler)
        handler.close()

    output = stream.getvalue()
    assert result == 1
    assert "Failed to load config" in output
    assert "Traceback" not in output


def test_console_entrypoint_and_help_path_smoke() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["scripts"]["weibo-auto-signin"] == "weibo_auto_signin.cli:main"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from weibo_auto_signin.cli import main; raise SystemExit(main(['--help']))",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Weibo super-topic auto check-in" in result.stdout
    assert "--config" in result.stdout
    assert "--account" not in result.stdout


def test_configure_logger_closes_replaced_handlers_and_disables_propagation(tmp_path) -> None:
    class TrackingHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.was_closed = False

        def close(self) -> None:
            self.was_closed = True
            super().close()

    logger = logging.getLogger("weibo-auto-signin")
    old_handler = TrackingHandler()
    logger.addHandler(old_handler)
    logger.propagate = True

    try:
        configured_logger = configure_logger(tmp_path)

        assert configured_logger is logger
        assert old_handler not in logger.handlers
        assert old_handler.was_closed is True
        assert logger.propagate is False
    finally:
        for handler in tuple(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        logger.propagate = True

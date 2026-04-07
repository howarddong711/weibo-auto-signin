from pathlib import Path

from weibo_auto_signin import __version__


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_checkin_workflow_exists() -> None:
    workflow_path = Path(".github/workflows/checkin.yml")

    assert workflow_path.is_file()

    workflow = workflow_path.read_text(encoding="utf-8")

    assert "WEIBO_COOKIES" in workflow
    assert "weibo_auto_signin.cli" in workflow

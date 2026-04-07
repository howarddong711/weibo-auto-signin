from weibo_auto_signin.cli import build_summary_lines
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

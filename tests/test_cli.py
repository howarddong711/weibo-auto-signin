import logging

from weibo_auto_signin.cli import build_summary_lines
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

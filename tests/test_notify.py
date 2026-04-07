from weibo_auto_signin.models import AccountCheckinResult, TopicCheckinResult
from weibo_auto_signin.notify import (
    build_notification_message,
    build_notification_title,
    send_notifications,
)


class FakeNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def send(self, title: str, body: str) -> bool:
        self.calls.append((title, body))
        return True


class FakeLogger:
    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []

    def info(self, message: str, *args) -> None:
        self.infos.append(message % args if args else message)

    def warning(self, message: str, *args) -> None:
        self.warnings.append(message % args if args else message)


def test_build_notification_title_uses_default_prefix() -> None:
    title = build_notification_title()
    assert title.startswith("微博超话签到汇总 ")


def test_build_notification_message_includes_counts_and_account_blocks() -> None:
    results = [
        AccountCheckinResult(
            account_name="account-1",
            ok=True,
            topic_results=[
                TopicCheckinResult(
                    title="Topic A", ok=True, message="ok", experience=4, rank=1
                )
            ],
        ),
        AccountCheckinResult(
            account_name="account-2",
            ok=False,
            error_message="Failed to bootstrap session: HTTP request failed",
        ),
        AccountCheckinResult(
            account_name="account-3",
            ok=False,
            cookie_invalid=True,
            error_message="Missing required cookie keys: SUBP",
        ),
    ]

    body = build_notification_message(results)

    assert "成功账号: 1" in body
    assert "失败账号: 1" in body
    assert "Cookie 失效: 1" in body
    assert "[account-1]" in body
    assert "Topic A: +4 exp rank 1" in body
    assert "[account-2]" in body
    assert "失败: Failed to bootstrap session: HTTP request failed" in body
    assert "[account-3]" in body
    assert "Cookie 无效: Missing required cookie keys: SUBP" in body


def test_send_notifications_uses_all_enabled_channels(monkeypatch) -> None:
    pushplus = FakeNotifier()
    email = FakeNotifier()

    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_FROM", "from@example.com")
    monkeypatch.setenv("SMTP_TO", "to@example.com")
    monkeypatch.setattr(
        "weibo_auto_signin.notify.build_pushplus_notifier", lambda: pushplus
    )
    monkeypatch.setattr("weibo_auto_signin.notify.build_email_notifier", lambda: email)

    send_notifications([AccountCheckinResult(account_name="account-1", ok=True)])

    assert len(pushplus.calls) == 1
    assert len(email.calls) == 1


def test_send_notifications_logs_active_channels(monkeypatch) -> None:
    pushplus = FakeNotifier()
    email = FakeNotifier()
    logger = FakeLogger()

    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_FROM", "from@example.com")
    monkeypatch.setenv("SMTP_TO", "to@example.com")
    monkeypatch.setattr(
        "weibo_auto_signin.notify.build_pushplus_notifier", lambda: pushplus
    )
    monkeypatch.setattr("weibo_auto_signin.notify.build_email_notifier", lambda: email)

    send_notifications(
        [AccountCheckinResult(account_name="account-1", ok=True)],
        logger=logger,
    )

    assert "Notification channels enabled: pushplus, email" in logger.infos


def test_send_notifications_warns_for_invalid_smtp_config(monkeypatch) -> None:
    logger = FakeLogger()

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "not-a-port")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_FROM", "from@example.com")
    monkeypatch.setenv("SMTP_TO", "to@example.com")

    send_notifications(
        [AccountCheckinResult(account_name="account-1", ok=True)],
        logger=logger,
    )

    assert "Notification config invalid via email: SMTP_PORT must be an integer" in logger.warnings

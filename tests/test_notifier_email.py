from __future__ import annotations

from email import message_from_string
from typing import ClassVar

from weibo_auto_signin.notifiers.email import EmailNotifier


class FakeSMTP:
    instances: ClassVar[list["FakeSMTP"]] = []

    def __init__(self, host: str, port: int, *, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = None
        self.sent = None
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username: str, password: str):
        self.logged_in = (username, password)

    def sendmail(self, from_addr: str, to_addrs: list[str], message: str):
        self.sent = (from_addr, to_addrs, message)


def test_email_notifier_sends_plain_text_message() -> None:
    FakeSMTP.instances = []
    notifier = EmailNotifier(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        from_addr="from@example.com",
        to_addrs=["to@example.com"],
        use_tls=True,
        timeout=12.5,
        smtp_factory=FakeSMTP,
    )

    ok = notifier.send(title="Title", body="Body")

    assert ok is True
    smtp = FakeSMTP.instances[0]
    assert smtp.host == "smtp.example.com"
    assert smtp.port == 587
    assert smtp.timeout == 12.5
    assert smtp.started_tls is True
    assert smtp.logged_in == ("user", "pass")
    assert smtp.sent is not None
    from_addr, to_addrs, raw_message = smtp.sent
    message = message_from_string(raw_message)
    assert from_addr == "from@example.com"
    assert to_addrs == ["to@example.com"]
    assert message["Subject"] == "Title"
    assert message["From"] == "from@example.com"
    assert message["To"] == "to@example.com"
    assert message.get_payload().strip() == "Body"

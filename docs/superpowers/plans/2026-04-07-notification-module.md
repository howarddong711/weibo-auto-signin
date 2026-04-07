# Notification Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight notification module that sends one plain-text summary per run through PushPlus and generic SMTP email without affecting the core check-in flow.

**Architecture:** The implementation adds a small notification layer downstream from the existing CLI/check-in pipeline. `notify.py` formats a shared plain-text summary and dispatches to channel adapters in `notifiers/`, while the CLI remains responsible for running the check-in flow and then calling the notification entrypoint.

**Tech Stack:** Python 3.13, `requests`, stdlib `smtplib` and `email`, `pytest`, `uv`

---

## Planned File Map

- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notify.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notifiers/__init__.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notifiers/pushplus.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notifiers/email.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/cli.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/README.md`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/.github/workflows/checkin.yml`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_notify.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_notifier_pushplus.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_notifier_email.py`

## Responsibilities

- `notify.py`
  - build notification title/body
  - load notification env configuration
  - decide which channels are enabled
  - call enabled channel senders
  - keep failures isolated per channel

- `notifiers/pushplus.py`
  - send one plain-text summary to PushPlus

- `notifiers/email.py`
  - send one plain-text summary through generic SMTP

- `cli.py`
  - after logging the summary, call the notification entrypoint
  - keep exit code based on check-in outcome, not notification outcome

### Task 1: Build Notification Summary Formatting

**Files:**
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notify.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_notify.py`

- [ ] **Step 1: Write the failing summary-format tests**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/tests/test_notify.py
from weibo_auto_signin.models import AccountCheckinResult, TopicCheckinResult
from weibo_auto_signin.notify import build_notification_message, build_notification_title


def test_build_notification_title_uses_default_prefix() -> None:
    title = build_notification_title()
    assert title.startswith("微博超话签到汇总 ")


def test_build_notification_message_includes_counts_and_account_blocks() -> None:
    results = [
        AccountCheckinResult(
            account_name="account-1",
            ok=True,
            topic_results=[
                TopicCheckinResult(title="Topic A", ok=True, message="ok", experience=4, rank=1)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && /Users/howarddong/Library/Python/3.9/bin/uv run --python 3.13 --extra dev pytest tests/test_notify.py -v`
Expected: FAIL with `ModuleNotFoundError` for `weibo_auto_signin.notify`

- [ ] **Step 3: Write minimal notification formatting**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notify.py
from __future__ import annotations

from datetime import date

from weibo_auto_signin.models import AccountCheckinResult


def build_notification_title(prefix: str = "微博超话签到汇总") -> str:
    return f"{prefix} {date.today().isoformat()}"


def build_notification_message(results: list[AccountCheckinResult]) -> str:
    success_count = sum(1 for result in results if result.ok)
    cookie_invalid_count = sum(1 for result in results if result.cookie_invalid)
    failed_count = sum(
        1 for result in results if not result.ok and not result.cookie_invalid
    )

    lines = [
        f"成功账号: {success_count}",
        f"失败账号: {failed_count}",
        f"Cookie 失效: {cookie_invalid_count}",
        "",
    ]

    for result in results:
        lines.append(f"[{result.account_name}]")
        if result.cookie_invalid:
            lines.append(f"Cookie 无效: {result.error_message}")
        elif not result.ok and not result.topic_results:
            lines.append(f"失败: {result.error_message}")
        else:
            for topic in result.topic_results:
                if topic.experience is not None:
                    rank_text = f" rank {topic.rank}" if topic.rank is not None else ""
                    lines.append(f"{topic.title}: +{topic.experience} exp{rank_text}")
                else:
                    lines.append(f"{topic.title}: {topic.message}")
        lines.append("")

    return "\n".join(lines).strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && /Users/howarddong/Library/Python/3.9/bin/uv run --python 3.13 --extra dev pytest tests/test_notify.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add src/weibo_auto_signin/notify.py tests/test_notify.py
git commit -m "feat: add notification summary formatting"
```

### Task 2: Add PushPlus Notifier

**Files:**
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notifiers/__init__.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notifiers/pushplus.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_notifier_pushplus.py`

- [ ] **Step 1: Write the failing PushPlus tests**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/tests/test_notifier_pushplus.py
from weibo_auto_signin.notifiers.pushplus import PushplusNotifier


class FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code


class FakeSession:
    def __init__(self) -> None:
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json, timeout))
        return FakeResponse()


def test_pushplus_notifier_posts_plain_text_payload() -> None:
    session = FakeSession()
    notifier = PushplusNotifier(token="token-123", session=session)

    ok = notifier.send(title="Title", body="Body")

    assert ok is True
    assert session.calls == [
        (
            "https://www.pushplus.plus/send",
            {
                "token": "token-123",
                "title": "Title",
                "content": "Body",
                "template": "txt",
            },
            10,
        )
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && /Users/howarddong/Library/Python/3.9/bin/uv run --python 3.13 --extra dev pytest tests/test_notifier_pushplus.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the PushPlus notifier**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notifiers/pushplus.py
from __future__ import annotations

import requests


class PushplusNotifier:
    def __init__(self, token: str, session: requests.Session | None = None) -> None:
        self.token = token
        self.session = session or requests.Session()

    def send(self, title: str, body: str) -> bool:
        response = self.session.post(
            "https://www.pushplus.plus/send",
            json={
                "token": self.token,
                "title": title,
                "content": body,
                "template": "txt",
            },
            timeout=10,
        )
        return 200 <= response.status_code < 300
```

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notifiers/__init__.py
from weibo_auto_signin.notifiers.email import EmailNotifier
from weibo_auto_signin.notifiers.pushplus import PushplusNotifier

__all__ = ["EmailNotifier", "PushplusNotifier"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && /Users/howarddong/Library/Python/3.9/bin/uv run --python 3.13 --extra dev pytest tests/test_notifier_pushplus.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add src/weibo_auto_signin/notifiers/__init__.py src/weibo_auto_signin/notifiers/pushplus.py tests/test_notifier_pushplus.py
git commit -m "feat: add pushplus notifier"
```

### Task 3: Add Generic SMTP Email Notifier

**Files:**
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notifiers/email.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_notifier_email.py`

- [ ] **Step 1: Write the failing email tests**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/tests/test_notifier_email.py
from weibo_auto_signin.notifiers.email import EmailNotifier


class FakeSMTP:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.started_tls = False
        self.logged_in = None
        self.sent = None

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
    notifier = EmailNotifier(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        from_addr="from@example.com",
        to_addrs=["to@example.com"],
        use_tls=True,
        smtp_factory=FakeSMTP,
    )

    ok = notifier.send(title="Title", body="Body")

    assert ok is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && /Users/howarddong/Library/Python/3.9/bin/uv run --python 3.13 --extra dev pytest tests/test_notifier_email.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the SMTP notifier**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notifiers/email.py
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Callable


class EmailNotifier:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
        use_tls: bool = True,
        smtp_factory: Callable[[str, int], smtplib.SMTP] = smtplib.SMTP,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_tls = use_tls
        self.smtp_factory = smtp_factory

    def send(self, title: str, body: str) -> bool:
        message = EmailMessage()
        message["Subject"] = title
        message["From"] = self.from_addr
        message["To"] = ", ".join(self.to_addrs)
        message.set_content(body)

        with self.smtp_factory(self.host, self.port) as smtp:
            if self.use_tls:
                smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.sendmail(self.from_addr, self.to_addrs, message.as_string())

        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && /Users/howarddong/Library/Python/3.9/bin/uv run --python 3.13 --extra dev pytest tests/test_notifier_email.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add src/weibo_auto_signin/notifiers/email.py tests/test_notifier_email.py
git commit -m "feat: add smtp email notifier"
```

### Task 4: Integrate Channel Selection And Dispatch

**Files:**
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notify.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/cli.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_notify.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/README.md`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/.github/workflows/checkin.yml`

- [ ] **Step 1: Write the failing dispatch/config tests**

```python
# Add to /Users/howarddong/develop/code/weibo-auto-signin/tests/test_notify.py
import os

from weibo_auto_signin.models import AccountCheckinResult
from weibo_auto_signin.notify import send_notifications


class FakeNotifier:
    def __init__(self) -> None:
        self.calls = []

    def send(self, title: str, body: str) -> bool:
        self.calls.append((title, body))
        return True


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
    monkeypatch.setattr("weibo_auto_signin.notify.build_pushplus_notifier", lambda: pushplus)
    monkeypatch.setattr("weibo_auto_signin.notify.build_email_notifier", lambda: email)

    send_notifications([AccountCheckinResult(account_name="account-1", ok=True)])

    assert len(pushplus.calls) == 1
    assert len(email.calls) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && /Users/howarddong/Library/Python/3.9/bin/uv run --python 3.13 --extra dev pytest tests/test_notify.py -v`
Expected: FAIL because builder/dispatch logic is missing

- [ ] **Step 3: Implement env-based dispatch and CLI integration**

```python
# Add to /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/notify.py
import os
from typing import Iterable

from weibo_auto_signin.notifiers.email import EmailNotifier
from weibo_auto_signin.notifiers.pushplus import PushplusNotifier


def build_pushplus_notifier() -> PushplusNotifier | None:
    token = os.getenv("PUSHPLUS_TOKEN", "").strip()
    if not token:
        return None
    return PushplusNotifier(token=token)


def build_email_notifier() -> EmailNotifier | None:
    required = {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": os.getenv("SMTP_PORT", "").strip(),
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_addr": os.getenv("SMTP_FROM", "").strip(),
        "to_raw": os.getenv("SMTP_TO", "").strip(),
    }
    if not all(required.values()):
        return None
    to_addrs = [item.strip() for item in required["to_raw"].split(",") if item.strip()]
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() != "false"
    return EmailNotifier(
        host=required["host"],
        port=int(required["port"]),
        username=required["username"],
        password=required["password"],
        from_addr=required["from_addr"],
        to_addrs=to_addrs,
        use_tls=use_tls,
    )


def send_notifications(results: list[AccountCheckinResult], logger=None) -> None:
    prefix = os.getenv("NOTIFY_TITLE_PREFIX", "微博超话签到汇总").strip() or "微博超话签到汇总"
    title = build_notification_title(prefix=prefix)
    body = build_notification_message(results)
    channels = [
        ("pushplus", build_pushplus_notifier()),
        ("email", build_email_notifier()),
    ]
    enabled = [(name, notifier) for name, notifier in channels if notifier is not None]
    if not enabled:
        if logger:
            logger.info("Notification disabled")
        return
    for name, notifier in enabled:
        try:
            ok = notifier.send(title=title, body=body)
            if logger:
                if ok:
                    logger.info("Notification sent via %s", name)
                else:
                    logger.warning("Notification failed via %s", name)
        except Exception as exc:
            if logger:
                logger.warning("Notification error via %s: %s", name, exc)
```

```python
# Modify /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/cli.py
from weibo_auto_signin.notify import send_notifications

# after summary logging
send_notifications(results, logger=logger)
```

README and workflow updates:
- document `PUSHPLUS_TOKEN`
- document SMTP env vars
- leave notifications optional in workflow setup

- [ ] **Step 4: Run focused and full tests**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && /Users/howarddong/Library/Python/3.9/bin/uv run --python 3.13 --extra dev pytest tests/test_notify.py tests/test_notifier_pushplus.py tests/test_notifier_email.py -v`
Expected: PASS

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && /Users/howarddong/Library/Python/3.9/bin/uv run --python 3.13 --extra dev pytest -q`
Expected: full suite PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add src/weibo_auto_signin/notify.py src/weibo_auto_signin/notifiers src/weibo_auto_signin/cli.py tests/test_notify.py tests/test_notifier_pushplus.py tests/test_notifier_email.py README.md .github/workflows/checkin.yml
git commit -m "feat: add notification dispatch integration"
```

## Plan Self-Review

- Spec coverage:
  - plain-text summary generation: Task 1
  - PushPlus support: Task 2
  - generic SMTP support: Task 3
  - env-based channel selection and best-effort dispatch: Task 4
  - CLI integration after run completion: Task 4
  - documentation/workflow env notes: Task 4
- Placeholder scan:
  - no `TBD`, `TODO`, or implied “fill this in later” steps remain
- Type consistency:
  - `AccountCheckinResult`, `TopicCheckinResult`, `PushplusNotifier`, `EmailNotifier`, and `send_notifications()` are used consistently across tasks

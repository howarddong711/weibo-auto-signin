from __future__ import annotations

import os
from datetime import date
from typing import Protocol

from weibo_auto_signin.models import AccountCheckinResult
from weibo_auto_signin.notifiers.email import EmailNotifier
from weibo_auto_signin.notifiers.pushplus import PushplusNotifier


class Notifier(Protocol):
    def send(self, title: str, body: str) -> bool: ...


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

    try:
        port = int(required["port"])
    except ValueError:
        return None

    to_addrs = [item.strip() for item in required["to_raw"].split(",") if item.strip()]
    if not to_addrs:
        return None

    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() != "false"
    return EmailNotifier(
        host=required["host"],
        port=port,
        username=required["username"],
        password=required["password"],
        from_addr=required["from_addr"],
        to_addrs=to_addrs,
        use_tls=use_tls,
    )


def _build_enabled_channels(logger=None) -> list[tuple[str, Notifier]]:
    channels: list[tuple[str, Notifier | None]] = []
    for name, builder in (
        ("pushplus", build_pushplus_notifier),
        ("email", build_email_notifier),
    ):
        try:
            channels.append((name, builder()))
        except Exception as exc:
            if logger:
                logger.warning("Notification config error via %s: %s", name, exc)
    return [(name, notifier) for name, notifier in channels if notifier is not None]


def send_notifications(results: list[AccountCheckinResult], logger=None) -> None:
    prefix = (
        os.getenv("NOTIFY_TITLE_PREFIX", "微博超话签到汇总").strip()
        or "微博超话签到汇总"
    )
    title = build_notification_title(prefix=prefix)
    body = build_notification_message(results)
    enabled = _build_enabled_channels(logger=logger)

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

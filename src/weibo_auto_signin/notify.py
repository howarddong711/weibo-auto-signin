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
    raw_config = {
        "SMTP_HOST": os.getenv("SMTP_HOST", "").strip(),
        "SMTP_PORT": os.getenv("SMTP_PORT", "").strip(),
        "SMTP_USERNAME": os.getenv("SMTP_USERNAME", "").strip(),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", "").strip(),
        "SMTP_FROM": os.getenv("SMTP_FROM", "").strip(),
        "SMTP_TO": os.getenv("SMTP_TO", "").strip(),
    }

    if not any(raw_config.values()):
        return None

    missing = [name for name, value in raw_config.items() if not value]
    if missing:
        raise ValueError(f"missing {', '.join(missing)}")

    try:
        port = int(raw_config["SMTP_PORT"])
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be an integer") from exc

    to_addrs = [item.strip() for item in raw_config["SMTP_TO"].split(",") if item.strip()]
    if not to_addrs:
        raise ValueError("SMTP_TO must include at least one recipient")

    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() != "false"
    return EmailNotifier(
        host=raw_config["SMTP_HOST"],
        port=port,
        username=raw_config["SMTP_USERNAME"],
        password=raw_config["SMTP_PASSWORD"],
        from_addr=raw_config["SMTP_FROM"],
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
                logger.warning("Notification config invalid via %s: %s", name, exc)
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

    if logger:
        logger.info(
            "Notification channels enabled: %s",
            ", ".join(name for name, _ in enabled),
        )

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

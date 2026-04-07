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

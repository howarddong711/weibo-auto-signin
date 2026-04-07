import argparse
from collections.abc import Sequence
from pathlib import Path

from weibo_auto_signin.checkin import run_accounts_checkin
from weibo_auto_signin.config import load_accounts_config
from weibo_auto_signin.logging import configure_logger
from weibo_auto_signin.models import AccountCheckinResult
from weibo_auto_signin.notify import send_notifications


def build_summary_lines(results: list[AccountCheckinResult]) -> list[str]:
    lines: list[str] = []
    for result in results:
        if result.cookie_invalid:
            lines.append(f"[COOKIE INVALID] {result.account_name}: {result.error_message}")
            continue
        label = _account_label(result)
        if not result.ok:
            if result.topic_results:
                lines.append(f"[FAILED] {label}")
                _append_topic_lines(lines, result)
            else:
                lines.append(f"[FAILED] {label}: {result.error_message}")
            continue

        lines.append(f"[OK] {label}")

        _append_topic_lines(lines, result)
    return lines


def _account_label(result: AccountCheckinResult) -> str:
    label = result.account_name
    if result.screen_name:
        label = f"{label} ({result.screen_name})"
    return label


def _append_topic_lines(
    lines: list[str], result: AccountCheckinResult
) -> None:
    for topic in result.topic_results:
        if topic.experience is not None:
            rank = f" rank {topic.rank}" if topic.rank is not None else ""
            lines.append(f"  - {topic.title}: +{topic.experience} exp{rank}")
        else:
            lines.append(f"  - {topic.title}: {topic.message}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Weibo super-topic auto check-in")
    parser.add_argument("--config", default="cookies.txt")
    args = parser.parse_args(argv)

    logger = configure_logger(Path("logs"))
    try:
        accounts = load_accounts_config(args.config)
    except (OSError, ValueError) as exc:
        logger.error("Failed to load config %s: %s", args.config, exc)
        return 1

    results = run_accounts_checkin(accounts)

    for line in build_summary_lines(results):
        logger.info(line)

    success_count = sum(1 for result in results if result.ok)
    logger.info(
        "Completed run: %s success, %s failed",
        success_count,
        len(results) - success_count,
    )
    send_notifications(results, logger=logger)
    return 0 if success_count else 1


if __name__ == "__main__":
    raise SystemExit(main())

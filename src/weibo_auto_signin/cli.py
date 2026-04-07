import argparse
from collections.abc import Sequence
from pathlib import Path

from weibo_auto_signin.checkin import run_accounts_checkin
from weibo_auto_signin.config import load_accounts_config
from weibo_auto_signin.logging import configure_logger
from weibo_auto_signin.models import AccountCheckinResult


def build_summary_lines(results: list[AccountCheckinResult]) -> list[str]:
    lines: list[str] = []
    for result in results:
        if result.cookie_invalid:
            lines.append(f"[COOKIE INVALID] {result.account_name}: {result.error_message}")
            continue
        if not result.ok:
            lines.append(f"[FAILED] {result.account_name}: {result.error_message}")
            continue

        label = result.account_name
        if result.screen_name:
            label = f"{label} ({result.screen_name})"
        lines.append(f"[OK] {label}")

        for topic in result.topic_results:
            if topic.experience is not None:
                rank = f" rank {topic.rank}" if topic.rank is not None else ""
                lines.append(f"  - {topic.title}: +{topic.experience} exp{rank}")
            else:
                lines.append(f"  - {topic.title}: {topic.message}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Weibo super-topic auto check-in")
    parser.add_argument("--config", default="accounts.json")
    parser.add_argument("--account")
    args = parser.parse_args(argv)

    logger = configure_logger(Path("logs"))
    accounts = load_accounts_config(args.config)
    if args.account:
        accounts = [account for account in accounts if account.name == args.account]

    results = run_accounts_checkin(accounts)

    for line in build_summary_lines(results):
        logger.info(line)

    success_count = sum(1 for result in results if result.ok)
    logger.info(
        "Completed run: %s success, %s failed",
        success_count,
        len(results) - success_count,
    )
    return 0 if success_count else 1


if __name__ == "__main__":
    raise SystemExit(main())

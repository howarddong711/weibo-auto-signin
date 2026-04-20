import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from weibo_auto_signin.browser_login import BrowserLoginError, login_with_browser
from weibo_auto_signin.checkin import run_accounts_checkin
from weibo_auto_signin.client import WeiboClient
from weibo_auto_signin.config import load_accounts_config
from weibo_auto_signin.cookie import parse_cookie_string
from weibo_auto_signin.cookie_store import save_cookie
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
    args = list(argv) if argv is not None else sys.argv[1:]
    if args[:1] == ["login"]:
        return login_main(args[1:])
    return checkin_main(args)


def checkin_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Weibo super-topic auto check-in")
    parser.add_argument("--config", default="cookies.txt")
    args = parser.parse_args(argv)

    logger = configure_logger(Path("logs"))
    try:
        accounts = load_accounts_config(args.config)
    except (OSError, ValueError) as exc:
        logger.error("Failed to load config %s: %s", args.config, exc)
        return 1

    logger.info("Loaded %s account(s), starting check-in", len(accounts))

    def log_topic_progress(index, total, topic, result):
        status = "OK" if result.ok else "FAILED"
        logger.info(
            "Progress %s/%s [%s] %s: %s",
            index,
            total,
            status,
            topic.title,
            result.message,
        )

    results = run_accounts_checkin(accounts, on_topic_result=log_topic_progress)

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


def login_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Log in to Weibo and export cookie")
    parser.add_argument("--output", default="cookies.txt")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--browser", choices=["chromium", "chrome", "msedge"], default="chromium")
    args = parser.parse_args(argv)

    logger = configure_logger(Path("logs"))
    logger.info("Opening %s for Weibo QR login", args.browser)
    logger.info("Please scan the QR code in the browser window")

    try:
        result = login_with_browser(
            timeout_seconds=args.timeout,
            headless=args.headless,
            browser_name=args.browser,
        )
        if not args.skip_verify:
            uid, screen_name, topic_count = verify_cookie(result.cookie)
            logger.info(
                "Verified account %s (%s), followed topics: %s",
                screen_name or "unknown",
                uid,
                topic_count,
            )
        save_cookie(args.output, result.cookie, append=args.append)
    except (BrowserLoginError, OSError, ValueError, RuntimeError) as exc:
        logger.error("Failed to login and save cookie: %s", exc)
        return 1

    logger.info("Saved Weibo cookie to %s", args.output)
    return 0


def verify_cookie(raw_cookie: str) -> tuple[str, str, int]:
    client = WeiboClient(parse_cookie_string(raw_cookie))
    uid = client.bootstrap_session()
    user_info = client.fetch_user_info()
    topics = client.fetch_followed_topics()
    return uid, user_info.get("screen_name", ""), len(topics)


if __name__ == "__main__":
    raise SystemExit(main())

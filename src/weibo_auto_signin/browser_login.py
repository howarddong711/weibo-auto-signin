from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from weibo_auto_signin.cookie import parse_cookie_string, require_cookie_keys


IMPORTANT_COOKIE_NAMES = (
    "XSRF-TOKEN",
    "SCF",
    "SUB",
    "SUBP",
    "ALF",
    "SSOLoginState",
    "WBPSESS",
    "PC_TOKEN",
)
COOKIE_DOMAIN_HINTS = ("weibo.com", "sina.com.cn", "sina.cn")
SESSION_COOKIE_NAMES = ("WBPSESS", "SSOLoginState", "PC_TOKEN")


class BrowserLoginError(RuntimeError):
    pass


BrowserName = Literal["chromium", "chrome", "msedge"]


@dataclass(slots=True, eq=True)
class BrowserLoginResult:
    cookie: str


def login_with_browser(
    *,
    timeout_seconds: int = 180,
    headless: bool = False,
    browser_name: BrowserName = "chromium",
) -> BrowserLoginResult:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserLoginError(
            "Playwright is not installed. Run: uv sync --extra login"
        ) from exc

    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(
                playwright,
                browser_name=browser_name,
                headless=headless,
            )
            try:
                context = browser.new_context(
                    locale="zh-CN",
                    viewport={"width": 1280, "height": 900},
                )
                page = context.new_page()
                page.goto("https://weibo.com/login.php", wait_until="domcontentloaded")
                baseline_sub = _wait_for_initial_sub(context, timeout_seconds=30)
                _wait_for_cookie(
                    context,
                    timeout_seconds=timeout_seconds,
                    previous_sub=baseline_sub,
                )
                page.goto("https://weibo.com", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                cookie = _wait_for_cookie(
                    context,
                    timeout_seconds=15,
                    require_session_cookie=True,
                    previous_sub=baseline_sub,
                )
                return BrowserLoginResult(cookie=cookie)
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise BrowserLoginError("Timed out while opening Weibo login page") from exc
    except PlaywrightError as exc:
        raise BrowserLoginError(_format_browser_error(browser_name, exc)) from exc


def build_cookie_line(cookies: Iterable[Mapping[str, object]]) -> str:
    selected: dict[str, str] = {}
    for cookie in sorted(cookies, key=_cookie_priority):
        domain = str(cookie.get("domain", ""))
        name = str(cookie.get("name", "")).strip()
        value = str(cookie.get("value", "")).strip()
        if not name or not value:
            continue
        if COOKIE_DOMAIN_HINTS and not any(hint in domain for hint in COOKIE_DOMAIN_HINTS):
            continue
        selected.setdefault(name, value)

    ordered_names = [
        name
        for name in IMPORTANT_COOKIE_NAMES
        if name in selected
    ]
    ordered_names.extend(
        name for name in sorted(selected) if name not in IMPORTANT_COOKIE_NAMES
    )
    return "; ".join(f"{name}={selected[name]}" for name in ordered_names)


def _wait_for_cookie(
    context,
    *,
    timeout_seconds: int,
    require_session_cookie: bool = False,
    previous_sub: str | None = None,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_cookie = ""
    while time.monotonic() < deadline:
        cookie = build_cookie_line(context.cookies())
        last_cookie = cookie or last_cookie
        if _cookie_is_ready(
            cookie,
            require_session_cookie=require_session_cookie,
            previous_sub=previous_sub,
        ):
            return cookie
        time.sleep(1.5)
    if last_cookie:
        raise BrowserLoginError(
            "Timed out waiting for complete Weibo cookie. Please scan the QR code again."
        )
    raise BrowserLoginError("Timed out waiting for Weibo login cookie")


def _wait_for_initial_sub(context, *, timeout_seconds: int) -> str | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        parsed = parse_cookie_string(build_cookie_line(context.cookies()))
        if parsed.get("SUB"):
            return parsed["SUB"]
        time.sleep(0.5)
    return None


def _cookie_is_ready(
    cookie: str,
    *,
    require_session_cookie: bool,
    previous_sub: str | None = None,
) -> bool:
    parsed = parse_cookie_string(cookie)
    try:
        require_cookie_keys(parsed)
    except ValueError:
        return False
    if previous_sub and parsed.get("SUB") == previous_sub:
        return False
    if not require_session_cookie:
        return True
    if not parsed.get("XSRF-TOKEN"):
        return False
    return any(parsed.get(name) for name in SESSION_COOKIE_NAMES)


def _launch_browser(playwright, *, browser_name: BrowserName, headless: bool):
    if browser_name == "chromium":
        return playwright.chromium.launch(headless=headless)
    if browser_name == "chrome":
        return playwright.chromium.launch(channel="chrome", headless=headless)
    if browser_name == "msedge":
        return playwright.chromium.launch(channel="msedge", headless=headless)
    raise BrowserLoginError(f"Unsupported browser: {browser_name}")


def _format_browser_error(browser_name: BrowserName, exc: Exception) -> str:
    if browser_name == "chrome":
        return (
            "Google Chrome was not found. Install Chrome, run "
            "'playwright install chrome', or retry without '--browser chrome' "
            "to use bundled Chromium."
        )
    if browser_name == "msedge":
        return (
            "Microsoft Edge was not found. Install Edge, run "
            "'playwright install msedge', or retry without '--browser msedge' "
            "to use bundled Chromium."
        )
    return f"Failed to open browser: {exc}"


def _cookie_priority(cookie: Mapping[str, object]) -> tuple[int, int, str]:
    domain = str(cookie.get("domain", ""))
    name = str(cookie.get("name", ""))
    domain_rank = 0 if "weibo.com" in domain else 1
    name_rank = (
        IMPORTANT_COOKIE_NAMES.index(name)
        if name in IMPORTANT_COOKIE_NAMES
        else len(IMPORTANT_COOKIE_NAMES)
    )
    return domain_rank, name_rank, name

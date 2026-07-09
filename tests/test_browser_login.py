from weibo_auto_signin.browser_login import build_cookie_line
from weibo_auto_signin.browser_login import _cookie_is_ready


def test_build_cookie_line_keeps_weibo_and_sina_cookies_in_stable_order() -> None:
    cookies = [
        {"name": "other", "value": "ignored", "domain": "example.com"},
        {"name": "WBPSESS", "value": "wbpsess", "domain": ".weibo.com"},
        {"name": "SUBP", "value": "subp", "domain": ".weibo.com"},
        {"name": "SUB", "value": "sub", "domain": ".weibo.com"},
        {"name": "SSOLoginState", "value": "sso", "domain": ".sina.com.cn"},
        {"name": "XSRF-TOKEN", "value": "xsrf", "domain": "weibo.com"},
        {"name": "custom", "value": "custom-value", "domain": ".weibo.com"},
    ]

    cookie_line = build_cookie_line(cookies)

    assert cookie_line == (
        "XSRF-TOKEN=xsrf; SUB=sub; SUBP=subp; "
        "SSOLoginState=sso; WBPSESS=wbpsess; custom=custom-value"
    )


def test_build_cookie_line_ignores_empty_cookie_values() -> None:
    cookies = [
        {"name": "SUB", "value": "", "domain": ".weibo.com"},
        {"name": "SUBP", "value": "subp", "domain": ".weibo.com"},
    ]

    assert build_cookie_line(cookies) == "SUBP=subp"


def test_build_cookie_line_prefers_weibo_cookie_when_names_duplicate() -> None:
    cookies = [
        {"name": "SUB", "value": "sina-sub", "domain": ".sina.com.cn"},
        {"name": "SUB", "value": "weibo-sub", "domain": ".weibo.com"},
    ]

    assert build_cookie_line(cookies) == "SUB=weibo-sub"


def test_cookie_is_not_ready_when_sub_matches_initial_login_page_cookie() -> None:
    cookie = "XSRF-TOKEN=xsrf; SUB=visitor; SUBP=subp; WBPSESS=wbpsess"

    assert (
        _cookie_is_ready(
            cookie,
            require_session_cookie=True,
            previous_sub="visitor",
        )
        is False
    )


def test_cookie_is_ready_after_sub_changes_and_session_cookie_exists() -> None:
    cookie = "XSRF-TOKEN=xsrf; SUB=logged-in; SUBP=subp; WBPSESS=wbpsess"

    assert (
        _cookie_is_ready(
            cookie,
            require_session_cookie=True,
            previous_sub="visitor",
        )
        is True
    )

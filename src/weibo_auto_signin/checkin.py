from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from weibo_auto_signin.client import Topic, WeiboClient
from weibo_auto_signin.cookie import (
    MissingCookieKeyError,
    parse_cookie_string,
    require_cookie_keys,
)
from weibo_auto_signin.models import (
    AccountCheckinResult,
    AccountConfig,
    TopicCheckinResult,
)


class CheckinClient(Protocol):
    def bootstrap_session(self) -> str: ...

    def fetch_user_info(self) -> dict[str, str]: ...

    def fetch_followed_topics(self) -> list[Topic]: ...

    def checkin_topic(self, topic: Topic) -> TopicCheckinResult: ...


def run_accounts_checkin(
    accounts: Sequence[AccountConfig],
    *,
    client_factory: Callable[[dict[str, str]], CheckinClient] = WeiboClient,
) -> list[AccountCheckinResult]:
    return [
        run_account_checkin(account, client_factory=client_factory)
        for account in accounts
    ]


def run_account_checkin(
    account: AccountConfig,
    *,
    client_factory: Callable[[dict[str, str]], CheckinClient] = WeiboClient,
) -> AccountCheckinResult:
    try:
        parsed_cookie = _parse_valid_cookie(account.cookie)
    except MissingCookieKeyError as exc:
        return AccountCheckinResult(
            account_name=account.name,
            ok=False,
            cookie_invalid=True,
            error_message=str(exc),
        )

    uid = ""
    screen_name = ""

    try:
        client = client_factory(parsed_cookie)
        uid = client.bootstrap_session()
        user_info = client.fetch_user_info()
        screen_name = user_info.get("screen_name", "")
        topics = client.fetch_followed_topics()
    except Exception as exc:
        return AccountCheckinResult(
            account_name=account.name,
            ok=False,
            uid=uid,
            screen_name=screen_name,
            error_message=_error_message(exc),
        )

    topic_results = [_checkin_topic(client, topic) for topic in topics]
    return AccountCheckinResult(
        account_name=account.name,
        ok=all(result.ok for result in topic_results),
        uid=uid,
        screen_name=screen_name,
        topic_results=topic_results,
    )


def _parse_valid_cookie(raw_cookie: str) -> dict[str, str]:
    parsed_cookie = parse_cookie_string(raw_cookie)
    validated_cookie = require_cookie_keys(parsed_cookie)
    return dict(validated_cookie)


def _checkin_topic(client: CheckinClient, topic: Topic) -> TopicCheckinResult:
    try:
        return client.checkin_topic(topic)
    except Exception as exc:
        return TopicCheckinResult(
            title=topic.title,
            ok=False,
            message=_error_message(exc),
        )


def _error_message(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__

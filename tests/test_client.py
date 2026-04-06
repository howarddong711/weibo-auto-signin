import json

import pytest
import requests

from weibo_auto_signin.client import Topic, WeiboClient, WeiboClientError


class FakeResponse:
    def __init__(self, *, headers=None, payload=None, status_error=None, json_error=None):
        self.headers = headers or {}
        self._payload = payload or {}
        self._status_error = status_error
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload

    def raise_for_status(self):
        if self._status_error is not None:
            raise self._status_error


class FakeSession:
    def __init__(self):
        self.cookies = {"XSRF-TOKEN": "xsrf-token"}
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com":
            return FakeResponse(headers={"x-log-uid": "12345"})
        if url == "https://weibo.com/ajax/profile/topicContent":
            return FakeResponse(
                payload={
                    "ok": 1,
                    "data": {
                        "max_page": 1,
                        "list": [{"title": "Example", "oid": "chaohua:100808abc"}],
                    },
                }
            )
        if url == "https://weibo.com/ajax/profile/info?uid=12345":
            return FakeResponse(payload={"ok": 1, "data": {"user": {"screen_name": "demo"}}})
        if url == "https://weibo.com/p/aj/general/button":
            return FakeResponse(
                payload={
                    "code": "100000",
                    "data": {"tipMessage": "今日签到，经验值+4", "alert_title": "第12名"},
                }
            )
        raise AssertionError(url)


class MissingXsrfSession(FakeSession):
    def __init__(self):
        super().__init__()
        self.cookies = {}


class HttpErrorSession(FakeSession):
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        return FakeResponse(status_error=requests.HTTPError("503 Server Error"))


class InvalidTopicsPayloadSession(FakeSession):
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com/ajax/profile/topicContent":
            return FakeResponse(
                payload={
                    "ok": 1,
                    "data": {"list": [{"title": "Example", "oid": "bad-oid"}]},
                }
            )
        return super().get(url, params=params, headers=headers)


class InvalidJsonSession(FakeSession):
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com/ajax/profile/topicContent":
            return FakeResponse(json_error=json.JSONDecodeError("bad json", "{}", 0))
        return super().get(url, params=params, headers=headers)


def test_bootstrap_session_sets_uid_and_xsrf_token() -> None:
    session = FakeSession()
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=session)

    assert client.bootstrap_session() == "12345"
    assert session.headers["x-xsrf-token"] == "xsrf-token"


def test_default_session_uses_requests_session() -> None:
    client = WeiboClient({"SUB": "1", "SUBP": "2"})

    assert isinstance(client.session, requests.Session)


def test_fetch_followed_topics_returns_topic_objects() -> None:
    session = FakeSession()
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=session)
    client.user_uid = "12345"

    topics = client.fetch_followed_topics()

    assert topics == [Topic(title="Example", topic_id="100808abc")]


def test_bootstrap_session_wraps_missing_xsrf_cookie() -> None:
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=MissingXsrfSession())

    with pytest.raises(WeiboClientError, match="bootstrap session"):
        client.bootstrap_session()


def test_fetch_followed_topics_wraps_http_failures() -> None:
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=HttpErrorSession())
    client.user_uid = "12345"

    with pytest.raises(WeiboClientError, match="fetch followed topics"):
        client.fetch_followed_topics()


@pytest.mark.parametrize("session_factory", [InvalidTopicsPayloadSession, InvalidJsonSession])
def test_fetch_followed_topics_wraps_invalid_payloads(session_factory) -> None:
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=session_factory())
    client.user_uid = "12345"

    with pytest.raises(WeiboClientError, match="fetch followed topics"):
        client.fetch_followed_topics()

import requests

from weibo_auto_signin.client import Topic, WeiboClient


class FakeResponse:
    def __init__(self, *, headers=None, payload=None):
        self.headers = headers or {}
        self._payload = payload or {}

    def json(self):
        return self._payload


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

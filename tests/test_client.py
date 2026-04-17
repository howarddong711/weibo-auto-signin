import json

import pytest
import requests

from weibo_auto_signin.client import Topic, WeiboClient, WeiboClientError


class FakeResponse:
    def __init__(
        self,
        *,
        headers=None,
        payload=None,
        status_error=None,
        json_error=None,
        text="",
        status_code=200,
    ):
        self.headers = headers or {}
        self._payload = payload or {}
        self._status_error = status_error
        self._json_error = json_error
        self.text = text
        self.status_code = status_code

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


class PaginatedTopicsSession(FakeSession):
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com/ajax/profile/topicContent":
            page = params["page"]
            topics = {
                1: [{"title": "Topic A", "oid": "chaohua:100808a"}],
                2: [{"title": "Topic B", "oid": "chaohua:100808b"}],
            }
            return FakeResponse(
                payload={
                    "ok": 1,
                    "data": {
                        "max_page": 2,
                        "list": topics[page],
                    },
                }
            )
        return super().get(url, params=params, headers=headers)


class RanklessSuccessSession(FakeSession):
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com/p/aj/general/button":
            return FakeResponse(
                payload={
                    "code": "100000",
                    "data": {"tipMessage": "今日签到，经验值+4"},
                }
            )
        return super().get(url, params=params, headers=headers)


class MessageOnlySuccessSession(FakeSession):
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com/p/aj/general/button":
            return FakeResponse(payload={"code": "100000", "msg": "签到成功"})
        return super().get(url, params=params, headers=headers)


class MinimalAlreadyCheckedInSession(FakeSession):
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com/p/aj/general/button":
            return FakeResponse(payload={"code": "382004"})
        return super().get(url, params=params, headers=headers)


class UnknownCheckinSession(FakeSession):
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com/p/aj/general/button":
            return FakeResponse(payload={"code": "100001", "msg": "需要验证"})
        return super().get(url, params=params, headers=headers)


class HtmlCheckinSession(FakeSession):
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com/p/aj/general/button":
            return FakeResponse(
                headers={"content-type": "text/html; charset=utf-8"},
                json_error=json.JSONDecodeError("bad json", "<html>验证</html>", 0),
                text="<html><title>验证</title><body>请先完成安全验证</body></html>",
            )
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


def test_fetch_followed_topics_returns_all_pages() -> None:
    session = PaginatedTopicsSession()
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=session)
    client.user_uid = "12345"

    topics = client.fetch_followed_topics()

    assert topics == [
        Topic(title="Topic A", topic_id="100808a"),
        Topic(title="Topic B", topic_id="100808b"),
    ]
    topic_pages = [
        params["page"]
        for url, params, _headers in session.calls
        if url == "https://weibo.com/ajax/profile/topicContent"
    ]
    assert topic_pages == [1, 2]


def test_checkin_topic_accepts_success_without_rank() -> None:
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=RanklessSuccessSession())

    result = client.checkin_topic(Topic(title="Topic A", topic_id="100808a"))

    assert result.ok is True
    assert result.title == "Topic A"
    assert result.message == "今日签到，经验值+4"
    assert result.experience == 4
    assert result.rank is None


def test_checkin_topic_accepts_success_message_without_data_block() -> None:
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=MessageOnlySuccessSession())

    result = client.checkin_topic(Topic(title="Topic A", topic_id="100808a"))

    assert result.ok is True
    assert result.message == "签到成功"
    assert result.experience is None
    assert result.rank is None


def test_checkin_topic_accepts_already_checked_in_without_message() -> None:
    client = WeiboClient(
        {"SUB": "1", "SUBP": "2"}, session=MinimalAlreadyCheckedInSession()
    )

    result = client.checkin_topic(Topic(title="Topic A", topic_id="100808a"))

    assert result.ok is True
    assert result.message == "Already checked in"


def test_checkin_topic_reports_unknown_response_summary() -> None:
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=UnknownCheckinSession())

    result = client.checkin_topic(Topic(title="Topic A", topic_id="100808a"))

    assert result.ok is False
    assert result.message == "Unknown check-in response: code=100001 msg=需要验证"


def test_checkin_topic_reports_non_json_response_diagnostic() -> None:
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=HtmlCheckinSession())

    with pytest.raises(WeiboClientError) as exc_info:
        client.checkin_topic(Topic(title="Topic A", topic_id="100808a"))

    message = str(exc_info.value)
    assert "invalid response payload" in message
    assert "status=200" in message
    assert "content-type=text/html; charset=utf-8" in message
    assert "请先完成安全验证" in message


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

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from weibo_auto_signin.models import TopicCheckinResult


class SessionProtocol(Protocol):
    cookies: dict[str, str]
    headers: dict[str, str]

    def get(
        self,
        url: str,
        params: dict[str, str | int] | None = None,
        headers: dict[str, str] | None = None,
    ) -> "ResponseProtocol": ...


class ResponseProtocol(Protocol):
    headers: dict[str, str]

    def json(self) -> object: ...


class DefaultResponse:
    def __init__(self, *, headers: dict[str, str], body: bytes) -> None:
        self.headers = headers
        self._body = body

    def json(self) -> object:
        return json.loads(self._body)


class DefaultSession:
    def __init__(self) -> None:
        self.cookies: dict[str, str] = {}
        self.headers: dict[str, str] = {}

    def get(
        self,
        url: str,
        params: dict[str, str | int] | None = None,
        headers: dict[str, str] | None = None,
    ) -> DefaultResponse:
        request_url = _build_url(url, params)
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)
        if self.cookies:
            request_headers["Cookie"] = "; ".join(
                f"{key}={value}" for key, value in self.cookies.items()
            )

        request = Request(request_url, headers=request_headers, method="GET")
        with urlopen(request) as response:
            body = response.read()
            response_headers = dict(response.headers.items())
            self._update_cookies(response.headers.get_all("Set-Cookie", []))
        return DefaultResponse(headers=response_headers, body=body)

    def _update_cookies(self, set_cookie_headers: list[str]) -> None:
        for raw_header in set_cookie_headers:
            parsed = SimpleCookie()
            parsed.load(raw_header)
            for key, morsel in parsed.items():
                self.cookies[key] = morsel.value


@dataclass(slots=True, eq=True)
class Topic:
    title: str
    topic_id: str


class WeiboClient:
    def __init__(
        self, cookies: dict[str, str], session: SessionProtocol | None = None
    ) -> None:
        self.session = session or DefaultSession()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        self.session.cookies.update(cookies)
        self.user_uid = ""

    def bootstrap_session(self) -> str:
        response = self.session.get("https://weibo.com")
        uid = response.headers.get("x-log-uid", "")
        if not uid:
            raise ValueError("Weibo session bootstrap failed: missing x-log-uid")
        self.user_uid = uid
        xsrf_token = self.session.cookies["XSRF-TOKEN"]
        self.session.headers["x-xsrf-token"] = xsrf_token
        return uid

    def fetch_user_info(self) -> dict[str, str]:
        response = self.session.get(
            f"https://weibo.com/ajax/profile/info?uid={self.user_uid}",
            headers=self._with_referer(f"https://weibo.com/u/{self.user_uid}"),
        )
        payload = response.json()
        user = payload["data"]["user"]
        return {"screen_name": user["screen_name"]}

    def fetch_followed_topics(self) -> list[Topic]:
        response = self.session.get(
            "https://weibo.com/ajax/profile/topicContent",
            params={"tabid": "231093_-_chaohua", "page": 1},
            headers=self._with_referer(
                f"https://weibo.com/u/page/follow/{self.user_uid}/231093_-_chaohua"
            ),
        )
        payload = response.json()
        return [
            Topic(title=item["title"], topic_id=item["oid"].split(":", 1)[1])
            for item in payload["data"]["list"]
        ]

    def checkin_topic(self, topic: Topic) -> TopicCheckinResult:
        response = self.session.get(
            "https://weibo.com/p/aj/general/button",
            params={
                "ajwvr": "6",
                "api": "http://i.huati.weibo.com/aj/super/checkin",
                "texta": "签到",
                "textb": "已签到",
                "status": "0",
                "id": topic.topic_id,
                "location": "page_100808_super_index",
                "__rnd": str(int(time.time() * 1000)),
            },
            headers=self._with_referer(f"https://weibo.com/p/{topic.topic_id}/super_index"),
        )
        payload = response.json()
        if str(payload.get("code")) == "100000":
            message = payload["data"]["tipMessage"]
            exp_match = re.search(r"(\d+)", message)
            rank_match = re.search(r"(\d+)", payload["data"]["alert_title"])
            return TopicCheckinResult(
                title=topic.title,
                ok=True,
                message=message,
                experience=int(exp_match.group(1)) if exp_match else None,
                rank=int(rank_match.group(1)) if rank_match else None,
            )
        if str(payload.get("code")) == "382004":
            return TopicCheckinResult(title=topic.title, ok=True, message=payload["msg"])
        return TopicCheckinResult(
            title=topic.title, ok=False, message="Unknown check-in response"
        )

    def _with_referer(self, referer: str) -> dict[str, str]:
        headers = dict(self.session.headers)
        headers["Referer"] = referer
        return headers


def _build_url(url: str, params: dict[str, str | int] | None) -> str:
    if not params:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(params)}"

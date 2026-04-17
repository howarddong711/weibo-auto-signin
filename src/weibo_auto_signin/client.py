from __future__ import annotations

import re
import time
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from weibo_auto_signin.models import TopicCheckinResult


BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0"
)


class ResponseLike(Protocol):
    headers: Mapping[str, str]

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...


class SessionLike(Protocol):
    headers: MutableMapping[str, str]
    cookies: MutableMapping[str, str]

    def get(
        self,
        url: str,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ResponseLike: ...


class WeiboClientError(RuntimeError):
    pass


@dataclass(slots=True, eq=True)
class Topic:
    title: str
    topic_id: str


class WeiboClient:
    def __init__(
        self, cookies: dict[str, str], session: SessionLike | None = None
    ) -> None:
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": BROWSER_USER_AGENT,
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        self.session.cookies.update(cookies)
        self.user_uid = ""

    def bootstrap_session(self) -> str:
        response = self._get("bootstrap session", "https://weibo.com")
        uid = self._require_non_empty(
            response.headers.get("x-log-uid"), "bootstrap session", "missing x-log-uid"
        )
        self.user_uid = uid
        xsrf_token = self._require_non_empty(
            self.session.cookies.get("XSRF-TOKEN"),
            "bootstrap session",
            "missing XSRF-TOKEN cookie",
        )
        self.session.headers["x-xsrf-token"] = xsrf_token
        return uid

    def fetch_user_info(self) -> dict[str, str]:
        payload = self._get_json(
            "fetch user info",
            f"https://weibo.com/ajax/profile/info?uid={self.user_uid}",
            headers=self._with_referer(f"https://weibo.com/u/{self.user_uid}"),
        )
        try:
            user = payload["data"]["user"]
            return {"screen_name": user["screen_name"]}
        except (KeyError, TypeError) as exc:
            raise self._invalid_payload("fetch user info") from exc

    def fetch_followed_topics(self) -> list[Topic]:
        topics: list[Topic] = []
        page = 1
        max_page = 1
        while page <= max_page:
            payload = self._get_json(
                "fetch followed topics",
                "https://weibo.com/ajax/profile/topicContent",
                params={"tabid": "231093_-_chaohua", "page": page},
                headers=self._with_referer(
                    f"https://weibo.com/u/page/follow/{self.user_uid}/231093_-_chaohua"
                ),
            )
            try:
                data = payload["data"]
                max_page = int(data.get("max_page", 1))
                topics.extend(
                    Topic(title=item["title"], topic_id=item["oid"].split(":", 1)[1])
                    for item in data["list"]
                )
            except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
                raise self._invalid_payload("fetch followed topics") from exc
            page += 1
        return topics

    def checkin_topic(self, topic: Topic) -> TopicCheckinResult:
        payload = self._get_json(
            "check in topic",
            "https://weibo.com/p/aj/general/button",
            params={
                "ajwvr": "6",
                "api": "http://i.huati.weibo.com/aj/super/checkin",
                "texta": "签到",
                "textb": "已签到",
                "status": "0",
                "id": topic.topic_id,
                "location": "page_100808_super_index",
                "timezone": "GMT+0800",
                "lang": "zh-cn",
                "plat": "Win32",
                "ua": BROWSER_USER_AGENT,
                "screen": "2560*1440",
                "__rnd": str(int(time.time() * 1000)),
            },
            headers=self._with_referer(f"https://weibo.com/p/{topic.topic_id}/super_index"),
        )
        if str(payload.get("code")) == "100000":
            return self._parse_success_checkin(topic, payload)
        if str(payload.get("code")) == "382004":
            return TopicCheckinResult(
                title=topic.title,
                ok=True,
                message=self._first_text(payload, "msg", "message") or "Already checked in",
            )
        return TopicCheckinResult(
            title=topic.title,
            ok=False,
            message=f"Unknown check-in response: {self._payload_summary(payload)}",
        )

    def _parse_success_checkin(
        self, topic: Topic, payload: Mapping[str, Any]
    ) -> TopicCheckinResult:
        data = payload.get("data")
        data_payload = data if isinstance(data, Mapping) else {}
        message = (
            self._first_text(data_payload, "tipMessage", "msg", "message")
            or self._first_text(payload, "tipMessage", "msg", "message")
            or "Check-in succeeded"
        )
        rank_source = self._first_text(data_payload, "alert_title", "rank") or ""
        exp_match = re.search(r"(\d+)", message)
        rank_match = re.search(r"(\d+)", rank_source)
        return TopicCheckinResult(
            title=topic.title,
            ok=True,
            message=message,
            experience=int(exp_match.group(1)) if exp_match else None,
            rank=int(rank_match.group(1)) if rank_match else None,
        )

    def _first_text(self, payload: Mapping[str, Any], *keys: str) -> str:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        return ""

    def _payload_summary(self, payload: Mapping[str, Any]) -> str:
        parts: list[str] = []
        for key in ("code", "msg", "message", "ok"):
            value = payload.get(key)
            if value is not None:
                parts.append(f"{key}={value}")
        if parts:
            return " ".join(parts)
        keys = ", ".join(sorted(str(key) for key in payload.keys())[:8])
        return f"keys=[{keys}]" if keys else "empty payload"

    def _with_referer(self, referer: str) -> dict[str, str]:
        headers = dict(self.session.headers)
        headers["Referer"] = referer
        return headers

    def _get(
        self,
        action: str,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ResponseLike:
        try:
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise WeiboClientError(f"Failed to {action}: HTTP request failed") from exc

    def _get_json(
        self,
        action: str,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        response = self._get(action, url, params=params, headers=headers)
        try:
            payload = response.json()
        except ValueError as exc:
            raise self._invalid_payload(
                action, detail=self._response_summary(response)
            ) from exc
        if not isinstance(payload, Mapping):
            raise self._invalid_payload(action, detail=self._response_summary(response))
        return payload

    def _require_non_empty(self, value: object, action: str, reason: str) -> str:
        if isinstance(value, str) and value:
            return value
        raise WeiboClientError(f"Failed to {action}: {reason}")

    def _invalid_payload(self, action: str, detail: str = "") -> WeiboClientError:
        suffix = f" ({detail})" if detail else ""
        return WeiboClientError(f"Failed to {action}: invalid response payload{suffix}")

    def _response_summary(self, response: ResponseLike) -> str:
        status_code = getattr(response, "status_code", "unknown")
        content_type = response.headers.get("content-type", "unknown")
        text = getattr(response, "text", "")
        snippet = self._compact_text(text)[:180] if isinstance(text, str) else ""
        parts = [f"status={status_code}", f"content-type={content_type}"]
        if snippet:
            parts.append(f"body={snippet}")
        return " ".join(parts)

    def _compact_text(self, text: str) -> str:
        return " ".join(text.split())

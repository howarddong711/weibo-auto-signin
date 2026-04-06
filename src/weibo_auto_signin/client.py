from __future__ import annotations

import re
import time
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from weibo_auto_signin.models import TopicCheckinResult


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
                "User-Agent": "Mozilla/5.0",
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
        payload = self._get_json(
            "fetch followed topics",
            "https://weibo.com/ajax/profile/topicContent",
            params={"tabid": "231093_-_chaohua", "page": 1},
            headers=self._with_referer(
                f"https://weibo.com/u/page/follow/{self.user_uid}/231093_-_chaohua"
            ),
        )
        try:
            return [
                Topic(title=item["title"], topic_id=item["oid"].split(":", 1)[1])
                for item in payload["data"]["list"]
            ]
        except (KeyError, IndexError, TypeError) as exc:
            raise self._invalid_payload("fetch followed topics") from exc

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
                "__rnd": str(int(time.time() * 1000)),
            },
            headers=self._with_referer(f"https://weibo.com/p/{topic.topic_id}/super_index"),
        )
        if str(payload.get("code")) == "100000":
            try:
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
            except (KeyError, TypeError) as exc:
                raise self._invalid_payload("check in topic") from exc
        if str(payload.get("code")) == "382004":
            try:
                return TopicCheckinResult(
                    title=topic.title, ok=True, message=payload["msg"]
                )
            except KeyError as exc:
                raise self._invalid_payload("check in topic") from exc
        return TopicCheckinResult(
            title=topic.title, ok=False, message="Unknown check-in response"
        )

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
            raise self._invalid_payload(action) from exc
        if not isinstance(payload, Mapping):
            raise self._invalid_payload(action)
        return payload

    def _require_non_empty(self, value: object, action: str, reason: str) -> str:
        if isinstance(value, str) and value:
            return value
        raise WeiboClientError(f"Failed to {action}: {reason}")

    def _invalid_payload(self, action: str) -> WeiboClientError:
        return WeiboClientError(f"Failed to {action}: invalid response payload")

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests

from weibo_auto_signin.models import TopicCheckinResult


@dataclass(slots=True, eq=True)
class Topic:
    title: str
    topic_id: str


class WeiboClient:
    def __init__(
        self, cookies: dict[str, str], session: requests.Session | None = None
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

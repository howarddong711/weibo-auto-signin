from __future__ import annotations

import requests


class PushplusNotifier:
    def __init__(self, token: str, session: requests.Session | None = None) -> None:
        self.token = token
        self.session = session or requests.Session()

    def send(self, title: str, body: str) -> bool:
        response = self.session.post(
            "https://www.pushplus.plus/send",
            json={
                "token": self.token,
                "title": title,
                "content": body,
                "template": "txt",
            },
            timeout=10,
        )
        return 200 <= response.status_code < 300

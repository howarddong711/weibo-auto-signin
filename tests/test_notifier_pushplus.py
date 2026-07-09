from weibo_auto_signin.notifiers.pushplus import PushplusNotifier


class FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code


class FakeSession:
    def __init__(self) -> None:
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json, timeout))
        return FakeResponse()


def test_pushplus_notifier_posts_plain_text_payload() -> None:
    session = FakeSession()
    notifier = PushplusNotifier(token="token-123", session=session)

    ok = notifier.send(title="Title", body="Body")

    assert ok is True
    assert session.calls == [
        (
            "https://www.pushplus.plus/send",
            {
                "token": "token-123",
                "title": "Title",
                "content": "Body",
                "template": "txt",
            },
            10,
        )
    ]

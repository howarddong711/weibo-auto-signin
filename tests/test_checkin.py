from weibo_auto_signin.checkin import run_accounts_checkin
from weibo_auto_signin.client import Topic, WeiboClientError
from weibo_auto_signin.models import AccountConfig, TopicCheckinResult


class FakeClient:
    def __init__(self, cookies, scenario):
        self.cookies = cookies
        self.scenario = scenario

    def bootstrap_session(self):
        error = self.scenario.get("bootstrap_error")
        if error is not None:
            raise error
        return self.scenario["uid"]

    def fetch_user_info(self):
        error = self.scenario.get("user_info_error")
        if error is not None:
            raise error
        return {"screen_name": self.scenario["screen_name"]}

    def fetch_followed_topics(self):
        error = self.scenario.get("topics_error")
        if error is not None:
            raise error
        return self.scenario["topics"]

    def checkin_topic(self, topic):
        outcome = self.scenario["topic_outcomes"][topic.title]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_run_accounts_checkin_marks_missing_cookie_keys_without_creating_client() -> None:
    client_calls = []

    def client_factory(parsed_cookie):
        client_calls.append(parsed_cookie)
        raise AssertionError("client factory should not be called for invalid cookies")

    results = run_accounts_checkin(
        [AccountConfig(name="broken-cookie", cookie="SUB=only-sub")],
        client_factory=client_factory,
    )

    assert client_calls == []
    assert len(results) == 1
    assert results[0].account_name == "broken-cookie"
    assert results[0].ok is False
    assert results[0].cookie_invalid is True
    assert results[0].error_message == "Missing required cookie keys: SUBP"


def test_run_accounts_checkin_continues_after_account_failure() -> None:
    scenarios = {
        "broken": {
            "bootstrap_error": WeiboClientError(
                "Failed to bootstrap session: HTTP request failed"
            )
        },
        "good": {
            "uid": "10002",
            "screen_name": "good-user",
            "topics": [Topic(title="Topic A", topic_id="a")],
            "topic_outcomes": {
                "Topic A": TopicCheckinResult(
                    title="Topic A",
                    ok=True,
                    message="already checked in",
                )
            },
        },
    }
    factory_inputs = []

    def client_factory(parsed_cookie):
        factory_inputs.append(parsed_cookie)
        return FakeClient(parsed_cookie, scenarios[parsed_cookie["SUB"]])

    results = run_accounts_checkin(
        [
            AccountConfig(name="broken-account", cookie="SUB=broken; SUBP=brokenp"),
            AccountConfig(
                name="good-account", cookie="SUB=good; SUBP=goodp; SCF=keep-me"
            ),
        ],
        client_factory=client_factory,
    )

    assert factory_inputs == [
        {"SUB": "broken", "SUBP": "brokenp"},
        {"SUB": "good", "SUBP": "goodp", "SCF": "keep-me"},
    ]
    assert [result.account_name for result in results] == [
        "broken-account",
        "good-account",
    ]
    assert results[0].ok is False
    assert results[0].error_message == "Failed to bootstrap session: HTTP request failed"
    assert results[1].ok is True
    assert results[1].uid == "10002"
    assert results[1].screen_name == "good-user"
    assert results[1].topic_results == [
        TopicCheckinResult(title="Topic A", ok=True, message="already checked in")
    ]


def test_run_accounts_checkin_continues_after_client_creation_failure() -> None:
    scenarios = {
        "good": {
            "uid": "10004",
            "screen_name": "good-user",
            "topics": [Topic(title="Topic A", topic_id="a")],
            "topic_outcomes": {
                "Topic A": TopicCheckinResult(
                    title="Topic A",
                    ok=True,
                    message="already checked in",
                )
            },
        }
    }

    def client_factory(parsed_cookie):
        if parsed_cookie["SUB"] == "broken":
            raise WeiboClientError("Failed to create client: invalid cookie state")
        return FakeClient(parsed_cookie, scenarios[parsed_cookie["SUB"]])

    results = run_accounts_checkin(
        [
            AccountConfig(name="broken-account", cookie="SUB=broken; SUBP=brokenp"),
            AccountConfig(name="good-account", cookie="SUB=good; SUBP=goodp"),
        ],
        client_factory=client_factory,
    )

    assert [result.account_name for result in results] == [
        "broken-account",
        "good-account",
    ]
    assert results[0].ok is False
    assert results[0].error_message == "Failed to create client: invalid cookie state"
    assert results[1].ok is True
    assert results[1].uid == "10004"
    assert results[1].screen_name == "good-user"


def test_run_accounts_checkin_continues_after_topic_failure() -> None:
    scenarios = {
        "good": {
            "uid": "10003",
            "screen_name": "topic-user",
            "topics": [
                Topic(title="Topic A", topic_id="a"),
                Topic(title="Topic B", topic_id="b"),
            ],
            "topic_outcomes": {
                "Topic A": WeiboClientError(
                    "Failed to check in topic: HTTP request failed"
                ),
                "Topic B": TopicCheckinResult(
                    title="Topic B",
                    ok=True,
                    message="经验值+4",
                    experience=4,
                ),
            },
        }
    }

    def client_factory(parsed_cookie):
        return FakeClient(parsed_cookie, scenarios[parsed_cookie["SUB"]])

    results = run_accounts_checkin(
        [AccountConfig(name="good-account", cookie="SUB=good; SUBP=goodp")],
        client_factory=client_factory,
    )

    assert len(results) == 1
    assert results[0].account_name == "good-account"
    assert results[0].uid == "10003"
    assert results[0].screen_name == "topic-user"
    assert results[0].ok is False
    assert results[0].topic_results == [
        TopicCheckinResult(
            title="Topic A",
            ok=False,
            message="Failed to check in topic: HTTP request failed",
        ),
        TopicCheckinResult(
            title="Topic B",
            ok=True,
            message="经验值+4",
            experience=4,
        ),
    ]

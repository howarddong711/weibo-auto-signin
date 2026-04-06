from dataclasses import dataclass, field


@dataclass(frozen=True)
class AccountConfig:
    name: str = ""
    cookie: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class TopicCheckinResult:
    title: str
    ok: bool
    message: str
    experience: int | None = None
    rank: int | None = None


@dataclass(frozen=True)
class AccountCheckinResult:
    account_name: str
    ok: bool
    uid: str = ""
    screen_name: str = ""
    cookie_invalid: bool = False
    error_message: str = ""
    topic_results: list[TopicCheckinResult] = field(default_factory=list)

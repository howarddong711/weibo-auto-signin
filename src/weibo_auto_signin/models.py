from dataclasses import dataclass, field


@dataclass(frozen=True)
class TopicCheckinResult:
    title: str
    status: str
    message: str
    experience_increment: int | None = None
    rank: str | None = None


@dataclass(frozen=True)
class AccountCheckinResult:
    display_name: str
    status: str
    uid: str | None = None
    cookie_invalid: bool = False
    topic_results: list[TopicCheckinResult] = field(default_factory=list)

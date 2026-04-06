from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AccountConfig:
    name: str
    cookie: str
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        if not self.cookie.strip():
            raise ValueError("cookie must be non-empty")


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

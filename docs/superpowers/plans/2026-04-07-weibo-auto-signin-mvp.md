# Weibo Auto Signin MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first open source release of `weibo-auto-signin`, a Python CLI that accepts multiple raw Weibo cookie strings from JSON config and performs super-topic check-in locally or through GitHub Actions.

**Architecture:** The project is a lightweight Python package under `src/weibo_auto_signin/` with clearly separated modules for config loading, cookie parsing, Weibo HTTP client behavior, check-in orchestration, logging, and CLI entrypoints. Local runs and GitHub Actions runs must share the same CLI path and JSON config format so behavior stays consistent and easy to document.

**Tech Stack:** Python 3.13, `requests`, `pytest`, `uv`, GitHub Actions

---

## Planned File Map

- Create: `/.gitignore`
- Create: `/README.md`
- Create: `/accounts.example.json`
- Create: `/pyproject.toml`
- Create: `/src/weibo_auto_signin/__init__.py`
- Create: `/src/weibo_auto_signin/models.py`
- Create: `/src/weibo_auto_signin/cookie.py`
- Create: `/src/weibo_auto_signin/config.py`
- Create: `/src/weibo_auto_signin/client.py`
- Create: `/src/weibo_auto_signin/checkin.py`
- Create: `/src/weibo_auto_signin/logging.py`
- Create: `/src/weibo_auto_signin/cli.py`
- Create: `/tests/test_smoke.py`
- Create: `/tests/test_cookie.py`
- Create: `/tests/test_config.py`
- Create: `/tests/test_client.py`
- Create: `/tests/test_checkin.py`
- Create: `/tests/test_cli.py`
- Create: `/.github/workflows/checkin.yml`

Each module has one responsibility:

- `models.py`: shared dataclasses and enums used across the package
- `cookie.py`: parse and validate raw cookie strings
- `config.py`: load JSON config, filter enabled accounts, and fail fast on invalid config
- `client.py`: encapsulate Weibo session bootstrap, topic fetching, and topic check-in requests
- `checkin.py`: orchestrate per-account and multi-account execution with continuation on failure
- `logging.py`: console and rotating-file logging setup
- `cli.py`: parse flags, invoke orchestration, and format terminal output

### Task 1: Scaffold The Package

**Files:**
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/.gitignore`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/README.md`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/accounts.example.json`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/pyproject.toml`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/__init__.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/tests/test_smoke.py
from weibo_auto_signin import __version__


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_smoke.py::test_package_exposes_version -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'weibo_auto_signin'`

- [ ] **Step 3: Write minimal project scaffold**

```toml
# /Users/howarddong/develop/code/weibo-auto-signin/pyproject.toml
[project]
name = "weibo-auto-signin"
version = "0.1.0"
description = "Weibo super-topic auto check-in CLI"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
  "requests>=2.32.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
]

[project.scripts]
weibo-auto-signin = "weibo_auto_signin.cli:main"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/__init__.py
__version__ = "0.1.0"
```

```gitignore
# /Users/howarddong/develop/code/weibo-auto-signin/.gitignore
.venv/
__pycache__/
.pytest_cache/
*.pyc
logs/
accounts.json
```

```json
// /Users/howarddong/develop/code/weibo-auto-signin/accounts.example.json
{
  "accounts": [
    {
      "name": "main-account",
      "cookie": "SUB=your_sub; SUBP=your_subp; SCF=your_scf",
      "enabled": true
    }
  ]
}
```

```md
# /Users/howarddong/develop/code/weibo-auto-signin/README.md
# weibo-auto-signin

Simple Weibo super-topic auto check-in CLI with local and GitHub Actions support.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_smoke.py::test_package_exposes_version -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add .gitignore README.md accounts.example.json pyproject.toml src/weibo_auto_signin/__init__.py tests/test_smoke.py
git commit -m "chore: scaffold weibo auto signin package"
```

### Task 2: Add Result Models And Cookie Parsing

**Files:**
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/models.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/cookie.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_cookie.py`

- [ ] **Step 1: Write the failing cookie parser tests**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/tests/test_cookie.py
from weibo_auto_signin.cookie import MissingCookieKeyError, parse_cookie_string, require_cookie_keys


def test_parse_cookie_string_keeps_valid_pairs() -> None:
    parsed = parse_cookie_string("SUB=aaa; SUBP=bbb; SCF=ccc")
    assert parsed == {"SUB": "aaa", "SUBP": "bbb", "SCF": "ccc"}


def test_parse_cookie_string_ignores_empty_segments() -> None:
    parsed = parse_cookie_string("SUB=aaa; ; broken; SUBP=bbb")
    assert parsed == {"SUB": "aaa", "SUBP": "bbb"}


def test_require_cookie_keys_raises_for_missing_required_keys() -> None:
    try:
        require_cookie_keys({"SUB": "aaa"})
    except MissingCookieKeyError as exc:
        assert exc.missing_keys == ["SUBP"]
    else:
        raise AssertionError("Expected MissingCookieKeyError")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_cookie.py -v`
Expected: FAIL with `ModuleNotFoundError` for `weibo_auto_signin.cookie`

- [ ] **Step 3: Write cookie parser and shared models**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/models.py
from dataclasses import dataclass, field


@dataclass(slots=True)
class AccountConfig:
    name: str
    cookie: str
    enabled: bool = True


@dataclass(slots=True)
class TopicCheckinResult:
    title: str
    ok: bool
    message: str
    experience: int | None = None
    rank: int | None = None


@dataclass(slots=True)
class AccountCheckinResult:
    account_name: str
    ok: bool
    uid: str = ""
    screen_name: str = ""
    cookie_invalid: bool = False
    error_message: str = ""
    topic_results: list[TopicCheckinResult] = field(default_factory=list)
```

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/cookie.py
class MissingCookieKeyError(ValueError):
    def __init__(self, missing_keys: list[str]) -> None:
        self.missing_keys = missing_keys
        super().__init__(f"Missing required cookie keys: {', '.join(missing_keys)}")


def parse_cookie_string(raw_cookie: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for part in raw_cookie.split(";"):
        segment = part.strip()
        if not segment or "=" not in segment:
            continue
        key, value = segment.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            parsed[key] = value
    return parsed


def require_cookie_keys(parsed_cookie: dict[str, str]) -> dict[str, str]:
    required_keys = ["SUB", "SUBP"]
    missing = [key for key in required_keys if not parsed_cookie.get(key)]
    if missing:
        raise MissingCookieKeyError(missing)
    return parsed_cookie
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_cookie.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add src/weibo_auto_signin/models.py src/weibo_auto_signin/cookie.py tests/test_cookie.py
git commit -m "feat: add cookie parsing and checkin models"
```

### Task 3: Load And Validate JSON Account Config

**Files:**
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/config.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_config.py`

- [ ] **Step 1: Write the failing config tests**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/tests/test_config.py
import json

import pytest

from weibo_auto_signin.config import ConfigError, load_accounts_config


def test_load_accounts_config_filters_disabled_accounts(tmp_path) -> None:
    config_path = tmp_path / "accounts.json"
    config_path.write_text(
        json.dumps(
            {
                "accounts": [
                    {"name": "a", "cookie": "SUB=1; SUBP=2", "enabled": True},
                    {"name": "b", "cookie": "SUB=3; SUBP=4", "enabled": False},
                ]
            }
        ),
        encoding="utf-8",
    )

    accounts = load_accounts_config(config_path)

    assert [account.name for account in accounts] == ["a"]


def test_load_accounts_config_rejects_missing_accounts_key(tmp_path) -> None:
    config_path = tmp_path / "accounts.json"
    config_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ConfigError, match="accounts"):
        load_accounts_config(config_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError` for `weibo_auto_signin.config`

- [ ] **Step 3: Write the config loader**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/config.py
import json
from pathlib import Path

from weibo_auto_signin.models import AccountConfig


class ConfigError(ValueError):
    pass


def load_accounts_config(path: str | Path) -> list[AccountConfig]:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    if "accounts" not in payload or not isinstance(payload["accounts"], list) or not payload["accounts"]:
        raise ConfigError("Config must include a non-empty 'accounts' array")

    accounts: list[AccountConfig] = []
    for item in payload["accounts"]:
        if not isinstance(item, dict):
            raise ConfigError("Each account item must be an object")
        cookie = item.get("cookie", "").strip()
        if not cookie:
            raise ConfigError("Each account must include a non-empty 'cookie'")
        name = (item.get("name") or "").strip() or "unnamed-account"
        enabled = item.get("enabled", True)
        accounts.append(AccountConfig(name=name, cookie=cookie, enabled=bool(enabled)))

    return [account for account in accounts if account.enabled]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_config.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add src/weibo_auto_signin/config.py tests/test_config.py
git commit -m "feat: load multi-account json config"
```

### Task 4: Implement The Weibo HTTP Client

**Files:**
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/client.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_client.py`

- [ ] **Step 1: Write the failing client tests**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/tests/test_client.py
from weibo_auto_signin.client import Topic, WeiboClient


class FakeResponse:
    def __init__(self, *, headers=None, payload=None):
        self.headers = headers or {}
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.cookies = {"XSRF-TOKEN": "xsrf-token"}
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        if url == "https://weibo.com":
            return FakeResponse(headers={"x-log-uid": "12345"})
        if url == "https://weibo.com/ajax/profile/topicContent":
            return FakeResponse(
                payload={
                    "ok": 1,
                    "data": {
                        "max_page": 1,
                        "list": [{"title": "Example", "oid": "chaohua:100808abc"}],
                    },
                }
            )
        if url == "https://weibo.com/ajax/profile/info?uid=12345":
            return FakeResponse(payload={"ok": 1, "data": {"user": {"screen_name": "demo"}}})
        if url == "https://weibo.com/p/aj/general/button":
            return FakeResponse(
                payload={
                    "code": "100000",
                    "data": {"tipMessage": "今日签到，经验值+4", "alert_title": "第12名"},
                }
            )
        raise AssertionError(url)


def test_bootstrap_session_sets_uid_and_xsrf_token() -> None:
    session = FakeSession()
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=session)

    assert client.bootstrap_session() == "12345"
    assert session.headers["x-xsrf-token"] == "xsrf-token"


def test_fetch_followed_topics_returns_topic_objects() -> None:
    session = FakeSession()
    client = WeiboClient({"SUB": "1", "SUBP": "2"}, session=session)
    client.user_uid = "12345"

    topics = client.fetch_followed_topics()

    assert topics == [Topic(title="Example", topic_id="100808abc")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_client.py -v`
Expected: FAIL with `ModuleNotFoundError` for `weibo_auto_signin.client`

- [ ] **Step 3: Write the client module**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/client.py
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
    def __init__(self, cookies: dict[str, str], session: requests.Session | None = None) -> None:
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
        response = self.session.get(f"https://weibo.com/ajax/profile/info?uid={self.user_uid}", headers=self._with_referer(f"https://weibo.com/u/{self.user_uid}"))
        payload = response.json()
        user = payload["data"]["user"]
        return {"screen_name": user["screen_name"]}

    def fetch_followed_topics(self) -> list[Topic]:
        response = self.session.get(
            "https://weibo.com/ajax/profile/topicContent",
            params={"tabid": "231093_-_chaohua", "page": 1},
            headers=self._with_referer(f"https://weibo.com/u/page/follow/{self.user_uid}/231093_-_chaohua"),
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
        return TopicCheckinResult(title=topic.title, ok=False, message="Unknown check-in response")

    def _with_referer(self, referer: str) -> dict[str, str]:
        headers = dict(self.session.headers)
        headers["Referer"] = referer
        return headers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_client.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add src/weibo_auto_signin/client.py tests/test_client.py
git commit -m "feat: add weibo session client"
```

### Task 5: Add Multi-Account Check-In Orchestration

**Files:**
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/checkin.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_checkin.py`

- [ ] **Step 1: Write the failing orchestration tests**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/tests/test_checkin.py
from weibo_auto_signin.checkin import run_accounts
from weibo_auto_signin.models import AccountConfig, TopicCheckinResult


class FakeClient:
    def __init__(self, cookies):
        self.cookies = cookies
        self.user_uid = "123"

    def bootstrap_session(self):
        return "123"

    def fetch_user_info(self):
        return {"screen_name": "demo"}

    def fetch_followed_topics(self):
        return [type("Topic", (), {"title": "Topic A", "topic_id": "1"})()]

    def checkin_topic(self, topic):
        return TopicCheckinResult(title=topic.title, ok=True, message="ok", experience=4, rank=1)


def test_run_accounts_returns_successful_result_for_valid_account() -> None:
    accounts = [AccountConfig(name="main", cookie="SUB=1; SUBP=2", enabled=True)]

    results = run_accounts(accounts, client_factory=lambda cookies: FakeClient(cookies), sleep_seconds=0)

    assert len(results) == 1
    assert results[0].account_name == "main"
    assert results[0].ok is True
    assert results[0].screen_name == "demo"


def test_run_accounts_marks_cookie_validation_failure() -> None:
    accounts = [AccountConfig(name="broken", cookie="SUB=1", enabled=True)]

    results = run_accounts(accounts, client_factory=lambda cookies: FakeClient(cookies), sleep_seconds=0)

    assert results[0].ok is False
    assert results[0].cookie_invalid is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_checkin.py -v`
Expected: FAIL with `ModuleNotFoundError` for `weibo_auto_signin.checkin`

- [ ] **Step 3: Write the orchestrator**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/checkin.py
import time
from collections.abc import Callable

from weibo_auto_signin.client import WeiboClient
from weibo_auto_signin.cookie import MissingCookieKeyError, parse_cookie_string, require_cookie_keys
from weibo_auto_signin.models import AccountCheckinResult, AccountConfig


def run_accounts(
    accounts: list[AccountConfig],
    client_factory: Callable[[dict[str, str]], WeiboClient] = WeiboClient,
    sleep_seconds: float = 1.0,
) -> list[AccountCheckinResult]:
    results: list[AccountCheckinResult] = []

    for account in accounts:
        try:
            cookies = require_cookie_keys(parse_cookie_string(account.cookie))
        except MissingCookieKeyError as exc:
            results.append(
                AccountCheckinResult(
                    account_name=account.name,
                    ok=False,
                    cookie_invalid=True,
                    error_message=str(exc),
                )
            )
            continue

        client = client_factory(cookies)
        try:
            uid = client.bootstrap_session()
            user = client.fetch_user_info()
            topics = client.fetch_followed_topics()
            topic_results = []
            for topic in topics:
                topic_results.append(client.checkin_topic(topic))
                if sleep_seconds:
                    time.sleep(sleep_seconds)
            results.append(
                AccountCheckinResult(
                    account_name=account.name,
                    ok=True,
                    uid=uid,
                    screen_name=user.get("screen_name", ""),
                    topic_results=topic_results,
                )
            )
        except Exception as exc:
            results.append(
                AccountCheckinResult(
                    account_name=account.name,
                    ok=False,
                    error_message=str(exc),
                )
            )

    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_checkin.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add src/weibo_auto_signin/checkin.py tests/test_checkin.py
git commit -m "feat: orchestrate multi-account topic checkin"
```

### Task 6: Add CLI, Logging, And Summary Output

**Files:**
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/logging.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/cli.py`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/tests/test_cli.py
from pathlib import Path

from weibo_auto_signin.cli import build_summary_lines
from weibo_auto_signin.models import AccountCheckinResult, TopicCheckinResult


def test_build_summary_lines_includes_account_and_topic_details() -> None:
    result = AccountCheckinResult(
        account_name="main",
        ok=True,
        screen_name="demo",
        topic_results=[TopicCheckinResult(title="Topic A", ok=True, message="ok", experience=4, rank=1)],
    )

    lines = build_summary_lines([result])

    assert any("main" in line for line in lines)
    assert any("Topic A" in line for line in lines)


def test_build_summary_lines_marks_cookie_invalid_accounts() -> None:
    result = AccountCheckinResult(account_name="broken", ok=False, cookie_invalid=True, error_message="missing SUBP")

    lines = build_summary_lines([result])

    assert any("cookie invalid" in line.lower() for line in lines)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError` for `weibo_auto_signin.cli`

- [ ] **Step 3: Write logging setup and CLI entrypoint**

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/logging.py
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def configure_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("weibo-auto-signin")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = TimedRotatingFileHandler(log_dir / "checkin.log", when="midnight", backupCount=30, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
```

```python
# /Users/howarddong/develop/code/weibo-auto-signin/src/weibo_auto_signin/cli.py
import argparse
from pathlib import Path

from weibo_auto_signin.checkin import run_accounts
from weibo_auto_signin.config import load_accounts_config
from weibo_auto_signin.logging import configure_logger
from weibo_auto_signin.models import AccountCheckinResult


def build_summary_lines(results: list[AccountCheckinResult]) -> list[str]:
    lines: list[str] = []
    for result in results:
        if result.cookie_invalid:
            lines.append(f"[COOKIE INVALID] {result.account_name}: {result.error_message}")
            continue
        if not result.ok:
            lines.append(f"[FAILED] {result.account_name}: {result.error_message}")
            continue
        label = result.screen_name or result.account_name
        lines.append(f"[OK] {label}")
        for topic in result.topic_results:
            if topic.experience is not None:
                lines.append(f"  - {topic.title}: +{topic.experience} exp rank {topic.rank}")
            else:
                lines.append(f"  - {topic.title}: {topic.message}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Weibo super-topic auto check-in")
    parser.add_argument("--config", default="accounts.json")
    parser.add_argument("--account")
    args = parser.parse_args()

    logger = configure_logger(Path("logs"))
    accounts = load_accounts_config(args.config)
    if args.account:
        accounts = [account for account in accounts if account.name == args.account]

    results = run_accounts(accounts)

    for line in build_summary_lines(results):
        logger.info(line)

    success_count = sum(1 for result in results if result.ok)
    logger.info("Completed run: %s success, %s failed", success_count, len(results) - success_count)
    return 0 if success_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_cli.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add src/weibo_auto_signin/logging.py src/weibo_auto_signin/cli.py tests/test_cli.py
git commit -m "feat: add cli output and rotating logs"
```

### Task 7: Add GitHub Actions Workflow And Expand README

**Files:**
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/README.md`
- Create: `/Users/howarddong/develop/code/weibo-auto-signin/.github/workflows/checkin.yml`

- [ ] **Step 1: Write the failing documentation/workflow check**

```python
# Add this test to /Users/howarddong/develop/code/weibo-auto-signin/tests/test_smoke.py
from pathlib import Path


def test_github_actions_workflow_exists() -> None:
    workflow = Path(".github/workflows/checkin.yml")
    assert workflow.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_smoke.py::test_github_actions_workflow_exists -v`
Expected: FAIL because `.github/workflows/checkin.yml` does not exist

- [ ] **Step 3: Write the workflow and full README**

```yaml
# /Users/howarddong/develop/code/weibo-auto-signin/.github/workflows/checkin.yml
name: Weibo Checkin

on:
  workflow_dispatch:
  schedule:
    - cron: "0 0 * * *"

jobs:
  checkin:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Write accounts config
        run: printf '%s' '${{ secrets.WEIBO_ACCOUNTS_JSON }}' > accounts.json
      - name: Install dependencies
        run: uv sync --extra dev
      - name: Run checkin
        run: uv run weibo-auto-signin --config accounts.json
```

```md
# /Users/howarddong/develop/code/weibo-auto-signin/README.md
# weibo-auto-signin

`weibo-auto-signin` is a simple Python CLI for Weibo super-topic auto check-in.

## Features

- Multi-account check-in from one JSON file
- Raw cookie string input
- Local CLI execution
- GitHub Actions scheduled execution
- Console and rotating-file logs

## Quick Start

1. Copy `accounts.example.json` to `accounts.json`
2. Paste one or more full Weibo cookie strings
3. Run `uv sync --extra dev`
4. Run `uv run weibo-auto-signin --config accounts.json`

## Config Format

```json
{
  "accounts": [
    {
      "name": "main-account",
      "cookie": "SUB=...; SUBP=...; SCF=...; ALF=...",
      "enabled": true
    }
  ]
}
```

## GitHub Actions

1. Fork this repository
2. Add a repository secret named `WEIBO_ACCOUNTS_JSON`
3. Paste the full JSON config as the secret value
4. Enable the workflow and adjust the schedule if needed

## Notes

- Cookies are secrets and should never be committed
- Expired cookies will cause account-level failures
- Weibo web endpoints may change over time
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest tests/test_smoke.py::test_github_actions_workflow_exists -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add .github/workflows/checkin.yml README.md tests/test_smoke.py
git commit -m "feat: add github actions workflow and setup docs"
```

### Task 8: Run Final Verification Before Any Release Work

**Files:**
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_smoke.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_cookie.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_config.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_client.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_checkin.py`
- Modify: `/Users/howarddong/develop/code/weibo-auto-signin/tests/test_cli.py`

- [ ] **Step 1: Add one end-to-end CLI smoke test with monkeypatch**

```python
# Add this test to /Users/howarddong/develop/code/weibo-auto-signin/tests/test_cli.py
from weibo_auto_signin.cli import main
from weibo_auto_signin.models import AccountCheckinResult, TopicCheckinResult


def test_main_returns_zero_when_one_account_succeeds(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "accounts.json"
    config_path.write_text('{"accounts":[{"name":"main","cookie":"SUB=1; SUBP=2","enabled":true}]}', encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["weibo-auto-signin", "--config", str(config_path)])
    monkeypatch.setattr(
        "weibo_auto_signin.cli.run_accounts",
        lambda accounts: [
            AccountCheckinResult(
                account_name="main",
                ok=True,
                screen_name="demo",
                topic_results=[TopicCheckinResult(title="Topic A", ok=True, message="ok")],
            )
        ],
    )

    assert main() == 0
```

- [ ] **Step 2: Run the full test suite**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 3: Run the CLI help output**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && uv run weibo-auto-signin --help`
Expected: exit code 0 and help text containing `--config` and `--account`

- [ ] **Step 4: Review repository tree and example config**

Run: `cd /Users/howarddong/develop/code/weibo-auto-signin && find . -maxdepth 3 -type f | sort`
Expected: package files, tests, workflow, README, and `accounts.example.json` all present

- [ ] **Step 5: Commit**

```bash
cd /Users/howarddong/develop/code/weibo-auto-signin
git add tests/test_cli.py
git commit -m "test: add final cli smoke coverage"
```

## Plan Self-Review

- Spec coverage:
  - local CLI flow: covered by Tasks 1, 3, 5, 6, and 8
  - JSON multi-account config: covered by Task 3
  - raw cookie parsing: covered by Task 2
  - Weibo session bootstrap, topic fetch, and check-in behavior: covered by Task 4
  - continuation on account/topic failure: covered by Task 5
  - console and file logs: covered by Task 6
  - bundled GitHub Actions workflow: covered by Task 7
  - documentation and security notes: covered by Task 7
- Placeholder scan:
  - no `TBD`, `TODO`, or implied “fill this in later” instructions remain
- Type consistency:
  - `AccountConfig`, `TopicCheckinResult`, `AccountCheckinResult`, `WeiboClient`, and `run_accounts()` names are used consistently across tasks

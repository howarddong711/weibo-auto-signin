import pytest

from weibo_auto_signin.cookie import (
    MissingCookieKeyError,
    parse_cookie_string,
    require_cookie_keys,
)
from weibo_auto_signin.models import AccountConfig


def test_parse_cookie_string_trims_segments_and_preserves_pairs() -> None:
    parsed = parse_cookie_string(" SUB=abc123 ; SUBP=def456 ; ALF=token=value ")

    assert parsed == {
        "SUB": "abc123",
        "SUBP": "def456",
        "ALF": "token=value",
    }


def test_parse_cookie_string_ignores_empty_and_malformed_segments() -> None:
    parsed = parse_cookie_string("SUB=abc123; ; malformed ; =skip ; SUBP=def456")

    assert parsed == {
        "SUB": "abc123",
        "SUBP": "def456",
    }


def test_require_cookie_keys_returns_cookie_when_required_keys_exist() -> None:
    parsed = {
        "SUB": "abc123",
        "SUBP": "def456",
        "SCF": "extra-value",
    }

    assert require_cookie_keys(parsed) is parsed


def test_require_cookie_keys_raises_with_missing_keys() -> None:
    with pytest.raises(MissingCookieKeyError) as exc_info:
        require_cookie_keys(
            {
                "SUB": "",
                "SCF": "extra-value",
            }
        )

    assert exc_info.value.missing_keys == ("SUB", "SUBP")


def test_account_config_rejects_blank_name_and_cookie() -> None:
    with pytest.raises(ValueError, match="name must be non-empty"):
        AccountConfig(name=" ", cookie="SUB=abc123; SUBP=def456")

    with pytest.raises(ValueError, match="cookie must be non-empty"):
        AccountConfig(name="main-account", cookie=" ")

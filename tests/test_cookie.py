import pytest

from weibo_auto_signin.cookie import (
    MissingCookieKeyError,
    parse_cookie_string,
    require_cookie_keys,
)


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

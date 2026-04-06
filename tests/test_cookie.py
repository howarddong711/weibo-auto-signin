from weibo_auto_signin.cookie import (
    missing_required_cookie_keys,
    parse_cookie_string,
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


def test_missing_required_cookie_keys_reports_absent_or_empty_values() -> None:
    missing = missing_required_cookie_keys(
        {
            "SUB": "",
            "SCF": "extra-value",
        }
    )

    assert missing == ("SUB", "SUBP")

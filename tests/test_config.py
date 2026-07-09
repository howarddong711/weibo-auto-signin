import pytest

from weibo_auto_signin.config import ConfigError, load_accounts_config


def test_load_accounts_config_reads_one_cookie_per_line(tmp_path) -> None:
    config_path = tmp_path / "cookies.txt"
    config_path.write_text(
        "SUB=1; SUBP=2\n\nSUB=3; SUBP=4; SCF=keep-me\n",
        encoding="utf-8",
    )

    accounts = load_accounts_config(config_path)

    assert [account.name for account in accounts] == ["account-1", "account-2"]
    assert [account.cookie for account in accounts] == [
        "SUB=1; SUBP=2",
        "SUB=3; SUBP=4; SCF=keep-me",
    ]


def test_load_accounts_config_rejects_empty_cookie_file(tmp_path) -> None:
    config_path = tmp_path / "cookies.txt"
    config_path.write_text("\n  \n", encoding="utf-8")

    with pytest.raises(ConfigError, match="non-empty"):
        load_accounts_config(config_path)


@pytest.mark.parametrize(
    ("raw_text", "message"),
    [
        ("SUB=1; SUBP=2\n123\nSUB=3; SUBP=4", "one cookie per line"),
        ("\n\n", "non-empty"),
    ],
)
def test_load_accounts_config_rejects_invalid_cookie_lines(tmp_path, raw_text, message) -> None:
    config_path = tmp_path / "cookies.txt"
    config_path.write_text(raw_text, encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_accounts_config(config_path)

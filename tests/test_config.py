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

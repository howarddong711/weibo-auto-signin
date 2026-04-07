import json
from pathlib import Path

from weibo_auto_signin.models import AccountConfig


class ConfigError(ValueError):
    pass


def load_accounts_config(path: str | Path) -> list[AccountConfig]:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ConfigError("Config must be a top-level JSON object")

    if (
        "accounts" not in payload
        or not isinstance(payload["accounts"], list)
        or not payload["accounts"]
    ):
        raise ConfigError("Config must include a non-empty 'accounts' array")

    accounts: list[AccountConfig] = []
    for item in payload["accounts"]:
        if not isinstance(item, dict):
            raise ConfigError("Each account item must be an object")

        cookie_value = item.get("cookie", "")
        if not isinstance(cookie_value, str):
            raise ConfigError("Each account 'cookie' must be a string")

        cookie = cookie_value.strip()
        if not cookie:
            raise ConfigError("Each account must include a non-empty 'cookie'")

        name_value = item.get("name")
        if name_value is None:
            name = "unnamed-account"
        else:
            if not isinstance(name_value, str):
                raise ConfigError("Each account 'name' must be a string")
            name = name_value.strip() or "unnamed-account"

        enabled = item.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ConfigError("Each account 'enabled' must be a boolean")

        accounts.append(AccountConfig(name=name, cookie=cookie, enabled=bool(enabled)))

    return [account for account in accounts if account.enabled]

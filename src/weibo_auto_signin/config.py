import json
from pathlib import Path

from weibo_auto_signin.models import AccountConfig


class ConfigError(ValueError):
    pass


def load_accounts_config(path: str | Path) -> list[AccountConfig]:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))

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

        cookie = item.get("cookie", "").strip()
        if not cookie:
            raise ConfigError("Each account must include a non-empty 'cookie'")

        name = (item.get("name") or "").strip() or "unnamed-account"
        enabled = item.get("enabled", True)
        accounts.append(AccountConfig(name=name, cookie=cookie, enabled=bool(enabled)))

    return [account for account in accounts if account.enabled]

from pathlib import Path

from weibo_auto_signin.models import AccountConfig


class ConfigError(ValueError):
    pass


def load_accounts_config(path: str | Path) -> list[AccountConfig]:
    config_path = Path(path)
    raw_text = config_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in raw_text.splitlines()]
    cookies = [line for line in lines if line]

    if not cookies:
        raise ConfigError("Config must include at least one non-empty cookie line")

    accounts: list[AccountConfig] = []
    for index, cookie in enumerate(cookies, start=1):
        if "=" not in cookie:
            raise ConfigError("Config must contain one cookie per line")
        accounts.append(AccountConfig(name=f"account-{index}", cookie=cookie))

    return accounts

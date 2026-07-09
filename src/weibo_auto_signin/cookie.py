from collections.abc import Mapping

REQUIRED_COOKIE_KEYS = ("SUB", "SUBP")


class MissingCookieKeyError(ValueError):
    def __init__(self, missing_keys: tuple[str, ...]) -> None:
        self.missing_keys = missing_keys
        super().__init__(f"Missing required cookie keys: {', '.join(missing_keys)}")


def parse_cookie_string(raw_cookie: str) -> dict[str, str]:
    parsed: dict[str, str] = {}

    for segment in raw_cookie.split(";"):
        item = segment.strip()
        if not item or "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            continue

        parsed[key] = value.strip()

    return parsed


def require_cookie_keys(parsed_cookie: Mapping[str, str]) -> Mapping[str, str]:
    missing_keys = tuple(
        key for key in REQUIRED_COOKIE_KEYS if not parsed_cookie.get(key)
    )
    if missing_keys:
        raise MissingCookieKeyError(missing_keys)
    return parsed_cookie

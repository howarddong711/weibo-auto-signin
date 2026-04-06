from collections.abc import Mapping

REQUIRED_COOKIE_KEYS = ("SUB", "SUBP")


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


def missing_required_cookie_keys(cookie_map: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(key for key in REQUIRED_COOKIE_KEYS if not cookie_map.get(key))

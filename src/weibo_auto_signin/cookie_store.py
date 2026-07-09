from __future__ import annotations

from pathlib import Path


def save_cookie(path: str | Path, cookie: str, *, append: bool = False) -> None:
    cookie_line = cookie.strip()
    if not cookie_line:
        raise ValueError("Cookie cannot be empty")

    cookie_path = Path(path)
    cookie_path.parent.mkdir(parents=True, exist_ok=True)

    if append and cookie_path.exists() and cookie_path.read_text(encoding="utf-8").strip():
        existing = cookie_path.read_text(encoding="utf-8")
        separator = "" if existing.endswith("\n") else "\n"
        with cookie_path.open("a", encoding="utf-8") as file:
            file.write(f"{separator}{cookie_line}\n")
        return

    cookie_path.write_text(f"{cookie_line}\n", encoding="utf-8")

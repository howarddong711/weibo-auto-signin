import pytest

from weibo_auto_signin.cookie_store import save_cookie


def test_save_cookie_overwrites_file_by_default(tmp_path) -> None:
    path = tmp_path / "cookies.txt"
    path.write_text("old-cookie\n", encoding="utf-8")

    save_cookie(path, "SUB=1; SUBP=2")

    assert path.read_text(encoding="utf-8") == "SUB=1; SUBP=2\n"


def test_save_cookie_appends_to_existing_file(tmp_path) -> None:
    path = tmp_path / "cookies.txt"
    path.write_text("SUB=1; SUBP=2\n", encoding="utf-8")

    save_cookie(path, "SUB=3; SUBP=4", append=True)

    assert path.read_text(encoding="utf-8") == "SUB=1; SUBP=2\nSUB=3; SUBP=4\n"


def test_save_cookie_rejects_empty_cookie(tmp_path) -> None:
    with pytest.raises(ValueError, match="Cookie cannot be empty"):
        save_cookie(tmp_path / "cookies.txt", "  ")

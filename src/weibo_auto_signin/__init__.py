"""Weibo auto sign-in package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("weibo-auto-signin")
except PackageNotFoundError:
    __version__ = "unknown"

"""Bilingual (zh / en) strings, following the system language."""

import locale


def _is_chinese() -> bool:
    try:
        lang = locale.getlocale()[0] or ""
    except ValueError:
        lang = ""
    if not lang:
        import os
        lang = os.environ.get("LANG", "")
    return lang.lower().startswith("zh") or lang.lower().startswith("chinese")


IS_CHINESE = _is_chinese()


def tr(zh: str, en: str) -> str:
    return zh if IS_CHINESE else en

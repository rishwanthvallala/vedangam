"""Language support. The active language is a per-request context variable so deep
calculation code can call `tr()` / `term()` without threading a parameter through."""
from __future__ import annotations

import contextvars
import json
import os
import re
from functools import lru_cache

LANG: contextvars.ContextVar[str] = contextvars.ContextVar("lang", default="en")
HERE = os.path.dirname(__file__)
LANGS = {"en": "English", "te": "తెలుగు"}


@lru_cache(maxsize=None)
def bundle(lang: str) -> dict:
    """{'terms': {...}, 'sentences': {...}, 'ui': {...}} for a language."""
    path = os.path.join(HERE, f"{lang}.json")
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    for k in ("terms", "sentences", "ui"):
        data.setdefault(k, {})
    chart_path = os.path.join(HERE, f"{lang}_chart.json")
    if os.path.exists(chart_path):
        with open(chart_path, encoding="utf-8") as f:
            data["chart"] = json.load(f)
        # planet/sign abbreviations also appear in table headers outside the charts
        for k, v in data["chart"].items():
            if len(k) == 2 and k not in ("AL", "UL", "HL", "GL", "Gk", "As"):
                data["terms"].setdefault(k, v)
    return data


def lang() -> str:
    return LANG.get()


def term(x):
    """Translate a single known term (planet, sign, nakshatra, dignity…)."""
    if not isinstance(x, str) or LANG.get() == "en":
        return x
    return bundle(LANG.get())["terms"].get(x, x)


def terms(xs, sep: str = ", ") -> str:
    return sep.join(term(x) for x in xs)


def tr(template: str, **kw) -> str:
    """Translate a sentence template, then fill placeholders (string values are passed
    through `term`, so planet/sign names come out in the same language)."""
    lg = LANG.get()
    tpl = template if lg == "en" else bundle(lg)["sentences"].get(template, template)
    vals = {k: (term(v) if isinstance(v, str) else v) for k, v in kw.items()}
    try:
        return tpl.format(**vals)
    except (KeyError, IndexError, ValueError):
        return template.format(**kw)


def ordinal(n: int) -> str:
    if LANG.get() == "te":
        return f"{n}వ"
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


_PH = re.compile(r"\{(\w+)\}")


def placeholders(s: str) -> set[str]:
    return set(_PH.findall(s))

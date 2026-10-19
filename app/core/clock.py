"""Single source of "now" for the engine. Tests freeze it so outputs are reproducible
(the browser build is checked against the server with the same frozen moment)."""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from datetime import datetime, timezone

_FROZEN: contextvars.ContextVar[datetime | None] = contextvars.ContextVar("frozen_now", default=None)


def utcnow() -> datetime:
    return _FROZEN.get() or datetime.now(timezone.utc)


def now_jd() -> float:
    from .ephemeris import jd_from_utc
    return jd_from_utc(utcnow())


@contextmanager
def frozen(iso: str | None):
    """Freeze now at an ISO UTC timestamp, e.g. "2026-10-19T06:00:00"."""
    if not iso:
        yield
        return
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    token = _FROZEN.set(dt)
    try:
        yield
    finally:
        _FROZEN.reset(token)

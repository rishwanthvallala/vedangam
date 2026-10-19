"""Offline place search (GeoNames cities ≥5000 pop.) and historical timezone
resolution through the IANA tz database (handles DST & war-time offsets)."""
from __future__ import annotations

import os
import unicodedata
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cities.tsv")


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower())
                   if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def _cities():
    rows = []
    with open(DATA, encoding="utf-8") as f:
        for line in f:
            name, ascii_, admin, country, lat, lon, pop, tz = line.rstrip("\n").split("\t")
            rows.append((name, ascii_, admin, country, float(lat), float(lon), int(pop), tz,
                         _fold(ascii_), _fold(name)))
    return rows  # already sorted by population desc


def search(q: str, limit: int = 12) -> list[dict]:
    q = q.strip()
    if len(q) < 2:
        return []
    parts = [_fold(p.strip()) for p in q.split(",")]
    city_q, rest = parts[0], [p for p in parts[1:] if p]
    out, seen = [], set()
    for exact_pass in (True, False):
        for r in _cities():
            name, ascii_, admin, country, lat, lon, pop, tz, fa, fn = r
            if exact_pass:
                ok = fa == city_q or fn == city_q
            else:
                ok = fa.startswith(city_q) or fn.startswith(city_q)
            if not ok:
                continue
            if rest and not all(p in _fold(admin) or p in _fold(country) for p in rest):
                continue
            key = (ascii_, admin, country)
            if key in seen:
                continue
            seen.add(key)
            out.append({"name": name, "admin": admin, "country": country, "lat": lat,
                        "lon": lon, "tz": tz, "population": pop,
                        "label": ", ".join(x for x in (name, admin, country) if x)})
            if len(out) >= limit:
                return out
    return out


def utc_offset_hours(tz_name: str, local: datetime) -> float:
    z = ZoneInfo(tz_name)
    off = local.replace(tzinfo=z).utcoffset()
    return off.total_seconds() / 3600.0


def local_to_utc(local: datetime, tz_name: str | None, offset_hours: float | None):
    """Returns (utc_datetime, offset_hours_used, is_dst)."""
    if offset_hours is not None:
        utc = (local - timedelta(hours=offset_hours)).replace(tzinfo=timezone.utc)
        return utc, offset_hours, False
    z = ZoneInfo(tz_name)
    aware = local.replace(tzinfo=z)
    off = aware.utcoffset().total_seconds() / 3600.0
    dst = bool(aware.dst() and aware.dst().total_seconds())
    return aware.astimezone(timezone.utc), off, dst


def fmt_offset(h: float) -> str:
    sign = "+" if h >= 0 else "-"
    h = abs(h)
    hh = int(h)
    mm = int(round((h - hh) * 60))
    if mm == 60:
        hh, mm = hh + 1, 0
    return f"UTC{sign}{hh:02d}:{mm:02d}"

"""Vimshottari and Yogini dasha systems."""
from __future__ import annotations

from ..i18n import tr
from .constants import DASHA_ORDER, DASHA_YEARS, NAK_LORD, NAK_SPAN, NAKSHATRAS, norm

LEVEL_NAMES = ["Mahadasha", "Antardasha", "Pratyantardasha", "Sookshma", "Prana"]


def _ymd(years: float) -> str:
    y = int(years)
    m_f = (years - y) * 12
    m = int(m_f)
    d = int(round((m_f - m) * 30.4375))
    if d >= 30:
        m, d = m + 1, 0
    if m >= 12:
        y, m = y + 1, 0
    return tr("{y}y {m}m {d}d", y=y, m=m, d=d)


def _children(lord: str, start: float, dur: float, depth: int, fmt, order=DASHA_ORDER,
              years=DASHA_YEARS, total=120.0):
    out = []
    i0 = order.index(lord)
    t = start
    for k in range(len(order)):
        sub = order[(i0 + k) % len(order)]
        d = dur * years[sub] / total
        node = {"lord": sub, "start": fmt(t), "end": fmt(t + d), "_s": t, "_e": t + d}
        if depth > 1:
            node["children"] = _children(sub, t, d, depth - 1, fmt, order, years, total)
        out.append(node)
        t += d
    return out


def vimshottari(moon_lon: float, birth_jd: float, fmt, year_days: float = 365.25,
                levels: int = 3, now_jd: float | None = None) -> dict:
    moon_lon = norm(moon_lon)
    nak = int(moon_lon // NAK_SPAN)
    frac = (moon_lon % NAK_SPAN) / NAK_SPAN
    lord = NAK_LORD[nak]
    yd = year_days
    start = birth_jd - frac * DASHA_YEARS[lord] * yd
    balance_years = (1 - frac) * DASHA_YEARS[lord]
    mds = []
    t = start
    i0 = DASHA_ORDER.index(lord)
    k = 0
    while t < birth_jd + 121 * yd:
        md = DASHA_ORDER[(i0 + k) % 9]
        dur = DASHA_YEARS[md] * yd
        node = {"lord": md, "start": fmt(t), "end": fmt(t + dur), "years": DASHA_YEARS[md],
                "_s": t, "_e": t + dur,
                "children": _children(md, t, dur, levels - 1, fmt) if levels > 1 else []}
        mds.append(node)
        t += dur
        k += 1
    current = []
    if now_jd is not None:
        current = current_chain(mds, now_jd, fmt, depth=5)
    result = {
        "system": "Vimshottari", "year_days": yd,
        "moon_nakshatra": NAKSHATRAS[nak], "starting_lord": lord,
        "balance": _ymd(balance_years), "balance_years": round(balance_years, 4),
        "periods": _strip(mds), "current": current,
    }
    return result


def current_chain(mds, jd, fmt, depth=5, order=DASHA_ORDER, years=DASHA_YEARS, total=120.0):
    """Running dasha lords from MD down to `depth` levels at jd."""
    chain = []
    level_nodes = mds
    span_lord, span_s, span_e = None, None, None
    for lvl in range(depth):
        node = None
        if level_nodes:
            for n in level_nodes:
                if n["_s"] <= jd < n["_e"]:
                    node = n
                    break
        elif span_lord is not None:
            subs = _children(span_lord, span_s, span_e - span_s, 1, fmt, order, years, total)
            for n in subs:
                if n["_s"] <= jd < n["_e"]:
                    node = n
                    break
        if node is None:
            break
        chain.append({"level": LEVEL_NAMES[lvl], "lord": node["lord"], "start": node["start"],
                      "end": node["end"]})
        span_lord, span_s, span_e = node["lord"], node["_s"], node["_e"]
        level_nodes = node.get("children") or None
    return chain


def _strip(nodes):
    out = []
    for n in nodes:
        m = {k: v for k, v in n.items() if not k.startswith("_") and k != "children"}
        if n.get("children"):
            m["children"] = _strip(n["children"])
        out.append(m)
    return out


# ------------------------------------------------------------------ Yogini
YOGINIS = [("Mangala", "Moon", 1), ("Pingala", "Sun", 2), ("Dhanya", "Jupiter", 3),
           ("Bhramari", "Mars", 4), ("Bhadrika", "Mercury", 5), ("Ulka", "Saturn", 6),
           ("Siddha", "Venus", 7), ("Sankata", "Rahu", 8)]


def yogini(moon_lon: float, birth_jd: float, fmt, year_days: float = 365.25,
           now_jd: float | None = None) -> dict:
    nak = int(norm(moon_lon) // NAK_SPAN)
    frac = (norm(moon_lon) % NAK_SPAN) / NAK_SPAN
    idx = (nak + 1 + 3) % 8
    idx = 7 if idx == 0 else idx - 1
    names = [y[0] for y in YOGINIS]
    yrs = {y[0]: y[2] for y in YOGINIS}
    lords = {y[0]: y[1] for y in YOGINIS}
    first = names[idx]
    start = birth_jd - frac * yrs[first] * year_days
    out, t, k = [], start, 0
    while t < birth_jd + 110 * year_days:
        nm = names[(idx + k) % 8]
        dur = yrs[nm] * year_days
        subs = _children(nm, t, dur, 1, fmt, order=names, years=yrs, total=36.0)
        out.append({"lord": nm, "planet": lords[nm], "years": yrs[nm], "start": fmt(t),
                    "end": fmt(t + dur), "_s": t, "_e": t + dur,
                    "children": [{**c, "planet": lords[c["lord"]]} for c in subs]})
        t += dur
        k += 1
    current = []
    if now_jd is not None:
        current = current_chain(out, now_jd, fmt, depth=2, order=names, years=yrs, total=36.0)
        for c in current:
            c["planet"] = lords[c["lord"]]
    return {"system": "Yogini", "starting": first, "balance": _ymd((1 - frac) * yrs[first]),
            "periods": _strip(out), "current": current}


# ------------------------------------------------------------------ Ashtottari (108 years)
ASHTOTTARI_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Saturn", "Jupiter", "Rahu", "Venus"]
ASHTOTTARI_YEARS = {"Sun": 6, "Moon": 15, "Mars": 8, "Mercury": 17, "Saturn": 10,
                    "Jupiter": 19, "Rahu": 12, "Venus": 21}
_A = 360.0 / 27.0
# 28-nakshatra scheme with Abhijit (U.Ashadha pada 4 + first 1/15 of Shravana), from Ardra
_ASHTO_SEGMENTS = [
    ("Sun", [(5 * _A, 6 * _A), (6 * _A, 7 * _A), (7 * _A, 8 * _A), (8 * _A, 9 * _A)]),
    ("Moon", [(9 * _A, 10 * _A), (10 * _A, 11 * _A), (11 * _A, 12 * _A)]),
    ("Mars", [(12 * _A, 13 * _A), (13 * _A, 14 * _A), (14 * _A, 15 * _A), (15 * _A, 16 * _A)]),
    ("Mercury", [(16 * _A, 17 * _A), (17 * _A, 18 * _A), (18 * _A, 19 * _A)]),
    ("Saturn", [(19 * _A, 20 * _A), (20 * _A, 276 + 40 / 60), (276 + 40 / 60, 280 + 53 / 60 + 20 / 3600),
                (280 + 53 / 60 + 20 / 3600, 22 * _A)]),
    ("Jupiter", [(22 * _A, 23 * _A), (23 * _A, 24 * _A), (24 * _A, 25 * _A)]),
    ("Rahu", [(25 * _A, 26 * _A), (26 * _A, 27 * _A), (0, _A), (_A, 2 * _A)]),
    ("Venus", [(2 * _A, 3 * _A), (3 * _A, 4 * _A), (4 * _A, 5 * _A)]),
]


def ashtottari(moon_lon: float, birth_jd: float, fmt, year_days: float = 365.25,
               now_jd: float | None = None, applicable: str = "") -> dict:
    m = norm(moon_lon)
    lord, balance = None, 0.0
    for lrd, segs in _ASHTO_SEGMENTS:
        per = ASHTOTTARI_YEARS[lrd] / len(segs)
        for i, (a, b) in enumerate(segs):
            if a <= m < b:
                frac = (m - a) / (b - a)
                lord = lrd
                balance = per * (1 - frac) + per * (len(segs) - i - 1)
                break
        if lord:
            break
    elapsed = ASHTOTTARI_YEARS[lord] - balance
    start = birth_jd - elapsed * year_days
    out, t, k = [], start, 0
    i0 = ASHTOTTARI_ORDER.index(lord)
    while t < birth_jd + 110 * year_days:
        md = ASHTOTTARI_ORDER[(i0 + k) % 8]
        dur = ASHTOTTARI_YEARS[md] * year_days
        out.append({"lord": md, "years": ASHTOTTARI_YEARS[md], "start": fmt(t), "end": fmt(t + dur),
                    "_s": t, "_e": t + dur,
                    "children": _children(md, t, dur, 2, fmt, ASHTOTTARI_ORDER, ASHTOTTARI_YEARS, 108.0)})
        t += dur
        k += 1
    current = current_chain(out, now_jd, fmt, 3, ASHTOTTARI_ORDER, ASHTOTTARI_YEARS, 108.0) if now_jd else []
    return {"system": "Ashtottari", "starting_lord": lord, "balance": _ymd(balance),
            "applicability": applicable, "periods": _strip(out), "current": current}


# ------------------------------------------------------------------ helpers for calendar / pravesh
def _vim_mds(moon_lon: float, birth_jd: float, yd: float):
    moon_lon = norm(moon_lon)
    nak = int(moon_lon // NAK_SPAN)
    frac = (moon_lon % NAK_SPAN) / NAK_SPAN
    lord = NAK_LORD[nak]
    t = birth_jd - frac * DASHA_YEARS[lord] * yd
    i0 = DASHA_ORDER.index(lord)
    for k in range(18):
        md = DASHA_ORDER[(i0 + k) % 9]
        dur = DASHA_YEARS[md] * yd
        yield md, t, dur
        t += dur


def _walk(lord, start, dur, depth, lo, hi, path):
    """Yield (path, start, end) for every sub-period down to `depth` overlapping [lo, hi]."""
    i0 = DASHA_ORDER.index(lord)
    t = start
    for k in range(9):
        sub = DASHA_ORDER[(i0 + k) % 9]
        d = dur * DASHA_YEARS[sub] / 120.0
        if t + d >= lo and t <= hi:
            p = path + [sub]
            yield p, t, t + d
            if depth > 1:
                yield from _walk(sub, t, d, depth - 1, lo, hi, p)
        t += d


def change_events(moon_lon: float, birth_jd: float, fmt, yd: float, lo: float, hi: float,
                  depth: int = 4) -> list[dict]:
    """Every Vimshottari period that begins between lo and hi (MD…Sookshma)."""
    out = []
    for md, s, dur in _vim_mds(moon_lon, birth_jd, yd):
        if s > hi:
            break
        if s + dur < lo:
            continue
        if lo <= s <= hi:
            out.append({"date": fmt(s), "level": 1, "level_name": LEVEL_NAMES[0], "lords": [md], "_jd": s})
        for path, a, b in _walk(md, s, dur, depth - 1, lo, hi, [md]):
            if lo <= a <= hi:
                out.append({"date": fmt(a), "level": len(path), "level_name": LEVEL_NAMES[len(path) - 1],
                            "lords": path, "_jd": a})
    out.sort(key=lambda e: (e["_jd"], e["level"]))
    for e in out:
        e.pop("_jd")
    return out


def running_jds(moon_lon: float, birth_jd: float, yd: float, at_jd: float, depth: int = 3):
    """[(level_name, lords, start_jd, end_jd)] of the periods running at `at_jd`."""
    for md, s, dur in _vim_mds(moon_lon, birth_jd, yd):
        if s <= at_jd < s + dur:
            out = [(LEVEL_NAMES[0], [md], s, s + dur)]
            for path, a, b in _walk(md, s, dur, depth - 1, at_jd, at_jd, [md]):
                if a <= at_jd < b:
                    out.append((LEVEL_NAMES[len(path) - 1], path, a, b))
            return out
    return []

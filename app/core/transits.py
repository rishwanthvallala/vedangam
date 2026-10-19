"""Transit tools: a year of sign ingresses (with retrograde stations), Ashtakavarga-based
transit strength over time, and daily positions for the animated transit chart."""
from __future__ import annotations

from . import ephemeris as E
from ..i18n import tr
from .constants import GRAHAS, NAKSHATRAS, SEVEN, SIGNS, deg_in_sign, dms, nakshatra_of, sign_of

SLOW = ["Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def _lon(jd, p, aya, node):
    return E.calc_body(jd, p, aya, node)


def year_ingresses(chart, inp, start_jd: float, days: int = 365) -> dict:
    """Sign changes and retrograde/direct stations for each planet over the period."""
    aya, node = chart.ayanamsa, chart.node
    moon_s, lag_s = chart.sign("Moon"), chart.lagna_sign
    end = start_jd + days
    rows, segments = [], {}
    for p in SLOW:
        step = 1.0 if p in ("Sun", "Mercury", "Venus", "Mars") else 2.0
        t = start_jd
        b = _lon(t, p, aya, node)
        cur_sign, cur_retro = sign_of(b.lon), b.speed < 0
        seg_start = t
        segs = []
        while t < end:
            t2 = min(t + step, end)
            b2 = _lon(t2, p, aya, node)
            s2, r2 = sign_of(b2.lon), b2.speed < 0
            if s2 != cur_sign:
                boundary = (s2 if (s2 - cur_sign) % 12 == 1 else cur_sign) * 30.0
                tc = E.find_crossing(lambda x: E.angdiff(_lon(x, p, aya, node).lon, boundary), t, t2)
                segs.append({"sign": SIGNS[cur_sign], "start": inp.fmt_jd(seg_start, False),
                             "end": inp.fmt_jd(tc, False), "_s": seg_start, "_e": tc})
                rows.append({"planet": p, "event": "ingress", "date": inp.fmt_jd(tc, False),
                             "sign": SIGNS[s2], "house_from_lagna": (s2 - lag_s) % 12 + 1,
                             "house_from_moon": (s2 - moon_s) % 12 + 1, "_jd": tc})
                cur_sign, seg_start = s2, tc
            if r2 != cur_retro and p not in ("Sun", "Rahu", "Ketu"):
                tc = E.find_crossing(lambda x: _lon(x, p, aya, node).speed, t, t2)
                rows.append({"planet": p, "event": "retrograde" if r2 else "direct",
                             "date": inp.fmt_jd(tc, False), "sign": SIGNS[sign_of(_lon(tc, p, aya, node).lon)],
                             "house_from_lagna": None, "house_from_moon": None, "_jd": tc})
                cur_retro = r2
            t = t2
        segs.append({"sign": SIGNS[cur_sign], "start": inp.fmt_jd(seg_start, False),
                     "end": inp.fmt_jd(end, False), "_s": seg_start, "_e": end})
        segments[p] = segs
    rows.sort(key=lambda r: r["_jd"])
    for r in rows:
        r.pop("_jd")
    for p in segments:
        for sg in segments[p]:
            sg["frac_start"] = round((sg.pop("_s") - start_jd) / days, 5)
            sg["frac_end"] = round((sg.pop("_e") - start_jd) / days, 5)
    return {"from": inp.fmt_jd(start_jd, False), "to": inp.fmt_jd(end, False),
            "events": rows, "segments": segments}


def strength_series(chart, inp, av: dict, start_jd: float, days: int = 365, step: float = 3.0) -> dict:
    """Bindus (BAV) of the sign each planet transits, sampled through the period; the SAV of
    the sign transited by Saturn and Jupiter is added as context."""
    aya, node = chart.ayanamsa, chart.node
    series = {p: [] for p in SEVEN}
    dates = []
    t = start_jd
    while t <= start_jd + days:
        dates.append(inp.fmt_jd(t, False))
        for p in SEVEN:
            s = sign_of(_lon(t, p, aya, node).lon)
            series[p].append(av["bav"][p]["bindus"][s])
        t += step
    return {"dates": dates, "series": series, "max": 8,
            "note": tr("BAV bindus of the transited sign: 5–8 favourable, 4 average, 0–3 difficult.")}


def frames(chart, inp, start_jd: float, days: int = 365, step: float = 1.0,
           planets=tuple(GRAHAS)) -> dict:
    """Daily sidereal longitudes for the animated transit chart."""
    aya, node = chart.ayanamsa, chart.node
    out = {p: [] for p in planets}
    retro = {p: [] for p in planets}
    dates = []
    t = start_jd
    while t <= start_jd + days:
        dates.append(inp.fmt_jd(t, False))
        for p in planets:
            b = _lon(t, p, aya, node)
            out[p].append(round(b.lon, 3))
            retro[p].append(b.speed < 0 and p not in ("Rahu", "Ketu"))
        t += step
    return {"dates": dates, "lon": out, "retro": retro, "natal_lagna": chart.lagna_sign,
            "natal_moon": chart.sign("Moon")}


def now_snapshot(jd: float, lat: float, lon: float, aya: str = "lahiri", node: str = "mean") -> list[dict]:
    rows = []
    for p in GRAHAS:
        b = E.calc_body(jd, p, aya, node)
        nk, pd = nakshatra_of(b.lon)
        rows.append({"planet": p, "sign": SIGNS[sign_of(b.lon)], "dms": dms(deg_in_sign(b.lon)),
                     "nakshatra": NAKSHATRAS[nk], "pada": pd,
                     "retro": b.speed < 0 and p not in ("Rahu", "Ketu"), "lon": b.lon})
    return rows

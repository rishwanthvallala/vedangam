"""Parashari building blocks: dignity, relationships, aspects, combustion, avasthas."""
from __future__ import annotations

from .constants import (COMBUST_ORB, DEBILITATION, ENEMIES, EXALTATION, FRIENDS, GRAHAS,
                        MOOLATRIKONA, OWN_SIGNS, SEVEN, SIGN_LORD, SIGNS, deg_in_sign, norm,
                        sign_of)
from .ephemeris import angdiff


def natural_relation(p: str, q: str) -> int:
    """+1 friend, 0 neutral, -1 enemy (p's view of q)."""
    if p == q:
        return 1
    if q in FRIENDS.get(p, []):
        return 1
    if q in ENEMIES.get(p, []):
        return -1
    return 0


def temporal_relation(sign_p: int, sign_q: int) -> int:
    h = (sign_q - sign_p) % 12 + 1
    return 1 if h in (2, 3, 4, 10, 11, 12) else -1


REL_NAMES = {2: "Adhi Mitra", 1: "Mitra", 0: "Sama", -1: "Shatru", -2: "Adhi Shatru"}


def compound_relation(p: str, q: str, signs: dict[str, int]) -> int:
    return natural_relation(p, q) + temporal_relation(signs[p], signs[q])


def is_moolatrikona(p: str, lon: float) -> bool:
    s, a, b = MOOLATRIKONA[p]
    return sign_of(lon) == s and a <= deg_in_sign(lon) < b


def dignity(p: str, lon: float, signs: dict[str, int] | None = None, use_mt: bool = True,
            sign_override: int | None = None) -> str:
    """Dignity of planet p at longitude lon (sign_override for varga charts)."""
    s = sign_of(lon) if sign_override is None else sign_override
    if EXALTATION.get(p, (None,))[0] == s:
        return "Exalted"
    if DEBILITATION.get(p, (None,))[0] == s:
        return "Debilitated"
    if use_mt and sign_override is None and is_moolatrikona(p, lon):
        return "Moolatrikona"
    if s in OWN_SIGNS.get(p, []):
        return "Own"
    lord = SIGN_LORD[s]
    if signs is not None and p in signs and lord in signs:
        r = compound_relation(p, lord, signs)
        return {2: "Great Friend", 1: "Friend", 0: "Neutral", -1: "Enemy",
                -2: "Great Enemy"}[r]
    r = natural_relation(p, lord)
    return {1: "Friend", 0: "Neutral", -1: "Enemy"}[r]


DIGNITY_SCORE = {"Exalted": 5, "Moolatrikona": 4, "Own": 3.5, "Great Friend": 3,
                 "Friend": 2, "Neutral": 1, "Enemy": 0, "Great Enemy": -0.5,
                 "Debilitated": -1}


def graha_aspects(p: str) -> list[int]:
    if p == "Mars":
        return [4, 7, 8]
    if p == "Jupiter":
        return [5, 7, 9]
    if p == "Saturn":
        return [3, 7, 10]
    if p in ("Rahu", "Ketu"):
        return [5, 7, 9]
    return [7]


def aspects_on_signs(signs: dict[str, int]) -> dict[int, list[str]]:
    """Which planets aspect each sign (Parashari full aspects)."""
    out = {i: [] for i in range(12)}
    for p, s in signs.items():
        for h in graha_aspects(p):
            out[(s + h - 1) % 12].append(p)
    return out


def combustion(p: str, lon: float, sun_lon: float, retro: bool) -> tuple[bool, float]:
    if p not in COMBUST_ORB:
        return False, 0.0
    dist = abs(angdiff(lon, sun_lon))
    orb = COMBUST_ORB[p][1 if retro else 0]
    return dist <= orb, dist


def baladi_avastha(lon: float) -> str:
    s, d = sign_of(lon), deg_in_sign(lon)
    names = ["Bala (infant)", "Kumara (youth)", "Yuva (adult)", "Vriddha (old)", "Mrita (dead)"]
    idx = min(int(d // 6), 4)
    if s % 2 == 1:
        idx = 4 - idx
    return names[idx]


def jagradadi_avastha(dig: str) -> str:
    if dig in ("Exalted", "Own", "Moolatrikona"):
        return "Jagrat (awake)"
    if dig in ("Great Friend", "Friend", "Neutral"):
        return "Swapna (dreaming)"
    return "Sushupti (asleep)"


def deeptadi_avastha(dig: str, combust: bool) -> str:
    if combust:
        return "Vikala (crippled)"
    return {"Exalted": "Deepta (blazing)", "Moolatrikona": "Swastha (healthy)",
            "Own": "Swastha (healthy)", "Great Friend": "Mudita (delighted)",
            "Friend": "Shanta (peaceful)", "Neutral": "Deena (meek)",
            "Enemy": "Dukhita (distressed)", "Great Enemy": "Dukhita (distressed)",
            "Debilitated": "Khala (wicked)"}[dig]


def planet_table(chart, kp_fn=None) -> list[dict]:
    """Detailed row per graha (incl. Lagna) — the standard 'Planetary Positions' table."""
    signs = {p: chart.sign(p) for p in GRAHAS}
    sun = chart.bodies["Sun"].lon
    rows = []
    asc_row = {"name": "Lagna", "lon": chart.asc, "sign": sign_of(chart.asc),
               "sign_name": SIGNS[sign_of(chart.asc)], "deg": deg_in_sign(chart.asc),
               "retro": False, "speed": None}
    from .constants import NAK_LORD, NAKSHATRAS, dms, nakshatra_of
    nk, pd = nakshatra_of(chart.asc)
    asc_row.update({"dms": dms(deg_in_sign(chart.asc)), "nakshatra": NAKSHATRAS[nk],
                    "pada": pd, "nak_lord": NAK_LORD[nk], "house": 1,
                    "sign_lord": SIGN_LORD[sign_of(chart.asc)]})
    if kp_fn:
        asc_row.update(kp_fn(chart.asc))
    rows.append(asc_row)
    for p in GRAHAS + [x for x in ("Uranus", "Neptune", "Pluto") if x in chart.bodies]:
        b = chart.bodies[p]
        d = b.to_dict()
        d["house"] = chart.house(p)
        d["bhava"] = chart.bhava_of(b.lon, chart.sripati)
        d["sign_lord"] = SIGN_LORD[sign_of(b.lon)]
        if p in GRAHAS:
            dig = dignity(p, b.lon, signs)
            comb, dist = combustion(p, b.lon, sun, b.retro)
            d.update({"dignity": dig, "combust": comb, "sun_dist": round(dist, 2),
                      "avastha_baladi": baladi_avastha(b.lon),
                      "avastha_jagradadi": jagradadi_avastha(dig),
                      "avastha_deeptadi": deeptadi_avastha(dig, comb)})
            if p in ("Rahu", "Ketu"):
                d["retro"] = True
        if kp_fn:
            d.update(kp_fn(b.lon))
        rows.append(d)
    return rows


def relationship_tables(chart) -> dict:
    signs = {p: chart.sign(p) for p in SEVEN}
    nat, tmp, comp = {}, {}, {}
    for p in SEVEN:
        nat[p], tmp[p], comp[p] = {}, {}, {}
        for q in SEVEN:
            if p == q:
                continue
            n = natural_relation(p, q)
            t = temporal_relation(signs[p], signs[q])
            nat[p][q] = {1: "Friend", 0: "Neutral", -1: "Enemy"}[n]
            tmp[p][q] = "Friend" if t > 0 else "Enemy"
            comp[p][q] = REL_NAMES[n + t]
    return {"natural": nat, "temporal": tmp, "compound": comp}


def aspect_table(chart) -> dict:
    """Planet → list of planets/houses it aspects (whole-sign Parashari drishti)."""
    out = {}
    for p in GRAHAS:
        s = chart.sign(p)
        hits = []
        for h in graha_aspects(p):
            tgt = (s + h - 1) % 12
            occ = [q for q in GRAHAS if q != p and chart.sign(q) == tgt]
            hits.append({"house": (tgt - chart.lagna_sign) % 12 + 1, "sign": SIGNS[tgt],
                         "aspect": h, "planets": occ})
        out[p] = hits
    return out


def sphuta_drishti(angle: float, aspecting: str) -> float:
    """BPHS graded aspect value (virupas, 0..60) for angular distance from aspecting
    to aspected body."""
    d = norm(angle)
    if d < 30 or d >= 300:
        v = 0.0
    elif d < 60:
        v = (d - 30) / 2
    elif d < 90:
        v = (d - 60) + 15
    elif d < 120:
        v = (120 - d) / 2 + 30
    elif d < 150:
        v = 150 - d
    elif d < 180:
        v = (d - 150) * 2
    else:
        v = (300 - d) / 2
    if aspecting == "Saturn" and (60 <= d < 90 or 270 <= d < 300):
        v += 45
    elif aspecting == "Jupiter" and (120 <= d < 150 or 240 <= d < 270):
        v += 30
    elif aspecting == "Mars" and (90 <= d < 120 or 210 <= d < 240):
        v += 15
    return min(v, 60.0)

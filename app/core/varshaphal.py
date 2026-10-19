"""Annual charts: Tajika Varshaphal (Tajika Neelakanthi, as in Jagannatha Hora /
Parashara's Light) and the Vedic Tithi Pravesha chart (Sanjay Rath).

Varshaphal
    Varsha Pravesha is the instant the sidereal (Lahiri) Sun returns to its natal sidereal
    longitude. From that chart come the Muntha, the five office-bearers (Pancha-adhikari),
    Pancha-vargiya bala, the year lord (Varshesha), Tajika aspects and yogas, the Sahams and
    the two annual dashas (Mudda and Patyayini).

Tithi Pravesha
    The instant near the birthday when the Moon-Sun elongation equals the natal elongation
    while the Sun is in its natal sidereal sign.
"""
from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from . import ephemeris as E
from .chart import BirthInput, SiderealChart
from .constants import (DASHA_ORDER, DASHA_YEARS, DEBILITATION, GRAHAS,
                        NAK_SPAN, NAKSHATRAS, SEVEN, SIGN_LORD, SIGNS, TITHIS, WEEKDAY_LORD,
                        WEEKDAYS, deg_in_sign, dms, nakshatra_of, norm, sign_of)
from .prashna import tajika_relation
from .vargas import varga_sign
from .vedic import combustion, natural_relation
from ..i18n import terms, tr

SIDEREAL_YEAR = 365.256363          # mean sidereal year (days); only seeds the Sun-return search

# ---------------------------------------------------------------- Tajika tables
# Tri-rashi pati by Varsha lagna sign (Aries..Pisces). Tajika Neelakanthi, Varsha-tantra; the
# same table is in B.V. Raman's "Varshaphala" and PyJHora (JHora). Sagittarius is Saturn by night.
TRI_RASHI_DAY = ["Sun", "Venus", "Saturn", "Venus", "Jupiter", "Moon", "Mercury", "Mars",
                 "Saturn", "Mars", "Jupiter", "Moon"]
TRI_RASHI_NIGHT = ["Jupiter", "Moon", "Mercury", "Mars", "Sun", "Venus", "Saturn", "Venus",
                   "Saturn", "Mars", "Jupiter", "Moon"]

# Tajika haddas: (lord, upper degree limit) per sign. Tajika Neelakanthi, cross-checked against
# PyJHora (JHora) and the "Tajik Shastra" encyclopaedia: the Egyptian terms, except that Gemini
# has Venus 6-12 / Jupiter 12-17 and Sagittarius has Mars 21-26 / Saturn 26-30.
HADDA = [
    [("Jupiter", 6), ("Venus", 12), ("Mercury", 20), ("Mars", 25), ("Saturn", 30)],    # Aries
    [("Venus", 8), ("Mercury", 14), ("Jupiter", 22), ("Saturn", 27), ("Mars", 30)],    # Taurus
    [("Mercury", 6), ("Venus", 12), ("Jupiter", 17), ("Mars", 24), ("Saturn", 30)],    # Gemini
    [("Mars", 7), ("Venus", 13), ("Mercury", 19), ("Jupiter", 26), ("Saturn", 30)],    # Cancer
    [("Jupiter", 6), ("Venus", 11), ("Saturn", 18), ("Mercury", 24), ("Mars", 30)],    # Leo
    [("Mercury", 7), ("Venus", 17), ("Jupiter", 21), ("Mars", 28), ("Saturn", 30)],    # Virgo
    [("Saturn", 6), ("Mercury", 14), ("Jupiter", 21), ("Venus", 28), ("Mars", 30)],    # Libra
    [("Mars", 7), ("Venus", 11), ("Mercury", 19), ("Jupiter", 24), ("Saturn", 30)],    # Scorpio
    [("Jupiter", 12), ("Venus", 17), ("Mercury", 21), ("Mars", 26), ("Saturn", 30)],   # Sagittarius
    [("Mercury", 7), ("Jupiter", 14), ("Venus", 22), ("Saturn", 26), ("Mars", 30)],    # Capricorn
    [("Mercury", 7), ("Venus", 13), ("Jupiter", 20), ("Mars", 25), ("Saturn", 30)],    # Aquarius
    [("Venus", 12), ("Jupiter", 16), ("Mercury", 19), ("Mars", 28), ("Saturn", 30)],   # Pisces
]

# Tajika drekkana lords: the 36 decans from 0° Aries take the planets in Chaldean order from Mars
# (Tajika Neelakanthi; K.S. Charak; "Tajik Shastra" encyclopaedia), not the Parashari D-3.
CHALDEAN = ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"]

# Pancha-vargiya bala maxima and the share given for own / friend / neutral / enemy lords:
# full, three-quarters (padona), half (dala), quarter (pada), Tajika Neelakanthi Samjna-tantra.
PVB_MAX = {"kshetra": 30.0, "uchcha": 20.0, "hadda": 15.0, "drekkana": 10.0, "navamsa": 5.0}
REL_SHARE = {"own": 1.0, "friend": 0.75, "neutral": 0.5, "enemy": 0.25}
# Friendship used for Pancha-vargiya bala. "tajika": by mutual position in the varsha chart
# (3/5/9/11 apart friends, 1/4/7/10 enemies, 2/6/8/12 neutral), as Neelakanthi defines Tajika
# friendship; "naisargika": BPHS natural friendship.
PVB_RELATIONSHIP = "tajika"

# Houses (from the aspecting planet) that carry a Tajika aspect, with their nature (Neelakanthi)
TAJIKA_SIGN_ASPECT = {1: ("conjunction", "Pratyaksha shatru"), 7: ("opposition", "Pratyaksha shatru"),
                      4: ("square", "Gupta shatru"), 10: ("square", "Gupta shatru"),
                      5: ("trine", "Pratyaksha mitra"), 9: ("trine", "Pratyaksha mitra"),
                      3: ("sextile", "Gupta mitra"), 11: ("sextile", "Gupta mitra")}
ANGLE_HOUSES = {0: {1}, 60: {3, 11}, 90: {4, 10}, 120: {5, 9}, 180: {7}}

# Muntha judgement by house from the Varsha lagna (Tajika Neelakanthi / B.V. Raman)
MUNTHA_GOOD = {1, 2, 3, 5, 9, 10, 11}

# Mudda dasha: Vimshottari compressed so that 120 years -> 360 Tajika days (3 days a year)
MUDDA_DAYS = {p: DASHA_YEARS[p] * 3 for p in DASHA_ORDER}
# Remainder of (janma nakshatra no. + completed years - 2) / 9 -> first lord (B.V. Raman,
# Varshaphala; Tajika Neelakanthi). Equals the natal nakshatra lord advanced one lord per year.
MUDDA_REMAINDER = {1: "Sun", 2: "Moon", 3: "Mars", 4: "Rahu", 5: "Jupiter", 6: "Saturn",
                   7: "Mercury", 8: "Ketu", 0: "Venus"}

# Sahams: (name, A, B, C, reversed by night) for A - B + C. PVR Narasimha Rao "Vedic Astrology:
# An Integrated Approach" ch. 32 (= the JHora list) cross-checked with B.V. Raman, Varshaphala
# ch. 8. "Hn" = Lagna + 30°(n-1) (JHora house point), "Ln" = lord of the nth sign.
# Mrityu and Apamrityu are deliberately omitted. Santana (progeny) is not in the JHora list; it
# uses the Prasava (childbirth) saham of Neelakanthi's longer list, Jupiter - Mercury + Lagna
# (single source, unverified against a second one).
SAHAMS = [
    ("Punya", "Moon", "Sun", "Asc", True),
    ("Vidya", "Sun", "Moon", "Asc", True),
    ("Yasha", "Jupiter", "Punya", "Asc", True),
    ("Mitra", "Jupiter", "Punya", "Venus", True),
    ("Mahatmya", "Punya", "Mars", "Asc", True),
    ("Asha", "Saturn", "Mars", "Asc", True),
    ("Samartha", "Mars", "LL", "Asc", True),
    ("Bhratri", "Jupiter", "Saturn", "Asc", False),
    ("Gaurava", "Jupiter", "Moon", "Sun", True),
    ("Pitri", "Saturn", "Sun", "Asc", True),
    ("Rajya", "Saturn", "Sun", "Asc", True),
    ("Matri", "Moon", "Venus", "Asc", True),
    ("Putra", "Jupiter", "Moon", "Asc", True),
    ("Jeeva", "Saturn", "Jupiter", "Asc", True),
    ("Karma", "Mars", "Mercury", "Asc", True),
    ("Roga", "Asc", "Moon", "Asc", False),
    ("Kali", "Jupiter", "Mars", "Asc", True),
    ("Shastra", "Jupiter", "Saturn", "Mercury", True),
    ("Bandhu", "Mercury", "Moon", "Asc", True),
    ("Paradesha", "H9", "L9", "Asc", False),
    ("Artha", "H2", "L2", "Asc", False),
    ("Paradara", "Venus", "Sun", "Asc", True),
    ("Vanik", "Moon", "Mercury", "Asc", True),
    ("Karyasiddhi", "Saturn", "Sun", "SunLord", True),     # night: Saturn - Moon + Moon-sign lord
    ("Vivaha", "Venus", "Saturn", "Asc", True),
    ("Santana", "Jupiter", "Mercury", "Asc", True),
    ("Santapa", "Saturn", "Moon", "H6", True),
    ("Shraddha", "Venus", "Mars", "Asc", True),
    ("Preeti", "Shastra", "Punya", "Asc", True),
    ("Jadya", "Mars", "Saturn", "Mercury", True),
    ("Vyapara", "Mars", "Saturn", "Asc", False),
    ("Shatru", "Mars", "Saturn", "Asc", True),
    ("Jalapatana", "Cancer15", "Saturn", "Asc", True),
    ("Bandhana", "Punya", "Saturn", "Asc", True),
    ("Labha", "H11", "L11", "Asc", False),
]
_POINT_LABEL = {"Asc": "Lagna", "LL": "Lagna lord", "H2": "2nd house", "L2": "2nd lord",
                "H6": "6th house", "H9": "9th house", "L9": "9th lord", "H11": "11th house",
                "L11": "11th lord", "SunLord": "Sun-sign lord", "MoonLord": "Moon-sign lord",
                "Cancer15": "15° Cancer"}


# ---------------------------------------------------------------- place / time helpers
def _place_spec(inp: BirthInput, place: dict | None) -> dict:
    if not place:
        return {"lat": inp.lat, "lon": inp.lon, "tz": inp.tz, "offset": inp.offset,
                "label": inp.place or ""}
    tz, off = place.get("tz"), place.get("offset")
    if tz is None and off is None:
        tz, off = inp.tz, inp.offset
    return {"lat": float(place["lat"]), "lon": float(place["lon"]), "tz": tz,
            "offset": None if off is None else float(off), "label": place.get("label") or ""}


def _input_at(jd: float, inp: BirthInput, spec: dict) -> BirthInput:
    """BirthInput for the exact instant jd at the given place (used for charts and fmt_jd)."""
    utc = E.utc_from_jd(jd)
    if spec["offset"] is not None:
        local = (utc + timedelta(hours=spec["offset"])).replace(tzinfo=None)
    else:
        local = utc.astimezone(ZoneInfo(spec["tz"])).replace(tzinfo=None)
    b = BirthInput(inp.name, inp.gender, local, spec["lat"], spec["lon"], spec["tz"],
                   spec["offset"], spec["label"])
    b.jd, b.utc = jd, utc            # keep the exact instant (no DST-fold / rounding drift)
    return b


def _utc_offset_hours(jd: float, spec: dict) -> float:
    if spec["offset"] is not None:
        return spec["offset"]
    off = E.utc_from_jd(jd).astimezone(ZoneInfo(spec["tz"])).utcoffset()
    return off.total_seconds() / 3600.0


def _sun_return(target: float, jd0: float, aya: str) -> float:
    """Newton iteration for the instant the sidereal Sun is at `target` near jd0."""
    jd = jd0
    for _ in range(30):
        b = E.calc_body(jd, "Sun", aya)
        step = E.angdiff(b.lon, target) / b.speed
        jd -= step
        if abs(step) < 1e-9:
            break
    return jd


def _pravesha(inp: BirthInput, chart: SiderealChart, year: int, spec: dict) -> tuple[float, int]:
    """(jd, completed years) of the sidereal solar return whose local date falls in `year`."""
    natal = chart.bodies["Sun"].lon
    n = year - inp.local_dt.year
    jd = inp.jd
    for _ in range(4):
        if n < 0:
            raise ValueError("The year precedes the birth year.")
        jd = _sun_return(natal, inp.jd + n * SIDEREAL_YEAR, chart.ayanamsa) if n else inp.jd
        y = int(_input_at(jd, inp, spec).fmt_jd(jd)[:4])
        if y == year:
            break
        n += year - y
    return jd, n


# ---------------------------------------------------------------- chart rows
def _points(ch: SiderealChart) -> dict:
    pts = {"Lagna": {"lon": round(ch.asc, 6), "sign": ch.lagna_sign}}
    for p, b in ch.bodies.items():
        pts[p] = {"lon": round(b.lon, 6), "sign": sign_of(b.lon), "retro": b.retro}
    return pts


def _planet_rows(ch: SiderealChart) -> list[dict]:
    rows = []
    for name in ["Lagna"] + GRAHAS:
        lon = ch.lon(name)
        nk, pd = nakshatra_of(lon)
        retro = False if name == "Lagna" else (name in ("Rahu", "Ketu") or ch.bodies[name].retro)
        rows.append({"name": name, "lon": round(lon, 6), "sign": sign_of(lon),
                     "sign_name": SIGNS[sign_of(lon)], "dms": dms(deg_in_sign(lon)),
                     "nakshatra": NAKSHATRAS[nk], "pada": pd, "house": ch.house(name),
                     "retro": retro})
    return rows


def _cusps(ch: SiderealChart) -> list[dict]:
    return [{"house": i + 1, "lon": round(c, 6), "sign": SIGNS[sign_of(c)], "dms": dms(deg_in_sign(c))}
            for i, c in enumerate(ch.cusps)]


# ---------------------------------------------------------------- Pancha-vargiya bala
def hadda_lord(lon: float) -> str:
    s, d = sign_of(lon), deg_in_sign(lon)
    for lord, lim in HADDA[s]:
        if d < lim:
            return lord
    return HADDA[s][-1][0]


def tajika_drekkana_lord(lon: float) -> str:
    return CHALDEAN[(sign_of(lon) * 3 + int(deg_in_sign(lon) // 10)) % 7]


def uchcha_bala(p: str, lon: float) -> float:
    """20 at deep exaltation, 0 at deep debilitation, 1 unit per 9°."""
    s, d = DEBILITATION[p]
    return abs(E.angdiff(lon, s * 30 + d)) / 9.0


def _relation(p: str, q: str, signs: dict[str, int]) -> str:
    if p == q:
        return "own"
    if PVB_RELATIONSHIP == "naisargika":
        return {1: "friend", 0: "neutral", -1: "enemy"}[natural_relation(p, q)]
    h = (signs[q] - signs[p]) % 12 + 1
    if h in (3, 5, 9, 11):
        return "friend"
    if h in (1, 4, 7, 10):
        return "enemy"
    return "neutral"


def _grade(v: float) -> str:
    return "Poorna (full)" if v >= 15 else "Madhya (medium)" if v >= 10 else \
        "Alpa (little)" if v >= 5 else "Heena (weak)"


def pancha_vargiya_bala(ch: SiderealChart) -> list[dict]:
    signs = {p: ch.sign(p) for p in SEVEN}
    rows = []
    for p in SEVEN:
        lon = ch.bodies[p].lon
        lords = {"kshetra": SIGN_LORD[sign_of(lon)], "hadda": hadda_lord(lon),
                 "drekkana": tajika_drekkana_lord(lon), "navamsa": SIGN_LORD[varga_sign(lon, 9)]}
        rels = {k: _relation(p, q, signs) for k, q in lords.items()}
        vals = {k: PVB_MAX[k] * REL_SHARE[rels[k]] for k in lords}
        vals["uchcha"] = uchcha_bala(p, lon)
        total = sum(vals.values())
        rows.append({"planet": p, **{k: round(vals[k], 2) for k in PVB_MAX},
                     "total": round(total, 2), "vimshopaka": round(total / 4.0, 2),
                     "grade": _grade(total / 4.0), "lords": lords, "relations": rels})
    return rows


# ---------------------------------------------------------------- Tajika aspects & yogas
def _house_between(ch: SiderealChart, a: str, b: str) -> int:
    return (ch.sign(b) - ch.sign(a)) % 12 + 1


def _ithasala_kind(rel: dict | None, h: int) -> str | None:
    """Vartamana / Poorna / Bhavishyat Ithasala, Ishrafa, or None (no valid Tajika contact)."""
    if not rel:
        return None
    consistent = h in ANGLE_HOUSES[rel["angle"]]
    if rel["applying"]:
        if not consistent:
            return "Bhavishyat"          # perfects only after the faster planet changes sign
        return "Poorna" if rel["gap"] <= 1.0 else "Vartamana"
    return "Ishrafa" if consistent else None


def tajika_aspects(ch: SiderealChart) -> list[dict]:
    out = []
    for i, a in enumerate(SEVEN):
        for b in SEVEN[i + 1:]:
            h = _house_between(ch, a, b)
            rel = tajika_relation(a, b, ch.bodies)
            if h not in TAJIKA_SIGN_ASPECT and rel is None:
                continue
            asp, nature = TAJIKA_SIGN_ASPECT.get(h, (None, None))
            row = {"a": a, "b": b, "house": h, "sign_aspect": asp, "nature": nature,
                   "friendly": None if nature is None else nature.endswith("mitra"),
                   "aspect": None, "angle": None, "gap": None, "orb": None, "type": None,
                   "applying": None, "days_to_exact": None,
                   "ithasala": _ithasala_kind(rel, h)}
            if rel:
                row.update(rel)
            out.append(row)
    return out


def _faster(ch: SiderealChart, a: str, b: str) -> str:
    return a if abs(ch.bodies[a].speed) >= abs(ch.bodies[b].speed) else b


def tajika_yogas(ch: SiderealChart, aspects: list[dict]) -> list[dict]:
    yogas: list[dict] = []
    rel = {(r["a"], r["b"]): r for r in aspects}
    rel.update({(r["b"], r["a"]): r for r in aspects})

    def kind(a, b):
        r = rel.get((a, b))
        return r["ithasala"] if r else None

    def is_itha(a, b):
        return kind(a, b) in ("Vartamana", "Poorna", "Bhavishyat")

    def no_aspect(a, b):
        return _house_between(ch, a, b) not in TAJIKA_SIGN_ASPECT

    houses = {p: ch.house(p) for p in SEVEN}
    if all(h in (1, 2, 4, 5, 7, 8, 10, 11) for h in houses.values()):
        yogas.append({"name": "Ikkavala", "planets": list(SEVEN), "description": tr(
            "All seven planets are in kendras and panapharas (houses 1, 2, 4, 5, 7, 8, 10, 11): gains, comfort and good fortune through the year.")})
    if all(h in (3, 6, 9, 12) for h in houses.values()):
        yogas.append({"name": "Induvara", "planets": list(SEVEN), "description": tr(
            "All seven planets are in apoklimas (houses 3, 6, 9, 12): worries, disappointments and ill health.")})

    pairs = [(r["a"], r["b"]) for r in aspects]
    itha = [(a, b) for a, b in pairs if is_itha(a, b)]
    for a, b in pairs:
        r = rel[(a, b)]
        if is_itha(a, b):
            f = _faster(ch, a, b)
            s = b if f == a else a
            yogas.append({"name": "Ithasala", "planets": [f, s], "kind": r["ithasala"], "description": tr(
                "{f} applies to {s} by {asp} ({k} Ithasala, {gap}° to exact within an orb of {orb}°): the matters they rule come together this year.",
                f=f, s=s, asp=tr(r["aspect"]), k=r["ithasala"], gap=r["gap"], orb=r["orb"])})
        elif r["ithasala"] == "Ishrafa":
            yogas.append({"name": "Ishrafa", "planets": [a, b], "description": tr(
                "{a} and {b} have just separated from their {asp} ({gap}° past exact): what they promise slips away or belongs to the past.",
                a=a, b=b, asp=tr(r["aspect"]), gap=r["gap"])})

    # Nakta (transfer of light) and Yamaya (collection of light) between unconnected planets
    for i, a in enumerate(SEVEN):
        for b in SEVEN[i + 1:]:
            if not no_aspect(a, b):
                continue
            for c in SEVEN:
                if c in (a, b) or not (is_itha(c, a) and is_itha(c, b)):
                    continue
                vc, va, vb = (abs(ch.bodies[x].speed) for x in (c, a, b))
                if vc > va and vc > vb:
                    yogas.append({"name": "Nakta", "planets": [a, b, c], "description": tr(
                        "{a} and {b} do not aspect each other, but the faster {c} is in Ithasala with both and carries the light between them: success through an intermediary.",
                        a=a, b=b, c=c)})
                elif vc < va and vc < vb:
                    yogas.append({"name": "Yamaya", "planets": [a, b, c], "description": tr(
                        "{a} and {b} do not aspect each other, but both apply to the slower {c}, which collects their light: success through a third person or a senior.",
                        a=a, b=b, c=c)})

    moon_itha = [p for p in SEVEN if p != "Moon" and is_itha("Moon", p)]
    signs = {p: ch.sign(p) for p in SEVEN}
    sun = ch.bodies["Sun"].lon
    for a, b in itha:
        f = _faster(ch, a, b)
        s = b if f == a else a
        # Kamboola: the Moon applies to one of an Ithasala pair
        xs = [x for x in (f, s) if x in moon_itha] if "Moon" not in (a, b) else []
        if xs:
            yogas.append({"name": "Kamboola", "planets": [f, s, "Moon"], "description": tr(
                "The Moon applies to {x} while {f} and {s} are in Ithasala: the Moon reinforces the Ithasala and the matter is achieved (Kamboola).",
                x=terms(xs), f=f, s=s)})
        # Manau: Mars or Saturn intercepts the faster planet by an inimical aspect
        for m in ("Mars", "Saturn"):
            if m in (a, b):
                continue
            rm = rel.get((f, m))
            if rm and rm["applying"] and rm["angle"] in (0, 90, 180) and is_itha(f, m):
                yogas.append({"name": "Manau", "planets": [f, s, m], "description": tr(
                    "{m} meets {f} by {asp} and cuts off the Ithasala between {f} and {s}: obstruction from rivals, or delays (Manau).",
                    m=m, f=f, s=s, asp=tr(rm["aspect"]))})
        # Radda: a party to the Ithasala is retrograde, combust or debilitated
        conds = []
        for p in (f, s):
            if p not in ("Sun", "Moon") and ch.bodies[p].retro:
                conds.append(tr("{p} is retrograde", p=p))
            if p != "Sun" and combustion(p, ch.bodies[p].lon, sun, ch.bodies[p].retro)[0]:
                conds.append(tr("{p} is combust", p=p))
            if DEBILITATION[p][0] == signs[p]:
                conds.append(tr("{p} is debilitated", p=p))
        if conds:
            yogas.append({"name": "Radda", "planets": [f, s], "description": tr(
                "The Ithasala between {f} and {s} is spoiled because {c}: the promise is withdrawn midway (Radda).",
                f=f, s=s, c=", ".join(conds))})
    # Khallasara: the Moon makes no Tajika contact within orbs (Shunya-marga)
    moon_void = not any(rel.get(("Moon", p)) and rel[("Moon", p)]["type"] for p in SEVEN if p != "Moon")
    if moon_void and itha:
        yogas.append({"name": "Khallasara", "planets": ["Moon"], "description": tr(
            "The Moon makes no Tajika aspect within orbs with any planet (Shunya-marga), so the Ithasalas of the year bear little fruit (Khallasara).")})
    return yogas


# ---------------------------------------------------------------- office-bearers & year lord
def _year_lord(bearers: list[dict], pvb: dict[str, float], ch: SiderealChart,
               muntha_lord: str, dr_pati: str) -> tuple[str, str]:
    offices: dict[str, list[str]] = {}
    for b in bearers:
        offices.setdefault(b["planet"], []).append(b["role"])
    hfrom = {p: (ch.lagna_sign - ch.sign(p)) % 12 + 1 for p in offices}   # lagna counted from p
    aspecting = [p for p in offices if hfrom[p] in TAJIKA_SIGN_ASPECT]
    if not aspecting:
        return muntha_lord, tr(
            "None of the five office-bearers aspects the Varsha lagna, so the Muntha lord {p} becomes the year lord (classical fallback).",
            p=muntha_lord)
    best = max(pvb[p] for p in aspecting)
    top = [p for p in aspecting if best - pvb[p] < 0.005]
    tie = ""
    if len(top) > 1:
        tie = " " + tr("{n} candidates were equally strong; the tie goes to the one holding more offices, then the Dina-ratri pati, then the Muntha lord.", n=len(top))
        top.sort(key=lambda p: (-len(offices[p]), p != dr_pati, p != muntha_lord))
    p = top[0]
    asp = TAJIKA_SIGN_ASPECT[hfrom[p]][0]
    if len(aspecting) == 1:
        reason = tr("{p} ({roles}) is the only office-bearer that aspects the Varsha lagna ({asp}), so it becomes the year lord; its vimshopaka strength is {v} of 20.",
                    p=p, roles=terms(offices[p]), asp=tr(asp), v=pvb[p])
    else:
        reason = tr("{p} ({roles}) has the highest Pancha-vargiya bala ({v} of 20) among the office-bearers that aspect the Varsha lagna ({asp}), so it becomes the year lord.",
                    p=p, roles=terms(offices[p]), v=pvb[p], asp=tr(asp))
    return p, reason + tie


# ---------------------------------------------------------------- Sahams
def _between(x: float, b: float, a: float) -> bool:
    """True if x lies on the zodiacal arc from b forward to a."""
    return (x - b) % 360.0 <= (a - b) % 360.0


def sahams(ch: SiderealChart, day: bool) -> list[dict]:
    asc = ch.asc
    ls = ch.lagna_sign
    pts = {p: ch.bodies[p].lon for p in SEVEN}
    pts.update({"Asc": asc, "LL": ch.bodies[SIGN_LORD[ls]].lon,
                "H2": norm(asc + 30), "H6": norm(asc + 150), "H9": norm(asc + 240),
                "H11": norm(asc + 300),
                "L2": ch.bodies[SIGN_LORD[(ls + 1) % 12]].lon,
                "L9": ch.bodies[SIGN_LORD[(ls + 8) % 12]].lon,
                "L11": ch.bodies[SIGN_LORD[(ls + 10) % 12]].lon,
                "SunLord": ch.bodies[SIGN_LORD[ch.sign("Sun")]].lon,
                "MoonLord": ch.bodies[SIGN_LORD[ch.sign("Moon")]].lon,
                "Cancer15": 105.0})
    lagna_lord = SIGN_LORD[ls]
    lab = lambda k: _POINT_LABEL.get(k, k)
    out = []
    for name, a, b, c, rev in SAHAMS:
        if name == "Samartha" and lagna_lord == "Mars":
            a, b = "Jupiter", "Mars"                    # Mars rules the lagna: Jupiter - Mars
        if name == "Karyasiddhi" and not day:
            b, c = "Moon", "MoonLord"                   # night: Saturn - Moon + Moon-sign lord
        elif rev and not day:
            a, b = b, a
        A, B, C = pts[a], pts[b], pts[c]
        lon = A - B + C
        if not _between(asc, B, A):                     # Neelakanthi: add a sign if the Lagna
            lon += 30.0                                 # is not between B and A (zodiacally)
        lon = norm(lon)
        pts[name] = lon
        out.append({"name": name, "lon": round(lon, 6), "sign": SIGNS[sign_of(lon)],
                    "sign_index": sign_of(lon), "dms": dms(deg_in_sign(lon)),
                    "house": (sign_of(lon) - ls) % 12 + 1,
                    "formula": f"{lab(a)} - {lab(b)} + {lab(c)}"})
    return out


# ---------------------------------------------------------------- annual dashas
def mudda_start_lord(natal_moon: float, age: int) -> str:
    n = int(norm(natal_moon) // NAK_SPAN) + 1          # janma nakshatra counted from Ashwini
    return MUDDA_REMAINDER[(n + age - 2) % 9]


def mudda_dasha(natal_moon: float, age: int, vp: float, year_days: float, fmt) -> list[dict]:
    """Vimshottari compressed into the Tajika year (scaled 360-day year). As with natal
    Vimshottari, the first lord runs with the balance left by the natal Moon in its nakshatra;
    after the ninth period the cycle restarts with the first lord, whose opening part closes the
    year. Periods (and antardashas) are clipped to [this, next Varsha Pravesha)."""
    frac = (norm(natal_moon) % NAK_SPAN) / NAK_SPAN
    lord0 = mudda_start_lord(natal_moon, age)
    scale = year_days / 360.0
    end_year = vp + year_days
    i0 = DASHA_ORDER.index(lord0)
    t = vp - frac * MUDDA_DAYS[lord0] * scale       # virtual start of the first period
    out = []
    for k in range(10):                             # 9 lords + the first lord again
        lord = DASHA_ORDER[(i0 + k) % 9]
        dur = MUDDA_DAYS[lord] * scale
        s, e = max(t, vp), min(t + dur, end_year)
        if e - s > 1e-7:
            j0, ct, kids = DASHA_ORDER.index(lord), t, []
            for m in range(9):
                sub = DASHA_ORDER[(j0 + m) % 9]
                cd = dur * DASHA_YEARS[sub] / 120.0
                cs, ce = max(ct, s), min(ct + cd, e)
                if ce - cs > 1e-7:
                    kids.append({"lord": sub, "start": fmt(cs), "end": fmt(ce),
                                 "days": round(ce - cs, 3)})
                ct += cd
            out.append({"lord": lord, "start": fmt(s), "end": fmt(e), "days": round(e - s, 3),
                        "full_days": round(dur, 3), "children": kids})
        t += dur
    return out


def patyayini_dasha(ch: SiderealChart, vp: float, year_days: float, fmt) -> list[dict]:
    """Krishamsha (degrees in sign) of Lagna + 7 planets, ascending; patyamsha = difference from
    the previous one; periods proportional to patyamsha, summing to the year."""
    ents = [("Lagna", deg_in_sign(ch.asc))] + [(p, deg_in_sign(ch.bodies[p].lon)) for p in SEVEN]
    ents.sort(key=lambda e: e[1])
    top = ents[-1][1] or 1e-9
    out, t, prev = [], vp, 0.0
    for p, k in ents:
        days = (k - prev) / top * year_days
        out.append({"planet": p, "start": fmt(t), "end": fmt(t + days), "days": round(days, 3),
                    "krishamsha": round(k, 4), "patyamsha": round(k - prev, 4)})
        t += days
        prev = k
    return out


# ---------------------------------------------------------------- public: Varshaphal
def varshaphal(inp: BirthInput, chart: SiderealChart, year: int, place: dict | None = None) -> dict:
    spec = _place_spec(inp, place)
    vp, age = _pravesha(inp, chart, year, spec)
    nxt = _sun_return(chart.bodies["Sun"].lon, vp + SIDEREAL_YEAR, chart.ayanamsa)
    year_days = nxt - vp
    vinp = _input_at(vp, inp, spec)
    ch = SiderealChart(vinp, ayanamsa=chart.ayanamsa, node=chart.node, include_outer=False)
    fmt = vinp.fmt_jd
    day = ch.is_day_birth()
    L = ch.lagna_sign

    # Muntha and the five office-bearers
    m_sign = (chart.lagna_sign + age) % 12
    m_house = (m_sign - L) % 12 + 1
    m_lord = SIGN_LORD[m_sign]
    dr_pati = SIGN_LORD[ch.sign("Sun" if day else "Moon")]
    bearers = [
        {"role": "Janma lagna lord", "planet": SIGN_LORD[chart.lagna_sign]},
        {"role": "Varsha lagna lord", "planet": SIGN_LORD[L]},
        {"role": "Muntha lord", "planet": m_lord},
        {"role": "Tri-rashi pati", "planet": (TRI_RASHI_DAY if day else TRI_RASHI_NIGHT)[L]},
        {"role": "Dina-ratri pati", "planet": dr_pati},
    ]
    pvb = pancha_vargiya_bala(ch)
    pvb_map = {r["planet"]: r["vimshopaka"] for r in pvb}
    yl, reason = _year_lord(bearers, pvb_map, ch, m_lord, dr_pati)
    aspects = tajika_aspects(ch)
    yogas = tajika_yogas(ch, aspects)
    sah = sahams(ch, day)
    natal_moon = chart.bodies["Moon"].lon
    mudda = mudda_dasha(natal_moon, age, vp, year_days, fmt)
    paty = patyayini_dasha(ch, vp, year_days, fmt)
    nak = int(norm(natal_moon) // NAK_SPAN)

    sun = ch.bodies["Sun"].lon
    notes = [
        tr("Varsha Pravesha: the sidereal Sun returns to its natal position, {d} {sg}, at {t}.",
           d=dms(deg_in_sign(sun)), sg=SIGNS[sign_of(sun)], t=fmt(vp)),
        tr("Day chart: the Varsha Pravesha falls between sunrise and sunset.") if day else
        tr("Night chart: the Varsha Pravesha falls between sunset and sunrise."),
        tr("This Tajika year lasts {d} days, until the next Varsha Pravesha on {t}.",
           d=round(year_days, 4), t=fmt(nxt)),
        (tr("Muntha is in house {h} ({sg}), a favourable position for the year.", h=m_house, sg=SIGNS[m_sign])
         if m_house in MUNTHA_GOOD else
         tr("Muntha is in house {h} ({sg}), a difficult position that calls for care this year.", h=m_house, sg=SIGNS[m_sign])),
        tr("Pancha-vargiya bala uses Tajika friendship (3, 5, 9 or 11 signs apart: friends; 1, 4, 7 or 10 apart: enemies; otherwise neutral), the Tajika haddas and the Tajika (Chaldean) drekkana lords."),
        tr("Sahams are computed in the Varsha chart; a house point is the Lagna degree plus 30° per house, and 30° is added when the Lagna does not fall between the subtracted and the added points."),
        tr("Mudda dasha opens with {l} (janma nakshatra {n} advanced by {a} completed years), running only its balance, in the same proportion as the natal Moon's remaining part of {n}; the opening part of {l} closes the year.",
           l=mudda[0]["lord"], n=NAKSHATRAS[nak], a=age),
    ]
    return {
        "year": year, "age": age, "moment": fmt(vp), "place": spec["label"],
        "jd": round(vp, 6), "day_chart": day, "next_pravesha": fmt(nxt),
        "year_days": round(year_days, 5),
        "points": _points(ch), "planets": _planet_rows(ch), "cusps": _cusps(ch),
        "muntha": {"sign": m_sign, "sign_name": SIGNS[m_sign], "house": m_house, "lord": m_lord},
        "office_bearers": bearers,
        "pvb": pvb,
        "year_lord": {"planet": yl, "reason": reason},
        "tajika_aspects": aspects, "tajika_yogas": yogas,
        "sahams": sah,
        "mudda_dasha": mudda, "patyayini_dasha": paty,
        "notes": notes,
    }


# ---------------------------------------------------------------- public: Tithi Pravesha
def _elongation(jd: float) -> float:
    return norm(E.calc_body(jd, "Moon", None).lon - E.calc_body(jd, "Sun", None).lon)


def _elongation_returns(t0: float, t1: float, target: float) -> list[float]:
    """All instants in [t0, t1] when the Moon-Sun elongation equals target."""
    f = lambda t: E.angdiff(_elongation(t), target)
    out, t, prev = [], t0, f(t0)
    while t < t1:
        t2 = t + 1.0
        cur = f(t2)
        if prev <= 0 < cur and cur - prev < 90:       # elongation grows ~12°/day
            out.append(E.find_crossing(f, t, t2, tol=1e-8))
        t, prev = t2, cur
    return out


def tithi_pravesha(inp: BirthInput, chart: SiderealChart, year: int, place: dict | None = None) -> dict:
    spec = _place_spec(inp, place)
    aya = chart.ayanamsa
    natal_el = norm(chart.bodies["Moon"].lon - chart.bodies["Sun"].lon)
    natal_sun_sign = sign_of(chart.bodies["Sun"].lon)
    sr, age = _pravesha(inp, chart, year, spec)
    cands = _elongation_returns(sr - 45.0, sr + 45.0, natal_el)
    in_sign = [t for t in cands if sign_of(E.calc_body(t, "Sun", aya).lon) == natal_sun_sign]
    tp = min(in_sign or cands, key=lambda t: abs(t - sr))
    tinp = _input_at(tp, inp, spec)
    ch = SiderealChart(tinp, ayanamsa=aya, node=chart.node, include_outer=False)
    fmt = tinp.fmt_jd
    sunrise = E.sun_times(tp, spec["lat"], spec["lon"])["sunrise"]
    wd = E.weekday_of_jd(sunrise + _utc_offset_hours(sunrise, spec) / 24.0)
    el = _elongation(tp)
    ti = int(el // 12) % 30
    sun = ch.bodies["Sun"].lon
    notes = [
        tr("Tithi Pravesha: the Moon is again {el}° ahead of the Sun, as at birth ({t}), with the Sun in {sg}, at {m}.",
           el=round(natal_el, 4), t=TITHIS[ti], sg=SIGNS[sign_of(sun)], m=fmt(tp)),
        tr("The Vedic day began at sunrise, {sr}, on a {wd}, so {p} rules the year (Sanjay Rath).",
           sr=fmt(sunrise), wd=WEEKDAYS[wd], p=WEEKDAY_LORD[wd]),
        tr("This is a Local Tithi Pravesha cast for the native's place of residence.") if place else
        tr("The chart is cast for the birth place."),
    ]
    if not in_sign:
        notes.append(tr("No return of the natal elongation falls while the Sun is in its natal sign this year; the one nearest the solar return is used."))
    return {
        "year": year, "age": age, "moment": fmt(tp), "place": spec["label"], "jd": round(tp, 6),
        "solar_return": fmt(sr), "local": bool(place),
        "points": _points(ch), "planets": _planet_rows(ch),
        "weekday": WEEKDAYS[wd], "sunrise": fmt(sunrise), "year_lord": WEEKDAY_LORD[wd],
        "tithi": {"name": TITHIS[ti], "index": ti + 1,
                  "paksha": "Shukla" if ti < 15 else "Krishna",
                  "elongation": round(el, 6), "natal_elongation": round(natal_el, 6),
                  "fraction_elapsed": round((el % 12.0) / 12.0, 6)},
        "notes": notes,
    }

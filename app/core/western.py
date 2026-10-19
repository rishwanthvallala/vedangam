"""Western (tropical) astrology: positions, houses, essential dignities, aspects,
patterns, balances, chart shape, moon phase, transits, progressions, solar return."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from . import ephemeris as E
from .constants import ELEMENT, MODALITY, SIGNS, deg_in_sign, dms, norm, sign_of
from .ephemeris import angdiff
from ..i18n import tr

BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus",
          "Neptune", "Pluto", "Chiron", "North Node"]
PERSONAL = {"Sun", "Moon", "Mercury", "Venus", "Mars"}

RULER_TRAD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars",
              "Jupiter", "Saturn", "Saturn", "Jupiter"]
RULER_MODERN = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Pluto",
                "Jupiter", "Saturn", "Uranus", "Neptune"]
EXALT = {"Sun": 0, "Moon": 1, "Mercury": 5, "Venus": 11, "Mars": 9, "Jupiter": 3,
         "Saturn": 6}
TERMS = [  # Egyptian terms (planet, end degree)
    [("Jupiter", 6), ("Venus", 12), ("Mercury", 20), ("Mars", 25), ("Saturn", 30)],
    [("Venus", 8), ("Mercury", 14), ("Jupiter", 22), ("Saturn", 27), ("Mars", 30)],
    [("Mercury", 6), ("Jupiter", 12), ("Venus", 17), ("Mars", 24), ("Saturn", 30)],
    [("Mars", 7), ("Venus", 13), ("Mercury", 19), ("Jupiter", 26), ("Saturn", 30)],
    [("Jupiter", 6), ("Venus", 11), ("Saturn", 18), ("Mercury", 24), ("Mars", 30)],
    [("Mercury", 7), ("Venus", 17), ("Jupiter", 21), ("Mars", 28), ("Saturn", 30)],
    [("Saturn", 6), ("Mercury", 14), ("Jupiter", 21), ("Venus", 28), ("Mars", 30)],
    [("Mars", 7), ("Venus", 11), ("Mercury", 19), ("Jupiter", 24), ("Saturn", 30)],
    [("Jupiter", 12), ("Venus", 17), ("Mercury", 21), ("Saturn", 26), ("Mars", 30)],
    [("Mercury", 7), ("Jupiter", 14), ("Venus", 22), ("Saturn", 26), ("Mars", 30)],
    [("Mercury", 7), ("Venus", 13), ("Jupiter", 20), ("Mars", 25), ("Saturn", 30)],
    [("Venus", 12), ("Jupiter", 16), ("Mercury", 19), ("Mars", 28), ("Saturn", 30)],
]
FACE_SEQ = ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"]
TRIPLICITY = {"Fire": ("Sun", "Jupiter", "Saturn"), "Earth": ("Venus", "Moon", "Mars"),
              "Air": ("Saturn", "Mercury", "Jupiter"), "Water": ("Venus", "Mars", "Moon")}

ASPECTS = [  # name, angle, orb (major luminaries get +2), symbol
    ("Conjunction", 0, 8, "☌"), ("Opposition", 180, 8, "☍"), ("Trine", 120, 7, "△"),
    ("Square", 90, 7, "□"), ("Sextile", 60, 5, "⚹"), ("Quincunx", 150, 3, "⚻"),
    ("Semi-sextile", 30, 2, "⚺"), ("Semi-square", 45, 2, "∠"),
    ("Sesquiquadrate", 135, 2, "⚼"), ("Quintile", 72, 1.5, "Q"), ("Biquintile", 144, 1.5, "bQ"),
]
HARMONIOUS = {"Trine", "Sextile", "Quintile", "Biquintile", "Semi-sextile"}
CHALLENGING = {"Square", "Opposition", "Quincunx", "Semi-square", "Sesquiquadrate"}


def _positions(jd, sidereal, node):
    out = {}
    for b in BODIES:
        nm = "North Node" if b == "North Node" else b
        body = E.calc_body(jd, nm, sidereal, node)
        out[b] = body
    sn = E.calc_body(jd, "South Node", sidereal, node)
    out["South Node"] = sn
    out["Lilith"] = E.calc_body(jd, "Lilith", sidereal)
    return out


def essential_dignity(p: str, lon: float, day: bool) -> dict:
    s, d = sign_of(lon), deg_in_sign(lon)
    res = {"domicile": False, "exaltation": False, "detriment": False, "fall": False,
           "triplicity": False, "term": None, "face": None, "score": 0}
    if p not in EXALT:
        rul = RULER_MODERN[s] == p
        det = RULER_MODERN[(s + 6) % 12] == p
        res.update({"domicile": rul, "detriment": det})
        res["label"] = "Domicile" if rul else ("Detriment" if det else "—")
        return res
    sc = 0
    if RULER_TRAD[s] == p:
        res["domicile"] = True
        sc += 5
    if EXALT[p] == s:
        res["exaltation"] = True
        sc += 4
    tr = TRIPLICITY[ELEMENT[s]]
    if (tr[0] if day else tr[1]) == p:
        res["triplicity"] = True
        sc += 3
    term = next(pl for pl, end in TERMS[s] if d < end)
    res["term"] = term
    if term == p:
        sc += 2
    face = FACE_SEQ[(s * 3 + int(d // 10)) % 7]
    res["face"] = face
    if face == p:
        sc += 1
    if RULER_TRAD[(s + 6) % 12] == p:
        res["detriment"] = True
        sc -= 5
    if (EXALT[p] + 6) % 12 == s:
        res["fall"] = True
        sc -= 4
    if sc == 0 and not any(res[k] for k in ("domicile", "exaltation", "triplicity")) and \
            term != p and face != p:
        res["peregrine"] = True
        sc = -5
    res["score"] = sc
    lbl = [k.capitalize() for k in ("domicile", "exaltation", "triplicity", "detriment", "fall")
           if res[k]]
    if term == p:
        lbl.append("Term")
    if face == p:
        lbl.append("Face")
    if res.get("peregrine"):
        lbl.append("Peregrine")
    res["label"] = ", ".join(lbl) or "—"
    return res


def aspects_between(pts: dict[str, float], speeds: dict[str, float], minor: bool = True,
                    pts2: dict[str, float] | None = None, orb_scale: float = 1.0):
    """Aspects among pts (or between pts and pts2)."""
    out = []
    names = list(pts.keys())
    pairs = []
    if pts2 is None:
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                pairs.append((a, b, pts[a], pts[b]))
    else:
        for a in names:
            for b in pts2:
                pairs.append((a, b, pts[a], pts2[b]))
    for a, b, la, lb in pairs:
        if pts2 is None and {a, b} in ({"North Node", "South Node"}, {"Ascendant", "Descendant"}):
            continue
        sep = abs(angdiff(la, lb))
        for name, ang, orb, sym in ASPECTS:
            if not minor and name not in ("Conjunction", "Opposition", "Trine", "Square",
                                          "Sextile", "Quincunx"):
                continue
            o = orb
            if ang in (0, 180, 120, 90) and ({"Sun", "Moon"} & {a, b}):
                o += 2
            if {a, b} & {"Chiron", "North Node", "South Node", "Lilith", "Fortune", "Vertex"}:
                o = min(o, 3 if ang in (0, 180, 90, 120, 60) else 1)
            o *= orb_scale
            diff = abs(sep - ang)
            if diff <= o:
                # applying test using speeds (if available)
                va, vb = speeds.get(a, 0.0), speeds.get(b, 0.0)
                if pts2 is not None:
                    vb = 0.0
                dt = 1 / 24
                sep2 = abs(angdiff(la + va * dt, lb + vb * dt))
                applying = abs(sep2 - ang) < diff
                out.append({"a": a, "b": b, "aspect": name, "symbol": sym, "angle": ang,
                            "orb": round(diff, 2), "orb_dms": dms(diff, False),
                            "applying": applying,
                            "nature": "harmonious" if name in HARMONIOUS else
                            ("challenging" if name in CHALLENGING else "neutral")})
                break
    return out


def find_patterns(asp: list[dict], pts: dict[str, float], houses_of: dict[str, int]) -> list[dict]:
    pl = [p for p in pts if p not in ("Ascendant", "Midheaven", "Lilith", "Fortune", "Vertex",
                                      "South Node")]
    rel = {}
    for a in asp:
        rel[frozenset((a["a"], a["b"]))] = a["aspect"]

    def has(x, y, name):
        return rel.get(frozenset((x, y))) == name

    out = []
    n = len(pl)
    seen = set()
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                a, b, c = pl[i], pl[j], pl[k]
                trio = frozenset((a, b, c))
                if has(a, b, "Trine") and has(b, c, "Trine") and has(a, c, "Trine"):
                    out.append({"pattern": "Grand Trine", "planets": [a, b, c],
                                "element": ELEMENT[sign_of(pts[a])]})
                for x, y, z in ((a, b, c), (a, c, b), (b, c, a)):
                    if has(x, y, "Opposition") and has(x, z, "Square") and has(y, z, "Square"):
                        if (trio, "T") not in seen:
                            seen.add((trio, "T"))
                            out.append({"pattern": "T-Square", "planets": [x, y, z], "apex": z})
                    if has(x, y, "Sextile") and has(x, z, "Quincunx") and has(y, z, "Quincunx"):
                        if (trio, "Y") not in seen:
                            seen.add((trio, "Y"))
                            out.append({"pattern": "Yod", "planets": [x, y, z], "apex": z})
    # Grand cross / kite / mystic rectangle
    for i in range(n):
        for j in range(i + 1, n):
            if not has(pl[i], pl[j], "Opposition"):
                continue
            for k in range(n):
                for l in range(k + 1, n):
                    if len({pl[i], pl[j], pl[k], pl[l]}) < 4 or not has(pl[k], pl[l], "Opposition"):
                        continue
                    a, b, c, d = pl[i], pl[j], pl[k], pl[l]
                    key = frozenset((a, b, c, d))
                    if (key, "G") in seen:
                        continue
                    if has(a, c, "Square") and has(a, d, "Square") and has(b, c, "Square") and has(b, d, "Square"):
                        seen.add((key, "G"))
                        out.append({"pattern": "Grand Cross", "planets": [a, b, c, d]})
                    elif ((has(a, c, "Trine") and has(b, d, "Trine") and has(a, d, "Sextile") and has(b, c, "Sextile")) or
                          (has(a, d, "Trine") and has(b, c, "Trine") and has(a, c, "Sextile") and has(b, d, "Sextile"))):
                        seen.add((key, "G"))
                        out.append({"pattern": "Mystic Rectangle", "planets": [a, b, c, d]})
    gts = [p for p in out if p["pattern"] == "Grand Trine"]
    for gt in gts:
        for apex in gt["planets"]:
            for q in pl:
                if q in gt["planets"]:
                    continue
                others = [x for x in gt["planets"] if x != apex]
                if has(apex, q, "Opposition") and all(has(q, o, "Sextile") for o in others):
                    out.append({"pattern": "Kite", "planets": gt["planets"] + [q], "apex": apex})
    # stelliums
    by_sign, by_house = {}, {}
    core = [p for p in pl if p not in ("Chiron", "North Node")]
    for p in core:
        by_sign.setdefault(sign_of(pts[p]), []).append(p)
        if p in houses_of:
            by_house.setdefault(houses_of[p], []).append(p)
    for s, ps in by_sign.items():
        if len(ps) >= 3:
            out.append({"pattern": "Stellium", "planets": ps, "where": tr("in {s}", s=SIGNS[s])})
    for hh, ps in by_house.items():
        if len(ps) >= 3:
            out.append({"pattern": "Stellium", "planets": ps, "where": tr("in house {h}", h=hh)})
    return out


def chart_shape(lons: list[float]) -> str:
    xs = sorted(norm(x) for x in lons)
    gaps = [((xs[(i + 1) % len(xs)] - xs[i]) % 360, i) for i in range(len(xs))]
    gaps.sort(reverse=True)
    biggest = gaps[0][0]
    occupied = 360 - biggest
    if occupied <= 120:
        return "Bundle"
    if occupied <= 180:
        return "Bowl"
    if biggest >= 120 and gaps[1][0] < 60:
        # one planet isolated across from the rest?
        if gaps[0][0] + gaps[1][0] > 180 and gaps[1][0] > 50:
            return "Bucket"
        return "Locomotive"
    if gaps[0][0] >= 60 and gaps[1][0] >= 60 and abs(gaps[0][0] - gaps[1][0]) < 90:
        return "Seesaw"
    if biggest < 60:
        return "Splash"
    return "Splay"


SHAPE_TEXT = {
    "Bundle": "All planets within a trine (120°): concentrated focus, specialist, self-contained.",
    "Bowl": "Planets within half the zodiac: self-contained, purposeful, driven to fill what is missing.",
    "Bucket": "A bowl with a single 'handle' planet opposite: that planet channels the whole chart's energy.",
    "Locomotive": "Planets spread over two-thirds with an empty trine: dynamic, self-driving, persistent.",
    "Seesaw": "Two opposing groups: weighing perspectives, relationships as mirrors, balancing act.",
    "Splash": "Planets evenly spread: wide interests, versatile, can scatter energy.",
    "Splay": "Irregular clusters: individualistic, resists categorisation, strong personal emphases.",
}

MOON_PHASES = [(45, "New Moon", "instinctive, initiating, projecting new beginnings"),
               (90, "Crescent", "striving, pushing past the past, building momentum"),
               (135, "First Quarter", "action-oriented, crisis in action, builder"),
               (180, "Gibbous", "analytical, perfecting, seeking meaning"),
               (225, "Full Moon", "awareness through relationship, fulfilment, objectivity"),
               (270, "Disseminating", "sharing wisdom, teaching, spreading ideas"),
               (315, "Last Quarter", "re-orientation, crisis in consciousness, reformer"),
               (360, "Balsamic", "release, visionary, completing karmic cycles")]


def solar_return(natal_sun: float, birth_jd: float, year: int, sidereal):
    """Exact moment the Sun returns to its natal longitude in `year`."""
    approx = E.jd_from_utc(datetime(year, 1, 1, tzinfo=timezone.utc)) + \
        ((natal_sun - 280.0) % 360) / 0.9856
    f = lambda t: angdiff(E.calc_body(t, "Sun", sidereal).lon, natal_sun)
    lo, hi = approx - 4, approx + 4
    return E.find_crossing(f, lo, hi)


def compute(inp, hsys: str = "P", sidereal: str | None = None, node: str = "true",
            minor: bool = True, now_jd: float | None = None) -> dict:
    jd = inp.jd
    pos = _positions(jd, sidereal, node)
    cusps, info = E.houses(jd, inp.lat, inp.lon, hsys, sidereal)
    asc, mc = info["asc"], info["mc"]
    sun_alt_day = _is_day(jd, inp, pos["Sun"])

    def house_of(lon):
        lon = norm(lon)
        for i in range(12):
            a, b = cusps[i], cusps[(i + 1) % 12]
            if (lon - a) % 360 < (b - a) % 360:
                return i + 1
        return 12

    fortune = norm(asc + pos["Moon"].lon - pos["Sun"].lon) if sun_alt_day else \
        norm(asc + pos["Sun"].lon - pos["Moon"].lon)
    pts = {b: pos[b].lon for b in BODIES}
    pts["Ascendant"], pts["Midheaven"] = asc, mc
    extra_pts = {"South Node": pos["South Node"].lon, "Lilith": pos["Lilith"].lon,
                 "Fortune": fortune, "Vertex": info["vertex"],
                 "Descendant": norm(asc + 180), "IC": norm(mc + 180)}
    speeds = {b: pos[b].speed for b in BODIES}
    rows = []
    for b in BODIES + ["South Node", "Lilith"]:
        body = pos[b]
        ed = essential_dignity(b, body.lon, sun_alt_day)
        rows.append({"name": b, "lon": body.lon, "sign": sign_of(body.lon),
                     "sign_name": SIGNS[sign_of(body.lon)], "deg": deg_in_sign(body.lon),
                     "dms": dms(deg_in_sign(body.lon)), "house": house_of(body.lon),
                     "retro": body.speed < 0, "speed": round(body.speed, 4),
                     "decl": round(body.decl, 2), "lat": round(body.lat, 2), "dignity": ed})
    for nm, lon in (("Fortune", fortune), ("Vertex", info["vertex"])):
        rows.append({"name": "Part of Fortune" if nm == "Fortune" else nm, "lon": lon,
                     "sign": sign_of(lon), "sign_name": SIGNS[sign_of(lon)],
                     "deg": deg_in_sign(lon), "dms": dms(deg_in_sign(lon)),
                     "house": house_of(lon), "retro": False})
    asp_pts = dict(pts)
    asp = aspects_between(asp_pts, speeds, minor)
    houses_of = {b: house_of(pts[b]) for b in BODIES}
    patterns = find_patterns(asp, pts, houses_of)
    # balances (weights: Sun/Moon/Asc 2, personal 1.5, others 1, outers 0.5)
    w = {"Sun": 2, "Moon": 2, "Ascendant": 2, "Midheaven": 1, "Mercury": 1.5, "Venus": 1.5,
         "Mars": 1.5, "Jupiter": 1, "Saturn": 1, "Uranus": 0.5, "Neptune": 0.5, "Pluto": 0.5}
    el = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
    mo = {"Cardinal": 0, "Fixed": 0, "Mutable": 0}
    el_p = {k: [] for k in el}
    mo_p = {k: [] for k in mo}
    for p, wt in w.items():
        s = sign_of(pts[p])
        el[ELEMENT[s]] += wt
        mo[MODALITY[s]] += wt
        el_p[ELEMENT[s]].append(p)
        mo_p[MODALITY[s]].append(p)
    hemi = {"East": 0, "West": 0, "North": 0, "South": 0}
    quad = {1: [], 2: [], 3: [], 4: []}
    for p in BODIES[:10]:
        hh = houses_of[p]
        hemi["East" if hh in (10, 11, 12, 1, 2, 3) else "West"] += 1
        hemi["South" if hh in (7, 8, 9, 10, 11, 12) else "North"] += 1
        quad[(hh - 1) // 3 + 1].append(p)
    phase_angle = norm(pos["Moon"].lon - pos["Sun"].lon)
    phase = next((n, d) for lim, n, d in MOON_PHASES if phase_angle < lim)
    shape = chart_shape([pts[p] for p in BODIES[:10]])
    asc_s = sign_of(asc)
    house_rows = []
    for i, c in enumerate(cusps):
        s = sign_of(c)
        house_rows.append({"house": i + 1, "lon": c, "sign": SIGNS[s], "dms": dms(deg_in_sign(c)),
                           "ruler": RULER_MODERN[s], "ruler_trad": RULER_TRAD[s],
                           "planets": [p for p in BODIES if houses_of[p] == i + 1]})
    # intercepted signs
    covered = {sign_of(c) for c in cusps}
    intercepted = [SIGNS[s] for s in range(12) if s not in covered]

    res = {
        "zodiac": "Sidereal" if sidereal else "Tropical",
        "house_system": E.HOUSE_SYSTEMS.get(hsys, hsys),
        "planets": rows, "houses": house_rows,
        "angles": {"Ascendant": _pt(asc), "Midheaven": _pt(mc), "Descendant": _pt(asc + 180),
                   "IC": _pt(mc + 180), "Vertex": _pt(info["vertex"]),
                   "East Point": _pt(info["eq_asc"])},
        "aspects": asp, "patterns": patterns,
        "elements": el, "elements_planets": el_p, "modalities": mo, "modalities_planets": mo_p,
        "hemispheres": hemi, "quadrants": quad,
        "moon_phase": {"name": phase[0], "angle": round(phase_angle, 2), "meaning": tr(phase[1])},
        "shape": {"name": shape, "meaning": tr(SHAPE_TEXT[shape])},
        "chart_ruler": {"traditional": RULER_TRAD[asc_s], "modern": RULER_MODERN[asc_s],
                        "ruler_house": houses_of.get(RULER_MODERN[asc_s]),
                        "ruler_sign": SIGNS[sign_of(pts[RULER_MODERN[asc_s]])]},
        "day_chart": sun_alt_day, "intercepted": intercepted,
        "_pts": pts, "_cusps": cusps,
    }
    if now_jd:
        res["transits"] = transits(pts, now_jd, sidereal, node, house_of)
        res["progressions"] = progressions(inp, pts, now_jd, sidereal, node, hsys)
        res["solar_return"] = solar_return_chart(inp, pos["Sun"].lon, now_jd, sidereal, hsys, node)
    return res


def _pt(lon):
    lon = norm(lon)
    return {"lon": lon, "sign": SIGNS[sign_of(lon)], "dms": dms(deg_in_sign(lon))}


def _is_day(jd, inp, sun_body):
    """Sun above the horizon (refraction-corrected) → day chart."""
    import swisseph as swe
    tb = E.calc_body(jd, "Sun", None)  # horizon transform needs tropical coordinates
    with E.LOCK:
        hor = swe.azalt(jd, swe.ECL2HOR, (inp.lon, inp.lat, 0), 1013.25, 15,
                        (tb.lon, tb.lat, tb.dist))
    return hor[1] > -0.833


def transits(natal: dict, now_jd: float, sidereal, node, house_of) -> dict:
    cur = {}
    sp = {}
    rows = []
    for b in BODIES:
        body = E.calc_body(now_jd, b, sidereal, node)
        cur[b] = body.lon
        sp[b] = body.speed
        rows.append({"name": b, "lon": body.lon, "sign_name": SIGNS[sign_of(body.lon)],
                     "dms": dms(deg_in_sign(body.lon)), "natal_house": house_of(body.lon),
                     "retro": body.speed < 0})
    asp = aspects_between(cur, sp, minor=False, pts2=natal, orb_scale=0.3)
    asp = [a for a in asp if a["a"] not in ("Moon",)]
    asp.sort(key=lambda a: a["orb"])
    return {"date": E.utc_from_jd(now_jd).strftime("%Y-%m-%d %H:%M UTC"), "positions": rows,
            "aspects": asp}


def progressions(inp, natal: dict, now_jd: float, sidereal, node, hsys) -> dict:
    age_years = (now_jd - inp.jd) / 365.2422
    pjd = inp.jd + age_years
    rows = []
    prog = {}
    for b in ["Sun", "Moon", "Mercury", "Venus", "Mars"]:
        body = E.calc_body(pjd, b, sidereal, node)
        prog[b] = body.lon
        rows.append({"name": b, "lon": body.lon, "sign_name": SIGNS[sign_of(body.lon)],
                     "dms": dms(deg_in_sign(body.lon)), "retro": body.speed < 0})
    # Solar-arc MC/Asc
    arc = norm(prog["Sun"] - natal["Sun"])
    pmc = norm(natal["Midheaven"] + arc)
    pasc = norm(natal["Ascendant"] + arc)
    prog["Midheaven"], prog["Ascendant"] = pmc, pasc
    rows.append({"name": "Midheaven (solar arc)", "lon": pmc, "sign_name": SIGNS[sign_of(pmc)],
                 "dms": dms(deg_in_sign(pmc))})
    rows.append({"name": "Ascendant (solar arc)", "lon": pasc, "sign_name": SIGNS[sign_of(pasc)],
                 "dms": dms(deg_in_sign(pasc))})
    asp = aspects_between(prog, {}, minor=False, pts2=natal, orb_scale=0.15)
    asp = [a for a in asp if a["a"] != a["b"]]
    phase = norm(prog["Moon"] - prog["Sun"])
    pphase = next(n for lim, n, d in MOON_PHASES if phase < lim)
    return {"age": round(age_years, 2), "positions": rows, "aspects": asp,
            "progressed_lunar_phase": pphase}


def solar_return_chart(inp, natal_sun: float, now_jd: float, sidereal, hsys, node) -> dict:
    y = E.utc_from_jd(now_jd).year
    t = solar_return(natal_sun, inp.jd, y, sidereal)
    if t > now_jd + 1:
        t = solar_return(natal_sun, inp.jd, y - 1, sidereal)
    cusps, info = E.houses(t, inp.lat, inp.lon, hsys, sidereal)

    def house_of(lon):
        for i in range(12):
            a, b = cusps[i], cusps[(i + 1) % 12]
            if (norm(lon) - a) % 360 < (b - a) % 360:
                return i + 1
        return 12
    rows = []
    for b in BODIES[:10]:
        lon = E.calc_body(t, b, sidereal, node).lon
        rows.append({"name": b, "sign_name": SIGNS[sign_of(lon)], "dms": dms(deg_in_sign(lon)),
                     "house": house_of(lon), "lon": lon})
    return {"moment": inp.fmt_jd(t), "asc": _pt(info["asc"]), "mc": _pt(info["mc"]),
            "planets": rows, "cusps": cusps,
            "note": tr("Solar return cast for the birth place.")}

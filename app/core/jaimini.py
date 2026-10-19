"""Jaimini system: Chara Karakas, Karakamsha, Arudha Padas, Rashi Drishti, Argala,
Chara Dasha (K.N. Rao) and Jaimini Raja yogas."""
from __future__ import annotations

from .constants import (DEBILITATION, EXALTATION, GRAHAS, OWN_SIGNS, SEVEN, SIGN_LORD,
                        SIGNS, deg_in_sign, norm)
from .vargas import varga_sign
from ..i18n import terms, tr

KARAKA_NAMES = ["AK", "AmK", "BK", "MK", "PiK", "PK", "GK", "DK"]
KARAKA_FULL = {"AK": "Atmakaraka (soul)", "AmK": "Amatyakaraka (career/minister)",
               "BK": "Bhratrikaraka (siblings/guru)", "MK": "Matrikaraka (mother)",
               "PiK": "Pitrikaraka (father)", "PK": "Putrakaraka (children)",
               "GK": "Gnatikaraka (rivals/disease)", "DK": "Darakaraka (spouse)"}

MOVABLE, FIXED, DUAL = {0, 3, 6, 9}, {1, 4, 7, 10}, {2, 5, 8, 11}
SAVYA = {0, 1, 2, 6, 7, 8}   # Aries, Taurus, Gemini, Libra, Scorpio, Sagittarius


def chara_karakas(chart, scheme: int = 8) -> list[dict]:
    cands = []
    for p in SEVEN:
        cands.append((deg_in_sign(chart.bodies[p].lon), p))
    if scheme == 8:
        cands.append((30 - deg_in_sign(chart.bodies["Rahu"].lon), "Rahu"))
    cands.sort(reverse=True)
    names = KARAKA_NAMES if scheme == 8 else [k for k in KARAKA_NAMES if k != "PiK"]
    out = []
    for (deg, p), k in zip(cands, names):
        out.append({"karaka": k, "full": tr(KARAKA_FULL[k]), "planet": p,
                    "degree": round(deg, 4)})
    return out


def rashi_aspects(sign: int) -> list[int]:
    if sign in MOVABLE:
        return [s for s in FIXED if s != (sign + 1) % 12]
    if sign in FIXED:
        return [s for s in MOVABLE if s != (sign - 1) % 12]
    return [s for s in DUAL if s != sign]


def _stronger_co_lord(chart, sign: int) -> str:
    """Jaimini rules for dual lordship of Scorpio (Mars/Ketu) and Aquarius (Saturn/Rahu)."""
    a = SIGN_LORD[sign]
    b = {7: "Ketu", 10: "Rahu"}.get(sign)
    if not b:
        return a
    sa, sb = chart.sign(a), chart.sign(b)
    # 1) one in the sign and the other outside → the one outside is taken
    if sa == sign and sb != sign:
        return b
    if sb == sign and sa != sign:
        return a
    # 2) more conjunctions
    def cnt(p):
        return sum(1 for q in GRAHAS if q != p and chart.sign(q) == chart.sign(p))
    ca, cb = cnt(a), cnt(b)
    if ca != cb:
        return a if ca > cb else b
    # 3) exaltation
    ea = EXALTATION[a][0] == sa
    eb = EXALTATION[b][0] == sb
    if ea != eb:
        return a if ea else b
    # 4) higher degree
    return a if deg_in_sign(chart.bodies[a].lon) >= deg_in_sign(chart.bodies[b].lon) else b


def arudha_padas(chart) -> dict:
    out = {}
    L = chart.lagna_sign
    for h in range(1, 13):
        hs = (L + h - 1) % 12
        lord = _stronger_co_lord(chart, hs)
        ls = chart.sign(lord)
        dist = (ls - hs) % 12
        pada = (ls + dist) % 12
        if pada == hs or pada == (hs + 6) % 12:
            pada = (pada + 9) % 12
        label = "AL" if h == 1 else ("UL" if h == 12 else f"A{h}")
        out[label] = {"house": h, "sign": pada, "sign_name": SIGNS[pada], "lord_used": lord,
                      "house_from_lagna": (pada - L) % 12 + 1}
    return out


def argala(chart, ref_sign: int) -> list[dict]:
    """Argala (intervention) on a reference sign and its obstruction (virodha)."""
    pairs = [(2, 12, "Dhana argala"), (4, 10, "Sukha argala"), (11, 3, "Labha argala"),
             (5, 9, "Putra argala (secondary)")]
    out = []
    occ = chart.sign_occupants()
    malefics = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
    for a, v, name in pairs:
        sa, sv = (ref_sign + a - 1) % 12, (ref_sign + v - 1) % 12
        pa, pv = occ[sa], occ[sv]
        status = "None"
        if pa:
            status = "Obstructed" if len(pv) >= len(pa) and pv else "Unobstructed"
        out.append({"type": tr(name), "from": a, "planets": pa, "obstruction_from": v,
                    "obstructing": pv, "status": status})
    # Vipareeta argala: malefics in 3rd
    s3 = (ref_sign + 2) % 12
    mal3 = [p for p in occ[s3] if p in malefics]
    if mal3:
        out.append({"type": tr("Vipareeta argala (malefics in 3rd)"), "from": 3, "planets": mal3,
                    "obstruction_from": 11, "obstructing": occ[(ref_sign + 10) % 12],
                    "status": "Unobstructed" if not occ[(ref_sign + 10) % 12] else "Obstructed"})
    return out


def _chara_years(chart, sign: int) -> int:
    lord = _stronger_co_lord(chart, sign)
    ls = chart.sign(lord)
    if sign in SAVYA:
        n = (ls - sign) % 12
    else:
        n = (sign - ls) % 12
    years = n if n else 12
    if EXALTATION.get(lord, (None,))[0] == ls:
        years += 1
    elif DEBILITATION.get(lord, (None,))[0] == ls:
        years -= 1
    return max(1, min(12, years))


def _sign_dasha(chart, inp, fmt, seq: list[int], year_days: float, now_jd, system: str,
                direction: str) -> dict:
    """Shared engine for rashi dashas: first cycle by Chara years, second cycle 12 − years;
    antardashas are 12 equal parts starting from the next sign (MD sign last)."""
    first = [(s, _chara_years(chart, s)) for s in seq]
    periods = []
    t = inp.jd
    for cycle in range(2):
        for s, y in first:
            yy = y if cycle == 0 else 12 - y
            if yy <= 0:
                continue
            dur = yy * year_days
            fwd = s in SAVYA
            sub = dur / 12
            ads = []
            for k in range(1, 13):
                asg = (s + (k if fwd else -k)) % 12
                ts = t + (k - 1) * sub
                ads.append({"sign": SIGNS[asg], "start": fmt(ts), "end": fmt(ts + sub)})
            periods.append({"sign": SIGNS[s], "years": yy, "start": fmt(t), "end": fmt(t + dur),
                            "_s": t, "_e": t + dur, "children": ads})
            t += dur
            if t > inp.jd + 120 * year_days:
                break
    current = None
    if now_jd:
        for p in periods:
            if p["_s"] <= now_jd < p["_e"]:
                current = p["sign"]
                break
    for p in periods:
        p.pop("_s"), p.pop("_e")
    return {"system": system, "direction": direction, "periods": periods, "current": current}


def chara_dasha(chart, inp, fmt, year_days=365.25, now_jd=None, variant: str = "knrao") -> dict:
    """K.N. Rao: order set by the 9th house from Lagna (savya → zodiacal).
    Lagna-footed variant (Iranganti/Rath school): order set by the Lagna sign itself."""
    L = chart.lagna_sign
    key = (L + 8) % 12 if variant == "knrao" else L
    forward = key in SAVYA
    seq = [(L + (i if forward else -i)) % 12 for i in range(12)]
    name = tr("Chara Dasha (K.N. Rao)") if variant == "knrao" else tr("Chara Dasha (Lagna-footed)")
    return _sign_dasha(chart, inp, fmt, seq, year_days, now_jd, name,
                       tr("Zodiacal") if forward else tr("Reverse"))


def padanadhamsa_dasha(chart, inp, fmt, arudhas: dict, year_days=365.25, now_jd=None) -> dict:
    """Padanadhamsa dasha: begins from the navamsa sign occupied by the lord of the Arudha
    Lagna (padanatha); runs forward from an odd sign, backward from an even sign."""
    al = arudhas["AL"]["sign"]
    lord = _stronger_co_lord(chart, al)
    start = varga_sign(chart.bodies[lord].lon, 9)
    forward = start % 2 == 0          # Aries (index 0) is odd
    seq = [(start + (i if forward else -i)) % 12 for i in range(12)]
    out = _sign_dasha(chart, inp, fmt, seq, year_days, now_jd, tr("Padanadhamsa Dasha"),
                      tr("Zodiacal") if forward else tr("Reverse"))
    out["padanatha"] = lord
    out["start_sign"] = SIGNS[start]
    return out


def raja_yogas(chart, karakas: list[dict], arudhas: dict) -> list[dict]:
    kmap = {k["karaka"]: k["planet"] for k in karakas}
    s = {p: chart.sign(p) for p in GRAHAS}
    out = []

    def linked(a, b):
        if a not in s or b not in s:
            return False
        return s[a] == s[b] or s[b] in rashi_aspects(s[a])

    ak, amk = kmap.get("AK"), kmap.get("AmK")
    pk, dk = kmap.get("PK"), kmap.get("DK")
    out.append({"name": tr("AK–AmK Raja Yoga"), "present": linked(ak, amk),
                "description": tr("Atmakaraka {ak} and Amatyakaraka {amk} conjoined or in mutual rashi drishti: a rise in career and authority.", ak=ak, amk=amk)})
    out.append({"name": tr("AK–PK Raja Yoga"), "present": linked(ak, pk),
                "description": tr("Atmakaraka {ak} and Putrakaraka {pk} linked: creative intelligence brings recognition.", ak=ak, pk=pk)})
    out.append({"name": tr("AK–DK Yoga"), "present": linked(ak, dk),
                "description": tr("Atmakaraka {ak} with Darakaraka {dk}: the spouse and partnerships are strongly tied to the life purpose.", ak=ak, dk=dk)})
    al = arudhas["AL"]["sign"]
    l7 = (al + 6) % 12
    ben = [p for p in ("Jupiter", "Venus", "Mercury", "Moon") if s[p] in (al, l7) or
           s[p] in rashi_aspects(al)]
    out.append({"name": tr("Benefics on Arudha Lagna"), "present": bool(ben),
                "description": tr("Benefics influencing the Arudha Lagna ({ps}) give a respected public image.", ps=terms(ben) or "–")})
    al11 = (al + 10) % 12
    gains = [p for p in GRAHAS if s[p] == al11]
    out.append({"name": tr("Planets in 11th from AL"), "present": bool(gains),
                "description": tr("Planets in the 11th from the AL ({ps}) show sources of steady gains.", ps=terms(gains) or "–")})
    al12 = (al + 11) % 12
    exp = [p for p in GRAHAS if s[p] == al12]
    out.append({"name": tr("Planets in 12th from AL"), "present": bool(exp),
                "description": tr("Planets in the 12th from the AL ({ps}) show channels of expenditure and loss.", ps=terms(exp) or "–")})
    return out


def compute(chart, inp, special: dict, fmt, now_jd, scheme=8) -> dict:
    karakas = chara_karakas(chart, scheme)
    ak = karakas[0]["planet"]
    kmsh = varga_sign(chart.bodies[ak].lon, 9)
    nav = {p: varga_sign(chart.bodies[p].lon, 9) for p in GRAHAS}
    nav_lagna = varga_sign(chart.asc, 9)
    in_kk = [p for p in GRAHAS if nav[p] == kmsh]
    # houses from Karakamsha in navamsa (Swamsha)
    swamsha_houses = {}
    for p in GRAHAS:
        swamsha_houses[p] = (nav[p] - kmsh) % 12 + 1
    arudhas = arudha_padas(chart)
    rasi_asp = {SIGNS[sg]: [SIGNS[x] for x in rashi_aspects(sg)] for sg in range(12)}
    planet_rasi_asp = {}
    for p in GRAHAS:
        tg = rashi_aspects(chart.sign(p))
        planet_rasi_asp[p] = {"signs": [SIGNS[x] for x in tg],
                              "planets": [q for q in GRAHAS if chart.sign(q) in tg]}
    return {
        "karakas": karakas, "atmakaraka": ak,
        "karakamsha": {"sign": SIGNS[kmsh], "sign_index": kmsh, "planets_in": in_kk,
                       "house_from_rasi_lagna": (kmsh - chart.lagna_sign) % 12 + 1,
                       "house_from_navamsa_lagna": (kmsh - nav_lagna) % 12 + 1,
                       "planets_from_karakamsha": swamsha_houses},
        "arudhas": arudhas,
        "rashi_drishti": rasi_asp, "planet_rashi_drishti": planet_rasi_asp,
        "argala_lagna": argala(chart, chart.lagna_sign),
        "argala_al": argala(chart, arudhas["AL"]["sign"]),
        "chara_dasha": chara_dasha(chart, inp, fmt, now_jd=now_jd),
        "chara_dasha_lagna": chara_dasha(chart, inp, fmt, now_jd=now_jd, variant="lagna"),
        "padanadhamsa": padanadhamsa_dasha(chart, inp, fmt, arudhas, now_jd=now_jd),
        "raja_yogas": raja_yogas(chart, karakas, arudhas),
        "special_lagnas": {k: {"lon": v, "sign": SIGNS[int(norm(v) // 30)],
                               "deg": round(norm(v) % 30, 4)} for k, v in special.items()},
    }

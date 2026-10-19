"""Builds complete result payloads for each astrology method."""
from __future__ import annotations

from datetime import datetime, timezone

from . import ashtakavarga, dasha as D, jaimini as J, kp as K, panchang as P, prashna as PR
from . import shadbala as SB, western as W, yogas as Y
from . import ephemeris as E
from .chart import BirthInput, SiderealChart, lord_house_table
from .constants import (GRAHAS, SEVEN, SIGN_LORD, SIGNS, deg_in_sign, dms, nakshatra_of,
                        NAKSHATRAS, NAK_LORD, norm, sign_of)
from .vargas import EXTRA_VARGA_NAMES, EXTRA_VARGAS, VARGA_NAMES, VARGAS, d60_deity, pushkar, varga_sign
from .vedic import (aspect_table, dignity, planet_table, relationship_tables)
from .. import interpret as I
from ..i18n import tr


def now_jd() -> float:
    from .clock import now_jd as _now
    return _now()


def _fmt_date(inp):
    return lambda jd: inp.fmt_jd(jd, with_time=False)


# ---------------------------------------------------------------- shared pieces
def chart_points(chart, cusps=None, extra: dict | None = None) -> dict:
    """Minimal data the front-end needs to draw Indian charts."""
    pts = {"Lagna": {"lon": chart.asc, "sign": chart.lagna_sign}}
    for p, b in chart.bodies.items():
        pts[p] = {"lon": b.lon, "sign": sign_of(b.lon), "retro": b.retro}
    if extra:
        for k, v in extra.items():
            pts[k] = {"lon": v, "sign": sign_of(v)}
    return pts


def varga_charts(chart, extra: bool = False) -> dict:
    out = {}
    names = {**VARGA_NAMES, **EXTRA_VARGA_NAMES} if extra else VARGA_NAMES
    for n in (VARGAS + EXTRA_VARGAS if extra else VARGAS):
        signs = {"Lagna": varga_sign(chart.asc, n)}
        for p in GRAHAS + [x for x in ("Uranus", "Neptune", "Pluto") if x in chart.bodies]:
            signs[p] = varga_sign(chart.bodies[p].lon, n)
        out[f"D{n}"] = {"name": tr(names[n]), "signs": signs, "extra": n in EXTRA_VARGAS}
    return out


VIMSHOPAKA_W = {1: 3.5, 2: 1, 3: 1, 4: 0.5, 7: 0.5, 9: 3, 10: 0.5, 12: 0.5, 16: 2, 20: 0.5,
                24: 0.5, 27: 0.5, 30: 1, 40: 0.5, 45: 0.5, 60: 4}
VIMSHOPAKA_PTS = {"Exalted": 20, "Moolatrikona": 20, "Own": 20, "Great Friend": 18,
                  "Friend": 15, "Neutral": 10, "Enemy": 7, "Great Enemy": 5, "Debilitated": 5}


def vimshopaka(chart) -> list[dict]:
    signs = {p: chart.sign(p) for p in SEVEN}
    rows = []
    for p in SEVEN:
        tot = 0.0
        detail = {}
        for n, w in VIMSHOPAKA_W.items():
            vs = varga_sign(chart.bodies[p].lon, n)
            dg = dignity(p, chart.bodies[p].lon, signs, use_mt=(n == 1),
                         sign_override=None if n == 1 else vs)
            pts = VIMSHOPAKA_PTS[dg]
            tot += pts * w / 20
            detail[f"D{n}"] = dg
        rows.append({"planet": p, "score": round(tot, 2), "out_of": 20, "detail": detail,
                     "grade": "Excellent" if tot >= 15 else "Good" if tot >= 12 else
                     "Average" if tot >= 9 else "Weak"})
    return rows


def house_table(chart, sav: list[int] | None = None) -> list[dict]:
    rows = lord_house_table(chart)
    from .vedic import aspects_on_signs
    asp = aspects_on_signs({p: chart.sign(p) for p in GRAHAS})
    for r in rows:
        s = (chart.lagna_sign + r["house"] - 1) % 12
        r["occupants"] = [p for p in GRAHAS if chart.sign(p) == s]
        r["aspected_by"] = asp[s]
        r["bhava_madhya"] = f"{dms(deg_in_sign(chart.bhava_madhya[r['house'] - 1]))} {SIGNS[sign_of(chart.bhava_madhya[r['house'] - 1])][:3]}"
        r["bhava_start"] = f"{dms(deg_in_sign(chart.sripati[r['house'] - 1]))} {SIGNS[sign_of(chart.sripati[r['house'] - 1])][:3]}"
        if sav:
            r["sav"] = sav[s]
    return rows


def gochara(chart, jd_now) -> dict:
    rows = []
    moon_s = chart.sign("Moon")
    good_from_moon = {"Sun": [3, 6, 10, 11], "Moon": [1, 3, 6, 7, 10, 11],
                      "Mars": [3, 6, 11], "Mercury": [2, 4, 6, 8, 10, 11],
                      "Jupiter": [2, 5, 7, 9, 11], "Venus": [1, 2, 3, 4, 5, 8, 9, 11, 12],
                      "Saturn": [3, 6, 11], "Rahu": [3, 6, 11], "Ketu": [3, 6, 11]}
    for p in GRAHAS:
        b = E.calc_body(jd_now, p, chart.ayanamsa, chart.node)
        s = sign_of(b.lon)
        hm = (s - moon_s) % 12 + 1
        nk, pd = nakshatra_of(b.lon)
        rows.append({"planet": p, "sign": SIGNS[s], "dms": dms(deg_in_sign(b.lon)),
                     "nakshatra": f"{NAKSHATRAS[nk]} {pd}", "retro": b.speed < 0,
                     "house_from_lagna": (s - chart.lagna_sign) % 12 + 1,
                     "house_from_moon": hm,
                     "result": "Favourable" if hm in good_from_moon[p] else "Challenging",
                     "lon": b.lon})
    return {"date": E.utc_from_jd(jd_now).strftime("%Y-%m-%d %H:%M UTC"), "planets": rows}


def base_vedic(inp: BirthInput, opts: dict, ayanamsa_default="lahiri", hsys="P"):
    chart = SiderealChart(inp, ayanamsa=opts.get("ayanamsa") or ayanamsa_default,
                          node=opts.get("node", "mean"), hsys=hsys,
                          hindu_sunrise=opts.get("sunrise") == "hindu")
    pan = P.compute(chart, inp)
    return chart, pan


def _clean_pan(pan: dict) -> dict:
    return {k: v for k, v in pan.items() if not k.startswith("_")}


def _aya_label(chart):
    return E.AYANAMSAS[chart.ayanamsa][1]


def ashtottari_note(chart, pan) -> str:
    """BPHS: Ashtottari applies when Rahu is in a kendra/trikona from the Lagna lord (not in
    Lagna); a common alternative uses Krishna-paksha day or Shukla-paksha night births."""
    ll = SIGN_LORD[chart.lagna_sign]
    h = (chart.sign("Rahu") - chart.sign(ll)) % 12 + 1
    rule1 = h in (1, 4, 5, 7, 9, 10) and chart.sign("Rahu") != chart.lagna_sign
    shukla = pan["tithi_index"] <= 15
    rule2 = (pan["day_birth"] and not shukla) or (not pan["day_birth"] and shukla)
    parts = [tr("Rahu is in house {h} from the Lagna lord {ll}, so the BPHS rule makes Ashtottari applicable.", h=h, ll=ll)
             if rule1 else tr("Rahu is in house {h} from the Lagna lord {ll}, so the BPHS rule is not met.", h=h, ll=ll)]
    kind = {(True, True): "day birth in Shukla paksha", (True, False): "day birth in Krishna paksha",
            (False, True): "night birth in Shukla paksha", (False, False): "night birth in Krishna paksha"}[(bool(pan["day_birth"]), shukla)]
    parts.append(tr("The paksha and day/night rule is met ({kind}).", kind=tr(kind)) if rule2 else
                 tr("The paksha and day/night rule is not met ({kind}).", kind=tr(kind)))
    return " ".join(parts)


def fertility_sphutas(chart) -> dict:
    """Beeja sphuta (Sun+Venus+Jupiter) and Kshetra sphuta (Moon+Mars+Jupiter)."""
    from .vargas import varga_sign
    b = chart.bodies
    out = {}
    for name, lon, want_odd in (("Beeja sphuta", b["Sun"].lon + b["Venus"].lon + b["Jupiter"].lon, True),
                                ("Kshetra sphuta", b["Moon"].lon + b["Mars"].lon + b["Jupiter"].lon, False)):
        lon = norm(lon)
        s_odd = sign_of(lon) % 2 == 0
        n_odd = varga_sign(lon, 9) % 2 == 0
        good = (s_odd and n_odd) if want_odd else (not s_odd and not n_odd)
        mixed = (s_odd or n_odd) if want_odd else (not s_odd or not n_odd)
        out[name] = {"sign": SIGNS[sign_of(lon)], "dms": dms(deg_in_sign(lon)),
                     "navamsa": SIGNS[varga_sign(lon, 9)],
                     "status": "Favourable" if good else ("Mixed" if mixed else "Weak"),
                     "rule": (tr("An odd sign and odd navamsa favour male fertility.") if want_odd else
                              tr("An even sign and even navamsa favour female fertility."))}
    return out


def _chakras(chart, inp, pan, jn):
    try:
        from . import chakras
        return chakras.compute(chart, inp, pan, jn)
    except Exception:  # module optional; never break the main chart
        import traceback
        traceback.print_exc()
        return None


def enrich_planets(chart, planets: list[dict]):
    """Pushkar navamsa/bhaga flags and apparent magnitude for each planet row."""
    for row in planets:
        if row["name"] == "Lagna":
            row.update(pushkar(chart.asc))
            continue
        row.update(pushkar(row["lon"]))
        row["magnitude"] = E.magnitude(chart.inp.jd, row["name"])


def bhrigu_bindu(chart) -> float:
    """Midpoint of Rahu and the Moon, measured from Rahu."""
    r, m = chart.bodies["Rahu"].lon, chart.bodies["Moon"].lon
    return norm(r + ((m - r) % 360) / 2)


def dasha_pravesh(chart, inp, yd: float, at_jd: float) -> list[dict]:
    """Charts cast for the start moment of the running Mahadasha, Antardasha and Pratyantardasha."""
    out = []
    for level, lords, s, e in D.running_jds(chart.bodies["Moon"].lon, inp.jd, yd, at_jd, 3):
        pts = {"Lagna": {"lon": E.ascendant_at(s, inp.lat, inp.lon, chart.ayanamsa)}}
        pts["Lagna"]["sign"] = sign_of(pts["Lagna"]["lon"])
        for p in GRAHAS:
            b = E.calc_body(s, p, chart.ayanamsa, chart.node)
            pts[p] = {"lon": b.lon, "sign": sign_of(b.lon), "retro": b.speed < 0}
        out.append({"level": level, "lords": lords, "moment": inp.fmt_jd(s), "end": inp.fmt_jd(e, False),
                    "lagna": SIGNS[pts["Lagna"]["sign"]], "points": pts})
    return out


# ---------------------------------------------------------------- PARASHARA
def parashara(inp: BirthInput, opts: dict) -> dict:
    chart, pan = base_vedic(inp, opts)
    jn = now_jd()
    yd = float(opts.get("year_days", 365.25))
    planets = planet_table(chart)
    signs = {p: chart.sign(p) for p in SEVEN}
    signs["Lagna"] = chart.lagna_sign
    av = ashtakavarga.compute(signs, chart.lagna_sign)
    sb = SB.compute(chart, inp, pan)
    yg = Y.detect(chart)
    vim = D.vimshottari(chart.bodies["Moon"].lon, inp.jd, _fmt_date(inp), yd, 3, jn)
    yog = D.yogini(chart.bodies["Moon"].lon, inp.jd, _fmt_date(inp), yd, jn)
    ash = D.ashtottari(chart.bodies["Moon"].lon, inp.jd, _fmt_date(inp), yd, jn,
                       ashtottari_note(chart, pan))
    special = P.special_lagnas(chart, inp, pan)
    special["Bhrigu Bindu"] = bhrigu_bindu(chart)
    enrich_planets(chart, planets)
    d60 = {p: dict(zip(("deity", "benefic"), d60_deity(chart.bodies[p].lon))) for p in GRAHAS}
    return {
        "method": "parashara", "title": tr("Parashari (Vedic) Analysis"),
        "settings": {"ayanamsa": _aya_label(chart), "node": chart.node,
                     "zodiac": "Sidereal", "houses": "Whole sign (Rasi) + Sripati bhava",
                     "year_days": yd},
        "panchang": _clean_pan(pan),
        "planets": planets,
        "points": chart_points(chart),
        "special_lagnas": {k: {"sign": SIGNS[sign_of(v)], "dms": dms(deg_in_sign(v)), "lon": v}
                           for k, v in special.items()},
        "vargas": varga_charts(chart, extra=True),
        "bhava_chalit": {p: chart.bhava_of(chart.bodies[p].lon, chart.sripati) for p in GRAHAS},
        "dasha_pravesh": dasha_pravesh(chart, inp, yd, jn),
        "houses": house_table(chart, av["sav"]),
        "aspects": aspect_table(chart),
        "relationships": relationship_tables(chart),
        "shadbala": sb, "ashtakavarga": av, "vimshopaka": vimshopaka(chart),
        "yogas": yg, "dasha": {"vimshottari": vim, "yogini": yog, "ashtottari": ash},
        "fertility": fertility_sphutas(chart),
        "sade_sati": Y.sade_sati(chart, inp),
        "transits": gochara(chart, jn),
        "d60": d60,
        "chakras": _chakras(chart, inp, pan, jn),
        "reading": I.vedic(chart, planets, pan, vim, yg, sb),
    }


# ---------------------------------------------------------------- KP
def _kp_chart(inp, opts):
    chart, pan = base_vedic(inp, opts, ayanamsa_default="kp", hsys="P")
    return chart, pan


def kp(inp: BirthInput, opts: dict) -> dict:
    chart, pan = _kp_chart(inp, opts)
    jn = now_jd()
    yd = float(opts.get("year_days", 365.25))
    rot = int(opts.get("rotate") or 1)
    cusps = K.rotate_cusps(chart.cusps, rot) if rot > 1 else chart.cusps
    lons = {p: chart.bodies[p].lon for p in GRAHAS}
    an = K.analyse(lons, cusps)
    sig = an["significators"]
    fort = K.fortuna(chart.asc, chart.bodies["Sun"].lon, chart.bodies["Moon"].lon)
    planets = planet_table(chart, K.kp_lords)
    nk, pd = nakshatra_of(fort)
    planets.append({"name": "Fortuna", "lon": fort, "sign": sign_of(fort), "sign_name": SIGNS[sign_of(fort)],
                    "deg": deg_in_sign(fort), "dms": dms(deg_in_sign(fort)), "nakshatra": NAKSHATRAS[nk],
                    "pada": pd, "nak_lord": NAK_LORD[nk], "retro": False, **K.kp_lords(fort)})
    for row in planets:
        if row["name"] == "Lagna":
            continue
        row["kp_house"] = sig["occupancy"].get(row["name"]) or K._bhava(row["lon"], cusps)
    vim = D.vimshottari(chart.bodies["Moon"].lon, inp.jd, _fmt_date(inp), yd, 3, jn)
    ash = D.ashtottari(chart.bodies["Moon"].lon, inp.jd, _fmt_date(inp), yd, jn,
                       ashtottari_note(chart, pan))
    verdicts = K.event_verdicts(cusps, lons, sig)
    timing = K.timing_windows(vim, verdicts, sig, "", jn, inp.jd, yd)
    for v in verdicts:
        v["windows"] = timing.get(v["key"], [])
        v["house_text"] = I.kp_house(v["cusp"])
    custom = None
    ce = opts.get("custom_event")
    if ce and ce.get("good"):
        ev = {"label": ce.get("label") or tr("Custom event"), "cusp": int(ce.get("cusp") or ce["good"][0]),
              "good": [int(x) for x in ce["good"]], "bad": [int(x) for x in ce.get("bad", [])],
              "note": "Custom event: CSL of the main cusp judged against your favourable and negating houses."}
        custom = K.event_verdicts(cusps, lons, sig, custom=ev)[0]
        custom["windows"] = K.timing_windows(vim, [custom], sig, "", jn, inp.jd, yd)["custom"]
    rp_now = K.ruling_planets(jn, inp.lat, inp.lon, chart.ayanamsa, chart.node, inp.offset_used)
    rp_birth = K.ruling_planets(inp.jd, inp.lat, inp.lon, chart.ayanamsa, chart.node, inp.offset_used)
    rect = K.rectify(inp.jd, inp.lat, inp.lon, chart.ayanamsa, chart.node, inp.offset_used, jn,
                     int(opts.get("rectify_window", 60)))
    for c in rect["candidates"]:
        c["start"], c["end"], c["mid"] = inp.fmt_jd(c["start"]), inp.fmt_jd(c["end"]), inp.fmt_jd(c["mid"])
    pts = chart_points(chart, extra={"Fortuna": fort})
    pts["Lagna"] = {"lon": cusps[0], "sign": sign_of(cusps[0])}
    bhava = {**sig["occupancy"], **{p: K._bhava(chart.bodies[p].lon, cusps)
                                    for p in ("Uranus", "Neptune", "Pluto")},
             "Fortuna": K._bhava(fort, cusps)}
    settings = {"ayanamsa": _aya_label(chart), "ayanamsa_value": dms(chart.aya),
                "houses": "Placidus", "node": chart.node, "year_days": yd}
    if rot > 1:
        settings["house_rotation"] = tr("house {n} taken as the 1st", n=rot)
    return {
        "method": "kp", "title": tr("KP (Krishnamurti Paddhati) Stellar Analysis"),
        "settings": settings, "rotation": rot,
        "panchang": _clean_pan(pan),
        "planets": planets,
        "cusps": an["csl"],
        "points": pts,
        "cusp_lons": cusps,
        "bhava_of": bhava,
        "significators": sig, "four_step": an["four_step"],
        "ruling_planets": {"now": rp_now, "birth": rp_birth},
        "rectification": rect,
        "events": verdicts, "custom_event": custom,
        "event_catalog": {k: {"label": v["label"], "cusp": v["cusp"], "good": v["good"], "bad": v["bad"]}
                          for k, v in K.EVENTS.items()},
        "dasha": {"vimshottari": vim, "ashtottari": ash},
        "star_texts": {p: I.kp_star(p) for p in GRAHAS},
        "house_texts": {h: I.kp_house(h) for h in range(1, 13)},
        "transits": gochara(chart, jn),
    }


# ---------------------------------------------------------------- KP HORARY
def _solve_armc(target_trop: float, lat: float, eps: float) -> float:
    f = lambda a: E.angdiff(E.houses_from_armc(a % 360, lat, eps, "O")[1]["asc"], target_trop)
    prev_a, prev = 0.0, f(0.0)
    for k in range(1, 361):
        a = k * 1.0
        cur = f(a)
        if abs(cur - prev) < 90 and ((prev <= 0 < cur) or (prev >= 0 > cur)):
            return E.find_crossing(f, prev_a, a, 1e-9) % 360
        prev_a, prev = a, cur
    return 0.0


def kp_horary(inp: BirthInput, opts: dict, number: int, question: str) -> dict:
    """KP horary (1–249). `inp` holds the time and place of judgment."""
    number = max(1, min(249, int(number)))
    sub = K.sub_table()[number - 1]
    aya_key = opts.get("ayanamsa") or "kp"
    aya = E.ayanamsa_value(inp.jd, aya_key)
    eps = E.obliquity(inp.jd)
    target_trop = norm(sub["start"] + aya)
    armc = _solve_armc(target_trop, inp.lat, eps)
    cusps_t, info = E.houses_from_armc(armc, inp.lat, eps, "P")
    cusps = [norm(c - aya) for c in cusps_t]
    cusps[0] = sub["start"]
    chart, pan = base_vedic(inp, {**opts, "ayanamsa": aya_key}, ayanamsa_default="kp")
    lons = {p: chart.bodies[p].lon for p in GRAHAS}
    an = K.analyse(lons, cusps)
    sig = an["significators"]
    planets = planet_table(chart, K.kp_lords)
    for row in planets:
        if row["name"] == "Lagna":
            row.update({"lon": cusps[0], "sign": sign_of(cusps[0]),
                        "sign_name": SIGNS[sign_of(cusps[0])], "deg": deg_in_sign(cusps[0]),
                        "dms": dms(deg_in_sign(cusps[0])), **K.kp_lords(cusps[0])})
            nk, pd = nakshatra_of(cusps[0])
            row.update({"nakshatra": NAKSHATRAS[nk], "pada": pd})
        elif row["name"] in sig["occupancy"]:
            row["kp_house"] = sig["occupancy"][row["name"]]
        else:
            row["kp_house"] = K._bhava(row["lon"], cusps)
    ev_key = question if question in K.EVENTS else None
    keys = [ev_key] if ev_key else ["marriage", "career", "wealth", "health", "foreign",
                                    "property", "children", "litigation"]
    verdicts = K.event_verdicts(cusps, lons, sig, keys)
    yd = 365.25
    jn = inp.jd
    vim = D.vimshottari(chart.bodies["Moon"].lon, inp.jd, _fmt_date(inp), yd, 3, jn)
    timing = K.timing_windows(vim, verdicts, sig, "", jn, inp.jd, yd, limit_years=5)
    for v in verdicts:
        v["windows"] = timing.get(v["key"], [])
        v["house_text"] = I.kp_house(v["cusp"])
    rp = K.ruling_planets(inp.jd, inp.lat, inp.lon, aya_key, chart.node, inp.offset_used)
    moon_sig = sig["planet"]["Moon"]
    reflection = K.reflection_of_mind(ev_key, sig, cusps) if ev_key else {}
    fort = K.fortuna(cusps[0], chart.bodies["Sun"].lon, chart.bodies["Moon"].lon)
    nk, pd = nakshatra_of(fort)
    planets.append({"name": "Fortuna", "lon": fort, "sign": sign_of(fort), "sign_name": SIGNS[sign_of(fort)],
                    "deg": deg_in_sign(fort), "dms": dms(deg_in_sign(fort)), "nakshatra": NAKSHATRAS[nk],
                    "pada": pd, "nak_lord": NAK_LORD[nk], "retro": False, "kp_house": K._bhava(fort, cusps),
                    **K.kp_lords(fort)})
    pts = chart_points(chart)
    pts["Lagna"] = {"lon": cusps[0], "sign": sign_of(cusps[0])}
    # RP agreement with fruitful significators
    for v in verdicts:
        v["rp_agreement"] = [p for p in v["significators"] if p in rp["ordered"] + rp["nodes"]]
    return {
        "method": "kp_horary", "title": tr("KP Horary: number {n}", n=number),
        "settings": {"ayanamsa": E.AYANAMSAS[aya_key][1], "houses": "Placidus (from horary ascendant)",
                     "node": chart.node},
        "horary": {"number": number, "sub": {k: sub[k] for k in ("sign", "nakshatra", "star_lord",
                                                                  "sub_lord", "from", "to")},
                   "ascendant": f"{dms(deg_in_sign(cusps[0]))} {SIGNS[sign_of(cusps[0])]}",
                   "armc": round(armc, 4), "question": tr(K.EVENTS.get(ev_key, {}).get("label", "General"))},
        "panchang": _clean_pan(pan),
        "planets": planets, "cusps": an["csl"], "cusp_lons": cusps, "points": pts,
        "bhava_of": {**sig["occupancy"], **{p: K._bhava(chart.bodies[p].lon, cusps)
                                            for p in ("Uranus", "Neptune", "Pluto")}},
        "significators": sig, "four_step": an["four_step"],
        "ruling_planets": {"now": rp},
        "events": verdicts,
        "moon_significations": moon_sig, "reflection": reflection,
        "dasha": {"vimshottari": vim},
        "star_texts": {p: I.kp_star(p) for p in GRAHAS},
    }


# ---------------------------------------------------------------- PRASHNA
def prashna(inp: BirthInput, opts: dict, question: str, number: int | None) -> dict:
    chart, pan = base_vedic(inp, opts)
    gul = P.gulika_longitude(chart, inp, pan, "gulika")
    an = PR.analyse(chart, inp, pan, question, number, gul)
    planets = planet_table(chart)
    special = P.special_lagnas(chart, inp, pan)
    return {
        "method": "prashna", "title": tr("Prashna Shastra (Vedic Horary)"),
        "settings": {"ayanamsa": _aya_label(chart), "node": chart.node,
                     "school": "Prashna Marga + Tajika (Neelakanthi)"},
        "panchang": _clean_pan(pan), "planets": planets, "points": chart_points(chart, extra={"Gk": gul}),
        "analysis": an,
        "vargas": {k: v for k, v in varga_charts(chart).items() if k in ("D1", "D9")},
        "houses": house_table(chart),
        "special_lagnas": {k: {"sign": SIGNS[sign_of(v)], "dms": dms(deg_in_sign(v)), "lon": v}
                           for k, v in special.items()},
        "lagna_text": I.prashna_lagna(SIGNS[chart.lagna_sign]),
    }


# ---------------------------------------------------------------- JAIMINI
def jaimini(inp: BirthInput, opts: dict) -> dict:
    chart, pan = base_vedic(inp, opts)
    jn = now_jd()
    special = P.special_lagnas(chart, inp, pan)
    scheme = int(opts.get("karakas", 8))
    j = J.compute(chart, inp, special, _fmt_date(inp), jn, scheme)
    planets = planet_table(chart)
    extra = {"AL": j["arudhas"]["AL"]["sign"] * 30 + 15, "UL": j["arudhas"]["UL"]["sign"] * 30 + 15,
             "HL": special["Hora Lagna"], "GL": special["Ghati Lagna"]}
    vg = varga_charts(chart)
    return {
        "method": "jaimini", "title": tr("Jaimini Sutras Analysis"),
        "settings": {"ayanamsa": _aya_label(chart), "karaka_scheme": tr("{n} karakas", n=scheme),
                     "chara_dasha": "K.N. Rao"},
        "panchang": _clean_pan(pan), "planets": planets,
        "points": chart_points(chart, extra=extra),
        "vargas": {k: v for k, v in vg.items() if k in ("D1", "D9", "D10", "D7", "D20", "D24")},
        "jaimini": j,
        "reading": I.jaimini(j),
    }


# ---------------------------------------------------------------- WESTERN
def western(inp: BirthInput, opts: dict, paschatya: bool = False) -> dict:
    zodiac = opts.get("zodiac", "tropical")
    sid = None
    if zodiac == "sidereal":
        sid = opts.get("ayanamsa") or "fagan_bradley"
    hsys = opts.get("hsys", "P")
    w = W.compute(inp, hsys=hsys, sidereal=sid, node=opts.get("node", "true"),
                  minor=opts.get("minor", True), now_jd=now_jd())
    reading = I.western(w)
    pts = w.pop("_pts")
    cusps = w.pop("_cusps")
    out = {"method": "paschatya" if paschatya else "western",
           "title": tr("Paschatya Jyotish (Western, Sayana)") if paschatya else tr("Western Astrology"),
           "settings": {"zodiac": w["zodiac"], "houses": w["house_system"],
                        "node": opts.get("node", "true")},
           "western": w, "wheel": {"points": pts, "cusps": cusps}, "reading": reading}
    if paschatya:
        # Sayana nakshatra / Indian chart view
        rows = []
        for p in w["planets"]:
            nk, pd = nakshatra_of(p["lon"])
            rows.append({"name": p["name"], "nakshatra": NAKSHATRAS[nk], "pada": pd,
                         "nak_lord": NAK_LORD[nk]})
        out["sayana_nakshatras"] = rows
        asc = w["angles"]["Ascendant"]["lon"]
        ip = {"Lagna": {"lon": asc, "sign": sign_of(asc)}}
        for p in w["planets"]:
            if p["name"] in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
                             "Uranus", "Neptune", "Pluto", "North Node", "South Node"):
                nm = {"North Node": "Rahu", "South Node": "Ketu"}.get(p["name"], p["name"])
                ip[nm] = {"lon": p["lon"], "sign": p["sign"], "retro": p["retro"]}
        out["points"] = ip
    return out


# ---------------------------------------------------------------- VARSHAPHAL
def annual(inp: BirthInput, opts: dict, year: int, residence: dict | None = None) -> dict:
    from . import varshaphal as V
    chart = SiderealChart(inp, ayanamsa=opts.get("ayanamsa") or "lahiri", node=opts.get("node", "mean"))
    v = V.varshaphal(inp, chart, year, residence)
    mu = v["muntha"]["sign"]
    v["points"]["Muntha"] = {"lon": mu * 30 + 15.0, "sign": mu}
    return {"varshaphal": v, "tithi_pravesha": V.tithi_pravesha(inp, chart, year, residence)}


def varshaphal(inp: BirthInput, opts: dict, year: int, residence: dict | None = None) -> dict:
    a = annual(inp, opts, year, residence)
    return {"method": "varshaphal", "title": tr("Varshaphal (Tajika annual chart)"),
            "settings": {"ayanamsa": E.AYANAMSAS[opts.get("ayanamsa") or "lahiri"][1],
                         "year": year}, **a}


# ---------------------------------------------------------------- MATCHING
def matching(boy: BirthInput, girl: BirthInput, opts: dict) -> dict:
    from . import matching as MT
    aya = opts.get("ayanamsa") or "lahiri"
    bc = SiderealChart(boy, ayanamsa=aya, node=opts.get("node", "mean"))
    gc = SiderealChart(girl, ayanamsa=aya, node=opts.get("node", "mean"))
    return {"method": "matching", "title": tr("Marriage matching"),
            "settings": {"ayanamsa": E.AYANAMSAS[aya][1]},
            "matching": MT.match(bc, gc, boy, girl),
            "boy_points": chart_points(bc), "girl_points": chart_points(gc),
            "partner": girl.summary()}


# ---------------------------------------------------------------- MUHURTA / CALENDAR
def muhurta(inp: BirthInput, opts: dict, m: dict, native_inp: BirthInput | None) -> dict:
    from . import muhurta as MU
    native = SiderealChart(native_inp) if native_inp else None
    res = MU.search(m.get("event", "general"), m.get("start_date"), int(m.get("days", 30)),
                    inp.lat, inp.lon, inp.tz, inp.offset, opts.get("ayanamsa") or "lahiri", native,
                    place=inp.place)
    return {"method": "muhurta", "title": tr("Muhurta search"), "settings": {}, "muhurta": res}


def calendar(inp: BirthInput, opts: dict, c: dict) -> dict:
    from . import muhurta as MU
    res = MU.month_panchang(int(c["year"]), int(c["month"]), inp.lat, inp.lon, inp.tz, inp.offset,
                            opts.get("ayanamsa") or "lahiri", place=inp.place)
    return {"method": "calendar", "title": tr("Panchanga calendar"), "settings": {}, "calendar": res}

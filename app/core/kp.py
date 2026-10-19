"""Krishnamurti Paddhati: sub-lord theory, significators, ruling planets,
cuspal sub-lord event analysis and dasha-based timing."""
from __future__ import annotations

from functools import lru_cache

from . import ephemeris as E
from ..i18n import tr
from .constants import (DASHA_ORDER, DASHA_YEARS, GRAHAS, NAK_LORD, NAK_SPAN, NAKSHATRAS,
                        SIGN_LORD, SIGNS, WEEKDAY_LORD, deg_in_sign, dms, norm, sign_of)


def _chain(lon: float, levels: int = 4) -> list[str]:
    """Star lord, sub lord, sub-sub lord, sub-sub-sub lord for a longitude."""
    lon = norm(lon)
    nak = int(lon // NAK_SPAN)
    lord = NAK_LORD[nak]
    start, span = nak * NAK_SPAN, NAK_SPAN
    out = [lord]
    for _ in range(levels - 1):
        i0 = DASHA_ORDER.index(lord)
        pos = lon - start
        acc = 0.0
        for k in range(9):
            sub = DASHA_ORDER[(i0 + k) % 9]
            w = span * DASHA_YEARS[sub] / 120.0
            if pos < acc + w or k == 8:
                start, span, lord = start + acc, w, sub
                break
            acc += w
        out.append(lord)
    return out


def kp_lords(lon: float) -> dict:
    c = _chain(lon, 4)
    return {"sign_lord": SIGN_LORD[sign_of(lon)], "star_lord": c[0], "sub_lord": c[1],
            "sub_sub_lord": c[2], "sss_lord": c[3]}


@lru_cache(maxsize=1)
def sub_table() -> list[dict]:
    """The 249 KP sub divisions (Aries 0° → Pisces 30°), split at sign boundaries."""
    rows = []
    for nak in range(27):
        lord = NAK_LORD[nak]
        i0 = DASHA_ORDER.index(lord)
        t = nak * NAK_SPAN
        for k in range(9):
            sub = DASHA_ORDER[(i0 + k) % 9]
            w = NAK_SPAN * DASHA_YEARS[sub] / 120.0
            a, b = t, t + w
            # split at sign boundaries
            cut = (int(a // 30) + 1) * 30
            pieces = [(a, b)] if b <= cut + 1e-9 else [(a, cut), (cut, b)]
            for pa, pb in pieces:
                rows.append({"start": pa, "end": pb, "sign": SIGNS[int((pa + 1e-9) // 30) % 12],
                             "sign_lord": SIGN_LORD[int((pa + 1e-9) // 30) % 12],
                             "nakshatra": NAKSHATRAS[nak], "star_lord": lord, "sub_lord": sub})
            t = b
    for i, r in enumerate(rows):
        r["no"] = i + 1
        r["from"] = f"{dms(r['start'] % 30)} {r['sign'][:3]}"
        r["to"] = f"{dms(((r['end'] - 1e-9) % 30) + 1e-9)} {r['sign'][:3]}"
    return rows


# --------------------------------------------------------------------- significators
def _bhava(lon: float, cusps: list[float]) -> int:
    lon = norm(lon)
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if (lon - a) % 360 < (b - a) % 360:
            return i + 1
    return 12


def significators(planet_lons: dict[str, float], cusps: list[float]) -> dict:
    planets = [p for p in GRAHAS if p in planet_lons]
    occ = {p: _bhava(planet_lons[p], cusps) for p in planets}
    owns = {p: [] for p in planets}
    for i, c in enumerate(cusps):
        owns[SIGN_LORD[sign_of(c)]].append(i + 1)
    star = {p: _chain(planet_lons[p], 1)[0] for p in planets}
    sign_lord = {p: SIGN_LORD[sign_of(planet_lons[p])] for p in planets}

    # Nodes act as agents: conjoined planets (same sign, within 10°) + sign lord
    agents = {}
    for node in ("Rahu", "Ketu"):
        conj = [q for q in planets if q not in ("Rahu", "Ketu") and
                sign_of(planet_lons[q]) == sign_of(planet_lons[node]) and
                abs(E.angdiff(planet_lons[q], planet_lons[node])) < 10]
        agents[node] = {"conjoined": conj, "sign_lord": sign_lord[node]}

    def own_houses(p):
        h = set(owns[p])
        if p in agents:
            for q in agents[p]["conjoined"] + [agents[p]["sign_lord"]]:
                h |= set(owns.get(q, []))
        return h

    def occ_houses(p):
        h = {occ[p]}
        if p in agents:
            for q in agents[p]["conjoined"] + [agents[p]["sign_lord"]]:
                h.add(occ[q])
        return h

    planet_sig = {}
    for p in planets:
        sl = star[p]
        A = sorted(occ_houses(sl))
        B = sorted({occ[p]})
        C = sorted(own_houses(sl))
        D = sorted(set(owns[p]))
        extra = []
        if p in agents:
            extra = sorted(own_houses(p) | occ_houses(p))
        allh = sorted(set(A) | set(B) | set(C) | set(D) | set(extra))
        planet_sig[p] = {"star_lord": sl, "A_star_occ": A, "B_occ": B, "C_star_own": C,
                         "D_own": D, "node_agent": extra, "all": allh,
                         "self_strength": sl == p, "sign_lord": sign_lord[p]}

    house_sig = {}
    for h in range(1, 13):
        occupants = [p for p in planets if occ[p] == h]
        owners = [p for p in planets if h in owns[p]]
        L1 = [p for p in planets if star[p] in occupants]
        L3 = [p for p in planets if star[p] in owners]
        house_sig[h] = {"L1_in_star_of_occupants": L1, "L2_occupants": occupants,
                        "L3_in_star_of_owner": L3, "L4_owner": owners,
                        "all": _uniq(L1 + occupants + L3 + owners)}
    return {"planet": planet_sig, "house": house_sig, "occupancy": occ, "ownership": owns,
            "node_agents": agents}


def _uniq(xs):
    seen, out = set(), []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# --------------------------------------------------------------------- ruling planets
def ruling_planets(jd: float, lat: float, lon: float, ayanamsa: str, node: str,
                   offset_hours: float) -> dict:
    asc = E.ascendant_at(jd, lat, lon, ayanamsa)
    moon = E.calc_body(jd, "Moon", ayanamsa, node).lon
    st = E.sun_times(jd, lat, lon)
    wd = E.weekday_of_jd(st["sunrise"] + offset_hours / 24.0)
    la, mo = kp_lords(asc), kp_lords(moon)
    rp = {"day_lord": WEEKDAY_LORD[wd],
          "lagna_sign_lord": la["sign_lord"], "lagna_star_lord": la["star_lord"],
          "lagna_sub_lord": la["sub_lord"],
          "moon_sign_lord": mo["sign_lord"], "moon_star_lord": mo["star_lord"],
          "moon_sub_lord": mo["sub_lord"], "asc": asc, "moon": moon}
    core = _uniq([rp["lagna_star_lord"], rp["lagna_sign_lord"], rp["moon_star_lord"],
                  rp["moon_sign_lord"], rp["day_lord"]])
    # Nodes join the RPs when posited in a sign or star owned by an RP
    nodes = []
    rahu = E.calc_body(jd, "Rahu", ayanamsa, node).lon
    for nm, nl in (("Rahu", rahu), ("Ketu", norm(rahu + 180))):
        if SIGN_LORD[sign_of(nl)] in core or _chain(nl, 1)[0] in core:
            nodes.append(nm)
    rp["ordered"] = core
    rp["sub_lords"] = _uniq([rp["lagna_sub_lord"], rp["moon_sub_lord"]])
    rp["nodes"] = nodes
    rp["asc_dms"] = f"{dms(deg_in_sign(asc))} {SIGNS[sign_of(asc)]}"
    rp["moon_dms"] = f"{dms(deg_in_sign(moon))} {SIGNS[sign_of(moon)]}"
    return rp


# --------------------------------------------------------------------- events
EVENTS = {
    "marriage": {"label": "Marriage", "cusp": 7, "good": [2, 7, 11], "bad": [1, 6, 10],
                 "note": "7th CSL signifying 2, 7, 11 promises marriage; 1, 6, 10 (12th to 2/7/11) deny or delay."},
    "career": {"label": "Job / Service", "cusp": 10, "good": [2, 6, 10, 11], "bad": [1, 5, 9, 12],
               "note": "10th CSL connected to 2, 6, 10, 11 shows employment and promotions; 5, 9, 12 indicate breaks or change."},
    "business": {"label": "Business", "cusp": 7, "good": [7, 10, 11, 2], "bad": [6, 8, 12],
                 "note": "Partnership/business: 7th & 10th CSL signifying 2, 7, 10, 11; 6/8/12 dominance suggests service is better."},
    "children": {"label": "Children / Progeny", "cusp": 5, "good": [2, 5, 11], "bad": [1, 4, 10],
                 "note": "5th CSL signifying 2, 5, 11 promises progeny; 1, 4, 10 cause delay/denial."},
    "education": {"label": "Education", "cusp": 4, "good": [4, 9, 11], "bad": [3, 8, 12],
                  "note": "4th CSL connected to 4, 9, 11 supports successful education; 3, 8, 12 indicate breaks."},
    "property": {"label": "Property / House", "cusp": 4, "good": [4, 11, 12], "bad": [3, 5, 10],
                 "note": "4th CSL signifying 4, 11, 12 (investment) favours acquiring property; 3, 5, 10 relate to sale/loss."},
    "vehicle": {"label": "Vehicle", "cusp": 4, "good": [4, 11], "bad": [3, 8, 12],
                "note": "4th CSL with 4 and 11 indicates acquiring vehicles."},
    "foreign": {"label": "Foreign travel / settlement", "cusp": 12, "good": [3, 9, 12], "bad": [2, 4, 11],
                "note": "12th CSL (and 9th) signifying 3, 9, 12 indicates travel and residence abroad; 4 & 11 keep one at home."},
    "wealth": {"label": "Wealth / Finance", "cusp": 2, "good": [2, 6, 11], "bad": [5, 8, 12],
               "note": "2nd CSL signifying 2, 6, 11 builds wealth; 5, 8, 12 indicate expenditure and losses."},
    "gains": {"label": "Income / Gains", "cusp": 11, "good": [2, 6, 11], "bad": [5, 8, 12],
              "note": "11th CSL signifying 2, 6, 11 fulfils desires and gives income."},
    "health": {"label": "Health (disease)", "cusp": 6, "good": [1, 5, 11], "bad": [6, 8, 12],
               "note": "6th CSL signifying 6, 8, 12 points to illness tendency; 1, 5, 11 give recovery."},
    "litigation": {"label": "Litigation / Competition", "cusp": 6, "good": [6, 11, 3], "bad": [5, 8, 12],
                   "note": "6th CSL linked to 6 & 11 gives victory over opponents; 5 & 12 favour the opponent."},
    "love": {"label": "Love affair", "cusp": 5, "good": [5, 7, 11], "bad": [1, 4, 10],
             "note": "5th CSL connected to 5, 7, 11 supports romance culminating in marriage."},
    "fame": {"label": "Fame / Status", "cusp": 10, "good": [10, 11, 1], "bad": [8, 12],
             "note": "10th CSL with 1, 10, 11 grants recognition and authority."},
    "spiritual": {"label": "Spiritual growth", "cusp": 12, "good": [5, 9, 12], "bad": [2, 6, 10, 11],
                  "note": "12th CSL connected to 5, 9, 12 supports moksha/spiritual practice."},
    "siblings": {"label": "Siblings", "cusp": 3, "good": [3, 11], "bad": [2, 10],
                 "note": "3rd CSL signifying 3 & 11 shows support from and gains through siblings."},
    "promotion": {"label": "Promotion / Rise in job", "cusp": 10, "good": [2, 6, 10, 11], "bad": [5, 9, 12],
                  "note": "10th CSL with 2, 6, 10, 11 gives elevation; 5 and 9 (12th to 6 and 10) bring breaks or reversals."},
    "higher_education": {"label": "Higher education", "cusp": 9, "good": [4, 9, 11], "bad": [3, 8, 12],
                         "note": "9th CSL signifying 4, 9, 11 supports higher studies; 3, 8, 12 interrupt them."},
    "competitive_exam": {"label": "Competitive exam / selection", "cusp": 6, "good": [4, 6, 9, 11], "bad": [5, 8, 12],
                         "note": "Success over competitors needs 6 and 11 with 4/9 for learning; 5, 8, 12 deny selection."},
    "speculation": {"label": "Speculation / Shares", "cusp": 5, "good": [2, 5, 11], "bad": [8, 12],
                    "note": "5th CSL connected to 2, 5, 11 gives gains from speculation; 8 and 12 bring losses."},
    "loan": {"label": "Getting a loan", "cusp": 6, "good": [2, 6, 11], "bad": [8, 12],
             "note": "6th CSL signifying 6 and 11 (with 2) sanctions loans; 8 and 12 relate to repayment and losses."},
}


def csl_analysis(cusps: list[float], planet_lons: dict, sig: dict) -> list[dict]:
    rows = []
    for i, c in enumerate(cusps):
        k = kp_lords(c)
        csl = k["sub_lord"]
        ps = sig["planet"][csl]
        rows.append({"cusp": i + 1, "lon": c, "sign": SIGNS[sign_of(c)],
                     "dms": dms(deg_in_sign(c)), **k,
                     "csl_star": ps["star_lord"],
                     "via_star": sorted(set(ps["A_star_occ"]) | set(ps["C_star_own"])),
                     "own": sorted(set(ps["B_occ"]) | set(ps["D_own"])),
                     "all": ps["all"],
                     "csl_sub": kp_lords(planet_lons[csl])["sub_lord"]})
    return rows


def event_verdicts(cusps: list[float], planet_lons: dict, sig: dict, events=None,
                   custom: dict | None = None) -> list[dict]:
    """Verdicts for EVENTS keys, or for one custom {label, cusp, good, bad} event."""
    out = []
    events = events or list(EVENTS.keys())
    items = [("custom", custom)] if custom else [(k, EVENTS[k]) for k in events]
    for key, ev in items:
        c = cusps[ev["cusp"] - 1]
        csl = kp_lords(c)["sub_lord"]
        ps = sig["planet"][csl]
        via_star = set(ps["A_star_occ"]) | set(ps["C_star_own"])
        own = set(ps["B_occ"]) | set(ps["D_own"])
        good = set(ev["good"])
        bad = set(ev["bad"])
        g_star, b_star = via_star & good, via_star & bad
        g_own, b_own = own & good, own & bad
        score = 2 * len(g_star) + len(g_own) - 1.5 * len(b_star) - 0.75 * len(b_own)
        # sub lord of the CSL (confirmation)
        csl_sub = kp_lords(planet_lons[csl])["sub_lord"]
        sub_star_h = set(sig["planet"][csl_sub]["A_star_occ"]) | set(sig["planet"][csl_sub]["C_star_own"])
        score += 0.5 * len(sub_star_h & good) - 0.5 * len(sub_star_h & bad)
        if g_star and score > 0:
            verdict = "Promised" if score >= 2 else "Promised (with conditions)"
        elif score > 0:
            verdict = "Weakly promised"
        elif g_star or g_own:
            verdict = "Mixed / delayed"
        else:
            verdict = "Not strongly indicated"
        # fruitful significators: planets signifying the good houses at L1/L2 (strongest)
        fs = []
        for hh in ev["good"]:
            hs = sig["house"][hh]
            for p in hs["L1_in_star_of_occupants"] + hs["L2_occupants"] + \
                    hs["L3_in_star_of_owner"] + hs["L4_owner"]:
                if p not in fs:
                    fs.append(p)
        out.append({"key": key, "event": tr(ev["label"]), "cusp": ev["cusp"], "csl": csl,
                    "csl_star": ps["star_lord"], "via_star": sorted(via_star), "own": sorted(own),
                    "good_houses": ev["good"], "bad_houses": ev["bad"],
                    "favourable_hits": sorted(g_star | g_own), "adverse_hits": sorted(b_star | b_own),
                    "csl_sub": csl_sub, "score": round(score, 2), "verdict": verdict,
                    "significators": fs, "rule": tr(ev["note"])})
    return out


def timing_windows(dasha: dict, verdicts: list[dict], sig: dict, now_label: str,
                   now_jd: float, birth_jd: float, year_days: float, limit_years: int = 25):
    """Find upcoming Dasha-Bhukti-Antara periods whose lords all signify the event's
    favourable houses (KP timing principle)."""
    from .dasha import _children
    fmt = lambda jd: E.utc_from_jd(jd).strftime("%Y-%m-%d")
    # rebuild MDs with numeric times
    periods = []
    lord0 = dasha["starting_lord"]
    t = birth_jd - (DASHA_YEARS[lord0] - dasha["balance_years"]) * year_days
    i0 = DASHA_ORDER.index(lord0)
    k = 0
    while t < now_jd + limit_years * year_days:
        md = DASHA_ORDER[(i0 + k) % 9]
        dur = DASHA_YEARS[md] * year_days
        if t + dur > now_jd:
            periods.append((md, t, dur))
        t += dur
        k += 1
    res = {}
    horizon = now_jd + limit_years * year_days
    for v in verdicts:
        good = set(v["good_houses"])
        bad = set(v["bad_houses"])
        need = min(2, len(good))

        def hits(p):
            a = set(sig["planet"][p]["all"])
            return len(a & good), len(a & bad)

        def md_ok(p):
            g, _ = hits(p)
            return g >= 1

        def ad_ok(p):
            g, b = hits(p)
            return g >= need and g > b

        def pd_ok(p):
            g, b = hits(p)
            return g >= 1 and g >= b

        wins = []
        for md, t0, dur in periods:
            if not md_ok(md):
                continue
            for ad in _children(md, t0, dur, 2, fmt):
                if ad["_e"] < now_jd or ad["_s"] > horizon or not ad_ok(ad["lord"]):
                    continue
                antaras = [{"lord": pd["lord"], "start": pd["start"], "end": pd["end"]}
                           for pd in ad["children"]
                           if pd["_e"] >= now_jd and pd_ok(pd["lord"])]
                if not antaras:
                    continue
                wins.append({"md": md, "ad": ad["lord"], "start": ad["start"], "end": ad["end"],
                             "antaras": antaras[:3]})
                if len(wins) >= 5:
                    break
            if len(wins) >= 5:
                break
        res[v["key"]] = wins
    return res


def four_step(planet_lons: dict, sig: dict) -> list[dict]:
    """KSK's four-step theory: planet, its star lord, its sub lord, and the sub lord's
    star lord, each with the houses it signifies (occupation + ownership)."""
    ps = sig["planet"]

    def own(p):
        return sorted(set(ps[p]["B_occ"]) | set(ps[p]["D_own"]) | set(ps[p]["node_agent"]))
    rows = []
    for p in ps:
        k = kp_lords(planet_lons[p])
        sl, sub = k["star_lord"], k["sub_lord"]
        sub_star = kp_lords(planet_lons[sub])["star_lord"]
        rows.append({"planet": p, "step1": own(p), "star_lord": sl, "step2": own(sl),
                     "sub_lord": sub, "step3": own(sub), "sub_star_lord": sub_star,
                     "step4": own(sub_star)})
    return rows


def reflection_of_mind(question: str, sig: dict, cusps: list[float]) -> dict:
    """KP horary: the chart is radical when the Moon or the Lagna sub lord signifies the
    houses of the matter asked about."""
    ev = EVENTS.get(question)
    if not ev:
        return {}
    qh = set(ev["good"]) | {ev["cusp"]}
    moon = set(sig["planet"]["Moon"]["all"])
    lcsl = kp_lords(cusps[0])["sub_lord"]
    lh = set(sig["planet"][lcsl]["all"])
    hit_m, hit_l = sorted(moon & qh), sorted(lh & qh)
    return {"question_houses": sorted(qh), "moon_houses": sorted(moon), "moon_hits": hit_m,
            "lagna_csl": lcsl, "lagna_csl_houses": sorted(lh), "lagna_csl_hits": hit_l,
            "reflects": bool(hit_m or hit_l),
            "note": (tr("The question is reflected in the chart: proceed with judgment.")
                     if hit_m or hit_l else
                     tr("Neither the Moon nor the Lagna sub lord signifies the matter. KP advises checking whether the question is sincere, or asking it again later."))}


def fortuna(asc: float, sun: float, moon: float) -> float:
    """KP Pars Fortuna (Asc + Moon − Sun, same formula day and night)."""
    return norm(asc + moon - sun)


def rotate_cusps(cusps: list[float], house: int) -> list[float]:
    k = (max(1, min(12, int(house))) - 1)
    return cusps[k:] + cusps[:k]


def rectify(jd: float, lat: float, lon: float, ayanamsa: str, node: str, offset_hours: float,
            judge_jd: float, window_min: int = 60, step_sec: int = 10) -> dict:
    """Ruling-planet birth-time rectification (K.S. Krishnamurti): within ±window of the
    recorded time, find the spans where the Lagna's sign, star and sub lords are all ruling
    planets at the moment of judgment."""
    rp = ruling_planets(judge_jd, lat, lon, ayanamsa, node, offset_hours)
    R = set(rp["ordered"]) | set(rp["sub_lords"]) | set(rp["nodes"])
    rahu = E.calc_body(jd, "Rahu", ayanamsa, node).lon
    node_sign_lord = {"Rahu": SIGN_LORD[sign_of(rahu)], "Ketu": SIGN_LORD[sign_of(norm(rahu + 180))]}

    def ok(p):
        return p in R or (p in node_sign_lord and node_sign_lord[p] in R)
    step = step_sec / 86400.0
    n = int(window_min * 60 / step_sec)
    spans, cur = [], None
    for i in range(-n, n + 1):
        t = jd + i * step
        asc = E.ascendant_at(t, lat, lon, ayanamsa)
        k = kp_lords(asc)
        full = ok(k["sign_lord"]) and ok(k["star_lord"]) and ok(k["sub_lord"])
        key = (k["sign_lord"], k["star_lord"], k["sub_lord"])
        if full and cur and cur["key"] == key:
            cur["end"], cur["asc_end"] = t, asc
        else:
            if cur:
                spans.append(cur)
            cur = {"key": key, "start": t, "end": t, "asc_start": asc, "asc_end": asc} if full else None
    if cur:
        spans.append(cur)
    out = []
    for sp in spans:
        mid = (sp["start"] + sp["end"]) / 2
        out.append({"sign_lord": sp["key"][0], "star_lord": sp["key"][1], "sub_lord": sp["key"][2],
                    "start": sp["start"], "end": sp["end"], "mid": mid,
                    "offset_min": round((mid - jd) * 1440, 1),
                    "asc_from": f"{dms(deg_in_sign(sp['asc_start']))} {SIGNS[sign_of(sp['asc_start'])]}",
                    "asc_to": f"{dms(deg_in_sign(sp['asc_end']))} {SIGNS[sign_of(sp['asc_end'])]}"})
    out.sort(key=lambda x: abs(x["offset_min"]))
    return {"ruling_planets": sorted(R), "window_min": window_min, "candidates": out[:12]}


def analyse(planet_lons: dict, cusps: list[float]) -> dict:
    sig = significators(planet_lons, cusps)
    csl = csl_analysis(cusps, planet_lons, sig)
    return {"significators": sig, "csl": csl, "four_step": four_step(planet_lons, sig)}

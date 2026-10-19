"""Vedic Prashna (horary) — Prashna Marga & Tajika (Neelakanthi) principles."""
from __future__ import annotations

from .constants import (EXALTATION, GRAHAS, NAKSHATRAS, SEVEN, SIGN_LORD, SIGNS,
                        deg_in_sign, nakshatra_of, norm, sign_of)
from .ephemeris import angdiff
from .vedic import combustion, dignity, DIGNITY_SCORE
from ..i18n import term, terms, tr

SHIRSHODAYA = {2, 4, 5, 6, 7, 10}           # Ge, Le, Vi, Li, Sc, Aq
PRISHTODAYA = {0, 1, 3, 8, 9}               # Ar, Ta, Cn, Sg, Cp
UBHAYODAYA = {11}                           # Pi
DIRECTION = ["East", "South", "West", "North"] * 3
DEEPTAMSA = {"Sun": 15, "Moon": 12, "Mars": 8, "Mercury": 7, "Jupiter": 9, "Venus": 7,
             "Saturn": 9}
TAJIKA_ASPECTS = {0: "conjunction", 60: "sextile (friendly)", 90: "square (inimical)",
                  120: "trine (friendly)", 180: "opposition (inimical)"}

QUESTIONS = {
    "general": {"label": "General / Will it succeed?", "house": 1},
    "marriage": {"label": "Marriage / Relationship", "house": 7},
    "career": {"label": "Job / Career", "house": 10},
    "business": {"label": "Business / Deal", "house": 7},
    "finance": {"label": "Money / Financial gain", "house": 11},
    "health": {"label": "Health / Recovery", "house": 6},
    "children": {"label": "Children / Pregnancy", "house": 5},
    "education": {"label": "Education / Exam", "house": 5},
    "property": {"label": "Property / Vehicle", "house": 4},
    "travel": {"label": "Travel / Foreign", "house": 9},
    "lost": {"label": "Lost article", "house": 2},
    "litigation": {"label": "Litigation / Dispute", "house": 6},
    "return": {"label": "Return of a person", "house": 7},
}


def tajika_relation(a: str, b: str, bodies) -> dict | None:
    """Ithasala (applying) / Ishrafa (separating) between two planets."""
    if a == b or a not in DEEPTAMSA or b not in DEEPTAMSA:
        return None
    la, lb = bodies[a].lon, bodies[b].lon
    va, vb = bodies[a].speed, bodies[b].speed
    orb = (DEEPTAMSA[a] + DEEPTAMSA[b]) / 2
    best = None
    for ang, nm in TAJIKA_ASPECTS.items():
        for sign in ((1, -1) if ang not in (0, 180) else (1,)):
            # gap: how far b must move relative to a to perfect the aspect
            sep = angdiff(lb - la, sign * ang)   # >0: b ahead of exact point
            rel_speed = vb - va
            if abs(sep) > orb:
                continue
            applying = sep * rel_speed < 0
            cand = {"aspect": nm, "angle": ang, "gap": round(abs(sep), 2), "orb": orb,
                    "type": "Ithasala (applying)" if applying else "Ishrafa (separating)",
                    "applying": applying,
                    "days_to_exact": round(abs(sep / rel_speed), 1) if applying and rel_speed else None}
            if best is None or cand["gap"] < best["gap"]:
                best = cand
    return best


def analyse(chart, inp, pan: dict, question: str, number: int | None, gulika: float) -> dict:
    q = QUESTIONS.get(question, QUESTIONS["general"])
    L = chart.lagna_sign
    karya_house = q["house"]
    ks = (L + karya_house - 1) % 12
    ll, kl = SIGN_LORD[L], SIGN_LORD[ks]
    signs = {p: chart.sign(p) for p in SEVEN}
    dig = {p: dignity(p, chart.bodies[p].lon, signs) for p in SEVEN}
    h = {p: chart.house(p) for p in GRAHAS}
    sun = chart.bodies["Sun"].lon
    moon = chart.bodies["Moon"].lon
    factors = []

    def add(score, text):
        factors.append({"score": score, "text": text})

    # 1. Rising sign nature
    if L in SHIRSHODAYA:
        add(+2, tr("Lagna {sg} is Shirshodaya (rises head first): the matter progresses smoothly.", sg=SIGNS[L]))
    elif L in PRISHTODAYA:
        add(-1.5, tr("Lagna {sg} is Prishtodaya (rises hind first): delays or obstacles come before the result.", sg=SIGNS[L]))
    else:
        add(0.5, tr("Lagna {sg} is Ubhayodaya: mixed results, success after effort.", sg=SIGNS[L]))
    mod = ["movable", "fixed", "dual"][L % 3]
    # 2. Lagna lord
    ds = DIGNITY_SCORE[dig[ll]] if ll in dig else 1
    add(round((ds - 1.5) * 0.8, 2), tr("Lagna lord {ll} is in house {hh} with dignity: {dg}.", ll=ll, hh=h[ll], dg=dig.get(ll, "")))
    if h[ll] in (6, 8, 12):
        add(-2, tr("The Lagna lord is in a dusthana ({hh}): the querent is weak or worried about the matter.", hh=h[ll]))
    elif h[ll] in (1, 4, 7, 10, 5, 9):
        add(+1.5, tr("The Lagna lord is in a kendra or trikona ({hh}): the querent has the strength to achieve the goal.", hh=h[ll]))
    comb, _ = combustion(ll, chart.bodies[ll].lon, sun, chart.bodies[ll].retro) if ll != "Sun" else (False, 0)
    if comb:
        add(-1.5, tr("The Lagna lord {ll} is combust: the querent's efforts are eclipsed.", ll=ll))
    # 3. Karya lord
    if kl != ll:
        add(round((DIGNITY_SCORE[dig[kl]] - 1.5) * 0.6, 2),
            tr("The karya (matter) lord {kl}, ruling house {kh}, is in house {hh} with dignity: {dg}.", kl=kl, kh=karya_house, hh=h[kl], dg=dig[kl]))
        if h[kl] in (6, 8, 12):
            add(-1.5, tr("The karya lord is in a dusthana ({hh}): the matter itself is weak or troubled.", hh=h[kl]))
        elif h[kl] in (1, 4, 7, 10, 11):
            add(+1.0, tr("The karya lord is in a kendra or the 11th ({hh}): the matter is supported.", hh=h[kl]))
    else:
        add(+1.0, tr("The Lagna lord also rules the karya bhava ({kh}): the querent controls the outcome.", kh=karya_house))
    # 4. Tajika yoga between lagna lord & karya lord
    taj = tajika_relation(ll, kl, chart.bodies) if ll != kl else None
    if taj:
        if taj["applying"]:
            sc = 2.5 if taj["angle"] in (0, 60, 120) else 1.5
            add(sc, tr("Ithasala: {ll} and {kl} are applying by {asp} (gap {gap}°, orb {orb}°), so the matter will materialise.", ll=ll, kl=kl, asp=tr(taj["aspect"]), gap=taj["gap"], orb=taj["orb"])
                + (" " + tr("It will need effort and may involve conflict.") if taj["angle"] in (90, 180) else ""))
        else:
            add(-2.0, tr("Ishrafa: {ll} and {kl} are separating by {asp}, so the opportunity has passed or will slip away.", ll=ll, kl=kl, asp=tr(taj["aspect"])))
    else:
        add(-0.5, tr("There is no Tajika aspect between the Lagna lord {ll} and the karya lord {kl}.", ll=ll, kl=kl))
    # 5. Moon
    mh = h["Moon"]
    elong = norm(moon - sun)
    waxing = elong < 180
    add(1.0 if waxing else -0.5, tr("The Moon is waxing ({d}° from the Sun).", d=round(elong, 1)) if waxing else tr("The Moon is waning ({d}° from the Sun).", d=round(elong, 1)))
    if mh in (6, 8, 12):
        add(-1.5, tr("The Moon is in house {mh}, a dusthana: the mind is anxious and the outcome uncertain.", mh=mh))
    elif mh in (1, 4, 7, 10, 5, 9, 11):
        add(+1.0, tr("The Moon in house {mh} supports the query.", mh=mh))
    taj_m = tajika_relation("Moon", kl, chart.bodies) if kl != "Moon" else None
    if taj_m and taj_m["applying"]:
        add(1.5, tr("The Moon is applying to the karya lord {kl} ({asp}): help arrives through others, a translation of light.", kl=kl, asp=tr(taj_m["aspect"])))
    # 6. Benefics/malefics distribution
    bens = [p for p in ("Jupiter", "Venus", "Mercury") if h[p] in (1, 4, 7, 10, 5, 9)]
    mals = [p for p in ("Saturn", "Mars", "Rahu", "Ketu", "Sun") if h[p] in (1, 7, 8, 4, 10)]
    mals_good = [p for p in ("Saturn", "Mars", "Rahu", "Sun") if h[p] in (3, 6, 11)]
    if bens:
        add(0.8 * len(bens), tr("Benefics in kendras or trikonas: {ps}.", ps=terms(bens)))
    if mals:
        add(-0.7 * len(mals), tr("Malefics in kendras or the 8th: {ps}.", ps=terms(mals)))
    if mals_good:
        add(0.5 * len(mals_good), tr("Malefics in upachayas (3, 6, 11): {ps}. They help overcome obstacles.", ps=terms(mals_good)))
    if h["Jupiter"] in (1, 5, 7, 9):   # in lagna or casting 5th/7th/9th aspect on it
        add(1.0, tr("Jupiter occupies or aspects the Lagna: protection and good counsel."))
    # 7. Panchanga at prashna
    tithi_idx = pan["tithi_index"]
    if tithi_idx in (4, 9, 14, 19, 24, 29):
        add(-1.0, tr("Rikta tithi ({t}): an empty tithi, so tasks tend not to bear fruit.", t=pan["tithi"]))
    if tithi_idx == 30:
        add(-1.0, tr("Amavasya at the time of the query: low vitality for new matters."))
    if pan["karana"] == "Vishti":
        add(-1.0, tr("Vishti (Bhadra) karana: obstacles."))
    # Arudha (from number)
    arudha = None
    if number:
        n = max(1, min(108, int(number)))
        a_sign = (n - 1) // 9
        arudha = {"number": n, "sign": SIGNS[a_sign], "navamsa": (n - 1) % 9 + 1,
                  "house_from_lagna": (a_sign - L) % 12 + 1}
        rel = (a_sign - L) % 12 + 1
        if rel in (1, 4, 7, 10, 5, 9, 11):
            add(1.0, tr("The Arudha ({sg}) falls in house {rel} from the Udaya lagna: the question and the moment are in harmony.", sg=SIGNS[a_sign], rel=rel))
        elif rel in (6, 8, 12):
            add(-1.0, tr("The Arudha falls in house {rel} from the Udaya lagna: the question and the moment are in discord.", rel=rel))
    # Sphutas
    tri = norm(chart.asc + moon + gulika)
    chatus = norm(tri + sun)
    pancha = norm(chatus + chart.bodies["Rahu"].lon)

    def sp(x):
        nk, pd = nakshatra_of(x)
        return {"lon": x, "sign": SIGNS[sign_of(x)], "deg": round(deg_in_sign(x), 3),
                "nakshatra": NAKSHATRAS[nk], "pada": pd}
    total = sum(f["score"] for f in factors)
    pct = max(5, min(95, round(50 + total * 6)))
    if pct >= 65:
        verdict = tr("Favourable: success is indicated")
    elif pct >= 50:
        verdict = tr("Moderately favourable: success with effort")
    elif pct >= 35:
        verdict = tr("Mixed: delays or partial success")
    else:
        verdict = tr("Unfavourable at present")
    timing = None
    if taj and taj["applying"]:
        timing = {"movable": tr("About {n} days (Tajika rule: degrees left to perfect the aspect, counted in days because the Lagna is movable).", n=taj["gap"]),
                  "dual": tr("About {n} weeks (Tajika rule: degrees left to perfect the aspect, counted in weeks because the Lagna is dual).", n=taj["gap"]),
                  "fixed": tr("About {n} months (Tajika rule: degrees left to perfect the aspect, counted in months because the Lagna is fixed).", n=taj["gap"])}[mod]
    extra = {}
    if question == "lost":
        extra = {
            "direction": term(DIRECTION[chart.sign(SIGN_LORD[(L + 1) % 12])]),
            "recovery": {"movable": tr("The article has moved away; recovery is difficult unless the 2nd and 11th are strong."),
                         "fixed": tr("The article is nearby, inside the premises; there is a good chance of recovery."),
                         "dual": tr("The article has shifted a short distance; recovery is partial or delayed.")}[mod],
            "thief_or_misplaced": tr("Probably misplaced by the querent") if h[ll] in (1, 2, 4) else tr("Possibly taken by someone else"),
        }
    return {
        "question": tr(q["label"]), "karya_house": karya_house, "karya_sign": SIGNS[ks],
        "lagna": SIGNS[L], "lagna_nature": mod,
        "rising": "Shirshodaya" if L in SHIRSHODAYA else ("Prishtodaya" if L in PRISHTODAYA else "Ubhayodaya"),
        "lagna_lord": ll, "karya_lord": kl, "tajika": taj, "moon_tajika": taj_m,
        "arudha": arudha, "factors": factors, "score": round(total, 2), "probability": pct,
        "verdict": verdict, "timing": timing,
        "sphutas": {"Trisphuta": sp(tri), "Chatussphuta": sp(chatus), "Panchasphuta": sp(pancha),
                    "Gulika": sp(gulika)},
        "tajika_matrix": _tajika_matrix(chart.bodies),
        "extra": extra,
    }


def _tajika_matrix(bodies) -> list[dict]:
    out = []
    for i, a in enumerate(SEVEN):
        for b in SEVEN[i + 1:]:
            r = tajika_relation(a, b, bodies)
            if r:
                out.append({"a": a, "b": b, **r})
    return out

"""Shadbala (six-fold planetary strength) and Bhava Bala — BPHS ch. 27 /
B.V. Raman 'Graha and Bhava Balas'. Values are in shashtiamsas (virupas)."""
from __future__ import annotations

import math

from . import ephemeris as E
from .constants import (DEBILITATION, SEVEN, SIGN_LORD, WEEKDAY_LORD, deg_in_sign,
                        norm, sign_of)
from .vargas import varga_sign
from .vedic import compound_relation, is_moolatrikona, sphuta_drishti

DEEP_EXALT = {"Sun": 10, "Moon": 33, "Mars": 298, "Mercury": 165, "Jupiter": 95,
              "Venus": 357, "Saturn": 200}
NAISARGIKA = {"Sun": 60.0, "Moon": 51.43, "Venus": 42.86, "Jupiter": 34.29,
              "Mercury": 25.71, "Mars": 17.14, "Saturn": 8.57}
REQUIRED_RUPA = {"Sun": 6.5, "Moon": 6.0, "Mars": 5.0, "Mercury": 7.0, "Jupiter": 6.5,
                 "Venus": 5.5, "Saturn": 5.0}
SAPTA_VARGAS = [1, 2, 3, 7, 9, 12, 30]
REL_VALUE = {2: 22.5, 1: 15.0, 0: 7.5, -1: 3.75, -2: 1.875}
KALI_EPOCH_JD = 588465.5  # Friday, 18 Feb 3102 BCE (Julian), Ujjain midnight


def _arc(a: float, b: float) -> float:
    d = abs(norm(a) - norm(b))
    return 360 - d if d > 180 else d


def _mercury_benefic(chart) -> bool:
    ms = chart.sign("Mercury")
    return not any(chart.sign(m) == ms for m in ("Mars", "Saturn", "Rahu", "Ketu"))


def compute(chart, inp, pan: dict) -> dict:
    lon = {p: chart.bodies[p].lon for p in SEVEN}
    signs = {p: sign_of(lon[p]) for p in SEVEN}
    res = {p: {} for p in SEVEN}

    # ---------------- Sthana bala
    for p in SEVEN:
        deb = norm(DEEP_EXALT[p] + 180)
        uchcha = _arc(lon[p], deb) / 3.0
        sv = 0.0
        sv_detail = {}
        for n in SAPTA_VARGAS:
            vs = varga_sign(lon[p], n)
            lord = SIGN_LORD[vs]
            if n == 1 and is_moolatrikona(p, lon[p]):
                v = 45.0
            elif lord == p:
                v = 30.0
            else:
                v = REL_VALUE[compound_relation(p, lord, signs)]
            sv += v
            sv_detail[f"D{n}"] = v
        nav = varga_sign(lon[p], 9)
        if p in ("Moon", "Venus"):
            oja = (15 if signs[p] % 2 == 1 else 0) + (15 if nav % 2 == 1 else 0)
        else:
            oja = (15 if signs[p] % 2 == 0 else 0) + (15 if nav % 2 == 0 else 0)
        h = chart.house(p)
        kendra = 60 if h in (1, 4, 7, 10) else (30 if h in (2, 5, 8, 11) else 15)
        dk = int(deg_in_sign(lon[p]) // 10)
        drek = 15 if ((p in ("Sun", "Mars", "Jupiter") and dk == 0) or
                      (p in ("Mercury", "Saturn") and dk == 1) or
                      (p in ("Moon", "Venus") and dk == 2)) else 0
        res[p]["sthana"] = {"uchcha": uchcha, "saptavargaja": sv, "ojayugma": oja,
                            "kendradi": kendra, "drekkana": drek,
                            "total": uchcha + sv + oja + kendra + drek,
                            "saptavarga_detail": sv_detail}

    # ---------------- Dig bala
    asc, mc = chart.asc, chart.mc
    weak = {"Sun": mc + 180, "Mars": mc + 180, "Jupiter": asc + 180, "Mercury": asc + 180,
            "Saturn": asc, "Moon": mc, "Venus": mc}
    for p in SEVEN:
        res[p]["dig"] = _arc(lon[p], weak[p]) / 3.0

    # ---------------- Kala bala
    jd = inp.jd
    lst_deg = E.sidereal_time(jd, inp.lon) * 15.0
    ha = norm(lst_deg - chart.bodies["Sun"].ra)          # hour angle, 0 = noon
    from_noon = ha if ha <= 180 else 360 - ha
    day_strength = (180 - from_noon) / 3.0               # 60 at noon, 0 at midnight
    elong = norm(lon["Moon"] - lon["Sun"])
    pk_angle = elong if elong <= 180 else 360 - elong
    merc_ben = _mercury_benefic(chart)
    sr, ss, nsr = pan["_sunrise_jd"], pan["_sunset_jd"], pan["_next_sunrise_jd"]
    if sr <= jd < ss:
        third = int((jd - sr) / ((ss - sr) / 3))
        tri_lord = ["Mercury", "Sun", "Saturn"][min(third, 2)]
    else:
        third = int((jd - ss) / ((nsr - ss) / 3))
        tri_lord = ["Moon", "Venus", "Mars"][min(third, 2)]
    # Abda/Masa lords from Kali ahargana (360-day years, 30-day months)
    ahar = int(math.floor(sr + inp.offset_used / 24.0 + 0.5) - math.floor(KALI_EPOCH_JD + 0.5))
    abda_wd = (5 + (ahar // 360) * 360) % 7
    masa_wd = (5 + (ahar // 30) * 30) % 7
    abda_lord, masa_lord = WEEKDAY_LORD[abda_wd], WEEKDAY_LORD[masa_wd]
    vara_lord = pan["vara_lord"]
    hora_lord = pan["hora_lord"]
    eps = chart.eps
    for p in SEVEN:
        if p == "Mercury":
            nat = 60.0
        elif p in ("Sun", "Jupiter", "Venus"):
            nat = day_strength
        else:
            nat = 60.0 - day_strength
        benefic = p in ("Jupiter", "Venus", "Moon") or (p == "Mercury" and merc_ben)
        paksha = pk_angle / 3.0 if benefic else 60.0 - pk_angle / 3.0
        if p == "Moon":
            paksha *= 2
        tri = 60.0 if (p == tri_lord or p == "Jupiter") else 0.0
        abda = 15.0 if p == abda_lord else 0.0
        masa = 30.0 if p == masa_lord else 0.0
        vara = 45.0 if p == vara_lord else 0.0
        hora = 60.0 if p == hora_lord else 0.0
        trop = norm(lon[p] + chart.aya)
        kranti = math.degrees(math.asin(math.sin(math.radians(eps)) *
                                        math.sin(math.radians(trop))))
        if p in ("Sun", "Mars", "Jupiter", "Venus"):
            ayana = (24 + kranti) / 48 * 60
        elif p in ("Moon", "Saturn"):
            ayana = (24 - kranti) / 48 * 60
        else:
            ayana = (24 + abs(kranti)) / 48 * 60
        if p == "Sun":
            ayana *= 2
        res[p]["kala"] = {"natonnata": nat, "paksha": paksha, "tribhaga": tri, "abda": abda,
                          "masa": masa, "vara": vara, "hora": hora, "ayana": ayana,
                          "yuddha": 0.0}
        res[p]["_kranti"] = kranti

    # ---------------- Chesta bala
    ml = E.mean_longitudes(jd)
    trop_true = {p: norm(lon[p] + chart.aya) for p in SEVEN}
    for p in SEVEN:
        if p == "Sun":      # Sun's chesta = its (undoubled) ayana bala
            ch = res[p]["kala"]["ayana"] / 2
        elif p == "Moon":   # Moon's chesta = its (undoubled) paksha bala
            ch = res[p]["kala"]["paksha"] / 2
        else:
            if p in ("Mars", "Jupiter", "Saturn"):
                sighra, madhya = ml["Sun"], ml[p]
            else:
                sighra, madhya = ml[p], ml["Sun"]
            ck = norm(sighra - (madhya + trop_true[p]) / 2.0)
            if ck > 180:
                ck = 360 - ck
            ch = ck / 3.0
        res[p]["chesta"] = ch
        res[p]["naisargika"] = NAISARGIKA[p]

    # ---------------- Drik bala
    moon_waxing = elong < 180
    for p in SEVEN:
        tot = 0.0
        for q in SEVEN:
            if q == p:
                continue
            v = sphuta_drishti(lon[p] - lon[q], q)
            ben = q in ("Jupiter", "Venus") or (q == "Mercury" and merc_ben) or \
                (q == "Moon" and moon_waxing)
            tot += v if ben else -v
        res[p]["drik"] = tot / 4.0

    # ---------------- Yuddha (planetary war among Mars..Saturn within 1°)
    war = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    wars = []
    for i, a in enumerate(war):
        for b in war[i + 1:]:
            if _arc(lon[a], lon[b]) < 1.0:
                la, lb = chart.bodies[a].lat, chart.bodies[b].lat
                win, lose = (a, b) if la >= lb else (b, a)
                def base(x):
                    k = res[x]["kala"]
                    return (res[x]["sthana"]["total"] + res[x]["dig"] +
                            sum(v for kk, v in k.items() if kk != "yuddha"))
                diff = abs(base(win) - base(lose))
                res[win]["kala"]["yuddha"] += diff
                res[lose]["kala"]["yuddha"] -= diff
                wars.append({"winner": win, "loser": lose, "value": round(diff, 2)})

    # ---------------- totals
    rows = []
    for p in SEVEN:
        r = res[p]
        kala_total = sum(r["kala"].values())
        r["kala"]["total"] = kala_total
        total = r["sthana"]["total"] + r["dig"] + kala_total + r["chesta"] + \
            r["naisargika"] + r["drik"]
        rupa = total / 60.0
        uch = r["sthana"]["uchcha"]
        ch = min(r["chesta"], 60.0)
        ishta = math.sqrt(max(uch, 0) * max(ch, 0))
        kashta = math.sqrt(max(60 - uch, 0) * max(60 - ch, 0))
        rows.append({
            "planet": p,
            "sthana": _r(r["sthana"]), "dig": round(r["dig"], 2), "kala": _r(r["kala"]),
            "chesta": round(r["chesta"], 2), "naisargika": r["naisargika"],
            "drik": round(r["drik"], 2), "total_virupa": round(total, 2),
            "rupa": round(rupa, 2), "required": REQUIRED_RUPA[p],
            "ratio": round(rupa / REQUIRED_RUPA[p], 3), "ishta": round(ishta, 2),
            "kashta": round(kashta, 2),
        })
    for i, row in enumerate(sorted(rows, key=lambda x: -x["ratio"])):
        row["rank"] = i + 1
    totals = {row["planet"]: row["total_virupa"] for row in rows}
    bhava = bhava_bala(chart, totals, merc_ben, moon_waxing)
    return {"planets": rows, "wars": wars, "bhava": bhava,
            "meta": {"abda_lord": abda_lord, "masa_lord": masa_lord, "vara_lord": vara_lord,
                     "hora_lord": hora_lord, "tribhaga_lord": tri_lord,
                     "mercury_benefic": merc_ben}}


def _r(d: dict) -> dict:
    return {k: (round(v, 2) if isinstance(v, (int, float)) else v) for k, v in d.items()}


def _bhava_category(lon: float) -> str:
    s, d = sign_of(lon), deg_in_sign(lon)
    if s in (2, 5, 6, 10) or (s == 8 and d < 15):
        return "nara"
    if s in (3, 11) or (s == 9 and d >= 15):
        return "jala"
    if s == 7:
        return "keeta"
    return "chatushpada"


def bhava_bala(chart, totals: dict, merc_ben: bool, moon_waxing: bool) -> list[dict]:
    madhya = chart.bhava_madhya
    out = []
    strong_house = {"nara": 0, "jala": 3, "keeta": 6, "chatushpada": 9}
    for h in range(12):
        m = madhya[h]
        lord = SIGN_LORD[sign_of(m)]
        adhipati = totals.get(lord, 0.0)
        cat = _bhava_category(m)
        weak_point = madhya[(strong_house[cat] + 6) % 12]
        dig = _arc(m, weak_point) / 3.0
        dr = 0.0
        for q in SEVEN:
            v = sphuta_drishti(m - chart.bodies[q].lon, q)
            if q in ("Jupiter",) or (q == "Mercury" and merc_ben):
                dr += v
            elif q == "Venus" or (q == "Moon" and moon_waxing):
                dr += v / 4
            else:
                dr -= v / 4
        total = adhipati + dig + dr
        out.append({"house": h + 1, "lord": lord, "adhipati": round(adhipati, 2),
                    "dig": round(dig, 2), "drishti": round(dr, 2),
                    "total_virupa": round(total, 2), "rupa": round(total / 60, 2)})
    for i, row in enumerate(sorted(out, key=lambda x: -x["total_virupa"])):
        row["rank"] = i + 1
    return out

"""Ashtakavarga (BPHS ch. 66-72): Bhinnashtakavarga, Sarvashtakavarga, reductions, pindas."""
from __future__ import annotations

from .constants import SEVEN, SIGN_LORD, SIGNS

REFS = SEVEN + ["Lagna"]

# Benefic places (houses counted from each reference) contributed to each planet's BAV
BAV_RULES = {
    "Sun": {"Sun": [1, 2, 4, 7, 8, 9, 10, 11], "Moon": [3, 6, 10, 11],
            "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [3, 5, 6, 9, 10, 11, 12],
            "Jupiter": [5, 6, 9, 11], "Venus": [6, 7, 12],
            "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [3, 4, 6, 10, 11, 12]},
    "Moon": {"Sun": [3, 6, 7, 8, 10, 11], "Moon": [1, 3, 6, 7, 10, 11],
             "Mars": [2, 3, 5, 6, 9, 10, 11], "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
             "Jupiter": [1, 4, 7, 8, 10, 11, 12], "Venus": [3, 4, 5, 7, 9, 10, 11],
             "Saturn": [3, 5, 6, 11], "Lagna": [3, 6, 10, 11]},
    "Mars": {"Sun": [3, 5, 6, 10, 11], "Moon": [3, 6, 11], "Mars": [1, 2, 4, 7, 8, 10, 11],
             "Mercury": [3, 5, 6, 11], "Jupiter": [6, 10, 11, 12], "Venus": [6, 8, 11, 12],
             "Saturn": [1, 4, 7, 8, 9, 10, 11], "Lagna": [1, 3, 6, 10, 11]},
    "Mercury": {"Sun": [5, 6, 9, 11, 12], "Moon": [2, 4, 6, 8, 10, 11],
                "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
                "Jupiter": [6, 8, 11, 12], "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
                "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [1, 2, 4, 6, 8, 10, 11]},
    "Jupiter": {"Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11], "Moon": [2, 5, 7, 9, 11],
                "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
                "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11], "Venus": [2, 5, 6, 9, 10, 11],
                "Saturn": [3, 5, 6, 12], "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11]},
    "Venus": {"Sun": [8, 11, 12], "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
              "Mars": [3, 5, 6, 9, 11, 12], "Mercury": [3, 5, 6, 9, 11],
              "Jupiter": [5, 8, 9, 10, 11], "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
              "Saturn": [3, 4, 5, 8, 9, 10, 11], "Lagna": [1, 2, 3, 4, 5, 8, 9, 11]},
    "Saturn": {"Sun": [1, 2, 4, 7, 8, 10, 11], "Moon": [3, 6, 11],
               "Mars": [3, 5, 6, 10, 11, 12], "Mercury": [6, 8, 9, 10, 11, 12],
               "Jupiter": [5, 6, 11, 12], "Venus": [6, 11, 12], "Saturn": [3, 5, 6, 11],
               "Lagna": [1, 3, 4, 6, 10, 11]},
}

RASHI_GUNA = [7, 10, 8, 4, 10, 5, 7, 8, 9, 5, 11, 12]
GRAHA_GUNA = {"Sun": 5, "Moon": 5, "Mars": 8, "Mercury": 5, "Jupiter": 10, "Venus": 7,
              "Saturn": 5}


def bhinna(signs: dict[str, int]) -> dict:
    """signs: planet/Lagna → sign index. Returns {planet: {"bindus":[12], "detail": {ref:[12]}}}"""
    out = {}
    for p in SEVEN:
        tot = [0] * 12
        detail = {}
        for ref in REFS:
            row = [0] * 12
            for h in BAV_RULES[p][ref]:
                s = (signs[ref] + h - 1) % 12
                row[s] = 1
                tot[s] += 1
            detail[ref] = row
        out[p] = {"bindus": tot, "total": sum(tot), "detail": detail}
    return out


def trikona_shodhana(b: list[int]) -> list[int]:
    r = b[:]
    for g in range(4):
        idx = [g, g + 4, g + 8]
        vals = [r[i] for i in idx]
        if 0 in vals:
            continue
        if vals[0] == vals[1] == vals[2]:
            for i in idx:
                r[i] = 0
        else:
            m = min(vals)
            for i in idx:
                r[i] -= m
    return r


EKADHI_PAIRS = [(0, 7), (1, 6), (2, 5), (8, 11), (9, 10)]


def ekadhipatya_shodhana(b: list[int], occupied: set[int]) -> list[int]:
    r = b[:]
    for a, c in EKADHI_PAIRS:
        va, vc = r[a], r[c]
        oa, oc = a in occupied, c in occupied
        if va == 0 or vc == 0:
            continue
        if oa and oc:
            continue
        if not oa and not oc:
            if va == vc:
                r[a] = r[c] = 0
            else:
                r[a] = r[c] = min(va, vc)
            continue
        occ, emp = (a, c) if oa else (c, a)
        if r[occ] > r[emp]:
            r[emp] = 0
        elif r[occ] < r[emp]:
            r[emp] = r[occ]
        else:
            r[emp] = 0
    return r


def compute(signs: dict[str, int], lagna_sign: int) -> dict:
    bav = bhinna(signs)
    sav = [sum(bav[p]["bindus"][s] for p in SEVEN) for s in range(12)]
    occupied = {signs[p] for p in SEVEN}
    reductions = {}
    for p in SEVEN:
        t = trikona_shodhana(bav[p]["bindus"])
        e = ekadhipatya_shodhana(t, occupied)
        rp = sum(e[s] * RASHI_GUNA[s] for s in range(12))
        gp = sum(e[signs[q]] * GRAHA_GUNA[q] for q in SEVEN)
        reductions[p] = {"trikona": t, "ekadhipatya": e, "rashi_pinda": rp,
                         "graha_pinda": gp, "shodhya_pinda": rp + gp}
    # SAV by house from lagna
    sav_house = [sav[(lagna_sign + h) % 12] for h in range(12)]
    analysis = []
    for h in range(12):
        v = sav_house[h]
        q = "Strong" if v >= 30 else ("Average" if v >= 25 else "Weak")
        analysis.append({"house": h + 1, "sign": SIGNS[(lagna_sign + h) % 12], "bindus": v,
                         "quality": q})
    kakshya_lords = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Lagna"]
    return {
        "bav": {p: {"bindus": bav[p]["bindus"], "total": bav[p]["total"],
                    "detail": bav[p]["detail"]} for p in SEVEN},
        "sav": sav, "sav_total": sum(sav), "sav_by_house": analysis,
        "reductions": reductions, "kakshya_order": kakshya_lords,
        "notes": {
            "wealth_ratio_11_vs_12": f"{sav_house[10]} vs {sav_house[11]}",
            "kendra_total": sav_house[0] + sav_house[3] + sav_house[6] + sav_house[9],
            "trikona_total": sav_house[0] + sav_house[4] + sav_house[8],
            "dusthana_total": sav_house[5] + sav_house[7] + sav_house[11],
        },
    }

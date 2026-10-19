"""Panchanga, Avakahada Chakra, Hora, Ghati, Rahu Kaal etc."""
from __future__ import annotations

import math

import swisseph as swe

from . import ephemeris as E
from ..i18n import lang, tr
from .constants import (HORA_SEQ, KARANAS_MOVABLE, NAK_GANA, NAK_LORD, NAK_NADI,
                        NAK_SYLLABLES, NAK_SYLLABLES_TE, NAK_YONI, NAKSHATRAS, NAK_SPAN, SIGN_LORD,
                        SIGN_VARNA, SIGN_VASHYA, SIGNS, TITHIS, WEEKDAY_LORD, WEEKDAYS,
                        YOGAS, ELEMENT, nakshatra_of, norm, sign_of)

MASAS = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada", "Ashwin",
         "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna"]
SAMVATSARAS = ["Prabhava", "Vibhava", "Shukla", "Pramoda", "Prajapati", "Angirasa", "Shrimukha",
               "Bhava", "Yuva", "Dhatri", "Ishvara", "Bahudhanya", "Pramathi", "Vikrama",
               "Vrisha", "Chitrabhanu", "Svabhanu", "Tarana", "Parthiva", "Vyaya", "Sarvajit",
               "Sarvadhari", "Virodhi", "Vikriti", "Khara", "Nandana", "Vijaya", "Jaya",
               "Manmatha", "Durmukhi", "Hevilambi", "Vilambi", "Vikari", "Sharvari", "Plava",
               "Shubhakrit", "Shobhakrit", "Krodhi", "Vishvavasu", "Parabhava", "Plavanga",
               "Kilaka", "Saumya", "Sadharana", "Virodhikrit", "Paridhavi", "Pramadicha",
               "Ananda", "Rakshasa", "Nala", "Pingala", "Kalayukti", "Siddharthi", "Raudra",
               "Durmati", "Dundubhi", "Rudhirodgari", "Raktakshi", "Krodhana", "Akshaya"]


def karana_name(k: int) -> str:
    if k == 0:
        return "Kimstughna"
    if k >= 57:
        return ["Shakuni", "Chatushpada", "Naga"][k - 57]
    return KARANAS_MOVABLE[(k - 1) % 7]


def _sun_moon(jd: float, aya: str):
    s = E.calc_body(jd, "Sun", aya).lon
    m = E.calc_body(jd, "Moon", aya).lon
    return s, m


def _elongation(jd: float) -> float:
    s = E.calc_body(jd, "Sun", None).lon
    m = E.calc_body(jd, "Moon", None).lon
    return norm(m - s)


def _find_elong_time(jd: float, target: float, forward: bool) -> float:
    """Nearest time (before/after jd) when Moon-Sun elongation == target."""
    step = 0.5 if forward else -0.5
    t = jd
    f = lambda x: E.angdiff(_elongation(x), target)
    prev = f(t)
    for _ in range(80):
        t2 = t + step
        cur = f(t2)
        if (prev <= 0 < cur) or (prev >= 0 > cur) if abs(cur - prev) < 180 else False:
            lo, hi = (t, t2) if t < t2 else (t2, t)
            return E.find_crossing(f, lo, hi)
        t, prev = t2, cur
    return jd


def _find_moon_nak_time(jd: float, boundary: float, forward: bool, aya: str) -> float:
    f = lambda x: E.angdiff(E.calc_body(x, "Moon", aya).lon, boundary)
    step = 0.25 if forward else -0.25
    t, prev = jd, f(jd)
    for _ in range(40):
        t2 = t + step
        cur = f(t2)
        if abs(cur - prev) < 180 and ((prev <= 0 < cur) or (prev >= 0 > cur)):
            lo, hi = (t, t2) if t < t2 else (t2, t)
            return E.find_crossing(f, lo, hi)
        t, prev = t2, cur
    return jd


def lunar_month(jd: float, aya: str) -> dict:
    """Amanta lunar month (new-moon to new-moon), with Adhika detection."""
    nm_prev = _find_elong_time(jd, 0.0, forward=False)
    nm_next = _find_elong_time(jd + 0.5, 0.0, forward=True)
    s1 = sign_of(E.calc_body(nm_prev, "Sun", aya).lon)
    s2 = sign_of(E.calc_body(nm_next, "Sun", aya).lon)
    adhika = s1 == s2
    idx = (s1 + 1) % 12
    return {"masa": MASAS[idx], "adhika": adhika, "new_moon_prev": nm_prev,
            "new_moon_next": nm_next}


def samvatsara(jd: float, aya: str) -> str:
    """60-year cycle (north Indian Jovian/Chandra-based approximation via Saka year)."""
    y, m, d, _ = swe.revjul(jd)
    lm = lunar_month(jd, aya)
    # Chaitra begins the year; months Chaitra..Phalguna belong to the year starting that spring
    year = y if (m > 3 or (m <= 4 and lm["masa"] in MASAS[:3])) else y - 1
    if m <= 3 and lm["masa"] in MASAS[9:]:
        year = y - 1
    saka = year - 78
    return SAMVATSARAS[(saka + 11) % 60]


def compute(chart, inp) -> dict:
    aya = chart.ayanamsa
    jd = inp.jd
    sun = chart.bodies["Sun"].lon
    moon = chart.bodies["Moon"].lon
    elong = norm(moon - sun)
    tithi_i = int(elong // 12)
    yoga_val = norm(sun + moon)
    yoga_i = int(yoga_val // NAK_SPAN)
    kar_i = int(elong // 6)
    nak_i, pada = nakshatra_of(moon)

    st = chart.sun
    sr, ss, nsr = st["sunrise"], st["sunset"], st["next_sunrise"]
    # Vedic weekday runs sunrise to sunrise
    local_sr = sr + inp.offset_used / 24.0
    vara_i = E.weekday_of_jd(local_sr)
    day_len = (nsr - sr) if nsr else 1.0
    hora_i = int((jd - sr) * 24 / day_len)
    hora_lord = HORA_SEQ[(HORA_SEQ.index(WEEKDAY_LORD[vara_i]) + hora_i) % 7]
    is_day = sr <= jd < ss
    ghati = (jd - sr) * 60.0
    # tithi / nakshatra end times
    tithi_end = _find_elong_time(jd, (tithi_i + 1) * 12 % 360, forward=True)
    tithi_start = _find_elong_time(jd, tithi_i * 12.0, forward=False)
    nak_end = _find_moon_nak_time(jd, ((nak_i + 1) * NAK_SPAN) % 360, True, aya)
    nak_start = _find_moon_nak_time(jd, nak_i * NAK_SPAN, False, aya)

    # Rahu Kaal / Yamaganda / Gulika Kaal (day octants)
    octant = (ss - sr) / 8 if ss else 1 / 16
    rk_idx = [8, 2, 7, 5, 6, 4, 3][vara_i] - 1
    yg_idx = [5, 4, 3, 2, 1, 7, 6][vara_i] - 1
    gk_idx = [7, 6, 5, 4, 3, 2, 1][vara_i] - 1

    def win(i):
        return [inp.fmt_jd(sr + i * octant), inp.fmt_jd(sr + (i + 1) * octant)]

    lm = lunar_month(jd, aya)
    moon_sign = sign_of(moon)
    mt = E.moon_times(jd, inp.lat, inp.lon)
    elapsed = (moon % NAK_SPAN) / NAK_SPAN
    return {
        "tithi": TITHIS[tithi_i], "tithi_index": tithi_i + 1,
        "tithi_left_pct": round((1 - (elong % 12) / 12) * 100, 2),
        "tithi_start": inp.fmt_jd(tithi_start), "tithi_end": inp.fmt_jd(tithi_end),
        "paksha": "Shukla (waxing)" if tithi_i < 15 else "Krishna (waning)",
        "vara": WEEKDAYS[vara_i], "vara_lord": WEEKDAY_LORD[vara_i],
        "nakshatra": NAKSHATRAS[nak_i], "nakshatra_pada": pada, "nakshatra_lord": NAK_LORD[nak_i],
        "nakshatra_left_pct": round((1 - elapsed) * 100, 2),
        "nakshatra_start": inp.fmt_jd(nak_start), "nakshatra_end": inp.fmt_jd(nak_end),
        "yoga": YOGAS[yoga_i], "yoga_index": yoga_i + 1,
        "karana": karana_name(kar_i), "karana_index": kar_i + 1,
        "masa": tr(("Adhika " if lm["adhika"] else "") + lm["masa"] + " masa"),
        "samvatsara": samvatsara(jd, aya),
        "sunrise": inp.fmt_jd(sr), "sunset": inp.fmt_jd(ss), "next_sunrise": inp.fmt_jd(nsr),
        "moonrise": inp.fmt_jd(mt["moonrise"]), "moonset": inp.fmt_jd(mt["moonset"]),
        "day_duration_h": round(((ss - sr) if ss else 0.5) * 24, 3),
        "birth_ghati": round(ghati, 3),
        "birth_ghati_vighati": tr("{g} gh {v} vigh", g=int(ghati), v=int((ghati % 1) * 60)),
        "day_birth": is_day,
        "hora_lord": hora_lord, "hora_number": hora_i + 1,
        "rahu_kaal": win(rk_idx), "yamaganda": win(yg_idx), "gulika_kaal": win(gk_idx),
        "ayanamsa": round(chart.aya, 6), "ayanamsa_dms": _dms(chart.aya),
        "sidereal_time": _hms(E.sidereal_time(jd, inp.lon)),
        "delta_t_sec": round(E.delta_t_seconds(jd), 2),
        "obliquity": round(chart.eps, 6),
        "avakahada": {
            "varna": SIGN_VARNA[moon_sign], "vashya": SIGN_VASHYA[moon_sign],
            "yoni": NAK_YONI[nak_i], "gana": NAK_GANA[nak_i], "nadi": NAK_NADI[nak_i],
            "rashi": SIGNS[moon_sign], "rashi_lord": SIGN_LORD[moon_sign],
            "nakshatra": tr("{n} pada {p}", n=NAKSHATRAS[nak_i], p=pada),
            "namakshar": (NAK_SYLLABLES_TE if lang() == "te" else NAK_SYLLABLES)[nak_i][pada - 1],
            "tatva": ELEMENT[moon_sign], "lagna": SIGNS[chart.lagna_sign],
            "lagna_lord": SIGN_LORD[chart.lagna_sign],
            "paya": _paya(nak_i),
        },
        "_sunrise_jd": sr, "_sunset_jd": ss, "_next_sunrise_jd": nsr, "_vara_index": vara_i,
    }


def _paya(nak_i: int) -> str:
    # Paya by Moon nakshatra (common Hindi-belt almanac convention)
    if nak_i in (26, 0, 1, 2, 3, 4):
        return "Gold (Swarna)"
    if nak_i in (5, 6, 7, 8, 9, 10, 11, 12, 13, 14):
        return "Silver (Rajat)"
    if nak_i in (15, 16, 17):
        return "Copper (Tamra)"
    return "Iron (Loha)"


def _dms(x: float) -> str:
    d = int(x)
    m = int((x - d) * 60)
    s = (x - d - m / 60) * 3600
    return f"{d}°{m:02d}'{s:05.2f}\""


def _hms(h: float) -> str:
    hh = int(h)
    mm = int((h - hh) * 60)
    ss = (h - hh - mm / 60) * 3600
    return f"{hh:02d}:{mm:02d}:{ss:05.2f}"


def gulika_longitude(chart, inp, pan: dict, kind: str = "gulika") -> float:
    """Gulika (start of Saturn's part) / Mandi (middle of it) longitude — Prashna Marga /
    Parashara; day & night divided into 8 parts each."""
    sr, ss, nsr = pan["_sunrise_jd"], pan["_sunset_jd"], pan["_next_sunrise_jd"]
    vara = pan["_vara_index"]
    jd = inp.jd
    if sr <= jd < ss:
        start, length, first = sr, (ss - sr) / 8, vara
    else:
        start, length = ss, (nsr - ss) / 8
        first = (vara + 4) % 7
    # part lords follow weekday order starting from `first`; Saturn index 6
    k = (6 - first) % 7
    t = start + k * length + (length / 2 if kind == "mandi" else 0.0)
    return E.ascendant_at(t, inp.lat, inp.lon, chart.ayanamsa)


def special_lagnas(chart, inp, pan: dict) -> dict:
    """Bhava, Hora, Ghati lagna (Jaimini/Parashara), Indu & Sree lagna, Varnada."""
    sr = pan["_sunrise_jd"]
    sun_sr = E.calc_body(sr, "Sun", chart.ayanamsa).lon
    mins = (inp.jd - sr) * 1440.0
    bl = norm(sun_sr + mins / 120.0 * 30)
    hl = norm(sun_sr + mins / 60.0 * 30)
    gl = norm(sun_sr + mins / 24.0 * 30)
    # Indu lagna
    kalas = {"Sun": 30, "Moon": 16, "Mars": 6, "Mercury": 8, "Jupiter": 10, "Venus": 12,
             "Saturn": 1}
    l9 = SIGN_LORD[(chart.lagna_sign + 8) % 12]
    m9 = SIGN_LORD[(chart.sign("Moon") + 8) % 12]
    tot = (kalas[l9] + kalas[m9]) % 12 or 12
    indu = (chart.sign("Moon") + tot - 1) % 12
    # Sree lagna
    moon = chart.bodies["Moon"].lon
    frac = (moon % NAK_SPAN) / NAK_SPAN
    sree = norm(chart.asc + frac * 360)
    gul = gulika_longitude(chart, inp, pan, "gulika")
    mandi = gulika_longitude(chart, inp, pan, "mandi")
    # Aprakasha grahas (BPHS ch. 3)
    sun = chart.bodies["Sun"].lon
    dhuma = norm(sun + 133 + 20 / 60)
    vyatipata = norm(360 - dhuma)
    parivesha = norm(vyatipata + 180)
    indrachapa = norm(360 - parivesha)
    upaketu = norm(indrachapa + 16 + 40 / 60)
    return {"Bhava Lagna": bl, "Hora Lagna": hl, "Ghati Lagna": gl,
            "Indu Lagna": indu * 30 + 15.0, "Sree Lagna": sree, "Gulika": gul, "Mandi": mandi,
            "Dhuma": dhuma, "Vyatipata": vyatipata, "Parivesha": parivesha,
            "Indrachapa": indrachapa, "Upaketu": upaketu}

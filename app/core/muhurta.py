"""Muhurta (electional) search and a monthly panchanga calendar.

The search follows Muhurta Chintamani (Daivajna Rama) and Kalaprakashika, as implemented by
almanac software such as Shri Muhurta and Parashara's Light: panchanga shuddhi (tithi, vara,
nakshatra, yoga, karana), event-specific month rules, the day-octant kaalas (Rahu, Yamaganda,
Gulika), lagna shuddhi (benefics in kendra/trikona, malefics in 3/6/11, pure 8th and so on) and,
when a birth chart is given, Tara bala and Chandra bala of the person.

The time range is scanned in 10-minute steps. Consecutive steps whose deciding factors are the
same are merged into a window, the edges of every window are refined by bisection, and the
windows are scored and ranked.
"""
from __future__ import annotations

import bisect
import calendar
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import ephemeris as E
from . import panchang as P
from .chart import BirthInput
from .constants import (GRAHAS, NAK_SPAN, NAKSHATRAS, SIGN_LORD, SIGNS, TITHIS, WEEKDAYS,
                        YOGAS, nakshatra_of, norm, sign_of)
from .vedic import combustion
from ..i18n import ordinal, term, terms, tr

MAX_DAYS = 90
STEP_MIN = 10
STEP = STEP_MIN / 1440.0
MIN_WINDOW_MIN = 10            # shorter windows are dropped as impractical
MAX_WINDOWS = 25
REFINE_ITER = 7                # 10 min / 2^7 ≈ 5 s edge precision
SANDHYA_MIN = 24               # 1 ghati either side of sunrise and sunset (Sandhya kala)
BASE_SCORE = 40                # points before the soft factors are added (result clamped 0..100)

SUN, MON, TUE, WED, THU, FRI, SAT = range(7)
(ARIES, TAURUS, GEMINI, CANCER, LEO, VIRGO, LIBRA, SCORPIO, SAGITTARIUS, CAPRICORN, AQUARIUS,
 PISCES) = range(12)
MOVABLE = [ARIES, CANCER, LIBRA, CAPRICORN]
FIXED = [TAURUS, LEO, SCORPIO, AQUARIUS]
DUAL = [GEMINI, VIRGO, SAGITTARIUS, PISCES]

MALEFICS = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]
# Points for a benefic in a kendra or trikona of the muhurta lagna (Jupiter strongest, MC)
BENEFIC_POINTS = {"Jupiter": 6, "Venus": 5, "Mercury": 3, "Moon": 2}
KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}
UPACHAYA_311 = {3, 6, 11}

# Rikta tithis (4, 9, 14 of either paksha) and Amavasya, in 1..30 numbering
RIKTA = {4, 9, 14, 19, 24, 29}
AMAVASYA = 30
PURNIMA = 15
# Yogas always rejected; the other seven of the nine "nitya dushta" yogas are listed per event
ALWAYS_BAD_YOGAS = ["Vyatipata", "Vaidhriti"]
NITYA_BAD = ["Vishkambha", "Atiganda", "Shula", "Ganda", "Vyaghata", "Vajra", "Parigha"]
# Nakshatra gandanta padas (Jyotirnibandha, as on Drik Panchang): the junctions of
# Ashlesha|Magha, Jyeshtha|Mula and Revati|Ashwini are rejected for auspicious work.
GANDANTA = {(8, 4), (9, 1), (17, 4), (18, 1), (26, 4), (0, 1)}
# Day-octant kaalas (1-based octant of daytime, Sunday first); same tables as panchang.compute
RAHU_OCTANT = [8, 2, 7, 5, 6, 4, 3]
YAMA_OCTANT = [5, 4, 3, 2, 1, 7, 6]
GULIKA_OCTANT = [7, 6, 5, 4, 3, 2, 1]
# Tara names, 1..9 counted from the janma nakshatra (MC Nakshatra prakarana)
TARAS = ["Janma", "Sampat", "Vipat", "Kshema", "Pratyari", "Sadhana", "Naidhana", "Mitra",
         "Parama Mitra"]
BAD_TARAS = {3, 5, 7}
# Chandra bala from the janma rashi (MC): good 1/3/6/7/10/11, 2/5/9 good only in Shukla paksha,
# 4/8/12 rejected (8th = Chandrashtama)
CHANDRA_GOOD = {1, 3, 6, 7, 10, 11}
CHANDRA_SHUKLA_ONLY = {2, 5, 9}
CHANDRA_BAD = {4, 8, 12}
# Disha shoola by weekday (MC Yatra prakarana: "shanau chandre tyajet purvam ...")
DISHA_SHOOLA = ["West", "East", "North", "North", "South", "West", "East"]


def _naks(*names: str) -> list[int]:
    return [NAKSHATRAS.index(n) for n in names]


def _both(*nums: int) -> set[int]:
    """Paksha-relative tithi numbers (1..14) applied to Shukla and Krishna paksha (1..30)."""
    return set(nums) | {n + 15 for n in nums}


# Nakshatra classes (MC Nakshatra prakarana; same grouping in Brihat Samhita and PL)
DHRUVA = ("Rohini", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada")
CHARA = ("Punarvasu", "Swati", "Shravana", "Dhanishta", "Shatabhisha")
KSHIPRA = ("Ashwini", "Pushya", "Hasta")
MRIDU = ("Mrigashira", "Chitra", "Anuradha", "Revati")
TIKSHNA = ("Ardra", "Ashlesha", "Jyeshtha", "Mula")

# Event rules. Each list cites the convention it follows; lists were cross-checked against at
# least two sources (the MC verse as remembered/quoted by the almanacs, plus Drik Panchang,
# Vedpanchang or Dekho Panchang). Tithis use 1..30 numbering; Rikta and Amavasya are always
# rejected regardless of these sets.
EVENTS: dict[str, dict] = {
    "marriage": {
        "label": "Marriage (Vivaha)",
        # MC Vivaha: "nirvedhaih shashi-kara-mula-maitra-pitrya-brahma-antya-uttara-pavanaih"
        # = 11 nakshatras (same list on Drik Panchang); Magha and Mula are omitted by some
        # modern almanacs, so they rank second.
        "nakshatras": {"best": _naks("Rohini", "Mrigashira", "Uttara Phalguni", "Hasta", "Swati",
                                     "Anuradha", "Uttara Ashadha", "Uttara Bhadrapada", "Revati"),
                       "good": _naks("Magha", "Mula")},
        # MC: 2,3,5,6,7,10,11,12,13; Raman also drops Ashtami and Purnima; Drik Panchang
        # also accepts Krishna Pratipada (the Moon is still full)
        "tithis": _both(2, 3, 5, 6, 7, 10, 11, 12, 13) | {16},
        # MC: Sun, Wed, Thu, Fri; Raman replaces Sunday with Monday; both disfavour Tue and Sat,
        # but Drik Panchang does not reject them, so they only cost points here
        "weekdays": {"best": [WED, THU, FRI], "good": [SUN, MON], "weak": [TUE, SAT],
                     "avoid": []},
        # MC/Raman: Gemini, Virgo, Libra best; Taurus, Cancer, Sagittarius, Pisces good
        "lagnas": {"best": [GEMINI, VIRGO, LIBRA], "good": [TAURUS, CANCER, SAGITTARIUS, PISCES],
                   "avoid": []},
        "bad_yogas": NITYA_BAD,
        # MC: "mithuna-kumbha-mriga-ali-vrisha-aja-ge ravau" (Sun in Ge, Aq, Cp, Sc, Ta, Ar)
        "sun_signs": [ARIES, TAURUS, GEMINI, SCORPIO, CAPRICORN, AQUARIUS],
        "lunar_months": None,
        "avoid_adhika": True,
        "combust": ["Jupiter", "Venus"],          # Guru/Shukra moudhya (MC, Dharmasindhu)
        "empty": [8],                             # Ashtama shuddhi
        "prefer_empty": {7: 12},                  # Jamitra: 7th should hold no planet
        "no_malefic": {},
        "forbid": {"Venus": [6], "Mars": [8]},    # Bhrigu shatka, Kuja ashtama
        "favour": ["Venus", "Jupiter"],
        "day_only": False,
        "evening_sandhya": False,                 # Godhuli lagna is allowed for marriage
        "janma_tara_avoid": False,
    },
    "griha_pravesha": {
        "label": "Griha pravesha (house warming)",
        # MC Griha pravesha: mridu and dhruva nakshatras; Vedpanchang/Dekho add Pushya,
        # Punarvasu, Dhanishta and Shatabhisha
        "nakshatras": {"best": _naks(*MRIDU, *DHRUVA),
                       "good": _naks("Pushya", "Punarvasu", "Dhanishta", "Shatabhisha")},
        # MC: tithis other than Rikta; Vedpanchang: 2,3,5,7,10,11,13; Ashtami/Purnima avoided
        "tithis": _both(2, 3, 5, 6, 7, 10, 11, 12, 13),
        # Drik Panchang rejects Sunday and Tuesday
        "weekdays": {"best": [MON, WED, THU, FRI], "good": [SAT], "avoid": [SUN, TUE]},
        # MC "sthire udaye": fixed lagna best, dual acceptable, movable rejected
        "lagnas": {"best": FIXED, "good": DUAL, "avoid": MOVABLE},
        "bad_yogas": NITYA_BAD,
        "sun_signs": None,
        # MC "jyeshtha-tapo-antya-madhave": Jyeshtha, Magha, Phalguna, Vaishakha best; Kartika
        # and Margashirsha acceptable; other lunar months rejected
        "lunar_months": {"best": [1, 2, 10, 11], "good": [7, 8]},
        "avoid_adhika": True,
        "combust": ["Jupiter", "Venus"],
        "empty": [4, 8],                          # MC "shuddha-ambu-randhre": 4th and 8th pure
        "prefer_empty": {},
        "no_malefic": {7: 8},
        "forbid": {},
        "favour": ["Jupiter", "Moon"],
        "day_only": False,
        "evening_sandhya": True,
        "janma_tara_avoid": False,
        "upachaya_lagna": True,                   # MC: lagna in upachaya from janma rashi
    },
    "vehicle": {
        "label": "Vehicle purchase",
        # Drik Panchang / Shubh Panchang: chara nakshatras best; Vedpanchang/Dekho add the
        # kshipra and mridu groups and Rohini
        "nakshatras": {"best": _naks(*CHARA),
                       "good": _naks("Ashwini", "Rohini", "Mrigashira", "Pushya", "Hasta",
                                     "Chitra", "Anuradha", "Revati")},
        # Vedpanchang and Dekho Panchang: 2,3,5,7,10,(11),13
        "tithis": _both(2, 3, 5, 7, 10, 11, 13),
        "weekdays": {"best": [MON, WED, THU, FRI], "good": [SUN, SAT], "avoid": []},
        "lagnas": {"best": [TAURUS, GEMINI, CANCER, VIRGO, LIBRA, SAGITTARIUS, PISCES],
                   "good": [ARIES, CAPRICORN], "avoid": []},
        "bad_yogas": NITYA_BAD,
        "sun_signs": None,
        "lunar_months": None,
        "avoid_adhika": False,
        "combust": [],
        "empty": [8],
        "prefer_empty": {},
        "no_malefic": {4: 6},                     # 4th (vehicles) free of malefics
        "forbid": {"Mars": [8]},
        "favour": ["Venus"],
        "day_only": True,                         # Drik discards late-night timings
        "evening_sandhya": True,
        "janma_tara_avoid": False,
    },
    "travel": {
        "label": "Travel (Yatra)",
        # MC Yatra: Ashwini, Pushya, Revati, Hasta, Mrigashira, Anuradha, Shravana, Dhanishta,
        # Punarvasu best (same nine on Dekho Panchang); Rohini, Uttaras, Purvas, Jyeshtha, Mula,
        # Shatabhisha middling
        "nakshatras": {"best": _naks("Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta",
                                     "Anuradha", "Shravana", "Dhanishta", "Revati"),
                       "good": _naks("Rohini", "Uttara Phalguni", "Uttara Ashadha",
                                     "Uttara Bhadrapada", "Purva Phalguni", "Purva Ashadha",
                                     "Purva Bhadrapada", "Jyeshtha", "Mula", "Shatabhisha")},
        # MC Yatra: avoid 6, 8, 12, Purnima, Amavasya, Rikta; Krishna Pratipada is good
        "tithis": _both(2, 3, 5, 7, 10, 11, 13) | {16},
        "weekdays": {"best": [MON, WED, THU, FRI], "good": [], "avoid": []},
        "lagnas": {"best": [GEMINI, CANCER, VIRGO, LIBRA, SAGITTARIUS, PISCES],
                   "good": [ARIES, TAURUS, CAPRICORN], "avoid": []},
        "bad_yogas": NITYA_BAD,
        "sun_signs": None,
        "lunar_months": None,
        "avoid_adhika": False,
        "combust": [],
        "empty": [8],
        "prefer_empty": {},
        "no_malefic": {7: 6},                     # 7th (destination) free of malefics
        "forbid": {},
        "favour": ["Jupiter", "Mercury"],
        "day_only": False,
        "evening_sandhya": True,
        "janma_tara_avoid": True,                 # MC: no journey on the janma tara
        "disha_shoola": True,
    },
    "business": {
        "label": "Business or shop opening",
        # MC: kshipra nakshatras for trade (panya), mridu for lasting goodwill; almanacs
        # (Astromedha, Dekho Panchang) list Ashwini, Rohini, Mrigashira, Pushya, Hasta, Chitra,
        # Anuradha, Revati
        "nakshatras": {"best": _naks(*KSHIPRA, *MRIDU, "Rohini"),
                       "good": _naks("Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada",
                                     *CHARA)},
        "tithis": _both(2, 3, 5, 7, 10, 11, 12, 13) | {PURNIMA},
        "weekdays": {"best": [WED, THU, FRI], "good": [MON, SUN], "weak": [TUE], "avoid": []},
        "lagnas": {"best": [TAURUS, GEMINI, VIRGO, LIBRA, SAGITTARIUS, PISCES],
                   "good": [CANCER, LEO, AQUARIUS], "avoid": []},
        "bad_yogas": NITYA_BAD,
        "sun_signs": None,
        "lunar_months": None,
        "avoid_adhika": False,
        "combust": [],
        "empty": [8],
        "prefer_empty": {},
        "no_malefic": {2: 4, 7: 4},
        "forbid": {},
        "favour": ["Mercury", "Jupiter"],
        "day_only": True,
        "evening_sandhya": True,
        "janma_tara_avoid": False,
    },
    "vidyarambha": {
        "label": "Vidyarambha (start of education)",
        # MC Samskara: "mrigat karat shruteh traye, ashvi-mula-purvika-traye, guru..." plus
        # dhruva, antya and maitra in the opinion of others. The common core (also on
        # Astromedha / Dekho Panchang) ranks first.
        "nakshatras": {"best": _naks("Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta",
                                     "Chitra", "Swati", "Shravana", "Dhanishta", "Shatabhisha"),
                       "good": _naks("Ardra", "Mula", "Purva Phalguni", "Purva Ashadha",
                                     "Purva Bhadrapada", *DHRUVA, "Revati", "Anuradha")},
        # MC: "shat-shara-trike ... shiva-arka-dig-dvike tithau" = 6, 5, 3, 11, 12, 10, 2
        "tithis": _both(2, 3, 5, 6, 10, 11, 12),
        # MC: "arka-jiva-vit-site'hni" = Sun, Thu, Wed, Fri
        "weekdays": {"best": [SUN, WED, THU, FRI], "good": [MON], "avoid": [TUE, SAT]},
        "lagnas": {"best": [GEMINI, VIRGO, SAGITTARIUS, PISCES],
                   "good": [TAURUS, CANCER, LEO, LIBRA], "avoid": []},
        "bad_yogas": NITYA_BAD,
        "sun_signs": None,
        "lunar_months": None,
        "avoid_adhika": True,
        "combust": ["Jupiter", "Venus"],
        "empty": [8],
        "prefer_empty": {},
        "no_malefic": {5: 6},
        "forbid": {},
        "favour": ["Jupiter", "Mercury"],         # MC: benefics in trikona/kendra
        "day_only": True,
        "evening_sandhya": True,
        "janma_tara_avoid": False,
    },
    "property": {
        "label": "Property purchase",
        # Fixed acquisition: dhruva and mridu nakshatras (Shubh Panchang: Rohini, Mrigashira,
        # Anuradha, Revati, Uttara Phalguni); the almanac land-purchase list (Mrigashira,
        # Punarvasu, Ashlesha, Magha, Vishakha, Anuradha, Mula, Revati) supplies the rest
        "nakshatras": {"best": _naks(*DHRUVA, "Mrigashira", "Anuradha", "Revati"),
                       "good": _naks("Punarvasu", "Pushya", "Ashlesha", "Magha", "Vishakha",
                                     "Mula")},
        "tithis": _both(2, 3, 5, 6, 7, 10, 11, 12, 13) | {PURNIMA},
        "weekdays": {"best": [MON, WED, THU, FRI], "good": [SUN, SAT], "avoid": []},
        "lagnas": {"best": FIXED, "good": DUAL, "avoid": []},
        "bad_yogas": NITYA_BAD,
        "sun_signs": None,
        "lunar_months": None,
        "avoid_adhika": False,
        "combust": [],
        "empty": [8],
        "prefer_empty": {},
        "no_malefic": {4: 6},
        "forbid": {},
        "favour": ["Jupiter", "Venus"],
        "day_only": True,
        "evening_sandhya": True,
        "janma_tara_avoid": False,
    },
    "naming": {
        "label": "Naming ceremony (Namakarana)",
        # MC Samskara: "mridu-dhruva-kshipra-chara-udushu", tithis other than Rikta and Parva
        # (8, 14, 15, 30), on benefic weekdays
        "nakshatras": {"best": _naks(*MRIDU, *DHRUVA, *KSHIPRA), "good": _naks(*CHARA)},
        "tithis": _both(1, 2, 3, 5, 6, 7, 10, 11, 12, 13),
        "weekdays": {"best": [MON, WED, THU, FRI], "good": [SUN], "avoid": [TUE, SAT]},
        "lagnas": {"best": [TAURUS, GEMINI, CANCER, VIRGO, LIBRA, SAGITTARIUS, PISCES],
                   "good": [LEO, CAPRICORN, AQUARIUS], "avoid": []},
        "bad_yogas": NITYA_BAD,
        "sun_signs": None,
        "lunar_months": None,
        "avoid_adhika": False,
        "combust": [],
        "empty": [8],
        "prefer_empty": {},
        "no_malefic": {},
        "forbid": {},
        "favour": ["Jupiter", "Moon"],
        "day_only": True,
        "evening_sandhya": True,
        "janma_tara_avoid": False,
    },
    "surgery": {
        "label": "Surgery or medical treatment",
        # MC Aushadha: kshipra, mridu, chara nakshatras and Mula for medicine (Ashwini, the
        # physician twins, first); tikshna nakshatras for cutting (Astromedha, Satyori)
        "nakshatras": {"best": _naks(*KSHIPRA),
                       "good": _naks(*MRIDU, *CHARA, *TIKSHNA)},
        # Rikta, Amavasya and Purnima avoided (Tempora, Astromedha); Ashtami (parva) avoided
        "tithis": _both(1, 2, 3, 5, 6, 7, 10, 11, 12, 13),
        # Tuesday (Mars, cutting) and Saturday favoured by Astromedha/Tempora
        "weekdays": {"best": [TUE, SAT], "good": [SUN, THU], "avoid": []},
        "lagnas": {"best": FIXED, "good": DUAL, "avoid": []},
        "bad_yogas": ["Atiganda", "Shula", "Ganda", "Vyaghata"],
        "sun_signs": None,
        "lunar_months": None,
        "avoid_adhika": False,
        "combust": [],
        "empty": [8],                             # Moon or Mars in the 8th: bleeding, danger
        "prefer_empty": {},
        "no_malefic": {1: 4},
        "forbid": {"Mars": [1, 8]},
        "favour": ["Jupiter"],
        "day_only": True,
        "evening_sandhya": True,
        "janma_tara_avoid": True,
    },
    "general": {
        "label": "General auspicious work",
        # MC: shubha nakshatras = dhruva, mridu, kshipra (best) and chara
        "nakshatras": {"best": _naks(*DHRUVA, *MRIDU, *KSHIPRA), "good": _naks(*CHARA)},
        "tithis": _both(2, 3, 5, 6, 7, 10, 11, 12, 13),
        "weekdays": {"best": [MON, WED, THU, FRI], "good": [SUN], "weak": [TUE, SAT],
                     "avoid": []},
        "lagnas": {"best": [TAURUS, GEMINI, CANCER, VIRGO, LIBRA, SAGITTARIUS, PISCES],
                   "good": [LEO, CAPRICORN, AQUARIUS], "avoid": []},
        "bad_yogas": NITYA_BAD,
        "sun_signs": None,
        "lunar_months": None,
        "avoid_adhika": False,
        "combust": [],
        "empty": [8],
        "prefer_empty": {},
        "no_malefic": {},
        "forbid": {},
        "favour": ["Jupiter"],
        "day_only": True,
        "evening_sandhya": True,
        "janma_tara_avoid": False,
    },
}


# ---------------------------------------------------------------- shared helpers
def _place_label(place: str, lat: float, lon: float) -> str:
    if place:
        return place
    return f"{abs(lat):.4f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.4f}°{'E' if lon >= 0 else 'W'}"


def _fmt_min(inp: BirthInput, jd: float | None, up: bool = False) -> str | None:
    """Local 'YYYY-MM-DD HH:MM'. up=True rounds up to the next whole minute so that a window
    start never shows a time before the boundary it was refined to."""
    if jd is None:
        return None
    if up:
        jd += 59.5 / 86400.0
    return inp.fmt_jd(jd)[:16]


def _hm(inp: BirthInput, jd: float | None) -> str | None:
    s = _fmt_min(inp, jd)
    return s[11:] if s else None


def _tithi_index(jd: float) -> int:
    """0..29 (Shukla Pratipada = 0, Amavasya = 29) from the Moon-Sun elongation."""
    return int(P._elongation(jd) // 12) % 30


def _lunations(jd0: float, jd1: float, aya: str) -> list[tuple[float, float, int, bool]]:
    """Amanta lunations covering [jd0, jd1]: (new moon, next new moon, masa index, adhika).
    Same naming rule as panchang.lunar_month (Sun's sidereal sign at the opening new moon)."""
    out = []
    nm = P._find_elong_time(jd0, 0.0, forward=False)
    while nm <= jd1:
        nxt = P._find_elong_time(nm + 1.0, 0.0, forward=True)
        s1 = sign_of(E.calc_body(nm, "Sun", aya).lon)
        s2 = sign_of(E.calc_body(nxt, "Sun", aya).lon)
        out.append((nm, nxt, (s1 + 1) % 12, s1 == s2))
        nm = nxt
    return out


def _masa_label(idx: int, adhika: bool) -> str:
    return tr(("Adhika " if adhika else "") + P.MASAS[idx] + " masa")


def _day_kaalas(sr: float, ss: float, vara: int) -> dict[str, tuple[float, float]]:
    octant = (ss - sr) / 8.0
    def part(table):
        i = table[vara] - 1
        return sr + i * octant, sr + (i + 1) * octant
    return {"rahu_kaal": part(RAHU_OCTANT), "yamaganda": part(YAMA_OCTANT),
            "gulika_kaal": part(GULIKA_OCTANT)}


# ---------------------------------------------------------------- muhurta search
@dataclass
class _Day:
    sunrise: float
    sunset: float
    next_sunrise: float
    vara: int
    blocks: list = field(default_factory=list)   # (start, end) intervals rejected outright
    abhijit: tuple[float, float] | None = None


@dataclass
class _Eval:
    key: tuple
    score: int
    reasons: list
    warnings: list
    info: dict


class _Scanner:
    """Evaluates the deciding factors of one event at any instant."""

    def __init__(self, ev_key: str, inp: BirthInput, jd0: float, jd1: float, aya: str, native):
        self.ev = EVENTS[ev_key]
        self.inp, self.aya = inp, aya
        self.lat, self.lon = inp.lat, inp.lon
        self.native = native
        if native is not None:
            self.janma_nak = nakshatra_of(native.bodies["Moon"].lon)[0]
            self.janma_rashi = native.sign("Moon")
            self.janma_lagna = native.lagna_sign
        self.days = self._build_days(jd0 - 1.5, jd1 + 1.5)
        self.day_starts = [d.sunrise for d in self.days]
        self.lunations = _lunations(jd0 - 1.0, jd1 + 1.0, aya)
        self.lun_starts = [x[0] for x in self.lunations]
        ev = self.ev
        self.allowed_naks = set(ev["nakshatras"]["best"]) | set(ev["nakshatras"]["good"])
        self.bad_yogas = set(ALWAYS_BAD_YOGAS) | set(ev["bad_yogas"])

    # -- calendar scaffolding
    def _build_days(self, a: float, b: float) -> list[_Day]:
        days = []
        t = a
        off = self.inp.offset_used / 24.0
        while t < b + 1:
            st = E.sun_times(t, self.lat, self.lon)
            sr, ss, nsr = st["sunrise"], st["sunset"], st["next_sunrise"]
            ss = ss if ss else sr + 0.5
            nsr = nsr if nsr else sr + 1.0
            if not days or sr > days[-1].sunrise + 0.5:
                vara = E.weekday_of_jd(sr + off)
                d = _Day(sr, ss, nsr, vara)
                kaalas = _day_kaalas(sr, ss, vara)
                d.blocks = list(kaalas.values())
                sw = SANDHYA_MIN / 1440.0
                d.blocks += [(sr, sr + sw), (nsr - sw, nsr)]          # morning twilights
                if self.ev["evening_sandhya"]:
                    d.blocks.append((ss - sw, ss + sw))
                if self.ev["day_only"]:
                    d.blocks.append((ss, nsr))
                mu = (ss - sr) / 15.0                                 # 15 day muhurtas
                if vara != WED:                                       # no Abhijit on Wednesday
                    d.abhijit = (sr + 7 * mu, sr + 8 * mu)
                days.append(d)
            t = nsr + 0.25
        return days

    def _day(self, jd: float) -> _Day:
        i = bisect.bisect_right(self.day_starts, jd) - 1
        return self.days[max(i, 0)]

    def _lunation(self, jd: float):
        i = bisect.bisect_right(self.lun_starts, jd) - 1
        return self.lunations[max(i, 0)]

    # -- the evaluation
    def evaluate(self, jd: float) -> _Eval | None:
        """Deciding factors at jd, or None when a hard rule rejects the moment."""
        ev, aya = self.ev, self.aya
        day = self._day(jd)
        for a, b in day.blocks:
            if a <= jd < b:
                return None
        vara = day.vara
        wk = ev["weekdays"]
        if vara in wk["avoid"]:
            return None
        sun_b = E.calc_body(jd, "Sun", aya)
        moon_b = E.calc_body(jd, "Moon", aya)
        sun, moon = sun_b.lon, moon_b.lon
        elong = norm(moon - sun)
        t_num = int(elong // 12) + 1                       # 1..30
        if t_num in RIKTA or t_num == AMAVASYA or t_num not in ev["tithis"]:
            return None
        karana = P.karana_name(int(elong // 6))
        if karana == "Vishti":
            return None
        yoga = YOGAS[int(norm(sun + moon) // NAK_SPAN) % 27]
        if yoga in self.bad_yogas:
            return None
        nak, pada = nakshatra_of(moon)
        if nak not in self.allowed_naks or (nak, pada) in GANDANTA:
            return None
        sun_sign = sign_of(sun)
        if ev["sun_signs"] is not None and sun_sign not in ev["sun_signs"]:
            return None
        _, _, masa, adhika = self._lunation(jd)
        if adhika and ev["avoid_adhika"]:
            return None
        lm = ev["lunar_months"]
        if lm is not None and masa not in lm["best"] + lm["good"]:
            return None

        reasons: list[tuple[int, str]] = []
        warnings: list[tuple[int, str]] = []
        moon_sign = sign_of(moon)
        shukla = t_num <= 15

        # Tara bala and Chandra bala of the person
        if self.native is not None:
            tara = ((nak - self.janma_nak) % 27) % 9 + 1
            if tara in BAD_TARAS or (tara == 1 and ev["janma_tara_avoid"]):
                return None
            ch = (moon_sign - self.janma_rashi) % 12 + 1
            if ch in CHANDRA_BAD:
                return None
            if tara == 1:
                warnings.append((-5, tr("Janma tara: the Moon is in the janma nakshatra {n}.",
                                        n=NAKSHATRAS[nak])))
            else:
                reasons.append((6, tr("Tara bala: {t} tara from the janma nakshatra {n}.",
                                      t=TARAS[tara - 1], n=NAKSHATRAS[self.janma_nak])))
            if ch in CHANDRA_GOOD:
                reasons.append((6, tr("Chandra bala: the Moon transits the {h} house from the "
                                      "janma rashi {s}.", h=ordinal(ch),
                                      s=SIGNS[self.janma_rashi])))
            elif ch in CHANDRA_SHUKLA_ONLY and shukla:
                reasons.append((3, tr("Chandra bala: the Moon in the {h} house from the janma "
                                      "rashi is acceptable in Shukla paksha.", h=ordinal(ch))))
            else:                                          # 2/5/9 in Krishna paksha
                warnings.append((-4, tr("Weak Chandra bala: the Moon in the {h} house from the "
                                        "janma rashi in Krishna paksha.", h=ordinal(ch))))

        # Planets and lagna
        bodies = {p: E.calc_body(jd, p, aya) for p in GRAHAS if p not in ("Sun", "Moon")}
        bodies["Sun"], bodies["Moon"] = sun_b, moon_b
        for p in ev["combust"]:
            if combustion(p, bodies[p].lon, sun, bodies[p].retro)[0]:
                return None
        asc = E.ascendant_at(jd, self.lat, self.lon, aya)
        lagna = sign_of(asc)
        lg = ev["lagnas"]
        if lagna in lg["avoid"]:
            return None
        if self.native is not None:
            for ref in (self.janma_rashi, self.janma_lagna):
                if (lagna - ref) % 12 + 1 == 8:          # janma ashtama lagna (MC)
                    return None
        house = {p: (sign_of(b.lon) - lagna) % 12 + 1 for p, b in bodies.items()}
        occupants = {h: [p for p in GRAHAS if house[p] == h] for h in range(1, 13)}
        for h in ev["empty"]:
            if occupants[h]:
                return None
        for p, hs in ev["forbid"].items():
            if house[p] in hs:
                return None

        # ---- soft factors (points)
        nk = ev["nakshatras"]
        if nak in nk["best"]:
            reasons.append((12, tr("Nakshatra {n} is among the best for this event.",
                                   n=NAKSHATRAS[nak])))
        else:
            reasons.append((6, tr("Nakshatra {n} is acceptable for this event.",
                                  n=NAKSHATRAS[nak])))
        reasons.append((0, tr("Tithi {t} is suitable.", t=TITHIS[t_num - 1])))
        bright = 72.0 <= elong <= 288.0
        if bright:
            reasons.append((5, tr("The Moon is bright (paksha bala).")))
        else:
            warnings.append((-5, tr("The Moon is weak, close to the Sun.")))
        if vara in wk["best"]:
            reasons.append((8, tr("Weekday {w} is favoured.", w=WEEKDAYS[vara])))
        elif vara in wk["good"]:
            reasons.append((4, tr("Weekday {w} is acceptable.", w=WEEKDAYS[vara])))
        elif vara in wk.get("weak", []):
            warnings.append((-10, tr("Weekday {w} is not favoured for this event.",
                                     w=WEEKDAYS[vara])))
        if lagna in lg["best"]:
            reasons.append((10, tr("Lagna {s} is among the best for this event.", s=SIGNS[lagna])))
        elif lagna in lg["good"]:
            reasons.append((5, tr("Lagna {s} is good for this event.", s=SIGNS[lagna])))
        else:
            warnings.append((-3, tr("Lagna {s} is not a preferred lagna for this event.",
                                    s=SIGNS[lagna])))
        if lm is not None and masa in lm["best"]:
            reasons.append((5, tr("{m} is a favoured month for this event.",
                                  m=_masa_label(masa, False))))
        if day.abhijit and day.abhijit[0] <= jd < day.abhijit[1]:
            reasons.append((5, tr("Abhijit muhurta (midday).")))

        # Lagna shuddhi: benefics in kendra/trikona, malefics in 3/6/11
        favour = set(ev.get("favour", []))
        for p, pts in BENEFIC_POINTS.items():
            if p == "Moon" and not bright:
                continue
            if house[p] in KENDRA_TRIKONA:
                extra = 2 if house[p] == 1 else 0
                extra += 3 if p in favour else 0
                reasons.append((pts + extra, tr("{p} in house {h} (kendra/trikona) strengthens the "
                                                "muhurta.", p=p, h=house[p])))
        for p in MALEFICS:
            h = house[p]
            if h in UPACHAYA_311:
                reasons.append((3, tr("Malefic {p} in house {h} is well placed.", p=p, h=h)))
            elif h == 1:
                warnings.append((-8, tr("Malefic {p} in the lagna.", p=p)))
            elif h in (4, 7, 10):
                warnings.append((-4, tr("Malefic {p} in kendra house {h}.", p=p, h=h)))
            elif h in (5, 9):
                warnings.append((-3, tr("Malefic {p} in trikona house {h}.", p=p, h=h)))
            elif h == 12:
                warnings.append((-2, tr("Malefic {p} in the 12th house.", p=p)))
        if house["Moon"] in (6, 12):
            warnings.append((-10, tr("The Moon is in house {h} from the muhurta lagna.",
                                     h=house["Moon"])))
        ll = SIGN_LORD[lagna]
        if house[ll] in (6, 8, 12):
            warnings.append((-5, tr("Lagna lord {p} is in house {h}.", p=ll, h=house[ll])))
        if any(house[p] == 12 for p in MALEFICS) and any(house[p] == 2 for p in MALEFICS):
            warnings.append((-10, tr("Papa kartari: malefics hem the lagna from the 2nd and "
                                     "12th houses.")))
        for h, pts in ev["prefer_empty"].items():
            if occupants[h]:
                warnings.append((-pts, tr("House {h} is occupied by {ps}; it should be empty.",
                                          h=h, ps=terms(occupants[h]))))
        for h, pts in ev["no_malefic"].items():
            bad = [p for p in occupants[h] if p in MALEFICS]
            if bad:
                warnings.append((-pts, tr("Malefic {ps} in house {h}.", ps=terms(bad), h=h)))
        if ev.get("upachaya_lagna") and self.native is not None:
            if (lagna - self.janma_rashi) % 12 + 1 in (3, 6, 10, 11):
                reasons.append((4, tr("The lagna is an upachaya from the janma rashi.")))
        if ev.get("disha_shoola"):
            warnings.append((0, tr("Disha shoola: avoid setting out towards the {d} on {w}.",
                                   d=DISHA_SHOOLA[vara], w=WEEKDAYS[vara])))
        if adhika:
            warnings.append((-3, tr("Adhika (intercalary) month.")))

        score = BASE_SCORE + sum(p for p, _ in reasons) + sum(p for p, _ in warnings)
        score = int(max(0, min(100, score)))
        r_txt = [t for _, t in reasons]
        w_txt = [t for _, t in warnings]
        info = {"weekday": WEEKDAYS[vara], "tithi": TITHIS[t_num - 1],
                "nakshatra": NAKSHATRAS[nak], "yoga": yoga, "karana": karana,
                "lagna": SIGNS[lagna]}
        key = (vara, t_num, nak, yoga, karana, lagna, score, tuple(r_txt), tuple(w_txt))
        return _Eval(key, score, r_txt, w_txt, info)

    def same(self, jd: float, key: tuple) -> bool:
        e = self.evaluate(jd)
        return e is not None and e.key == key

    def refine(self, a: float, b: float, key: tuple, entering: bool) -> float:
        """Bisect the moment the state `key` begins (entering) or ends inside [a, b]."""
        lo, hi = a, b
        for _ in range(REFINE_ITER):
            mid = (lo + hi) / 2
            inside = self.same(mid, key)
            if entering:
                lo, hi = (lo, mid) if inside else (mid, hi)
            else:
                lo, hi = (mid, hi) if inside else (lo, mid)
        return hi if entering else lo


def _rules(ev_key: str, native) -> list[str]:
    ev = EVENTS[ev_key]
    nk = ev["nakshatras"]

    def tnum(n: int) -> str:
        return term("Purnima") if n == PURNIMA else str(n if n < 15 else n - 15)

    sh = ", ".join(tnum(n) for n in sorted(ev["tithis"]) if n <= 15)
    kr = ", ".join(tnum(n) for n in sorted(ev["tithis"]) if n > 15)
    out = [
        tr("Best nakshatras: {ns}.", ns=terms(NAKSHATRAS[i] for i in nk["best"])),
    ]
    if nk["good"]:
        out.append(tr("Also acceptable: {ns}.", ns=terms(NAKSHATRAS[i] for i in nk["good"])))
    out.append(tr("Tithis allowed: Shukla {s}; Krishna {k}.", s=sh, k=kr))
    wk = ev["weekdays"]
    out.append(tr("Favoured weekdays: {ws}.", ws=terms(WEEKDAYS[i] for i in wk["best"] + wk["good"])))
    if wk.get("weak"):
        out.append(tr("Weekdays that lose points: {ws}.", ws=terms(WEEKDAYS[i] for i in wk["weak"])))
    if wk["avoid"]:
        out.append(tr("Weekdays rejected: {ws}.", ws=terms(WEEKDAYS[i] for i in wk["avoid"])))
    lg = ev["lagnas"]
    out.append(tr("Preferred lagnas: {ls}.", ls=terms(SIGNS[i] for i in lg["best"] + lg["good"])))
    if lg["avoid"]:
        out.append(tr("Lagnas rejected: {ls}.", ls=terms(SIGNS[i] for i in lg["avoid"])))
    if ev["sun_signs"] is not None:
        out.append(tr("Only while the Sun is in {ss} (solar months).",
                      ss=terms(SIGNS[i] for i in ev["sun_signs"])))
    if ev["lunar_months"] is not None:
        lm = ev["lunar_months"]
        out.append(tr("Only in the lunar months {ms}.",
                      ms=", ".join(term(P.MASAS[i]) for i in lm["best"] + lm["good"])))
    if ev["avoid_adhika"]:
        out.append(tr("Adhika (intercalary) months are rejected."))
    if ev["combust"]:
        out.append(tr("Rejected while {ps} is combust (Guru/Shukra moudhya).",
                      ps=terms(ev["combust"], " / ")))
    out.append(tr("Always rejected: Rikta tithis (4, 9, 14), Amavasya, Vishti karana, the "
                  "yogas {ys}, Rahu kaal, Yamaganda and Gulika kaal.",
                  ys=terms(sorted(set(ALWAYS_BAD_YOGAS) | set(ev["bad_yogas"]),
                                  key=YOGAS.index))))
    out.append(tr("Gandanta padas (end of Ashlesha, Jyeshtha, Revati; start of Magha, Mula, "
                  "Ashwini) are rejected."))
    if ev["evening_sandhya"]:
        out.append(tr("Sandhya: {m} minutes either side of sunrise and sunset are rejected.",
                      m=SANDHYA_MIN))
    else:
        out.append(tr("Sandhya: {m} minutes either side of sunrise are rejected; the sunset "
                      "twilight (Godhuli) is allowed.", m=SANDHYA_MIN))
    if ev["day_only"]:
        out.append(tr("Only daytime (sunrise to sunset) is considered."))
    out.append(tr("Houses that must be empty: {hs}.", hs=", ".join(str(h) for h in ev["empty"])))
    if ev["prefer_empty"]:
        out.append(tr("Houses that should be empty: {hs}.",
                      hs=", ".join(str(h) for h in ev["prefer_empty"])))
    if ev["no_malefic"]:
        out.append(tr("Houses that should be free of malefics: {hs}.",
                      hs=", ".join(str(h) for h in ev["no_malefic"])))
    for p, hs in ev["forbid"].items():
        out.append(tr("{p} must not be in house {hs}.", p=p, hs=", ".join(str(h) for h in hs)))
    out.append(tr("Score: benefics in kendra/trikona and malefics in 3/6/11 add points; malefics "
                  "in kendras, the Moon in 6/12, Papa kartari and a weak lagna lord subtract."))
    if native is not None:
        out.append(tr("Tara bala from the janma nakshatra {n}: Vipat (3), Pratyari (5) and "
                      "Naidhana (7) taras are rejected.",
                      n=NAKSHATRAS[nakshatra_of(native.bodies["Moon"].lon)[0]]))
        if ev["janma_tara_avoid"]:
            out.append(tr("The janma tara is also rejected for this event."))
        out.append(tr("Chandra bala from the janma rashi {s}: the Moon in the 4th, 8th or 12th is "
                      "rejected; the 2nd, 5th and 9th count only in Shukla paksha.",
                      s=SIGNS[native.sign("Moon")]))
        out.append(tr("A lagna that is the 8th from the janma rashi or janma lagna is rejected."))
    else:
        out.append(tr("No birth chart given: Tara bala and Chandra bala were not applied."))
    out.append(tr("Weekday is reckoned from sunrise to sunrise."))
    out.append(tr("Scanned in {m}-minute steps; steps with identical deciding factors are merged "
                  "into windows whose edges are refined to the minute.", m=STEP_MIN))
    return out


def search(event: str, start_date: str, days: int, lat: float, lon: float, tz: str | None,
           offset: float | None = None, ayanamsa: str = "lahiri", native=None, *,
           place: str = "") -> dict:
    """Best muhurta windows for an event over `days` days (max 90) from local `start_date`
    (YYYY-MM-DD). `native` is an optional SiderealChart for Tara bala and Chandra bala."""
    ev_key = event if event in EVENTS else "general"
    days = max(1, min(int(days), MAX_DAYS))
    y, m, d = (int(x) for x in start_date.split("-"))
    start_local = datetime(y, m, d)
    inp = BirthInput("", "", start_local, lat, lon, tz, offset, place)
    end_inp = BirthInput("", "", start_local + timedelta(days=days), lat, lon, tz, offset, place)
    jd0, jd1 = inp.jd, end_inp.jd
    sc = _Scanner(ev_key, inp, jd0, jd1, ayanamsa, native)

    n = int((jd1 - jd0) / STEP + 1e-9)
    times = [jd0 + i * STEP for i in range(n)]
    states = [sc.evaluate(t) for t in times]

    windows = []
    i = 0
    while i < n:
        e = states[i]
        if e is None:
            i += 1
            continue
        j = i
        while j + 1 < n and states[j + 1] is not None and states[j + 1].key == e.key:
            j += 1
        start = times[i] if i == 0 else sc.refine(times[i - 1], times[i], e.key, True)
        nxt = times[j + 1] if j + 1 < n else jd1
        end = jd1 if j == n - 1 and sc.same(jd1, e.key) else \
            sc.refine(times[j], nxt, e.key, False)
        if (end - start) * 1440 >= MIN_WINDOW_MIN:
            windows.append((e, start, end))
        i = j + 1

    windows.sort(key=lambda w: (-w[0].score, w[1]))
    out = []
    for e, a, b in windows[:MAX_WINDOWS]:
        out.append({"start": _fmt_min(inp, a, up=True), "end": _fmt_min(inp, b),
                    "duration_min": int((b - a) * 1440), "score": e.score, **e.info,
                    "reasons": e.reasons, "warnings": e.warnings})
    return {
        "event": tr(EVENTS[ev_key]["label"]), "event_key": ev_key,
        "place": _place_label(place, lat, lon),
        "range": [start_local.strftime("%Y-%m-%d"),
                  (start_local + timedelta(days=days - 1)).strftime("%Y-%m-%d")],
        "windows": out,
        "rules": _rules(ev_key, native),
        "events": {k: tr(v["label"]) for k, v in EVENTS.items()},
    }


# ---------------------------------------------------------------- monthly panchanga
# Special days and the moment the tithi is tested (udaya = sunrise; the others follow the
# usual vrata rules: Pradosha at sunset, Vinayaka Chaturthi at midday, Sankashti at moonrise,
# Kalashtami and Masa Shivaratri at nishita / midnight)
SPECIAL_TITHIS = [
    (10, "ekadashi", "Shukla Ekadashi", "udaya"),
    (25, "ekadashi", "Krishna Ekadashi", "udaya"),
    (12, "pradosha", "Pradosha", "sunset"),
    (27, "pradosha", "Pradosha", "sunset"),
    (14, "purnima", "Purnima", "udaya"),
    (29, "amavasya", "Amavasya", "udaya"),
    (3, "chaturthi", "Vinayaka Chaturthi", "midday"),
    (18, "chaturthi", "Sankashti Chaturthi", "moonrise"),
    (5, "shashthi", "Skanda Shashthi", "udaya"),
    (20, "shashthi", "Krishna Shashthi", "udaya"),
    (7, "ashtami", "Durgashtami", "udaya"),
    (22, "ashtami", "Kalashtami", "nishita"),
    (28, "shivaratri", "Masa Shivaratri", "nishita"),
]


def month_panchang(year: int, month: int, lat: float, lon: float, tz: str | None,
                   offset: float | None = None, ayanamsa: str = "lahiri", *,
                   place: str = "") -> dict:
    """Panchanga for every civil day of a month at a place, taken at local sunrise."""
    aya = ayanamsa
    ndays = calendar.monthrange(year, month)[1]
    first = datetime(year, month, 1)

    def local_jd(dt: datetime) -> float:
        return BirthInput("", "", dt, lat, lon, tz, offset, place).jd

    fmt = BirthInput("", "", first, lat, lon, tz, offset, place)
    # day -1 gives context so a tithi already marked on the last day of the previous month
    # is not marked again on the 1st
    dates = [first + timedelta(days=k) for k in range(-1, ndays + 1)]
    mids = [local_jd(d) for d in dates]                      # local midnights
    lun = _lunations(mids[0] - 1, mids[-1] + 1, aya)
    lun_starts = [x[0] for x in lun]
    off = fmt.offset_used / 24.0

    raw = []
    for k in range(len(dates) - 1):
        mid, next_mid = mids[k], mids[k + 1]
        st = E.sun_times(mid + 0.5, lat, lon)
        sr = st["sunrise"]
        ss = st["sunset"] or sr + 0.5
        nsr = st["next_sunrise"] or sr + 1.0
        vara = E.weekday_of_jd(sr + off)
        sun = E.calc_body(sr, "Sun", aya).lon
        moon = E.calc_body(sr, "Moon", aya).lon
        elong = norm(moon - sun)
        ti = int(elong // 12) % 30
        nak, _ = nakshatra_of(moon)
        t_end = P._find_elong_time(sr, (ti + 1) * 12 % 360, forward=True)
        n_end = P._find_moon_nak_time(sr, ((nak + 1) * NAK_SPAN) % 360, True, aya)
        mr = E.moon_times(mid + 1.0, lat, lon)["moonrise"]   # search starts at midnight
        if mr is not None and mr >= next_mid:
            mr = None
        # kshaya: the next tithi starts and ends before the next sunrise
        kshaya = None
        if t_end < nsr:
            t2 = P._find_elong_time(t_end + 1e-4, (ti + 2) * 12 % 360, forward=True)
            if t2 < nsr:
                kshaya = (ti + 1) % 30
        nishita = (ss + nsr) / 2
        moments = {"udaya": ti, "sunset": _tithi_index(ss),
                   "midday": _tithi_index((sr + ss) / 2),
                   "moonrise": _tithi_index(mr) if mr else ti,
                   "nishita": _tithi_index(nishita)}
        i = bisect.bisect_right(lun_starts, sr) - 1
        _, _, masa, adhika = lun[max(i, 0)]
        kaalas = _day_kaalas(sr, ss, vara)
        sun_mid, sun_next = (E.calc_body(mid, "Sun", aya).lon, E.calc_body(next_mid, "Sun", aya).lon)
        sankranti = None
        if sign_of(sun_mid) != sign_of(sun_next):
            b = sign_of(sun_next) * 30.0
            t = E.find_crossing(lambda x: E.angdiff(E.calc_body(x, "Sun", aya).lon, b),
                                mid, next_mid)
            sankranti = (sign_of(sun_next), t)
        raw.append({
            "date": dates[k].strftime("%Y-%m-%d"), "weekday": WEEKDAYS[vara],
            "sunrise": _hm(fmt, sr), "sunset": _hm(fmt, ss), "moonrise": _hm(fmt, mr),
            "tithi": TITHIS[ti], "tithi_end": _fmt_min(fmt, t_end),
            "paksha": "Shukla" if ti < 15 else "Krishna",
            "nakshatra": NAKSHATRAS[nak], "nakshatra_end": _fmt_min(fmt, n_end),
            "yoga": YOGAS[int(norm(sun + moon) // NAK_SPAN) % 27],
            "karana": P.karana_name(int(elong // 6)),
            "moon_sign": SIGNS[sign_of(moon)],
            "rahu_kaal": [_hm(fmt, x) for x in kaalas["rahu_kaal"]],
            "yamaganda": [_hm(fmt, x) for x in kaalas["yamaganda"]],
            "gulika_kaal": [_hm(fmt, x) for x in kaalas["gulika_kaal"]],
            "masa": _masa_label(masa, adhika),
            "special": [],
            "_moments": moments, "_kshaya": kshaya, "_sankranti": sankranti,
        })

    # special days: the first day whose test moment falls in the tithi; a kshaya tithi that
    # never touches a sunrise is placed on the day it occurs
    for t_idx, key, name, rule in SPECIAL_TITHIS:
        prev_hit = False
        for k, r in enumerate(raw):
            hit = r["_moments"][rule] == t_idx or (rule == "udaya" and r["_kshaya"] == t_idx)
            if hit and not prev_hit and k > 0:
                r["special"].append({"key": key, "name": term(name) if key in
                                     ("ekadashi", "purnima", "amavasya") else tr(name),
                                     "tithi": TITHIS[t_idx]})
            prev_hit = hit
    for r in raw:
        if r["_sankranti"]:
            s, t = r["_sankranti"]
            r["special"].insert(0, {"key": "sankranti", "name": term(f"{SIGNS[s]} Sankranti"),
                                    "sign": SIGNS[s], "time": _fmt_min(fmt, t)})

    days_out = []
    for r in raw[1:]:
        for k in ("_moments", "_kshaya", "_sankranti"):
            r.pop(k)
        days_out.append(r)
    return {"year": year, "month": month, "place": _place_label(place, lat, lon),
            "days": days_out}

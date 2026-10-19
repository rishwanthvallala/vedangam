"""Transit chakras of the Narapati-Jayacharya (Swarodaya) school and allied tools:
Sarvatobhadra, Kota, Sanghatta, Sudarshana and Ghata (Ghataka) chakras.

The nakshatra-based chakras (Sarvatobhadra, Kota, Sanghatta) use the 28-star scheme with
Abhijit (276°40'–280°53'20"), as Narapati does. Signs, tithis and varas come from the
ordinary sidereal chart and panchanga.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import ephemeris as E
from . import panchang as P
from .chart import BirthInput, SiderealChart
from .constants import (GRAHAS, NAK_SPAN, NAKSHATRAS, SIGN_LORD, SIGNS, TITHIS, WEEKDAYS,
                        nakshatra_of, norm, sign_of)
from .geo import local_to_utc, zone
from ..i18n import terms, tr

# ---------------------------------------------------------------- 28-nakshatra scheme
ABHIJIT_START = 276.0 + 40.0 / 60.0                  # 276°40'  (U.Ashadha pada 4 begins)
ABHIJIT_END = 280.0 + 53.0 / 60.0 + 20.0 / 3600.0    # 280°53'20" (1/15 of Shravana)
ABHIJIT = 21                                         # index of Abhijit in NAK28
NAK28 = NAKSHATRAS[:21] + ["Abhijit"] + NAKSHATRAS[21:]

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
NODES = {"Rahu", "Ketu"}
# Mean daily motion (deg/day, Surya Siddhanta values). Faster than this = shighra/atichara.
# Mercury and Venus share the Sun's mean motion (59'08").
MEAN_MOTION = {"Sun": 0.985609, "Moon": 13.176358, "Mars": 0.524033, "Mercury": 0.985609,
               "Jupiter": 0.083091, "Venus": 0.985609, "Saturn": 0.033459}


def nak28_of(lon: float) -> int:
    """Index into NAK28 (0 = Ashwini … 21 = Abhijit … 27 = Revati)."""
    lon = norm(lon)
    if ABHIJIT_START <= lon < ABHIJIT_END:
        return ABHIJIT
    i = int(lon // NAK_SPAN) % 27
    return i + 1 if i >= 21 else i


def motion(p: str, speed: float) -> str:
    """'retrograde' | 'fast' | 'normal' (nodes are always retrograde)."""
    if p in NODES or speed < 0:
        return "retrograde"
    return "fast" if speed > MEAN_MOTION.get(p, 1e9) else "normal"


def nature(p: str, bodies: dict) -> str:
    """Benefic/malefic as used in transit chakras: the Moon is benefic while waxing; Mercury
    turns malefic when it shares a sign with a malefic; Jupiter and Venus are benefic."""
    if p in ("Jupiter", "Venus"):
        return "benefic"
    if p == "Moon":
        return "benefic" if norm(bodies["Moon"].lon - bodies["Sun"].lon) < 180 else "malefic"
    if p == "Mercury":
        s = sign_of(bodies["Mercury"].lon)
        bad = any(sign_of(bodies[q].lon) == s for q in MALEFICS if q in bodies)
        return "malefic" if bad else "benefic"
    return "malefic"


# ---------------------------------------------------------------- namakshara
# Devanagari namakshara per pada (same scheme as constants.NAK_SYLLABLES). Shravana pada 4
# is the Abhijit/Shravana "Kha" (खा; NAK_SYLLABLES romanises it "Gha").
NAK_AKSHARA = [
    ["चू", "चे", "चो", "ला"], ["ली", "लू", "ले", "लो"], ["अ", "इ", "उ", "ए"],
    ["ओ", "वा", "वी", "वू"], ["वे", "वो", "का", "की"], ["कू", "घ", "ङ", "छ"],
    ["के", "को", "हा", "ही"], ["हू", "हे", "हो", "डा"], ["डी", "डू", "डे", "डो"],
    ["मा", "मी", "मू", "मे"], ["मो", "टा", "टी", "टू"], ["टे", "टो", "पा", "पी"],
    ["पू", "ष", "ण", "ठ"], ["पे", "पो", "रा", "री"], ["रू", "रे", "रो", "ता"],
    ["ती", "तू", "ते", "तो"], ["ना", "नी", "नू", "ने"], ["नो", "या", "यी", "यू"],
    ["ये", "यो", "भा", "भी"], ["भू", "धा", "फा", "ढा"], ["भे", "भो", "जा", "जी"],
    ["जू", "जे", "जो", "खा"], ["गा", "गी", "गू", "गे"], ["गो", "सा", "सी", "सू"],
    ["से", "सो", "दा", "दी"], ["दू", "थ", "झ", "ञ"], ["दे", "दो", "चा", "ची"],
]

# Initial letter -> Sarvatobhadra consonant cell. Narapati's 20 letters are used directly;
# vowel-initial names go to the "A" letter (Krittika/Rohini row); Narapati's equivalences
# b=v, sh=s, ṣ=kh, ṇ=n; aspirates and nasals fall to the unaspirated letter of their varga.
LETTER_CELL = {
    "अ": "a", "इ": "a", "उ": "a", "ए": "a", "ओ": "a",
    "व": "va", "ब": "va", "क": "ka", "ह": "ha", "ड": "dda", "ढ": "dda",
    "म": "ma", "ट": "tta", "ठ": "tta", "प": "pa", "फ": "pa", "र": "ra", "त": "ta", "थ": "ta",
    "न": "na", "ण": "na", "य": "ya", "भ": "bha", "ज": "ja", "झ": "ja", "ञ": "ja",
    "ख": "kha", "ष": "kha", "ग": "ga", "घ": "ga", "ङ": "ga", "स": "sa", "श": "sa",
    "द": "da", "ध": "da", "च": "cha", "छ": "cha", "ल": "la",
}
# Letters that share vedha in Sarvatobhadra (Narapati: j = y).
LETTER_EQUIV = {"ja": "ya", "ya": "ja"}

# Varga (letter-group) lords, used for Kota Pala: vowels-Sun, ka-Mars, cha-Venus,
# ṭa-Mercury, ta-Jupiter, pa-Saturn, ya-Moon, śa-Rahu (the pada table in JHora/PyJHora).
VARGA_LORD = {}
for _lord, _letters in (("Sun", "अइउएओ"), ("Mars", "कखगघङ"), ("Venus", "चछजझञ"),
                        ("Mercury", "टठडढण"), ("Jupiter", "तथदधन"), ("Saturn", "पफबभम"),
                        ("Moon", "यरलव"), ("Rahu", "शषसह")):
    for _ch in _letters:
        VARGA_LORD[_ch] = _lord


def namakshara(lon: float) -> str:
    nk, pada = nakshatra_of(lon)
    return NAK_AKSHARA[nk][pada - 1]


# ---------------------------------------------------------------- Sarvatobhadra layout
# 9×9 grid with East on top (Krittika…Ashlesha), South on the right, West at the bottom
# and North on the left, as in Jagannatha Hora. Checked cell by cell against the
# Wikipedia "Sarvatobhadra Chakra" table and PyJHora's Sarvatobadra grid (which has North
# on top, i.e. this grid rotated). Codes: n=nakshatra, v=vowel, c=consonant, s=sign index,
# t=tithi group.
_SBC_CODES = [
    ["v:a", "n:Krittika", "n:Rohini", "n:Mrigashira", "n:Ardra", "n:Punarvasu", "n:Pushya",
     "n:Ashlesha", "v:aa"],
    ["n:Bharani", "v:u", "c:a", "c:va", "c:ka", "c:ha", "c:dda", "v:uu", "n:Magha"],
    ["n:Ashwini", "c:la", "v:lri", "s:1", "s:2", "s:3", "v:lrii", "c:ma", "n:Purva Phalguni"],
    ["n:Revati", "c:cha", "s:0", "v:o", "t:Nanda", "v:au", "s:4", "c:tta",
     "n:Uttara Phalguni"],
    ["n:Uttara Bhadrapada", "c:da", "s:11", "t:Rikta", "t:Purna", "t:Bhadra", "s:5", "c:pa",
     "n:Hasta"],
    ["n:Purva Bhadrapada", "c:sa", "s:10", "v:ah", "t:Jaya", "v:am", "s:6", "c:ra", "n:Chitra"],
    ["n:Shatabhisha", "c:ga", "v:ai", "s:9", "s:8", "s:7", "v:e", "c:ta", "n:Swati"],
    ["n:Dhanishta", "v:rii", "c:kha", "c:ja", "c:bha", "c:ya", "c:na", "v:ri", "n:Vishakha"],
    ["v:ii", "n:Shravana", "n:Abhijit", "n:Uttara Ashadha", "n:Purva Ashadha", "n:Mula",
     "n:Jyeshtha", "n:Anuradha", "v:i"],
]
# label, Devanagari, Telugu
VOWELS = {"a": ("A", "अ", "అ"), "aa": ("Aa", "आ", "ఆ"), "i": ("I", "इ", "ఇ"),
          "ii": ("Ii", "ई", "ఈ"), "u": ("U", "उ", "ఉ"), "uu": ("Uu", "ऊ", "ఊ"),
          "ri": ("Ri", "ऋ", "ఋ"), "rii": ("Rii", "ॠ", "ౠ"), "lri": ("Lri", "ऌ", "ఌ"),
          "lrii": ("Lrii", "ॡ", "ౡ"), "e": ("E", "ए", "ఏ"), "ai": ("Ai", "ऐ", "ఐ"),
          "o": ("O", "ओ", "ఓ"), "au": ("Au", "औ", "ఔ"), "am": ("Am", "अं", "అం"),
          "ah": ("Ah", "अः", "అః")}
CONSONANTS = {"a": ("A", "अ", "అ"), "va": ("Va", "व", "వ"), "ka": ("Ka", "क", "క"),
              "ha": ("Ha", "ह", "హ"), "dda": ("Ḍa", "ड", "డ"), "ma": ("Ma", "म", "మ"),
              "tta": ("Ṭa", "ट", "ట"), "pa": ("Pa", "प", "ప"), "ra": ("Ra", "र", "ర"),
              "ta": ("Ta", "त", "త"), "na": ("Na", "न", "న"), "ya": ("Ya", "य", "య"),
              "bha": ("Bha", "भ", "భ"), "ja": ("Ja", "ज", "జ"), "kha": ("Kha", "ख", "ఖ"),
              "ga": ("Ga", "ग", "గ"), "sa": ("Sa", "स", "స"), "da": ("Da", "द", "ద"),
              "cha": ("Cha", "च", "చ"), "la": ("La", "ल", "ల")}
# Tithi groups (tithi numbers within a paksha) and the weekdays Narapati puts with them.
TITHI_GROUPS = ["Nanda", "Bhadra", "Jaya", "Rikta", "Purna"]
TITHI_GROUP_DAYS = {"Nanda": [0, 2], "Bhadra": [1, 3], "Jaya": [4], "Rikta": [5], "Purna": [6]}
WEEKDAY_GROUP = {d: g for g, ds in TITHI_GROUP_DAYS.items() for d in ds}


def tithi_group(tithi_index: int) -> str:
    """tithi_index 1..30 → Nanda (1,6,11), Bhadra (2,7,12), Jaya (3,8,13),
    Rikta (4,9,14), Purna (5,10,15/30)."""
    return TITHI_GROUPS[(tithi_index - 1) % 5]


def _cid(r: int, c: int) -> str:
    return f"{r}-{c}"


def _build_sbc():
    grid, by = [], {"n": {}, "v": {}, "c": {}, "s": {}, "t": {}}
    for r, row in enumerate(_SBC_CODES):
        out = []
        for c, code in enumerate(row):
            kind, key = code.split(":")
            cell = {"id": _cid(r, c)}
            if kind == "n":
                cell.update(label=key, kind="nakshatra", nakshatra=NAK28.index(key))
                by["n"][NAK28.index(key)] = cell["id"]
            elif kind == "v":
                lab, dv, te = VOWELS[key]
                cell.update(label=lab, kind="vowel", deva=dv, te=te)
                by["v"][key] = cell["id"]
            elif kind == "c":
                lab, dv, te = CONSONANTS[key]
                cell.update(label=lab, kind="consonant", deva=dv, te=te)
                by["c"][key] = cell["id"]
            elif kind == "s":
                s = int(key)
                cell.update(label=SIGNS[s], kind="sign", sign=s)
                by["s"][s] = cell["id"]
            else:
                g = TITHI_GROUPS.index(key)
                cell.update(label=key, kind="center" if key == "Purna" else "tithi",
                            tithis=[g + 1, g + 6, g + 11],
                            weekdays=[WEEKDAYS[d] for d in TITHI_GROUP_DAYS[key]])
                by["t"][key] = cell["id"]
            out.append(cell)
        grid.append(out)
    return grid, by


SBC_GRID, SBC_INDEX = _build_sbc()

# Vedha directions from an outer-ring nakshatra cell, facing the centre. "front" crosses the
# grid; "left" is the diagonal toward the zodiacal (direct-motion) side, "right" the diagonal
# toward the side the planet came from. Narapati: madhya-gati → front (sammukha), shighra →
# left (vama), vakri → right (dakshina); Sun, Moon, Rahu, Ketu always have all three.
_SIDE_VECTORS = {
    "top": {"front": (1, 0), "left": (1, 1), "right": (1, -1)},
    "right": {"front": (0, -1), "left": (1, -1), "right": (-1, -1)},
    "bottom": {"front": (-1, 0), "left": (-1, -1), "right": (-1, 1)},
    "left": {"front": (0, 1), "left": (-1, 1), "right": (1, 1)},
}
VEDHA_FOR_MOTION = {"normal": "front", "fast": "left", "retrograde": "right"}
ALL_VEDHA = {"Sun", "Moon", "Rahu", "Ketu"}


def _side(r: int, c: int) -> str:
    if r == 0:
        return "top"
    if c == 8:
        return "right"
    if r == 8:
        return "bottom"
    return "left"


def vedha_lines(cell_id: str) -> dict[str, list[str]]:
    """{'front': [...], 'left': [...], 'right': [...]} cells pierced from a nakshatra cell
    (the source cell itself excluded, the far outer-ring cell included)."""
    r0, c0 = (int(x) for x in cell_id.split("-"))
    out = {}
    for typ, (dr, dc) in _SIDE_VECTORS[_side(r0, c0)].items():
        cells, r, c = [], r0 + dr, c0 + dc
        while 0 <= r < 9 and 0 <= c < 9:
            cells.append(_cid(r, c))
            r, c = r + dr, c + dc
        out[typ] = cells
    return out


def _active_vedhas(p: str, mot: str) -> set[str]:
    return {"front", "left", "right"} if p in ALL_VEDHA else {VEDHA_FOR_MOTION[mot]}


def _cell_label(cid: str) -> str:
    r, c = (int(x) for x in cid.split("-"))
    return SBC_GRID[r][c]["label"]


def sarvatobhadra(chart, pan: dict, now_bodies: dict) -> dict:
    natal: dict[str, list[str]] = {}
    transit: dict[str, list[str]] = {}
    for p in GRAHAS:
        natal.setdefault(SBC_INDEX["n"][nak28_of(chart.bodies[p].lon)], []).append(p)
        transit.setdefault(SBC_INDEX["n"][nak28_of(now_bodies[p].lon)], []).append(p)

    vedha = []
    active_cells: dict[str, list[tuple[str, str]]] = {}   # cell -> [(planet, type)]
    for p in GRAHAS:
        b = now_bodies[p]
        src = SBC_INDEX["n"][nak28_of(b.lon)]
        mot = motion(p, b.speed)
        act = _active_vedhas(p, mot)
        for typ, cells in vedha_lines(src).items():
            vedha.append({"planet": p, "source": "transit", "type": typ, "from": src,
                          "cells": cells, "active": typ in act, "motion": mot})
            if typ in act:
                for cid in cells:
                    active_cells.setdefault(cid, []).append((p, typ))
        active_cells.setdefault(src, []).append((p, "occupied"))

    moon = chart.bodies["Moon"].lon
    letter_key = LETTER_CELL.get(namakshara(moon)[0])
    points = {
        "Janma nakshatra": SBC_INDEX["n"][nak28_of(moon)],
        "Name letter": SBC_INDEX["c"][letter_key] if letter_key else None,
        "Janma rashi": SBC_INDEX["s"][sign_of(moon)],
        "Tithi": SBC_INDEX["t"][tithi_group(pan["tithi_index"])],
        "Weekday": SBC_INDEX["t"][WEEKDAY_GROUP[pan["_vara_index"]]],
    }
    hits = []
    for point, cid in points.items():
        if cid is None:
            continue
        cells = [cid]
        if point == "Name letter" and letter_key in LETTER_EQUIV:
            cells.append(SBC_INDEX["c"][LETTER_EQUIV[letter_key]])
        seen = set()
        for cc in cells:
            for p, typ in active_cells.get(cc, []):
                if (p, typ) not in seen:
                    seen.add((p, typ))
                    hits.append({"point": point, "planet": p,
                                 "nature": nature(p, now_bodies), "type": typ})

    summary = [tr("Vedha rule (Narapati): a planet at normal speed casts front vedha, a fast "
                  "planet left vedha and a retrograde planet right vedha; the Sun, Moon, Rahu "
                  "and Ketu cast all three. A planet on a cell also afflicts it.")]
    malefic_points = 0
    for point, cid in points.items():
        if cid is None:
            summary.append(tr("{point}: no matching letter cell.", point=point))
            continue
        ph = [h for h in hits if h["point"] == point]
        if not ph:
            summary.append(tr("{point} ({label}) is free of transit vedha.",
                              point=point, label=_cell_label(cid)))
            continue
        bad = [h["planet"] for h in ph if h["nature"] == "malefic"]
        good = [h["planet"] for h in ph if h["nature"] == "benefic"]
        if bad:
            malefic_points += 1
        parts = ", ".join(tr("{p} ({n}, {t})", p=h["planet"], n=h["nature"], t=h["type"])
                          for h in ph)
        summary.append(tr("{point} ({label}) is pierced by {who}.",
                          point=point, label=_cell_label(cid), who=parts))
        if bad and good:
            summary.append(tr("Benefic vedha on {point} softens the malefic vedha.",
                              point=point))
    verdicts = {
        0: "No native point carries malefic vedha: transits are broadly supportive.",
        1: "Malefic vedha on one native point: worry and friction (Narapati: one vedha brings "
           "anxiety or conflict).",
        2: "Malefic vedha on two native points: classically loss of money or position.",
        3: "Malefic vedha on three native points: classically illness or defeat; avoid new "
           "risks.",
    }
    summary.append(tr(verdicts.get(malefic_points,
                                   "Malefic vedha on four or more native points: a severe "
                                   "period in the classical texts; weigh it with dasha and "
                                   "other transits before concluding.")))
    return {"grid": [[dict(c) for c in row] for row in SBC_GRID], "natal": natal,
            "transit": transit, "vedha": vedha, "native_points": points, "hits": hits,
            "summary": summary}


# ---------------------------------------------------------------- Kota chakra
KOTA_RINGS = ["Stambha", "Madhya", "Prakara", "Bahya"]
KOTA_DIRS = ["East", "South", "West", "North"]
# Seven stars per direction counted from the janma star: in through Bahya → Prakara →
# Madhya → Stambha, then out through Madhya → Prakara → Bahya (Narapati; PyJHora's
# kota_chakra_star_placement gives the same rings: outer 1,7,8,14…, inner 4,11,18,25).
_KOTA_PATH = ["Bahya", "Prakara", "Madhya", "Stambha", "Madhya", "Prakara", "Bahya"]
INNER = {"Stambha", "Madhya"}


def kota_position(nak: int, janma: int) -> dict:
    """Ring, direction and pravesha/nirgama of a NAK28 index counted from the janma star."""
    k = (nak - janma) % 28            # 0-based count
    j = k % 7
    return {"count": k + 1, "ring": _KOTA_PATH[j], "direction": KOTA_DIRS[k // 7],
            "entering": j <= 3}


def kota_pala(moon_lon: float) -> str:
    """Lord of the letter-group of the Moon's pada namakshara."""
    return VARGA_LORD[namakshara(moon_lon)[0]]


def _moving_in(pos: dict, mot: str) -> bool:
    """A direct planet moves inward in pravesha stars; a retrograde one in nirgama stars."""
    return pos["entering"] != (mot == "retrograde")


def kota(chart, now_bodies: dict) -> dict:
    moon = chart.bodies["Moon"].lon
    janma = nak28_of(moon)
    swami = SIGN_LORD[sign_of(moon)]
    pala = kota_pala(moon)
    cells = {f"{r}|{d}": [] for r in KOTA_RINGS for d in KOTA_DIRS}
    index = {}
    for k in range(28):
        n = (janma + k) % 28
        pos = kota_position(n, janma)
        entry = {"nakshatra": NAK28[n], "count": k + 1, "entering": pos["entering"],
                 "natal": [], "transit": []}
        cells[f"{pos['ring']}|{pos['direction']}"].append(entry)
        index[n] = entry
    for p in GRAHAS:
        index[nak28_of(chart.bodies[p].lon)]["natal"].append(p)
        index[nak28_of(now_bodies[p].lon)]["transit"].append(p)

    def where(p):
        b = now_bodies[p]
        pos = kota_position(nak28_of(b.lon), janma)
        return pos, motion(p, b.speed)

    a = [tr("Kota Swami is {p} (lord of the janma rashi {s}); Kota Pala is {q} (lord of the "
            "letter group of the Moon's pada).", p=swami, s=SIGNS[sign_of(moon)], q=pala)]
    for role, p in (("Kota Swami", swami), ("Kota Pala", pala)):
        pos, mot = where(p)
        direction = tr("moving inward") if _moving_in(pos, mot) else tr("moving outward")
        a.append(tr("{role} {p} transits {n} in the {ring} ring ({d}), {m}.", role=role, p=p,
                    n=NAK28[nak28_of(now_bodies[p].lon)], ring=pos["ring"],
                    d=pos["direction"], m=direction))
        a.append(tr("{role} is inside the fort: its protection is strong.", role=role)
                 if pos["ring"] in INNER else
                 tr("{role} is outside the inner fort: its protection is weaker.", role=role))
    bad_in, good_in = [], []
    for p in GRAHAS:
        pos, mot = where(p)
        if pos["ring"] not in INNER:
            continue
        n = NAK28[nak28_of(now_bodies[p].lon)]
        inward = _moving_in(pos, mot)
        if nature(p, now_bodies) == "malefic":
            bad_in.append(p)
            a.append(tr("{p} (malefic) in the {ring} ring at {n}: stress on health, disputes "
                        "and obstacles; it is {m}.", p=p, ring=pos["ring"], n=n,
                        m=tr("entering, so pressure is building") if inward
                        else tr("leaving, so pressure is easing")))
        else:
            good_in.append(p)
            a.append(tr("{p} (benefic) is in the {ring} ring at {n}: it guards the fort.",
                        p=p, ring=pos["ring"], n=n))
    if bad_in and not good_in:
        a.append(tr("Malefics hold the inner fort with no benefic guard: a period to protect "
                    "health and avoid conflict."))
    elif bad_in:
        a.append(tr("Malefics and benefics share the inner fort: mixed results, with "
                    "protection against the worst."))
    elif good_in:
        a.append(tr("Only benefics are in the inner fort: well protected."))
    else:
        a.append(tr("No planet is in the inner rings: the fort is quiet."))
    return {"swami": swami, "pala": pala, "rings": KOTA_RINGS, "directions": KOTA_DIRS,
            "janma": NAK28[janma], "cells": cells, "assessment": a}


# ---------------------------------------------------------------- Sanghatta chakra
# Counts from the janma star (Muhurta Chintamani / Narapati; astrobix "Adhanadi nakshatra"):
# Karma 10, Sanghatika 16, Samudayika 18, Vainashika 23, Manasa 25. Counted in the
# 28-star scheme with Abhijit, as the Sanghatta chakra is drawn.
SANGHATTA = [("Janma", 1), ("Karma", 10), ("Sanghatika", 16), ("Samudayika", 18),
             ("Vainashika", 23), ("Manasa", 25)]
SANGHATTA_MEANING = {
    "Janma": "body and health",
    "Karma": "work and undertakings",
    "Sanghatika": "major losses and setbacks with associates",
    "Samudayika": "accidents and group or family troubles",
    "Vainashika": "illness and quarrels with loved ones",
    "Manasa": "the mind: worry and guilt",
}
WINDOW_PLANETS = {"Saturn": 3.0, "Mars": 1.0, "Rahu": 3.0, "Ketu": 3.0, "Sun": 0.5}
# Look back/ahead so a stay already running (or running past the year) has true end dates.
_MARGIN = {"Saturn": 900.0, "Mars": 240.0, "Rahu": 420.0, "Ketu": 420.0, "Sun": 20.0}


def _stays(p: str, t0: float, t1: float, step: float, aya: str, node: str):
    """[(nak28, start_jd | None, end_jd | None)] contiguous stays between t0 and t1."""
    def idx(t):
        return nak28_of(E.calc_body(t, p, aya, node).lon)

    out, t, cur, start = [], t0, idx(t0), None
    while t < t1:
        t2 = min(t + step, t1)
        n2 = idx(t2)
        if n2 != cur:
            lo, hi = t, t2
            for _ in range(24):
                mid = (lo + hi) / 2
                if idx(mid) == cur:
                    lo = mid
                else:
                    hi = mid
            out.append((cur, start, hi))
            start, cur = hi, idx(hi)
        t = t2
    out.append((cur, start, None))
    return out


def sanghatta(chart, inp, now_jd: float, now_bodies: dict, days: int = 365) -> dict:
    janma = nak28_of(chart.bodies["Moon"].lon)
    special = [{"name": nm, "count": c, "nakshatra": NAK28[(janma + c - 1) % 28]}
               for nm, c in SANGHATTA]
    by_nak = {NAK28.index(s["nakshatra"]): s for s in special}
    now = []
    for n, s in by_nak.items():
        pl = [p for p in GRAHAS if nak28_of(now_bodies[p].lon) == n]
        if pl:
            now.append({"special": s["name"], "nakshatra": s["nakshatra"], "planets": pl,
                        "malefic": any(nature(p, now_bodies) == "malefic" for p in pl)})
    now.sort(key=lambda x: dict(SANGHATTA)[x["special"]])

    end = now_jd + days
    upcoming = []
    for p, step in WINDOW_PLANETS.items():
        m = _MARGIN[p]
        for n, a, b in _stays(p, now_jd - m, end + m, step, chart.ayanamsa, chart.node):
            if n not in by_nak or (b is not None and b < now_jd) or (a is not None and a > end):
                continue
            upcoming.append({"planet": p, "special": by_nak[n]["name"],
                             "nakshatra": NAK28[n],
                             "start": inp.fmt_jd(a, with_time=False),
                             "end": inp.fmt_jd(b, with_time=False),
                             "ongoing": a is None or a <= now_jd})
    upcoming.sort(key=lambda w: (w["start"] or "", w["planet"]))

    notes = [tr("Special stars are counted from the janma nakshatra {n} in the 28-star scheme "
                "(with Abhijit).", n=NAK28[janma])]
    for x in now:
        mean = tr(SANGHATTA_MEANING[x["special"]])
        names = terms(x["planets"])
        if x["malefic"]:
            notes.append(tr("{who} in {n}, your {s} star: arishta for {m}.", who=names,
                            n=x["nakshatra"], s=x["special"], m=mean))
        else:
            notes.append(tr("{who} in {n}, your {s} star: a benefic touch on {m}.", who=names,
                            n=x["nakshatra"], s=x["special"], m=mean))
    if not now:
        notes.append(tr("No planet transits a Sanghatta special star now."))
    slow = [w for w in upcoming if w["planet"] in ("Saturn", "Rahu", "Ketu")]
    for w in slow:
        notes.append(tr("{p} occupies your {s} star {n} from {a} to {b}: a long arishta "
                        "window for {m}.", p=w["planet"], s=w["special"], n=w["nakshatra"],
                        a=w["start"] or "?", b=w["end"] or "?",
                        m=tr(SANGHATTA_MEANING[w["special"]])))
    return {"special": special, "now": now, "upcoming": upcoming, "notes": notes}


# ---------------------------------------------------------------- Sudarshana chakra
def _anniversary_jd(inp, year: int) -> float:
    dt = inp.local_dt
    try:
        d = dt.replace(year=year)
    except ValueError:                     # 29 Feb in a non-leap year
        d = dt.replace(year=year, day=28)
    utc, _, _ = local_to_utc(d, inp.tz, inp.offset)
    return E.jd_from_utc(utc)


def sudarshana(chart, inp, now_jd: float, now_local: datetime) -> dict:
    refs = {"Lagna": chart.lagna_sign, "Moon": chart.sign("Moon"), "Sun": chart.sign("Sun")}
    rings = {k: [(s + i) % 12 for i in range(12)] for k, s in refs.items()}
    planets = {p: chart.sign(p) for p in GRAHAS}
    b = inp.local_dt
    age = now_local.year - b.year - ((now_local.month, now_local.day, now_local.time())
                                     < (b.month, b.day, b.time()))
    age = max(age, 0)
    house = age % 12 + 1
    ys, ye = _anniversary_jd(inp, b.year + age), _anniversary_jd(inp, b.year + age + 1)
    frac = min(max((now_jd - ys) / (ye - ys), 0.0), 0.999999)
    month = int(frac * 12) + 1
    month_house = (house + month - 2) % 12 + 1
    signs = {k: (s + house - 1) % 12 for k, s in refs.items()}
    current = {"age": age, "year": age + 1, "house": house, "signs": signs,
               "from": inp.fmt_jd(ys, with_time=False), "to": inp.fmt_jd(ye, with_time=False),
               "month": {"n": month, "house": month_house,
                         "signs": {k: (s + month_house - 1) % 12 for k, s in refs.items()}}}
    notes = [tr("Sudarshana dasha: year n of life activates house n from the Lagna, Moon and "
                "Sun together (house 1 again in years 13, 25, ...); each month within the year "
                "advances one house.")]
    notes.append(tr("Year {y} (age {a}, {f} to {t}) activates house {h}.", y=age + 1, a=age,
                    f=current["from"], t=current["to"], h=house))
    for k, s in signs.items():
        occ = [p for p in GRAHAS if planets[p] == s]
        if occ:
            notes.append(tr("From the {r}: {s} with {o}.", r=k, s=SIGNS[s],
                            o=terms(occ)))
        else:
            notes.append(tr("From the {r}: {s} (lord {l}).", r=k, s=SIGNS[s], l=SIGN_LORD[s]))
    notes.append(tr("Running month {m} of the year activates house {h}.", m=month,
                    h=month_house))
    return {"rings": rings, "planets": planets, "current": current, "notes": notes}


# ---------------------------------------------------------------- Ghata chakra
# Ghata (Ghataka) chakra by janma rashi. Masa, tithi group, vara, nakshatra and prahara agree
# in astrovachmi.com and sanjayprabhakaran.blogspot.com (2025). Yoga/karana variants where
# they differ are kept as alternates. Ghata Chandra is counted from the janma rashi
# (1,5,9,2,6,10,3,7,4,8,11,12; SJC/Anandamoyee, Melooha). Ghata lagna (same / opposite sex)
# follows Sanjay Rath's table (Melooha and Anandamoyee agree for Ar, Ta, Ge, Cn, Sc).
# rashi: (masa, tithi group, weekday, nakshatra, yogas, karanas, prahara, chandra count,
#         (lagna same sex, lagna opposite sex))
GHATA = {
    0: ("Kartika", "Nanda", 0, "Magha", ["Vishkambha"], ["Bava"], 1, 1, (0, 6)),
    1: ("Margashirsha", "Purna", 6, "Hasta", ["Shukla", "Sukarma", "Shula"], ["Shakuni"], 4, 5,
        (1, 7)),
    2: ("Ashadha", "Bhadra", 1, "Swati", ["Parigha"], ["Kaulava", "Chatushpada"], 3, 9, (3, 9)),
    3: ("Pausha", "Bhadra", 3, "Anuradha", ["Vyaghata"], ["Naga"], 1, 2, (6, 0)),
    4: ("Jyeshtha", "Jaya", 6, "Mula", ["Dhriti"], ["Bava"], 1, 6, (9, 3)),
    5: ("Bhadrapada", "Purna", 6, "Shravana", ["Shukla", "Shubha", "Shula"], ["Kaulava"], 1, 10,
        (11, 5)),
    6: ("Magha", "Rikta", 4, "Shatabhisha", ["Shukla"], ["Taitila"], 4, 3, (5, 11)),
    7: ("Ashwin", "Nanda", 5, "Revati", ["Vyatipata"], ["Garaja"], 1, 7, (7, 1)),
    8: ("Shravana", "Jaya", 5, "Bharani", ["Vajra"], ["Taitila"], 1, 4, (8, 2)),
    9: ("Vaishakha", "Rikta", 2, "Rohini", ["Vaidhriti"], ["Shakuni"], 4, 8, (10, 4)),
    10: ("Chaitra", "Jaya", 4, "Ardra", ["Ganda"], ["Kimstughna", "Vanija"], 3, 11, (2, 8)),
    11: ("Phalguna", "Purna", 5, "Ashlesha", ["Vajra"], ["Chatushpada", "Vishti"], 4, 12,
         (4, 10)),
}


def ghata_table(rashi: int) -> dict:
    masa, grp, wd, nak, yogas, kar, prahara, cc, (ls, lo) = GHATA[rashi]
    return {"masa": masa, "tithi_group": grp, "weekday": wd, "nakshatra": nak, "yogas": yogas,
            "karanas": kar, "prahara": prahara, "chandra": (rashi + cc - 1) % 12,
            "lagna_same": ls, "lagna_opposite": lo}


def _sign_windows(t0: float, t1: float, target: int, lat: float, lon: float, aya: str,
                  step: float = 1.0 / 144.0) -> list[tuple[float, float]]:
    """Intervals in [t0, t1) when the ascendant is in `target` sign."""
    def inside(t):
        return sign_of(E.ascendant_at(t, lat, lon, aya)) == target

    def edge(a, b, ia):
        for _ in range(20):
            m = (a + b) / 2
            if inside(m) == ia:
                a = m
            else:
                b = m
        return (a + b) / 2

    out, t, prev = [], t0, inside(t0)
    start = t0 if prev else None
    while t < t1:
        t2 = min(t + step, t1)
        cur = inside(t2)
        if cur != prev:
            e = edge(t, t2, prev)
            if cur:
                start = e
            else:
                out.append((start, e))
                start = None
        t, prev = t2, cur
    if start is not None:
        out.append((start, t1))
    return out


def ghata(chart, inp, now_jd: float, now_inp, now_chart, now_pan: dict) -> dict:
    rashi = chart.sign("Moon")
    g = ghata_table(rashi)
    gi = TITHI_GROUPS.index(g["tithi_group"])
    items = [
        {"factor": "Month", "value": g["masa"]},
        {"factor": "Tithi", "value": g["tithi_group"],
         "detail": tr("{a}, {b}, {c} of either paksha", a=gi + 1, b=gi + 6, c=gi + 11)},
        {"factor": "Weekday", "value": WEEKDAYS[g["weekday"]]},
        {"factor": "Nakshatra", "value": g["nakshatra"]},
        {"factor": "Yoga", "value": g["yogas"][0]},
        {"factor": "Karana", "value": g["karanas"][0]},
        {"factor": "Prahara", "value": str(g["prahara"])},
        {"factor": "Moon sign", "value": SIGNS[g["chandra"]]},
        {"factor": "Lagna", "value": SIGNS[g["lagna_same"]]},
        {"factor": "Lagna (opposite sex)", "value": SIGNS[g["lagna_opposite"]]},
    ]
    for it, key in ((items[4], "yogas"), (items[5], "karanas")):
        if len(g[key]) > 1:
            it["variants"] = g[key]

    today = []
    lm = P.lunar_month(now_jd, chart.ayanamsa)
    if lm["masa"] == g["masa"]:
        today.append({"factor": "Month", "value": lm["masa"], "active": True})
    t_idx = now_pan["tithi_index"]
    if tithi_group(t_idx) == g["tithi_group"]:
        today.append({"factor": "Tithi", "value": TITHIS[t_idx - 1], "active": True,
                      "window": [now_pan["tithi_start"], now_pan["tithi_end"]]})
    if now_pan["_vara_index"] == g["weekday"]:
        today.append({"factor": "Weekday", "value": WEEKDAYS[g["weekday"]], "active": True})
    if now_pan["nakshatra"] == g["nakshatra"]:
        today.append({"factor": "Nakshatra", "value": g["nakshatra"], "active": True,
                      "window": [now_pan["nakshatra_start"], now_pan["nakshatra_end"]]})
    if now_pan["yoga"] in g["yogas"]:
        today.append({"factor": "Yoga", "value": now_pan["yoga"], "active": True})
    if now_pan["karana"] in g["karanas"]:
        today.append({"factor": "Karana", "value": now_pan["karana"], "active": True})
    if now_chart.sign("Moon") == g["chandra"]:
        today.append({"factor": "Moon sign", "value": SIGNS[g["chandra"]], "active": True})
    sr, ss, nsr = now_pan["_sunrise_jd"], now_pan["_sunset_jd"], now_pan["_next_sunrise_jd"]
    if ss:
        q = (ss - sr) / 4.0
        a, b = sr + (g["prahara"] - 1) * q, sr + g["prahara"] * q
        today.append({"factor": "Prahara", "value": str(g["prahara"]),
                      "active": a <= now_jd < b,
                      "window": [inp.fmt_jd(a), inp.fmt_jd(b)]})
    if nsr:
        for a, b in _sign_windows(sr, nsr, g["lagna_same"], inp.lat, inp.lon, chart.ayanamsa):
            today.append({"factor": "Lagna", "value": SIGNS[g["lagna_same"]],
                          "active": a <= now_jd < b,
                          "window": [inp.fmt_jd(a), inp.fmt_jd(b)]})

    notes = [tr("Ghata (Ghataka) factors for janma rashi {s}: avoid them for starting "
                "important work, travel, litigation or surgery. Marriage, upanayana, yajna "
                "and pilgrimage are classically exempt.", s=SIGNS[rashi])]
    notes.append(tr("Month is the amanta lunar month; prahara n is the n-th quarter of the "
                    "day from sunrise; lagna is the rising sign at the birth place."))
    notes.append(tr("Lagna, rashi (Moon sign) and tithi ghata act on the mind; nakshatra and "
                    "weekday ghata on the body. The opposite-sex lagna is used when judging "
                    "a partner."))
    for it in items:
        if "variants" in it:
            notes.append(tr("Sources differ on the {f} for this rashi ({v}); all variants are "
                            "checked for today.", f=it["factor"], v=", ".join(it["variants"])))
    hit = [t for t in today if t["factor"] not in ("Prahara", "Lagna")]
    if hit:
        notes.append(tr("Today carries ghata: {x}.",
                        x=", ".join(tr("{f} {v}", f=t["factor"], v=t["value"]) for t in hit)))
    else:
        notes.append(tr("Today's month, tithi, weekday, nakshatra, yoga, karana and Moon sign "
                        "are free of ghata; only the daily ghata prahara and lagna windows "
                        "apply."))
    return {"rashi": SIGNS[rashi], "items": items, "today": today, "notes": notes}


# ---------------------------------------------------------------- entry point
def _now_input(inp, now_jd: float) -> BirthInput:
    """A BirthInput for `now_jd` at the birth place (same zone handling)."""
    utc = E.utc_from_jd(now_jd)
    if inp.offset is not None:
        local = utc + timedelta(hours=inp.offset)
    else:
        local = utc.astimezone(zone(inp.tz))
    return BirthInput(inp.name, inp.gender, local.replace(tzinfo=None), inp.lat, inp.lon,
                      inp.tz, inp.offset, inp.place)


def compute(chart, inp, pan: dict, now_jd: float) -> dict:
    """chart: SiderealChart (Lahiri), inp: BirthInput, pan: panchang.compute(chart, inp) result,
    now_jd: JD (UT) for current transits. Returns {"sarvatobhadra":…, "kota":…, "sanghatta":…,
    "sudarshan":…, "ghata":…}"""
    now_inp = _now_input(inp, now_jd)
    now_chart = SiderealChart(now_inp, ayanamsa=chart.ayanamsa, node=chart.node,
                              hindu_sunrise=chart.hindu_sunrise, include_outer=False)
    now_pan = P.compute(now_chart, now_inp)
    now_bodies = now_chart.bodies
    return {
        "sarvatobhadra": sarvatobhadra(chart, pan, now_bodies),
        "kota": kota(chart, now_bodies),
        "sanghatta": sanghatta(chart, inp, now_jd, now_bodies),
        "sudarshan": sudarshana(chart, inp, now_jd, now_inp.local_dt),
        "ghata": ghata(chart, inp, now_jd, now_inp, now_chart, now_pan),
    }

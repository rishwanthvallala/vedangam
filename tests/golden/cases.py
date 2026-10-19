"""Deterministic test matrix for comparing the in-browser engine with the native one.

Covers births from 1850 to 2049, both hemispheres, polar latitudes, DST and war-time
offsets, every method, optional settings, both languages and every API endpoint. The
clock is frozen so "now"-dependent output (transits, running dasha, ruling planets) is
reproducible."""
from __future__ import annotations

import random

NOW = "2026-10-19T06:00:00"
CITIES = [  # label, lat, lon, tz
    ("Hyderabad", 17.38405, 78.45636, "Asia/Kolkata"), ("Chennai", 13.08784, 80.27847, "Asia/Kolkata"),
    ("Mumbai", 19.07283, 72.88261, "Asia/Kolkata"), ("Delhi", 28.65195, 77.23149, "Asia/Kolkata"),
    ("Kolkata", 22.56263, 88.36304, "Asia/Kolkata"), ("Vijayawada", 16.50745, 80.6466, "Asia/Kolkata"),
    ("New York", 40.71427, -74.00597, "America/New_York"), ("Los Angeles", 34.05223, -118.24368, "America/Los_Angeles"),
    ("London", 51.50853, -0.12574, "Europe/London"), ("Sydney", -33.86785, 151.20732, "Australia/Sydney"),
    ("Tokyo", 35.6895, 139.69171, "Asia/Tokyo"), ("Sao Paulo", -23.5475, -46.63611, "America/Sao_Paulo"),
    ("Cape Town", -33.92584, 18.42322, "Africa/Johannesburg"), ("Reykjavik", 64.13548, -21.89541, "Atlantic/Reykjavik"),
    ("Tromso", 69.6489, 18.95508, "Europe/Oslo"), ("Auckland", -36.84853, 174.76349, "Pacific/Auckland"),
    ("Moscow", 55.75222, 37.61556, "Europe/Moscow"), ("Dubai", 25.07725, 55.30927, "Asia/Dubai"),
    ("Singapore", 1.28967, 103.85007, "Asia/Singapore"), ("Honolulu", 21.30694, -157.85834, "Pacific/Honolulu"),
]


def _birth(rnd: random.Random, i: int) -> dict:
    label, lat, lon, tz = CITIES[i % len(CITIES)]
    y = rnd.randint(1850, 2049)
    return {"name": f"Case {i}", "gender": rnd.choice(["Male", "Female"]),
            "date": f"{y}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}",
            "time": f"{rnd.randint(0, 23):02d}:{rnd.randint(0, 59):02d}:{rnd.randint(0, 59):02d}",
            "place": {"label": label, "lat": lat, "lon": lon, "tz": tz}, "options": {}}


def cases() -> list[dict]:
    rnd = random.Random(20261019)
    births = [
        {"name": "India", "gender": "Male", "date": "1947-08-15", "time": "00:00:00",
         "place": {"label": "Delhi", "lat": 28.6139, "lon": 77.209, "tz": "Asia/Kolkata"}, "options": {}},
        {"name": "Ravi", "gender": "Male", "date": "1990-05-21", "time": "14:35:00",
         "place": {"label": "Hyderabad", "lat": 17.38405, "lon": 78.45636, "tz": "Asia/Kolkata"}, "options": {}},
        {"name": "War time", "gender": "Female", "date": "1943-03-01", "time": "04:15:00",
         "place": {"label": "Kolkata", "lat": 22.5726, "lon": 88.3639, "tz": "Asia/Kolkata"}, "options": {}},
        {"name": "Pre-sunrise", "gender": "Female", "date": "2010-12-31", "time": "05:00:00",
         "place": {"label": "Mumbai", "lat": 19.076, "lon": 72.8777, "tz": "Asia/Kolkata"}, "options": {}},
        {"name": "Manual offset", "gender": "Male", "date": "1890-06-10", "time": "09:30:00", "offset": 5.5,
         "place": {"label": "Madras", "lat": 13.08, "lon": 80.27, "tz": None}, "options": {}},
    ] + [_birth(rnd, i) for i in range(35)]
    out = []

    def add(path, body=None, query=None, tag=""):
        out.append({"id": f"{len(out):04d} {path} {tag}".strip(), "path": path,
                    "query": {**(query or {}), "now": NOW} if query is not None or path == "/api/now" else {},
                    "body": {**(body or {}), "now": NOW} if body is not None else {}})

    for i, b in enumerate(births):
        for m in ("parashara", "kp", "jaimini", "western", "paschatya"):
            add("/api/chart", {**b, "method": m}, tag=f"{m} #{i}")
        y = int(b["date"][:4]) + 30
        if y < 2100:
            add("/api/chart", {**b, "method": "varshaphal", "year": y}, tag=f"varshaphal #{i}")
    for i, b in enumerate(births[:10]):   # alternative settings
        add("/api/chart", {**b, "method": "parashara", "options": {"ayanamsa": "raman", "node": "true",
            "year_days": 365.2425, "sunrise": "hindu", "karakas": 7}}, tag=f"parashara-alt #{i}")
        add("/api/chart", {**b, "method": "kp", "options": {"ayanamsa": "kp_new", "rotate": 7,
            "rectify_window": 30}}, tag=f"kp-alt #{i}")
        add("/api/chart", {**b, "method": "western", "options": {"hsys": "K", "zodiac": "sidereal",
            "ayanamsa": "fagan_bradley", "minor": False}}, tag=f"western-alt #{i}")
        add("/api/chart", {**b, "method": "jaimini", "options": {"karakas": 7}}, tag=f"jaimini-alt #{i}")
    for i, b in enumerate(births[:8]):    # Telugu
        for m in ("parashara", "kp", "jaimini", "western"):
            add("/api/chart", {**b, "method": m, "lang": "te"}, tag=f"{m}-te #{i}")
    for i, b in enumerate(births[:10]):
        add("/api/chart", {**b, "method": "kp_horary", "horary_number": 1 + i * 24,
            "question": ["marriage", "career", "wealth", "health", "foreign", "property", "children",
                         "litigation", "education", "general"][i]}, tag=f"horary #{i}")
        add("/api/chart", {**b, "method": "prashna", "prashna_number": 1 + i * 10,
            "question": ["general", "marriage", "career", "finance", "health", "children", "travel",
                         "lost", "litigation", "property"][i]}, tag=f"prashna #{i}")
    for i in range(10):
        b, g = births[2 * i], births[2 * i + 1]
        partner = {k: g[k] for k in ("name", "date", "time", "place")}
        add("/api/chart", {**b, "gender": "Male", "method": "matching",
            "partner": {**partner, "gender": "Female"}, "lang": "te" if i % 3 == 0 else "en"}, tag=f"matching #{i}")
    for i, ev in enumerate(["marriage", "griha_pravesha", "vehicle", "travel", "business"]):
        add("/api/chart", {**births[i], "method": "muhurta", "muhurta": {"event": ev, "start_date": "2026-11-01",
            "days": 15, "use_native": i % 2 == 0}}, tag=f"muhurta {ev}")
    for i, (y, mth) in enumerate([(2026, 11), (2027, 1), (2027, 4), (1999, 12), (2030, 8)]):
        add("/api/chart", {**births[i], "method": "calendar", "calendar": {"year": y, "month": mth}}, tag=f"calendar {y}-{mth}")
    for i, b in enumerate(births[:5]):
        add("/api/transits", b, tag=f"#{i}")
        add("/api/dasha_calendar", {**b, "year": 2026, "month": 11 - i}, tag=f"#{i}")
        add("/api/varshaphal", {**b, "year": 2026, "residence": CITIES_DICT[i]}, tag=f"#{i}")
    for i, c in enumerate(CITIES[:5]):
        add("/api/now", query={"lat": c[1], "lon": c[2], "tz": c[3], "label": c[0], "lang": "te" if i == 0 else "en"}, tag=c[0])
    add("/api/search", {"charts": births[:12], "kind": "yoga", "value": "Raja"}, tag="yoga")
    add("/api/search", {"charts": births[:12], "kind": "dasha_now", "value": "Venus"}, tag="dasha")
    add("/api/meta", query={})
    add("/api/kp/subtable", query={})
    add("/api/i18n/te", query={})
    return out


CITIES_DICT = [{"label": c[0], "lat": c[1], "lon": c[2], "tz": c[3]} for c in CITIES]

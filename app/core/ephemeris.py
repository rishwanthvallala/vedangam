"""Thin, thread-safe wrapper over the Swiss Ephemeris (same engine used by
Jagannatha Hora, Astrodienst, KP Stellar-class programs)."""
from __future__ import annotations

import math
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import swisseph as swe

from .constants import (NAK_LORD, NAK_SPAN, NAKSHATRAS, SIGNS, deg_in_sign, dms,
                        nakshatra_of, norm, sign_of)

EPHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ephe")
swe.set_ephe_path(EPHE_PATH)

LOCK = threading.RLock()

AYANAMSAS = {
    "lahiri": (swe.SIDM_LAHIRI, "Lahiri (Chitrapaksha)"),
    "kp": (swe.SIDM_KRISHNAMURTI, "KP (Krishnamurti)"),
    "kp_new": (swe.SIDM_KRISHNAMURTI_VP291, "KP New (VP291)"),
    "raman": (swe.SIDM_RAMAN, "B.V. Raman"),
    "yukteshwar": (swe.SIDM_YUKTESHWAR, "Sri Yukteshwar"),
    "true_chitra": (swe.SIDM_TRUE_CITRA, "True Chitra"),
    "true_pushya": (swe.SIDM_TRUE_PUSHYA, "True Pushya (PVR)"),
    "lahiri_icrc": (swe.SIDM_LAHIRI_ICRC, "Lahiri ICRC"),
    "jn_bhasin": (swe.SIDM_JN_BHASIN, "J.N. Bhasin"),
    "fagan_bradley": (swe.SIDM_FAGAN_BRADLEY, "Fagan-Bradley (Western sidereal)"),
}

HOUSE_SYSTEMS = {
    "P": "Placidus", "K": "Koch", "O": "Porphyry", "R": "Regiomontanus",
    "C": "Campanus", "E": "Equal (Asc)", "W": "Whole Sign", "B": "Alcabitius",
    "M": "Morinus", "T": "Topocentric", "S": "Sripati",
}

BODY_IDS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
    "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN,
    "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO,
    "Chiron": swe.CHIRON, "Lilith": swe.MEAN_APOG,
}

BASE_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


# ---------------------------------------------------------------- time helpers
def jd_from_utc(dt_utc: datetime) -> float:
    h = dt_utc.hour + dt_utc.minute / 60 + (dt_utc.second + dt_utc.microsecond / 1e6) / 3600
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, h, swe.GREG_CAL)


def utc_from_jd(jd: float) -> datetime:
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    base = datetime(y, m, d, tzinfo=timezone.utc)
    return base + timedelta(hours=h)


def weekday_of_jd(jd_local_civil: float) -> int:
    """0 = Sunday. Input must be a JD shifted to local civil time."""
    return int(math.floor(jd_local_civil + 1.5)) % 7


# ---------------------------------------------------------------- core calcs
@dataclass
class Body:
    name: str
    lon: float
    lat: float
    speed: float
    dist: float = 0.0
    decl: float = 0.0
    ra: float = 0.0
    extra: dict = field(default_factory=dict)

    @property
    def retro(self) -> bool:
        return self.speed < 0

    def to_dict(self) -> dict:
        nak, pada = nakshatra_of(self.lon)
        d = {
            "name": self.name, "lon": round(self.lon, 6), "lat": round(self.lat, 4),
            "speed": round(self.speed, 5), "retro": self.retro, "decl": round(self.decl, 4),
            "sign": sign_of(self.lon), "sign_name": SIGNS[sign_of(self.lon)],
            "deg": round(deg_in_sign(self.lon), 6), "dms": dms(deg_in_sign(self.lon)),
            "nakshatra": NAKSHATRAS[nak], "nak_index": nak, "pada": pada,
            "nak_lord": NAK_LORD[nak],
        }
        d.update(self.extra)
        return d


def set_sidereal(ayanamsa: str | None):
    if ayanamsa:
        swe.set_sid_mode(AYANAMSAS[ayanamsa][0], 0, 0)


def ayanamsa_value(jd: float, ayanamsa: str) -> float:
    with LOCK:
        set_sidereal(ayanamsa)
        return swe.get_ayanamsa_ex_ut(jd, swe.FLG_SWIEPH)[1]


def obliquity(jd: float) -> float:
    xx, _ = swe.calc_ut(jd, swe.ECL_NUT, 0)
    return xx[0]  # true obliquity


def calc_body(jd: float, name: str, sidereal: str | None, node: str = "mean") -> Body:
    with LOCK:
        set_sidereal(sidereal)
        flags = BASE_FLAGS | (swe.FLG_SIDEREAL if sidereal else 0)
        if name in ("Rahu", "Ketu", "North Node", "South Node"):
            pid = swe.MEAN_NODE if node == "mean" else swe.TRUE_NODE
        else:
            pid = BODY_IDS[name]
        xx, _ = swe.calc_ut(jd, pid, flags)
        eq, _ = swe.calc_ut(jd, pid, (flags & ~swe.FLG_SIDEREAL) | swe.FLG_EQUATORIAL)
    lon, lat, dist, spd = xx[0], xx[1], xx[2], xx[3]
    ra, decl = eq[0], eq[1]
    if name in ("Ketu", "South Node"):
        lon, lat, decl = norm(lon + 180), -lat, -decl
        ra = norm(ra + 180)
    return Body(name, norm(lon), lat, spd, dist, decl, ra)


def calc_bodies(jd: float, names, sidereal: str | None, node: str = "mean") -> dict[str, Body]:
    return {n: calc_body(jd, n, sidereal, node) for n in names}


def houses(jd: float, lat: float, lon: float, hsys: str, sidereal: str | None):
    """Returns (cusps[12], info) where info has asc, mc, armc, vertex."""
    with LOCK:
        set_sidereal(sidereal)
        flags = swe.FLG_SIDEREAL if sidereal else 0
        try:
            cusps, ascmc = swe.houses_ex(jd, lat, lon, hsys.encode(), flags)
        except swe.Error:
            cusps, ascmc = swe.houses_ex(jd, lat, lon, b"O", flags)
    return list(cusps), {"asc": ascmc[0], "mc": ascmc[1], "armc": ascmc[2],
                         "vertex": ascmc[3], "eq_asc": ascmc[4]}


def houses_from_armc(armc: float, lat: float, eps: float, hsys: str = "P"):
    with LOCK:
        try:
            cusps, ascmc = swe.houses_armc(armc, lat, eps, hsys.encode())
        except swe.Error:  # Placidus/Koch undefined inside the polar circles
            cusps, ascmc = swe.houses_armc(armc, lat, eps, b"O")
    return list(cusps), {"asc": ascmc[0], "mc": ascmc[1], "armc": ascmc[2], "vertex": ascmc[3]}


def ascendant_at(jd: float, lat: float, lon: float, sidereal: str | None) -> float:
    _, info = houses(jd, lat, lon, "O", sidereal)
    return info["asc"]


def sidereal_time(jd: float, lon: float) -> float:
    """Local sidereal time in hours."""
    gst = swe.sidtime(jd)
    return (gst + lon / 15.0) % 24


def delta_t_seconds(jd: float) -> float:
    return swe.deltat(jd) * 86400


# ---------------------------------------------------------------- rise/set
def _rise_set(jd_start: float, body: int, lat: float, lon: float, mode: int,
              hindu: bool = False) -> float | None:
    flags = mode
    if hindu:
        flags |= swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION
    with LOCK:
        try:
            res, tret = swe.rise_trans(jd_start, body, flags, (lon, lat, 0.0), 1013.25, 15.0,
                                       swe.FLG_SWIEPH)
        except swe.Error:
            return None
    return tret[0] if res == 0 else None


def sun_times(jd: float, lat: float, lon: float, hindu: bool = False) -> dict:
    """Sunrise preceding (or equal to) jd, following sunset & next sunrise."""
    sr = _rise_set(jd - 1.5, swe.SUN, lat, lon, swe.CALC_RISE, hindu)
    if sr is None:
        # polar day/night — fall back to 6:00 local mean time
        lmt_midnight = math.floor(jd + 0.5 + lon / 360.0) - 0.5 - lon / 360.0
        sr = lmt_midnight + 0.25
        if sr > jd:
            sr -= 1
        return {"sunrise": sr, "sunset": sr + 0.5, "next_sunrise": sr + 1, "approx": True}
    while True:
        nxt = _rise_set(sr + 0.01, swe.SUN, lat, lon, swe.CALC_RISE, hindu)
        if nxt is None or nxt > jd:
            break
        sr = nxt
    ss = _rise_set(sr + 0.01, swe.SUN, lat, lon, swe.CALC_SET, hindu)
    nsr = _rise_set(sr + 0.01, swe.SUN, lat, lon, swe.CALC_RISE, hindu)
    return {"sunrise": sr, "sunset": ss, "next_sunrise": nsr, "approx": False}


def moon_times(jd: float, lat: float, lon: float) -> dict:
    mr = _rise_set(jd - 1.0, swe.MOON, lat, lon, swe.CALC_RISE)
    ms = _rise_set(jd - 1.0, swe.MOON, lat, lon, swe.CALC_SET)
    return {"moonrise": mr, "moonset": ms}


# ---------------------------------------------------------------- search helpers
def find_crossing(f, t0: float, t1: float, tol: float = 1e-6):
    """Bisection on f(t) (angle difference in (-180,180]) changing sign in [t0,t1]."""
    a, b = t0, t1
    fa = f(a)
    for _ in range(60):
        m = (a + b) / 2
        fm = f(m)
        if (fa <= 0) == (fm <= 0):
            a, fa = m, fm
        else:
            b = m
        if b - a < tol:
            break
    return (a + b) / 2


def angdiff(a: float, b: float) -> float:
    """Signed difference a-b in (-180, 180]."""
    d = (a - b) % 360.0
    return d - 360.0 if d > 180 else d


def mean_longitudes(jd: float) -> dict:
    """Mean tropical geocentric longitudes (Standish J2000 elements) — used by
    Chesta Bala. Mercury/Venus values are heliocentric mean longitudes (sighrocca)."""
    T = (jd - 2451545.0) / 36525.0
    L = {
        "Mercury": 252.25032350 + 149472.67411175 * T,
        "Venus": 181.97909950 + 58517.81538729 * T,
        "Earth": 100.46457166 + 35999.37244981 * T,
        "Mars": -4.55343205 + 19140.30268499 * T,
        "Jupiter": 34.39644051 + 3034.74612775 * T,
        "Saturn": 49.95424423 + 1222.49362201 * T,
    }
    L = {k: norm(v) for k, v in L.items()}
    L["Sun"] = norm(L["Earth"] + 180.0)
    return L


def magnitude(jd: float, name: str) -> float | None:
    """Apparent visual magnitude (Swiss Ephemeris phenomena)."""
    if name not in BODY_IDS or name in ("Lilith",):
        return None
    with LOCK:
        try:
            attr = swe.pheno_ut(jd, BODY_IDS[name], swe.FLG_SWIEPH)
        except swe.Error:
            return None
    vals = attr[0] if isinstance(attr[0], (list, tuple)) else attr
    return round(vals[4], 2)

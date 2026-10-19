"""Chart input handling and the base sidereal chart used by all Vedic methods."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import ephemeris as E
from .constants import GRAHAS, SIGNS, norm, sign_of
from .geo import fmt_offset, local_to_utc


@dataclass
class BirthInput:
    name: str
    gender: str
    local_dt: datetime            # naive local civil time
    lat: float
    lon: float
    tz: str | None = None         # IANA zone
    offset: float | None = None   # manual UTC offset (hours) overrides tz
    place: str = ""

    def __post_init__(self):
        utc, off, dst = local_to_utc(self.local_dt, self.tz, self.offset)
        self.utc = utc
        self.offset_used = off
        self.dst = dst
        self.jd = E.jd_from_utc(utc)

    @property
    def tzinfo(self):
        return timezone(timedelta(hours=self.offset_used))

    def fmt_jd(self, jd: float | None, with_time: bool = True) -> str | None:
        if jd is None:
            return None
        dt = E.utc_from_jd(jd)
        if self.tz and self.offset is None:
            try:
                dt = dt.astimezone(ZoneInfo(self.tz))
            except Exception:
                dt = dt.astimezone(self.tzinfo)
        else:
            dt = dt.astimezone(self.tzinfo)
        return dt.strftime("%Y-%m-%d %H:%M:%S" if with_time else "%Y-%m-%d")

    def summary(self) -> dict:
        return {
            "name": self.name, "gender": self.gender, "place": self.place,
            "local": self.local_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": self.local_dt.strftime("%A"),
            "utc": self.utc.strftime("%Y-%m-%d %H:%M:%S"),
            "lat": self.lat, "lon": self.lon, "tz": self.tz,
            "offset": fmt_offset(self.offset_used), "dst": self.dst,
            "jd": round(self.jd, 6),
            "lat_dms": _geo_dms(self.lat, "N", "S"), "lon_dms": _geo_dms(self.lon, "E", "W"),
        }


def _geo_dms(v: float, pos: str, neg: str) -> str:
    h = pos if v >= 0 else neg
    v = abs(v)
    d = int(v)
    m = int(round((v - d) * 60))
    if m == 60:
        d, m = d + 1, 0
    return f"{d}°{m:02d}'{h}"


@dataclass
class SiderealChart:
    inp: BirthInput
    ayanamsa: str = "lahiri"
    node: str = "mean"
    hsys: str = "P"
    hindu_sunrise: bool = False
    include_outer: bool = True
    bodies: dict = field(default_factory=dict)

    def __post_init__(self):
        jd = self.inp.jd
        names = GRAHAS + (["Uranus", "Neptune", "Pluto"] if self.include_outer else [])
        self.bodies = E.calc_bodies(jd, names, self.ayanamsa, self.node)
        self.aya = E.ayanamsa_value(jd, self.ayanamsa)
        self.cusps, self.hinfo = E.houses(jd, self.inp.lat, self.inp.lon, self.hsys, self.ayanamsa)
        self.asc = self.hinfo["asc"]
        self.mc = self.hinfo["mc"]
        # Sripati bhava (sandhi = start) & Porphyry (bhava madhya)
        self.sripati, _ = E.houses(jd, self.inp.lat, self.inp.lon, "S", self.ayanamsa)
        self.bhava_madhya, _ = E.houses(jd, self.inp.lat, self.inp.lon, "O", self.ayanamsa)
        self.eps = E.obliquity(jd)
        self.sun = E.sun_times(jd, self.inp.lat, self.inp.lon, self.hindu_sunrise)
        self.lagna_sign = sign_of(self.asc)

    # ---- convenience
    def lon(self, p: str) -> float:
        return self.asc if p == "Lagna" else self.bodies[p].lon

    def sign(self, p: str) -> int:
        return sign_of(self.lon(p))

    def house(self, p: str, ref_sign: int | None = None) -> int:
        """Whole-sign house from lagna (or a reference sign)."""
        ref = self.lagna_sign if ref_sign is None else ref_sign
        return (self.sign(p) - ref) % 12 + 1

    def bhava_of(self, lon: float, cusps=None) -> int:
        """House number whose [cusp_i, cusp_i+1) arc contains lon (cusp-start systems)."""
        cusps = cusps or self.cusps
        lon = norm(lon)
        for i in range(12):
            a, b = cusps[i], cusps[(i + 1) % 12]
            span = (b - a) % 360
            if (lon - a) % 360 < span:
                return i + 1
        return 12

    def is_day_birth(self) -> bool:
        s = self.sun
        return s["sunrise"] <= self.inp.jd < (s["sunset"] or s["sunrise"] + 0.5)

    def sign_occupants(self, planets=GRAHAS) -> dict[int, list[str]]:
        occ = {i: [] for i in range(12)}
        for p in planets:
            occ[self.sign(p)].append(p)
        return occ


def lord_house_table(chart: SiderealChart) -> list[dict]:
    from .constants import SIGN_LORD
    rows = []
    for h in range(1, 13):
        s = (chart.lagna_sign + h - 1) % 12
        lord = SIGN_LORD[s]
        rows.append({"house": h, "sign": SIGNS[s], "lord": lord,
                     "lord_in_house": chart.house(lord), "lord_in_sign": SIGNS[chart.sign(lord)]})
    return rows

"""Muhurta search and monthly panchanga checks. Run: .venv/bin/python -m tests.test_muhurta"""
import json
import time
from datetime import datetime, timedelta

from app.core import ephemeris as E
from app.core import muhurta as M
from app.core import panchang as P
from app.core.chart import BirthInput, SiderealChart
from app.core.constants import COMBUST_ORB, nakshatra_of, sign_of

HYD = (17.38405, 78.45636, "Asia/Kolkata")
DEL = (28.6139, 77.2090, "Asia/Kolkata")
BAD_TITHIS = {4, 9, 14, 19, 24, 29, 30}          # Rikta + Amavasya, 1..30


def native_1990():
    return SiderealChart(BirthInput("Native", "M", datetime(1990, 5, 21, 14, 35), *HYD))


def native_1947():
    return SiderealChart(BirthInput("India", "", datetime(1947, 8, 15, 0, 0), *DEL))


def _local(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def _pan_at(dt: datetime, lat, lon, tz):
    """Independent path: the existing panchang.compute at a local moment."""
    inp = BirthInput("", "", dt, lat, lon, tz)
    return inp, P.compute(SiderealChart(inp), inp)


def _overlaps(a0: str, a1: str, b0: str, b1: str) -> bool:
    return a0 < b1[:16] and a1 > b0[:16]


def _sample(w: dict, step_min: int = 2):
    """Local datetimes from a window's start to end (inclusive)."""
    t, end = _local(w["start"]), _local(w["end"])
    while t <= end:
        yield t
        t += timedelta(minutes=step_min)


def _print_windows(r: dict, n: int = 8):
    print(f"  {r['event']} @ {r['place']} {r['range']}: {len(r['windows'])} windows")
    for w in r["windows"][:n]:
        print(f"   {w['start']} → {w['end'][11:]} [{w['score']:3d}] {w['weekday'][:3]} "
              f"{w['tithi']}, {w['nakshatra']}, {w['yoga']}, {w['karana']}, lagna {w['lagna']}")
        print("      +", " | ".join(w["reasons"][:4]))
        if w["warnings"]:
            print("      -", " | ".join(w["warnings"][:3]))


def test_marriage_hyderabad_nov_2026():
    lat, lon, tz = HYD
    t0 = time.time()
    r = M.search("marriage", "2026-11-01", 30, lat, lon, tz, place="Hyderabad")
    print(f"  search took {time.time() - t0:.2f}s")
    _print_windows(r)
    json.dumps(r)
    ws = r["windows"]
    assert r["range"] == ["2026-11-01", "2026-11-30"]
    assert 0 < len(ws) <= M.MAX_WINDOWS
    keys = [(-w["score"], w["start"]) for w in ws]
    assert keys == sorted(keys), "windows must be sorted by score, then date"
    for w in ws:
        assert w["start"] < w["end"]
        # Rahu kaal / Yamaganda / Gulika of the Vedic day at both ends, from panchang.compute
        for edge in (w["start"], w["end"]):
            _, pan = _pan_at(_local(edge), lat, lon, tz)
            for k in ("rahu_kaal", "yamaganda", "gulika_kaal"):
                a, b = pan[k]
                assert not _overlaps(w["start"], w["end"], a, b), (w, k, a, b)
        # no Rikta tithi or Amavasya anywhere inside the window (2-minute samples)
        for t in _sample(w):
            jd = BirthInput("", "", t, lat, lon, tz).jd
            assert int(P._elongation(jd) // 12) + 1 not in BAD_TITHIS, (w, t)
            # marriage: Sun in an allowed solar month, Guru and Shukra not combust
            sun = E.calc_body(jd, "Sun", "lahiri")
            assert sign_of(sun.lon) in M.EVENTS["marriage"]["sun_signs"]
            for p in ("Jupiter", "Venus"):
                b = E.calc_body(jd, p, "lahiri")
                assert abs(E.angdiff(b.lon, sun.lon)) > COMBUST_ORB[p][1 if b.retro else 0]
        _, pan = _pan_at(_local(w["start"]), lat, lon, tz)
        assert pan["tithi_index"] not in BAD_TITHIS
        assert pan["tithi"] == w["tithi"] and pan["nakshatra"] == w["nakshatra"]
        assert pan["karana"] != "Vishti" and pan["yoga"] not in ("Vyatipata", "Vaidhriti")


def test_native_tara_and_chandra_bala():
    for native, (lat, lon, tz) in ((native_1990(), HYD), (native_1947(), DEL)):
        jn = nakshatra_of(native.bodies["Moon"].lon)[0]
        jr = native.sign("Moon")
        r = M.search("general", "2026-11-01", 60, lat, lon, tz, native=native)
        print(f"  native {native.inp.name}: janma nakshatra index {jn}, rashi {jr}")
        _print_windows(r, 4)
        assert r["windows"]
        for w in r["windows"]:
            for t in (_local(w["start"]), _local(w["end"])):
                jd = BirthInput("", "", t, lat, lon, tz).jd
                moon = E.calc_body(jd, "Moon", "lahiri").lon
                tara = ((nakshatra_of(moon)[0] - jn) % 27) % 9 + 1
                assert tara not in (3, 5, 7), (w, tara)
                assert (sign_of(moon) - jr) % 12 + 1 not in (4, 8, 12), w
            assert any("Tara bala" in x or "Janma tara" in x
                       for x in w["reasons"] + w["warnings"])


def test_all_events_and_cap():
    lat, lon, tz = HYD
    for key in M.EVENTS:
        t0 = time.time()
        r = M.search(key, "2026-12-01", 200, lat, lon, tz, native=native_1990())
        dt = time.time() - t0
        json.dumps(r)
        assert r["range"] == ["2026-12-01", "2027-02-28"], r["range"]      # capped at 90 days
        assert set(r["events"]) == set(M.EVENTS) and r["rules"]
        top = r["windows"][0] if r["windows"] else {}
        print(f"  {key:15s} {dt:4.2f}s {len(r['windows']):2d} windows; best "
              f"{top.get('start')} [{top.get('score')}] {top.get('nakshatra')} {top.get('lagna')}")
        for w in r["windows"]:
            if M.EVENTS[key]["day_only"]:
                _, pan = _pan_at(_local(w["start"]), lat, lon, tz)
                assert pan["sunrise"][:16] <= w["start"] and w["end"] <= pan["sunset"][:16], w
    # unknown event falls back to general; manual UTC offset instead of a zone
    r = M.search("nonsense", "2026-11-01", 7, lat, lon, None, offset=5.5)
    assert r["event_key"] == "general"


def test_month_panchang():
    lat, lon, tz = HYD
    t0 = time.time()
    m = M.month_panchang(2026, 11, lat, lon, tz, place="Hyderabad")
    dt = time.time() - t0
    print(f"  month_panchang 2026-11 Hyderabad took {dt:.3f}s")
    assert dt < 2.0
    json.dumps(m)
    days = m["days"]
    assert len(days) == 30 and days[0]["date"] == "2026-11-01" and days[-1]["date"] == "2026-11-30"
    for d in days:
        sp = ", ".join(x["name"] + (f" {x['time']}" if x.get("time") else "") for x in d["special"])
        print(f"   {d['date']} {d['weekday'][:3]} ↑{d['sunrise']} ↓{d['sunset']} "
              f"☾{d['moonrise'] or '--:--'} {d['tithi']} (→{d['tithi_end'][5:]}) "
              f"{d['nakshatra']} (→{d['nakshatra_end'][5:]}) {d['yoga']}/{d['karana']} "
              f"{d['moon_sign']} RK {'-'.join(d['rahu_kaal'])} {d['masa']} {sp}")
        # same values as panchang.compute two minutes after sunrise
        y, mo, dd = (int(x) for x in d["date"].split("-"))
        hh, mm = (int(x) for x in d["sunrise"].split(":"))
        _, pan = _pan_at(datetime(y, mo, dd, hh, mm) + timedelta(minutes=2), lat, lon, tz)
        assert pan["sunrise"][11:16] == d["sunrise"]
        assert (pan["tithi"], pan["nakshatra"], pan["yoga"], pan["karana"]) == \
            (d["tithi"], d["nakshatra"], d["yoga"], d["karana"]), (d["date"], pan["tithi"])
        assert [x[11:16] for x in pan["rahu_kaal"]] == d["rahu_kaal"]
        assert [x[11:16] for x in pan["gulika_kaal"]] == d["gulika_kaal"]
        assert pan["tithi_end"][:16] == d["tithi_end"] and pan["masa"] == d["masa"]
    special = [x for d in days for x in d["special"]]
    keys = [x["key"] for x in special]
    assert keys.count("ekadashi") == 2 and keys.count("purnima") == 1
    assert keys.count("amavasya") == 1 and keys.count("pradosha") == 2
    assert keys.count("shivaratri") == 1
    sk = [x for x in special if x["key"] == "sankranti"]
    assert len(sk) == 1 and sk[0]["sign"] == "Scorpio" and sk[0]["time"].startswith("2026-11-16")


def test_month_panchang_1947_and_polar():
    lat, lon, tz = DEL
    t0 = time.time()
    m = M.month_panchang(1947, 8, lat, lon, tz, place="Delhi")
    print(f"  month_panchang 1947-08 Delhi took {time.time() - t0:.3f}s")
    d15 = next(d for d in m["days"] if d["date"] == "1947-08-15")
    print("  ", d15)
    # 15 Aug 1947 sunrise: Moon in Pushya/Cancer, Krishna paksha (independence chart at 00:00)
    assert d15["moon_sign"] == "Cancer" and d15["paksha"] == "Krishna"
    assert len(m["days"]) == 31
    # polar summer: no sunset/moonrise must not crash
    t0 = time.time()
    m = M.month_panchang(2026, 6, 69.6492, 18.9553, "Europe/Oslo", place="Tromso")
    print(f"  month_panchang 2026-06 Tromso took {time.time() - t0:.3f}s; "
          f"21st: {m['days'][20]['sunrise']} / {m['days'][20]['sunset']}")
    json.dumps(m)


if __name__ == "__main__":
    for fn in [v for k, v in dict(globals()).items() if k.startswith("test_")]:
        print("running", fn.__name__)
        fn()
        print("passed", fn.__name__)

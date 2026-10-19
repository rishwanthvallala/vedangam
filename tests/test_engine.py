"""Engine regression checks. Run: .venv/bin/python -m tests.test_engine"""
from datetime import datetime

from app.core import kp as K, methods as M
from app.core.chart import BirthInput
from app.core.constants import sign_dms
from app.core.vargas import varga_sign


def india_1947():
    return BirthInput("India", "", datetime(1947, 8, 15, 0, 0, 0), 28.6139, 77.2090, "Asia/Kolkata")


def test_reference_positions():
    """India independence chart (Lahiri) — values published by JHora/Parashara's Light."""
    r = M.parashara(india_1947(), {})
    p = {x["name"]: x for x in r["planets"]}
    assert p["Lagna"]["sign_name"] == "Taurus" and 7.6 < p["Lagna"]["deg"] < 7.9
    assert p["Moon"]["sign_name"] == "Cancer" and 3.9 < p["Moon"]["deg"] < 4.1
    assert p["Sun"]["sign_name"] == "Cancer" and 27.9 < p["Sun"]["deg"] < 28.1
    assert p["Rahu"]["sign_name"] == "Taurus"
    assert r["dasha"]["vimshottari"]["starting_lord"] == "Saturn"


def test_kp_subtable():
    t = K.sub_table()
    assert len(t) == 249
    assert t[0]["star_lord"] == "Ketu" and t[0]["sub_lord"] == "Ketu"
    assert abs(t[-1]["end"] - 360) < 1e-9
    # Virgo 9°43' → Uttara Phalguni (Sun), sub Venus
    k = K.kp_lords(150 + 9 + 43 / 60)
    assert (k["star_lord"], k["sub_lord"]) == ("Sun", "Venus")


def test_vargas():
    assert varga_sign(0.5, 9) == 0          # Aries navamsa 1 → Aries
    assert varga_sign(30.5, 9) == 9         # Taurus navamsa 1 → Capricorn
    assert varga_sign(15.0, 2) == 3         # odd sign 2nd half → Cancer (Moon hora)
    assert varga_sign(2.0, 30) == 0         # odd sign 0-5 → Mars (Aries)
    assert varga_sign(32.0, 30) == 1        # even sign 0-5 → Venus (Taurus)


def test_all_methods_many_places():
    places = [
        ("Tromso polar", 69.6492, 18.9553, "Europe/Oslo", datetime(1995, 6, 21, 12, 0)),
        ("Sydney", -33.8688, 151.2093, "Australia/Sydney", datetime(2001, 1, 15, 23, 59, 59)),
        ("New York DST", 40.7128, -74.0060, "America/New_York", datetime(1977, 7, 4, 3, 30)),
        ("Kolkata 1885", 22.5726, 88.3639, "Asia/Kolkata", datetime(1885, 3, 1, 4, 15)),
        ("Pre-sunrise Mumbai", 19.076, 72.8777, "Asia/Kolkata", datetime(2010, 12, 31, 5, 0)),
    ]
    for name, lat, lon, tz, dt in places:
        b = BirthInput(name, "F", dt, lat, lon, tz)
        M.parashara(b, {})
        M.kp(b, {})
        M.jaimini(b, {})
        M.western(b, {})
        M.western(b, {"zodiac": "sidereal"}, paschatya=False)
        M.prashna(b, {}, "career", 77)
        M.kp_horary(b, {}, 200, "career")
        print("ok", name)


if __name__ == "__main__":
    for fn in [v for k, v in dict(globals()).items() if k.startswith("test_")]:
        fn()
        print("passed", fn.__name__)

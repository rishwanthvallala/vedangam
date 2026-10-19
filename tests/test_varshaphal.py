"""Varshaphal / Tithi Pravesha checks. Run: .venv/bin/python -m tests.test_varshaphal"""
import json
from datetime import datetime

from app.core import ephemeris as E
from app.core import varshaphal as V
from app.core.chart import BirthInput, SiderealChart
from app.core.constants import (DASHA_ORDER, NAK_SPAN, SIGN_LORD, SIGNS, WEEKDAY_LORD, WEEKDAYS,
                                norm, sign_of)
from app.i18n import LANG

NYC = {"lat": 40.7128, "lon": -74.0060, "tz": "America/New_York", "label": "New York"}
REQUIRED_SAHAMS = {"Punya", "Vidya", "Yasha", "Mitra", "Mahatmya", "Asha", "Samartha", "Bhratri",
                   "Gaurava", "Pitri", "Rajya", "Matri", "Putra", "Jeeva", "Karma", "Roga",
                   "Vivaha", "Santana", "Paradesha", "Artha", "Labha", "Vyapara"}
YOGA_NAMES = {"Ithasala", "Ishrafa", "Nakta", "Yamaya", "Kamboola", "Manau", "Radda",
              "Khallasara", "Ikkavala", "Induvara"}


def hyderabad():
    return BirthInput("Hyd", "M", datetime(1990, 5, 21, 14, 35), 17.38405, 78.45636,
                      "Asia/Kolkata", place="Hyderabad")


def delhi():
    return BirthInput("India", "", datetime(1947, 8, 15, 0, 0), 28.6139, 77.2090,
                      "Asia/Kolkata", place="Delhi")


def new_year_birth():
    return BirthInput("NY", "F", datetime(1980, 12, 31, 23, 30), 40.7128, -74.0060,
                      "America/New_York", place="New York")


def _cases():
    for mk in (hyderabad, delhi):
        inp = mk()
        yield inp, SiderealChart(inp)


def _secs(jd_str):
    return datetime.strptime(jd_str, "%Y-%m-%d %H:%M:%S")


def test_sun_return_exact():
    for inp, ch in _cases():
        for year in (inp.local_dt.year + 1, 2000, 2026):
            r = V.varshaphal(inp, ch, year)
            sun = E.calc_body(r["jd"], "Sun", ch.ayanamsa).lon
            err = abs(E.angdiff(sun, ch.bodies["Sun"].lon)) * 3600
            assert err < 1.0, (inp.place, year, err)
            assert r["moment"].startswith(str(year)), (r["moment"], year)
            assert r["age"] == year - inp.local_dt.year
            assert 365.2 < r["year_days"] < 365.3, r["year_days"]
            assert abs(r["points"]["Sun"]["lon"] - ch.bodies["Sun"].lon) < 1e-5


def test_place_changes_chart_not_instant():
    inp, ch = next(_cases())
    a = V.varshaphal(inp, ch, 2026)
    b = V.varshaphal(inp, ch, 2026, NYC)
    assert abs(a["jd"] - b["jd"]) < 1e-6
    assert b["place"] == "New York" and a["place"] == "Hyderabad"
    assert a["points"]["Lagna"]["sign"] != b["points"]["Lagna"]["sign"]
    assert b["moment"] == "2026-05-21 10:34:42", b["moment"]      # EDT = IST - 9h30


def test_age_zero_and_bounds():
    inp, ch = next(_cases())
    r = V.varshaphal(inp, ch, 1990)
    assert r["age"] == 0 and abs(r["jd"] - inp.jd) < 1e-6
    assert r["muntha"]["sign"] == ch.lagna_sign
    try:
        V.varshaphal(inp, ch, 1989)
    except ValueError:
        pass
    else:
        raise AssertionError("year before birth should raise")
    nb = new_year_birth()
    nch = SiderealChart(nb)
    for year in range(2020, 2027):
        r = V.varshaphal(nb, nch, year)
        assert r["moment"].startswith(str(year)), (year, r["moment"])


def test_muntha_and_office_bearers():
    for inp, ch in _cases():
        r = V.varshaphal(inp, ch, 2026)
        m = r["muntha"]
        assert m["sign"] == (ch.lagna_sign + r["age"]) % 12
        L = r["points"]["Lagna"]["sign"]
        assert m["house"] == (m["sign"] - L) % 12 + 1 and m["lord"] == SIGN_LORD[m["sign"]]
        roles = {b["role"]: b["planet"] for b in r["office_bearers"]}
        assert list(roles) == ["Janma lagna lord", "Varsha lagna lord", "Muntha lord",
                               "Tri-rashi pati", "Dina-ratri pati"]
        assert roles["Janma lagna lord"] == SIGN_LORD[ch.lagna_sign]
        assert roles["Varsha lagna lord"] == SIGN_LORD[L]
        tri = (V.TRI_RASHI_DAY if r["day_chart"] else V.TRI_RASHI_NIGHT)[L]
        assert roles["Tri-rashi pati"] == tri
        lum = r["points"]["Sun" if r["day_chart"] else "Moon"]["sign"]
        assert roles["Dina-ratri pati"] == SIGN_LORD[lum]
        yl = r["year_lord"]["planet"]
        assert yl in roles.values() and r["year_lord"]["reason"]


def test_tables():
    assert V.hadda_lord(5.0) == "Jupiter" and V.hadda_lord(29.9) == "Saturn"
    assert V.hadda_lord(60 + 7) == "Venus" and V.hadda_lord(60 + 13) == "Jupiter"   # Gemini
    assert V.hadda_lord(240 + 22) == "Mars" and V.hadda_lord(240 + 27) == "Saturn"  # Sagittarius
    assert V.tajika_drekkana_lord(1) == "Mars" and V.tajika_drekkana_lord(15) == "Sun"
    assert V.tajika_drekkana_lord(35) == "Mercury" and V.tajika_drekkana_lord(359) == "Mars"
    assert V.tajika_drekkana_lord(125) == "Saturn"                                 # Leo I
    assert abs(V.uchcha_bala("Sun", 10) - 20) < 1e-9 and abs(V.uchcha_bala("Sun", 190)) < 1e-9
    assert abs(V.uchcha_bala("Saturn", 110) - 10) < 1e-9
    # Mudda start lord: Raman's remainder formula == natal nakshatra lord advanced per year
    for nak in range(27):
        moon = nak * NAK_SPAN + 1.0
        for age in range(0, 40):
            assert V.mudda_start_lord(moon, age) == DASHA_ORDER[(nak + age) % 9]


def test_pvb():
    for inp, ch in _cases():
        r = V.varshaphal(inp, ch, 2026)
        assert [x["planet"] for x in r["pvb"]] == ["Sun", "Moon", "Mars", "Mercury", "Jupiter",
                                                   "Venus", "Saturn"]
        for row in r["pvb"]:
            parts = [row[k] for k in V.PVB_MAX]
            assert all(0 <= row[k] <= V.PVB_MAX[k] + 1e-9 for k in V.PVB_MAX), row
            assert abs(sum(parts) - row["total"]) < 0.03, row
            assert abs(row["total"] / 4 - row["vimshopaka"]) < 0.01
            for k in ("kshetra", "hadda", "drekkana", "navamsa"):
                assert row[k] in [V.PVB_MAX[k] * f for f in V.REL_SHARE.values()], (k, row[k])
            if row["planet"] in ("Sun", "Moon"):
                assert row["hadda"] < 15                      # luminaries own no hadda


def test_sahams():
    for inp, ch in _cases():
        for place in (None, NYC):
            r = V.varshaphal(inp, ch, 2026, place)
            names = [s["name"] for s in r["sahams"]]
            assert REQUIRED_SAHAMS <= set(names), REQUIRED_SAHAMS - set(names)
            assert not any("mrit" in n.lower() for n in names)
            L = r["points"]["Lagna"]["sign"]
            for s in r["sahams"]:
                assert 0 <= s["lon"] < 360 and s["sign"] == SIGNS[sign_of(s["lon"])]
                assert s["house"] == (sign_of(s["lon"]) - L) % 12 + 1
            # Punya by hand, including the 30° rule
            p = r["points"]
            asc, sun, moon = p["Lagna"]["lon"], p["Sun"]["lon"], p["Moon"]["lon"]
            a, b = (moon, sun) if r["day_chart"] else (sun, moon)
            exp = a - b + asc + (0 if (asc - b) % 360 <= (a - b) % 360 else 30)
            punya = next(s for s in r["sahams"] if s["name"] == "Punya")
            assert abs(norm(exp) - punya["lon"]) < 1e-5


def test_mudda_and_patyayini():
    for inp, ch in _cases():
        r = V.varshaphal(inp, ch, 2026)
        md = r["mudda_dasha"]
        nak = int(ch.bodies["Moon"].lon // NAK_SPAN)
        assert md[0]["lord"] == DASHA_ORDER[(nak + r["age"]) % 9]
        assert md[0]["start"] == r["moment"] and md[-1]["end"] == r["next_pravesha"]
        assert abs(sum(m["days"] for m in md) - r["year_days"]) < 0.01
        for x, y in zip(md, md[1:]):
            assert x["end"] == y["start"]
        for m in md:
            assert abs(sum(c["days"] for c in m["children"]) - m["days"]) < 0.01
            assert m["children"][0]["start"] == m["start"] and m["children"][-1]["end"] == m["end"]
        full = {m["lord"]: m["full_days"] for m in md}
        assert abs(sum(full.values()) - r["year_days"]) < 0.01        # 9 lords = one year
        pt = r["patyayini_dasha"]
        assert len(pt) == 8 and {x["planet"] for x in pt} == {"Lagna", "Sun", "Moon", "Mars",
                                                               "Mercury", "Jupiter", "Venus", "Saturn"}
        assert pt[0]["start"] == r["moment"] and pt[-1]["end"] == r["next_pravesha"]
        assert abs(sum(x["days"] for x in pt) - r["year_days"]) < 0.01
        assert [x["krishamsha"] for x in pt] == sorted(x["krishamsha"] for x in pt)


def test_aspects_and_yogas():
    for inp, ch in _cases():
        r = V.varshaphal(inp, ch, 2026)
        for a in r["tajika_aspects"]:
            assert a["a"] != a["b"] and 1 <= a["house"] <= 12
            assert a["sign_aspect"] is not None or a["aspect"] is not None
        for y in r["tajika_yogas"]:
            assert y["name"] in YOGA_NAMES and y["planets"] and isinstance(y["description"], str)
        assert any(y["name"] == "Ithasala" for y in r["tajika_yogas"])


def test_tithi_pravesha():
    for inp, ch in _cases():
        natal_el = norm(ch.bodies["Moon"].lon - ch.bodies["Sun"].lon)
        for year in (2024, 2025, 2026):
            t = V.tithi_pravesha(inp, ch, year)
            el = V._elongation(t["jd"])
            assert abs(E.angdiff(el, natal_el)) < 1e-4, (el, natal_el)
            assert t["points"]["Sun"]["sign"] == sign_of(ch.bodies["Sun"].lon)
            assert t["moment"].startswith(str(year))
            assert abs((_secs(t["moment"]) - _secs(t["solar_return"])).days) <= 31
            assert t["year_lord"] == WEEKDAY_LORD[WEEKDAYS.index(t["weekday"])]
            assert _secs(t["sunrise"]) <= _secs(t["moment"])
            assert (_secs(t["moment"]) - _secs(t["sunrise"])).total_seconds() < 86400 * 1.01
        loc = V.tithi_pravesha(inp, ch, 2026, NYC)
        base = V.tithi_pravesha(inp, ch, 2026)
        assert loc["local"] and not base["local"]
        assert abs(loc["jd"] - base["jd"]) < 1e-6          # the tithi instant is geocentric
        assert loc["points"]["Lagna"]["sign"] != base["points"]["Lagna"]["sign"]


def test_json_and_telugu():
    for inp, ch in _cases():
        json.dumps(V.varshaphal(inp, ch, 2026))
        json.dumps(V.tithi_pravesha(inp, ch, 2026, NYC))
    tok = LANG.set("te")
    try:
        inp, ch = next(_cases())
        r = V.varshaphal(inp, ch, 2026)
        assert r["year_lord"]["reason"]
        V.tithi_pravesha(inp, ch, 2026)
    finally:
        LANG.reset(tok)


def show():
    for inp, ch in _cases():
        r = V.varshaphal(inp, ch, 2026)
        print(f"\n=== {inp.place}: Varsha Pravesha {r['moment']} (age {r['age']}), "
              f"{'day' if r['day_chart'] else 'night'}, next {r['next_pravesha']}")
        print("Lagna", SIGNS[r["points"]["Lagna"]["sign"]], "| Muntha", r["muntha"])
        print("Office-bearers", [(b["role"], b["planet"]) for b in r["office_bearers"]])
        print("Year lord:", r["year_lord"]["planet"], "-", r["year_lord"]["reason"])
        for row in r["pvb"]:
            print(f"  {row['planet']:8} K{row['kshetra']:6} U{row['uchcha']:6} H{row['hadda']:6} "
                  f"D{row['drekkana']:5} N{row['navamsa']:5} = {row['total']:6} -> {row['vimshopaka']}")
        for y in r["tajika_yogas"]:
            print("  yoga", y["name"], y["planets"])
        print("  sahams", [(s["name"], s["sign"], s["house"]) for s in r["sahams"][:8]], "...")
        print("  mudda", [(m["lord"], m["start"][:10], m["days"]) for m in r["mudda_dasha"]])
        print("  patyayini", [(p["planet"], p["start"][:10], p["days"]) for p in r["patyayini_dasha"]])
        t = V.tithi_pravesha(inp, ch, 2026)
        print(f"  Tithi Pravesha {t['moment']} ({t['tithi']['name']}), {t['weekday']} -> {t['year_lord']}")


if __name__ == "__main__":
    for fn in [v for k, v in dict(globals()).items() if k.startswith("test_")]:
        fn()
        print("passed", fn.__name__)
    show()

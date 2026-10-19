"""Marriage-matching checks. Run: .venv/bin/python -m tests.test_matching"""
import json
from datetime import datetime

from app.core import matching as M
from app.core.chart import BirthInput, SiderealChart
from app.core.constants import ENEMIES, FRIENDS, NAK_YONI, SEVEN
from app.i18n import LANG

HYD = (17.38405, 78.45636, "Asia/Kolkata")


def _couple(bname, bdt, gname, gdt, bplace=HYD, gplace=HYD):
    b = BirthInput(bname, "M", bdt, *bplace)
    g = BirthInput(gname, "F", gdt, *gplace)
    r = M.match(SiderealChart(b), SiderealChart(g), b, g)
    json.dumps(r)                       # must be JSON-serialisable
    return r


def _k(r):
    return {k["name"]: k for k in r["ashtakoota"]["kootas"]}


def _p(r):
    return {p["name"]: p for p in r["dashakoota"]["poruthams"]}


def _show(r):
    a = r["ashtakoota"]
    print(f'  {r["boy"]["nakshatra"]}-{r["boy"]["pada"]} ({r["boy"]["moon_sign"]}) x '
          f'{r["girl"]["nakshatra"]}-{r["girl"]["pada"]} ({r["girl"]["moon_sign"]}): '
          + ", ".join(f'{k["name"]} {k["score"]}/{k["adjusted"]}' for k in a["kootas"])
          + f' = {a["total"]}/{a["adjusted_total"]}; poruthams {r["dashakoota"]["count_ok"]}/10')
    for s in r["summary"]:
        print("   ", s)


# ----------------------------------------------------------------------------- tables
def test_tables():
    # Graha Maitri table equals the BPHS natural-friendship rule.
    pts = {(1, 1): 5, (1, 0): 4, (0, 1): 4, (0, 0): 3, (1, -1): 1, (-1, 1): 1,
           (0, -1): 0.5, (-1, 0): 0.5, (-1, -1): 0}

    def rel(p, q):
        return 1 if q in FRIENDS[p] else -1 if q in ENEMIES[p] else 0

    for i, p in enumerate(SEVEN):
        for j, q in enumerate(SEVEN):
            want = 5 if p == q else pts[(rel(p, q), rel(q, p))]
            assert M.GRAHA_MAITRI_PTS[i][j] == want, (p, q)
    # Yoni: same yoni 4, and the zeros are exactly the 7 sworn-enemy pairs (both ways).
    enemies = {frozenset(x) for x in [("Horse", "Buffalo"), ("Elephant", "Lion"),
                                      ("Sheep", "Monkey"), ("Serpent", "Mongoose"),
                                      ("Dog", "Deer"), ("Cat", "Rat"), ("Cow", "Tiger")]}
    zeros = {frozenset((M.YONIS[i], M.YONIS[j])) for i in range(14) for j in range(14)
             if M.YONI_PTS[i][j] == 0}
    assert zeros == enemies
    assert all(M.YONI_PTS[i][i] == 4 for i in range(14))
    # Each yoni has exactly one male nakshatra among the 27 (Abhijit's female mongoose is omitted).
    males = sorted(NAK_YONI[n] for n in M.YONI_MALE)
    assert males == sorted(M.YONIS)
    # Rajju groups partition the 27 nakshatras; Siro has the 3 middle stars.
    allr = sorted(n for ns in M.RAJJU.values() for n in ns)
    assert allr == list(range(27)) and M.RAJJU["Siro"] == (4, 13, 22)
    # Vedha: every star in one pair, Mrigashira/Chitra/Dhanishta mutually in two.
    seen = {}
    for p in M.VEDHA_PAIRS:
        for n in p:
            seen[n] = seen.get(n, 0) + 1
    assert sorted(seen) == list(range(27))
    assert {n for n, c in seen.items() if c == 2} == {4, 13, 22}
    # Diagonals of the group tables give full points.
    assert all(M.VASHYA_PTS[i][i] == 2 for i in range(5))
    assert all(M.GANA_PTS[i][i] == 6 for i in range(3))
    # Ekanakshatra lists: 8 uttama + 8 adhama, rest madhyama.
    assert len(M.EKA_NAK_UTTAMA) == 8 and len(M.EKA_NAK_ADHAMA) == 8
    assert not M.EKA_NAK_UTTAMA & M.EKA_NAK_ADHAMA
    # Vashya halves of Sagittarius / Capricorn.
    assert M.vashya_group(245) == "Manava" and M.vashya_group(255) == "Chatushpada"
    assert M.vashya_group(275) == "Chatushpada" and M.vashya_group(290) == "Jalachara"


def test_bands():
    assert [M.band(x) for x in (0, 17.5, 18, 24.5, 25, 32.5, 33, 36)] == [
        "Not recommended", "Not recommended", "Average", "Average", "Good", "Good",
        "Excellent", "Excellent"]


def test_hand_worked_pair():
    """Boy Rohini (Taurus 15°), girl Ashwini (Aries 5°): worked by hand from the tables."""
    b, g = M.moon_of("B", 45.0), M.moon_of("G", 5.0)
    a = M.ashtakoota(b, g)
    k = {x["name"]: x for x in a["kootas"]}
    # Varna Vaishya<Kshatriya 0; Vashya both quadrupeds 2; Tara Kshema/Vadha 1.5;
    # Yoni girl Horse x boy Serpent 3; Maitri Venus-Mars 3; Gana girl Deva x boy Manushya 6;
    # Bhakoot 2/12 with neutral lords 0 (no parihara); Nadi Antya vs Adi 8.
    assert [k[n]["score"] for n in ("Varna", "Vashya", "Tara", "Yoni", "Graha Maitri", "Gana",
                                    "Bhakoot", "Nadi")] == [0, 2, 1.5, 3, 3, 6, 0, 8]
    assert a["total"] == 23.5 and a["adjusted_total"] == 23.5 and a["rating"] == "Average"
    assert a["uncancelled_doshas"] == ["Bhakoot"]
    d = M.dashakoota(b, g)
    p = {x["name"]: x["result"] for x in d["poruthams"]}
    assert p == {"Dina": "Uttama", "Gana": "Madhyama", "Mahendra": "Yes",
                 "Stree Deergha": "Adhama", "Yoni": "Madhyama", "Rasi": "Adhama",
                 "Rasyadhipati": "Madhyama", "Vasya": "Adhama", "Rajju": "Yes", "Vedha": "Yes"}
    assert d["count_ok"] == 7 and d["critical_ok"]
    # Vedha and Rajju failures: Rohini x Swati (vedha pair, both Kantha rajju)
    d = M.dashakoota(M.moon_of("B", 45.0), M.moon_of("G", 190.0))
    p = {x["name"]: x["result"] for x in d["poruthams"]}
    assert p["Vedha"] == "No" and p["Rajju"] == "No" and not d["critical_ok"]


def test_parihara_rules():
    # Bhakoot 6/8 with the same lord (Aries-Scorpio, Mars) is cancelled.
    a = M.ashtakoota(M.moon_of("B", 220.0), M.moon_of("G", 10.0))
    bh = {x["name"]: x for x in a["kootas"]}["Bhakoot"]
    assert bh["score"] == 0 and bh["adjusted"] == 7 and bh["cancelled"]
    # Bhakoot 6/8 Aries-Virgo (Mars-Mercury 0.5) stays.
    a = M.ashtakoota(M.moon_of("B", 160.0), M.moon_of("G", 10.0))
    bh = {x["name"]: x for x in a["kootas"]}["Bhakoot"]
    assert bh["adjusted"] == 0 and not bh["cancelled"]
    # Nadi: same rashi, different nakshatras (Ashwini & Krittika-1 in Aries are Adi/Antya, so
    # use Ardra (Gemini 10°) and Punarvasu-2 (Gemini 25°): both Adi).
    a = M.ashtakoota(M.moon_of("B", 70.0), M.moon_of("G", 85.0))
    nd = {x["name"]: x for x in a["kootas"]}["Nadi"]
    assert nd["dosha"] and nd["cancelled"] and nd["adjusted"] == 8
    # Gana dosha (girl Rakshasa Krittika-Aries, boy Deva Ashwini) cancelled by same rashi.
    a = M.ashtakoota(M.moon_of("B", 5.0), M.moon_of("G", 28.0))
    gn = {x["name"]: x for x in a["kootas"]}["Gana"]
    assert gn["score"] == 1 and gn["dosha"] and gn["adjusted"] == 6


# ----------------------------------------------------------------------------- real couples
def test_couple_hyderabad_delhi():
    """Hyderabad 1990 boy with the India 1947 chart as the girl (different nakshatras)."""
    r = _couple("Ravi", datetime(1990, 5, 21, 14, 35), "India", datetime(1947, 8, 15, 0, 0),
                gplace=(28.6139, 77.2090, "Asia/Kolkata"))
    _show(r)
    assert (r["boy"]["moon_sign"], r["boy"]["nakshatra"], r["boy"]["pada"]) == ("Pisces", "Revati", 2)
    assert (r["girl"]["moon_sign"], r["girl"]["nakshatra"], r["girl"]["pada"]) == ("Cancer", "Pushya", 1)
    k = _k(r)
    assert k["Tara"]["boy"] == "Sampat" and k["Tara"]["girl"] == "Parama Mitra"
    assert k["Bhakoot"]["score"] == 0 and k["Bhakoot"]["cancelled"]    # 5/9, Jupiter-Moon friendly
    assert r["ashtakoota"]["total"] == 27 and r["ashtakoota"]["adjusted_total"] == 34
    assert r["dashakoota"]["count_ok"] == 8 and r["dashakoota"]["critical_ok"]
    kb, kg = r["kuja"]["boy"], r["kuja"]["girl"]
    assert kb["from"] == {"Lagna": 6, "Moon": 12, "Venus": 12} and not kb["present"]
    assert kg["mars_sign"] == "Gemini" and kg["from"]["Lagna"] == 2 and not kg["present"]
    assert r["seventh_lord"]["girl"]["lord"] == "Mars" and r["seventh_lord"]["girl"]["occupants"] == ["Ketu"]


def test_couple_same_nakshatra():
    """Both Moons in Revati (Pisces): different padas cancel Nadi dosha; same pada does not."""
    r = _couple("Ravi", datetime(1990, 5, 21, 14, 35), "Sita", datetime(1990, 1, 4, 11, 0))
    _show(r)
    assert r["boy"]["nakshatra"] == r["girl"]["nakshatra"] == "Revati"
    assert r["boy"]["pada"] != r["girl"]["pada"]
    nd = _k(r)["Nadi"]
    assert nd["score"] == 0 and nd["adjusted"] == 8 and "different padas" in nd["note"]
    p = _p(r)
    assert p["Dina"]["result"] == "Uttama"                 # Revati is an uttama eka-nakshatra
    assert p["Rajju"]["result"] == "No" and not r["dashakoota"]["critical_ok"]
    assert any("same nakshatra" in n for n in r["notes"])

    r = _couple("Ravi", datetime(1990, 5, 21, 14, 35), "Gita", datetime(1990, 1, 4, 18, 0))
    _show(r)
    assert r["boy"]["pada"] == r["girl"]["pada"]
    assert _k(r)["Nadi"]["adjusted"] == 0 and "Nadi" in r["ashtakoota"]["uncancelled_doshas"]
    assert _p(r)["Dina"]["result"] == "Madhyama"            # same pada lowers it one grade


def test_couple_nakshatra_across_signs():
    """Krittika pada 1 (Aries) boy and Krittika pada 2 (Taurus) girl."""
    r = _couple("Arun", datetime(1990, 1, 7, 9, 0), "Lata", datetime(1990, 1, 7, 16, 0))
    _show(r)
    assert (r["boy"]["moon_sign"], r["girl"]["moon_sign"]) == ("Aries", "Taurus")
    k = _k(r)
    assert k["Nadi"]["cancelled"] and "different Moon signs" in k["Nadi"]["note"]
    assert k["Bhakoot"]["dosha"] and not k["Bhakoot"]["cancelled"]       # 2/12, Mars-Venus neutral
    assert r["ashtakoota"]["total"] == 19 and r["ashtakoota"]["adjusted_total"] == 27


def test_couple_one_sided_kuja():
    """Girl with Mars in Pisces conjunct Venus, 12th from the Moon: uncancelled Kuja dosha."""
    r = _couple("Ravi", datetime(1990, 5, 21, 14, 35), "Uma", datetime(1990, 5, 23, 7, 0))
    _show(r)
    kg = r["kuja"]["girl"]
    assert kg["present"] and kg["dosha_from"] == ["Moon", "Venus"] and kg["strength"] == 2
    assert not r["kuja"]["boy"]["present"] and not r["kuja"]["balanced"]
    assert "Only the girl" in r["kuja"]["verdict"]


def test_telugu_output():
    tok = LANG.set("te")
    try:
        r = _couple("Ravi", datetime(1990, 5, 21, 14, 35), "Sita", datetime(1990, 1, 4, 11, 0))
        assert r["boy"]["nakshatra"] == "Revati"          # identifiers stay English
        assert all(isinstance(s, str) and s for s in r["summary"])
    finally:
        LANG.reset(tok)


if __name__ == "__main__":
    for fn in [v for k, v in dict(globals()).items() if k.startswith("test_")]:
        fn()
        print("passed", fn.__name__)

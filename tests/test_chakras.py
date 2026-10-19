"""Chakra engine checks. Run: .venv/bin/python -m tests.test_chakras"""
import json
from datetime import datetime, timezone

from app.core import chakras as C, ephemeris as E, panchang as P
from app.core.chart import BirthInput, SiderealChart
from app.core.constants import NAKSHATRAS, SIGNS

NOW = E.jd_from_utc(datetime(2026, 10, 19, 6, 0, tzinfo=timezone.utc))


def hyderabad_1990():
    return BirthInput("Hyderabad", "M", datetime(1990, 5, 21, 14, 35), 17.38405, 78.45636,
                      "Asia/Kolkata")


def india_1947():
    return BirthInput("India", "", datetime(1947, 8, 15, 0, 0), 28.6139, 77.2090,
                      "Asia/Kolkata")


def _run(inp):
    chart = SiderealChart(inp)
    pan = P.compute(chart, inp)
    return chart, pan, C.compute(chart, inp, pan, NOW)


def _token(cell: dict) -> str:
    """Normalise one of our cells to the token used by the reference grids below."""
    if cell["kind"] == "nakshatra":
        return cell["label"]
    if cell["kind"] == "sign":
        return SIGNS[cell["sign"]]
    if cell["kind"] in ("tithi", "center"):
        return cell["label"]
    key = {v[0]: k for k, v in (C.VOWELS if cell["kind"] == "vowel" else C.CONSONANTS).items()}
    return ("v:" if cell["kind"] == "vowel" else "c:") + key[cell["label"]]


def test_sbc_layout_against_wikipedia():
    """Wikipedia 'Sarvatobhadra Chakra' table, read column by column from the bottom."""
    nk = NAKSHATRAS
    cols = [
        ["v:ii", nk[22], nk[23], nk[24], nk[25], nk[26], nk[0], nk[1], "v:a"],
        [nk[21], "v:rii", "c:ga", "c:sa", "c:da", "c:cha", "c:la", "v:u", nk[2]],
        ["Abhijit", "c:kha", "v:ai", "Aquarius", "Pisces", "Aries", "v:lri", "c:a", nk[3]],
        [nk[20], "c:ja", "Capricorn", "v:ah", "Rikta", "v:o", "Taurus", "c:va", nk[4]],
        [nk[19], "c:bha", "Sagittarius", "Jaya", "Purna", "Nanda", "Gemini", "c:ka", nk[5]],
        [nk[18], "c:ya", "Scorpio", "v:am", "Bhadra", "v:au", "Cancer", "c:ha", nk[6]],
        [nk[17], "c:na", "v:e", "Libra", "Virgo", "Leo", "v:lrii", "c:dda", nk[7]],
        [nk[16], "v:ri", "c:ta", "c:ra", "c:pa", "c:tta", "c:ma", "v:uu", nk[8]],
        ["v:i", nk[15], nk[14], nk[13], nk[12], nk[11], nk[10], nk[9], "v:aa"],
    ]
    for c, col in enumerate(cols):
        for k, tok in enumerate(col):
            assert _token(C.SBC_GRID[8 - k][c]) == tok, (8 - k, c, tok)


def test_sbc_layout_against_pyjhora():
    """PyJHora ui/chakra.py Sarvatobadra grid (North on top): ours[r][c] == PJ[c][8-r]."""
    pj = [
        ['ii', 23, 24, 25, 26, 27, 1, 2, 'a'],
        [22, 'rii', 'g', 's', 'd', 'ch', 'l', 'u', 3],
        [28, 'kh', 'ai', 11, 12, 1, 'lu', 'a', 4],
        [21, 'j', 10, 'ah', 'Rikita', 'o', 2, 'v', 5],
        [20, 'bh', 9, 'Jaya', 'Pooma', 'Nanda', 3, 'k', 6],
        [19, 'y', 8, 'am', 'Bhadra', 'au', 4, 'h', 7],
        [18, 'n', 'e', 7, 6, 5, 'luu', 'd', 8],
        [17, 'ri', 't', 'r', 'p', 't~', 'm', 'uu', 9],
        ['i', 16, 15, 14, 13, 12, 11, 10, 'aa'],
    ]
    letters = {"lri": "lu", "lrii": "luu", "va": "v", "ka": "k", "ha": "h", "dda": "d",
               "ma": "m", "tta": "t~", "pa": "p", "ra": "r", "ta": "t", "na": "n", "ya": "y",
               "bha": "bh", "ja": "j", "kha": "kh", "ga": "g", "sa": "s", "da": "d",
               "cha": "ch", "la": "l"}
    tithi = {"Nanda": "Nanda", "Bhadra": "Bhadra", "Jaya": "Jaya", "Rikta": "Rikita",
             "Purna": "Pooma"}
    for r in range(9):
        for c in range(9):
            cell, ref = C.SBC_GRID[r][c], pj[c][8 - r]
            if cell["kind"] == "nakshatra":
                want = "Abhijit" if ref == 28 else NAKSHATRAS[ref - 1]
                assert cell["label"] == want, (r, c)
            elif cell["kind"] == "sign":
                assert cell["sign"] == ref - 1, (r, c)
            elif cell["kind"] in ("tithi", "center"):
                assert tithi[cell["label"]] == ref, (r, c)
            else:
                key = _token(cell)[2:]
                assert letters.get(key, key) == ref, (r, c, key, ref)


def test_sbc_counts_and_vedha_geometry():
    kinds = [c["kind"] for row in C.SBC_GRID for c in row]
    assert kinds.count("nakshatra") == 28 and kinds.count("vowel") == 16
    assert kinds.count("consonant") == 20 and kinds.count("sign") == 12
    assert kinds.count("tithi") == 4 and kinds.count("center") == 1
    lab = C._cell_label
    # Ashwini: front Purva Phalguni, left (forward) Rohini, right (backward) Jyeshtha
    v = C.vedha_lines(C.SBC_INDEX["n"][0])
    assert lab(v["front"][-1]) == "Purva Phalguni"
    assert lab(v["left"][-1]) == "Rohini" and lab(v["right"][-1]) == "Jyeshtha"
    # Krittika: front Shravana, left Vishakha, right Bharani
    v = C.vedha_lines(C.SBC_INDEX["n"][2])
    assert lab(v["front"][-1]) == "Shravana"
    assert lab(v["left"][-1]) == "Vishakha" and v["right"] == [C.SBC_INDEX["n"][1]]
    # Magha (South side): front Bharani, left Shravana
    v = C.vedha_lines(C.SBC_INDEX["n"][9])
    assert lab(v["front"][-1]) == "Bharani" and lab(v["left"][-1]) == "Shravana"


def test_nak28_and_letters():
    assert C.nak28_of(276.6) == 20 and C.nak28_of(276.7) == C.ABHIJIT
    assert C.nak28_of(280.88) == C.ABHIJIT and C.nak28_of(280.9) == 22
    assert C.NAK28[C.nak28_of(359.9)] == "Revati" and C.NAK28[C.nak28_of(0.1)] == "Ashwini"
    # every namakshara maps to one of Narapati's 20 letter cells
    for row in C.NAK_AKSHARA:
        for syl in row:
            assert C.LETTER_CELL[syl[0]] in C.CONSONANTS, syl
    assert C.tithi_group(1) == "Nanda" and C.tithi_group(15) == "Purna"
    assert C.tithi_group(30) == "Purna" and C.tithi_group(19) == "Rikta"


def test_kota_rules():
    # rings: outer 1,7,8,14,15,21,22,28 ... inner 4,11,18,25 (PyJHora placement table)
    rings = {}
    for k in range(28):
        rings.setdefault(C.kota_position(k, 0)["ring"], []).append(k + 1)
    assert rings["Bahya"] == [1, 7, 8, 14, 15, 21, 22, 28]
    assert rings["Prakara"] == [2, 6, 9, 13, 16, 20, 23, 27]
    assert rings["Madhya"] == [3, 5, 10, 12, 17, 19, 24, 26]
    assert rings["Stambha"] == [4, 11, 18, 25]
    # Kota Pala = varga lord of the pada namakshara; PyJHora kota_paala table, rows 0-20
    pj = [[5, 5, 5, 1], [1, 1, 1, 1], [0, 0, 0, 0], [0, 1, 1, 1], [1, 1, 2, 2], [2, 2, 2, 5],
          [2, 2, 7, 7], [7, 7, 7, 3], [3, 3, 3, 3], [6, 6, 6, 6], [6, 3, 3, 3], [3, 3, 6, 6],
          [6, 7, 3, 3], [6, 6, 1, 1], [1, 1, 1, 4], [4, 4, 4, 4], [4, 4, 4, 4], [4, 1, 1, 1],
          [1, 1, 6, 6], [6, 4, 6, 3], [6, 6, 5, 5]]
    names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"]
    for n, row in enumerate(pj):
        for pd, lord in enumerate(row):
            lon = n * 360 / 27 + pd * 360 / 108 + 0.5
            assert C.kota_pala(lon) == names[lord], (NAKSHATRAS[n], pd + 1)


def test_ghata_table():
    g = C.ghata_table(2)                     # Gemini
    assert SIGNS[g["chandra"]] == "Aquarius"  # SJC: ghataka chandra 9th from Gemini
    assert (SIGNS[g["lagna_same"]], SIGNS[g["lagna_opposite"]]) == ("Cancer", "Capricorn")
    assert g["nakshatra"] == "Swati" and g["weekday"] == 1 and g["tithi_group"] == "Bhadra"
    g = C.ghata_table(7)                     # Scorpio: Taurus Moon, Revati, Friday, Nanda
    assert SIGNS[g["chandra"]] == "Taurus" and g["nakshatra"] == "Revati" and g["weekday"] == 5
    assert SIGNS[C.ghata_table(8)["chandra"]] == "Pisces"
    for r in range(12):
        t = C.ghata_table(r)
        assert (t["lagna_opposite"] - t["lagna_same"]) % 12 == 6
        assert t["masa"] in P.MASAS and t["nakshatra"] in NAKSHATRAS


def _shape(res):
    json.dumps(res, ensure_ascii=False)
    assert set(res) == {"sarvatobhadra", "kota", "sanghatta", "sudarshan", "ghata"}
    s = res["sarvatobhadra"]
    assert len(s["grid"]) == 9 and all(len(r) == 9 for r in s["grid"])
    assert sum(len(v) for v in s["natal"].values()) == 9
    assert sum(len(v) for v in s["transit"].values()) == 9
    assert len(s["vedha"]) == 27 and all(v["type"] in ("front", "left", "right")
                                         for v in s["vedha"])
    assert set(s["native_points"]) == {"Janma nakshatra", "Name letter", "Janma rashi",
                                       "Tithi", "Weekday"}
    k = res["kota"]
    assert len(k["cells"]) == 16 and sum(len(v) for v in k["cells"].values()) == 28
    assert len(res["sanghatta"]["special"]) == 6
    for w in res["sanghatta"]["upcoming"]:
        assert w["start"] <= w["end"] and w["planet"] in C.WINDOW_PLANETS
    sd = res["sudarshan"]
    assert all(len(v) == 12 for v in sd["rings"].values())
    assert sd["current"]["house"] == sd["current"]["age"] % 12 + 1
    assert res["ghata"]["items"][0]["factor"] == "Month"


def test_hyderabad_1990():
    chart, pan, res = _run(hyderabad_1990())
    _shape(res)
    s = res["sarvatobhadra"]
    # Moon in Revati pada 2 ("Do" → Da), Pisces, Krishna Dwadashi (Bhadra), Monday (Bhadra)
    assert s["native_points"] == {"Janma nakshatra": C.SBC_INDEX["n"][27],
                                  "Name letter": C.SBC_INDEX["c"]["da"],
                                  "Janma rashi": C.SBC_INDEX["s"][11],
                                  "Tithi": C.SBC_INDEX["t"]["Bhadra"],
                                  "Weekday": C.SBC_INDEX["t"]["Bhadra"]}
    k = res["kota"]
    assert (k["swami"], k["pala"]) == ("Jupiter", "Jupiter")
    assert k["cells"]["Bahya|East"][0]["nakshatra"] == "Revati"
    sg = res["sanghatta"]["special"]
    assert [x["nakshatra"] for x in sg] == ["Revati", "Ashlesha", "Swati", "Anuradha",
                                           "Abhijit", "Dhanishta"]
    cur = res["sudarshan"]["current"]
    assert cur["age"] == 36 and cur["house"] == 1 and cur["signs"]["Lagna"] == chart.lagna_sign
    assert res["ghata"]["rashi"] == "Pisces"
    _print(res)


def test_india_1947():
    chart, pan, res = _run(india_1947())
    _shape(res)
    s = res["sarvatobhadra"]
    # Moon Pushya pada 1 ("Hu" → Ha), Cancer, Krishna Trayodashi (Jaya), Thursday (Jaya)
    assert s["native_points"]["Janma nakshatra"] == C.SBC_INDEX["n"][7]
    assert s["native_points"]["Name letter"] == C.SBC_INDEX["c"]["ha"]
    assert s["native_points"]["Tithi"] == s["native_points"]["Weekday"] == C.SBC_INDEX["t"]["Jaya"]
    assert (res["kota"]["swami"], res["kota"]["pala"]) == ("Moon", "Rahu")
    assert res["sudarshan"]["current"]["age"] == 79 and res["sudarshan"]["current"]["house"] == 8
    assert res["ghata"]["rashi"] == "Cancer"
    assert res["ghata"]["items"][3]["value"] == "Anuradha"
    # Sun windows last 13-15 days (about 4 in Abhijit)
    for w in res["sanghatta"]["upcoming"]:
        if w["planet"] == "Sun":
            d = (datetime.fromisoformat(w["end"]) - datetime.fromisoformat(w["start"])).days
            assert 3 <= d <= 15, w
    _print(res)


def _print(res):
    s = res["sarvatobhadra"]
    print("  SBC points:", s["native_points"])
    for line in s["summary"]:
        print("   ", line)
    print("  Kota:", res["kota"]["swami"], res["kota"]["pala"])
    for line in res["kota"]["assessment"]:
        print("   ", line)
    for w in res["sanghatta"]["upcoming"]:
        print("    window", w)
    print("  Sudarshan:", res["sudarshan"]["current"])
    print("  Ghata:", res["ghata"]["items"])
    print("  Ghata today:", res["ghata"]["today"])


if __name__ == "__main__":
    for fn in [v for k, v in dict(globals()).items() if k.startswith("test_")]:
        fn()
        print("passed", fn.__name__)

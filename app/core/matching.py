"""Marriage compatibility (Vivaha Melapaka).

* North Indian Ashtakoota / Guna Milan (36 points) with the classical pariharas
  (Muhurta Chintamani, Jyotirnibandha, Muhurta Pradipa, Kala Prakasika, Muhurta Ganapati).
* South Indian Dashakoota / 10 Poruthams (Tamil-Telugu practice, B.V. Raman's "Muhurtha").
* Kuja (Mangal) dosha of both charts with the standard cancellations and dosha samya.
* Supporting notes: Moon signs, nakshatras and the 7th lord of each chart.

Everything is judged from the Moon's sidereal position (Lahiri by default, whatever the
SiderealChart was built with). Scoring tables are oriented [girl][boy] as printed in the
almanacs ("bride rows, groom columns").
"""
from __future__ import annotations

from dataclasses import dataclass

from .constants import (ENEMIES, FRIENDS, GRAHAS, NAK_GANA, NAK_LORD, NAK_NADI, NAK_YONI,
                        NAKSHATRAS, SEVEN, SIGN_LORD, SIGN_VARNA, SIGNS, deg_in_sign,
                        nakshatra_of, sign_of)
from .vargas import varga_sign
from .vedic import aspects_on_signs, dignity
from ..i18n import ordinal, terms, tr

# ----------------------------------------------------------------------------- tables
# Varna rank of the Moon sign (Muhurta Chintamani: water=Brahmin, fire=Kshatriya,
# earth=Vaishya, air=Shudra; same as SIGN_VARNA). Boy's varna >= girl's earns the point.
VARNA_RANK = {"Brahmin": 4, "Kshatriya": 3, "Vaishya": 2, "Shudra": 1}

# Vashya groups. Sagittarius 0-15 human / 15-30 quadruped, Capricorn 0-15 quadruped /
# 15-30 aquatic (Muhurta Chintamani; onlinejyotish.com, aadri.in and PyJHora agree).
VASHYA_GROUPS = ["Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta"]
_VASHYA_OF_SIGN = {0: "Chatushpada", 1: "Chatushpada", 2: "Manava", 3: "Jalachara",
                   4: "Vanachara", 5: "Manava", 6: "Manava", 7: "Keeta", 10: "Manava",
                   11: "Jalachara"}
# Vashya points [girl][boy] in VASHYA_GROUPS order. This is the table reproduced identically by
# AstroYogi, AnytimeAstro, aadri.in, InstaAstro and PyJHora's "astroyogi" option.
VASHYA_PTS = [
    [2, 1, 1, 1.5, 1],      # girl Chatushpada
    [1, 2, 1.5, 0, 1],      # girl Manava
    [1, 1.5, 2, 1, 1],      # girl Jalachara
    [0, 0, 0, 2, 0],        # girl Vanachara (Leo)
    [1, 1, 1, 0, 2],        # girl Keeta (Scorpio)
]

TARA_NAMES = ["Janma", "Sampat", "Vipat", "Kshema", "Pratyari", "Sadhaka", "Vadha", "Mitra",
              "Parama Mitra"]
BAD_TARAS = {3, 5, 7}       # Vipat, Pratyari, Vadha (remainder of the count / 9)

# 14 yonis in the order of the standard matrix.
YONIS = ["Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat", "Cow", "Buffalo",
         "Tiger", "Deer", "Monkey", "Mongoose", "Lion"]
# Yoni points [girl][boy]. Identical in Saravali/Maitreya ("Bride" rows), aadri.in ("Female"
# rows) and VedAstro; PyJHora differs only in Lion-Buffalo. The 0s are the 7 sworn-enemy pairs.
YONI_PTS = [
    [4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1],   # Horse
    [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0],   # Elephant
    [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],   # Sheep
    [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],   # Serpent
    [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1],   # Dog
    [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],   # Cat
    [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2],   # Rat
    [1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],   # Cow
    [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],   # Buffalo
    [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1],   # Tiger
    [1, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1],   # Deer
    [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2],   # Monkey
    [2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2],   # Mongoose
    [1, 0, 1, 2, 1, 1, 2, 1, 2, 1, 1, 2, 2, 4],   # Lion
]
YONI_RELATION = {4: "same yoni", 3: "friendly", 2: "neutral", 1: "unfriendly",
                 0: "sworn enemies"}
# Male yoni nakshatras (Saravali, aadri.in); every other nakshatra is a female yoni.
YONI_MALE = {0, 1, 3, 7, 8, 9, 11, 14, 15, 17, 18, 19, 20, 24}

# Graha Maitri points by Moon-sign lords (SEVEN order). Standard table (onlinejyotish.com,
# aadri.in, PyJHora); it equals the BPHS natural-friendship rule 5/4/3/1/0.5/0.
GRAHA_MAITRI_PTS = [
    [5, 5, 5, 4, 5, 0, 0],          # Sun
    [5, 5, 4, 1, 4, 0.5, 0.5],      # Moon
    [5, 4, 5, 0.5, 5, 3, 0.5],      # Mars
    [4, 1, 0.5, 5, 0.5, 5, 4],      # Mercury
    [5, 4, 5, 0.5, 5, 0.5, 3],      # Jupiter
    [0, 0.5, 3, 5, 0.5, 5, 5],      # Venus
    [0, 0.5, 0.5, 4, 3, 5, 5],      # Saturn
]

GANAS = ["Deva", "Manushya", "Rakshasa"]
# Gana points [girl][boy] (onlinejyotish.com, Saravali/Maitreya, PyJHora agree).
GANA_PTS = [[6, 6, 0], [5, 6, 0], [1, 0, 6]]

# Bhakoot: count of the boy's Moon sign from the girl's that is inauspicious.
BHAKOOT_BAD = {2: "2/12", 12: "2/12", 5: "5/9", 9: "5/9", 6: "6/8", 8: "6/8"}

# Vashya rashis (Muhurta Chintamani / B.V. Raman): signs that are amenable to each sign.
VASYA_RASI = {0: (4, 7), 1: (3, 6), 2: (5,), 3: (7, 8), 4: (6,), 5: (2, 11), 6: (5, 9),
              7: (3,), 8: (11,), 9: (0, 10), 10: (0,), 11: (9,)}

# Nakshatras whose Eka-Nadi is excused by Narada Samhita (shown as a note only, since the
# lists in Narada and in the Piyushadhara commentary differ).
NADI_NARADA_EXEMPT = {1, 3, 5, 7, 9, 15, 21, 25}

# Same-nakshatra (Eka nakshatra) marriage, Tamil/Telugu almanac convention (Kalaprakasika).
EKA_NAK_UTTAMA = {3, 5, 9, 12, 15, 21, 25, 26}
EKA_NAK_ADHAMA = {1, 8, 14, 17, 18, 22, 23, 24}

# Mahendra: count girl -> boy (B.V. Raman, rekhai.in, PyJHora).
MAHENDRA_COUNTS = {4, 7, 10, 13, 16, 19, 22, 25}

# Rajju groups (B.V. Raman / VedAstro and PyJHora agree) and the classical effect of sharing one.
RAJJU = {"Pada": (0, 8, 9, 17, 18, 26), "Kati": (1, 7, 10, 16, 19, 25),
         "Nabhi": (2, 6, 11, 15, 20, 24), "Kantha": (3, 5, 12, 14, 21, 23),
         "Siro": (4, 13, 22)}
RAJJU_OF = {n: r for r, ns in RAJJU.items() for n in ns}
RAJJU_EFFECT = {"Siro": "danger to the husband's longevity",
                "Kantha": "danger to the wife's longevity",
                "Nabhi": "trouble concerning children",
                "Kati": "poverty", "Pada": "constant wandering and separation"}

# Vedha pairs (B.V. Raman; Mrigashira-Chitra-Dhanishta are mutually vedha in Tamil practice).
VEDHA_PAIRS = {frozenset(p) for p in [(0, 17), (1, 16), (2, 15), (3, 14), (5, 21), (6, 20),
                                       (7, 19), (8, 18), (9, 26), (10, 25), (11, 24),
                                       (12, 23), (4, 22), (4, 13), (13, 22)]}

# Kuja dosha houses (South Indian set including the 2nd) and B.V. Raman's sign exceptions:
# Mars in these houses (counted from the reference) in these signs gives no dosha.
KUJA_HOUSES = {1, 2, 4, 7, 8, 12}
KUJA_SIGN_EXCEPTIONS = {2: (2, 5), 12: (1, 6), 4: (0, 7), 7: (9, 3), 8: (8, 11)}

ASHTA_BANDS = [(0, 17.5, "Not recommended"), (18, 24.5, "Average"), (25, 32.5, "Good"),
               (33, 36, "Excellent")]
OK_RESULTS = {"Uttama", "Madhyama", "Yes"}


# ----------------------------------------------------------------------------- helpers
@dataclass
class _Moon:
    """The Moon-based attributes that every koota uses."""
    name: str
    lon: float
    sign: int
    nak: int
    pada: int
    navamsa: int

    @property
    def lord(self) -> str:
        return SIGN_LORD[self.sign]


def moon_of(name: str, moon_lon: float) -> _Moon:
    nk, pd = nakshatra_of(moon_lon)
    return _Moon(name, moon_lon, sign_of(moon_lon), nk, pd, varga_sign(moon_lon, 9))


def _num(x: float) -> float | int:
    return int(x) if float(x).is_integer() else round(x, 2)


def _rel(p: str, q: str) -> int:
    """Natural (BPHS) relation of p towards q: +1 friend, 0 neutral, -1 enemy."""
    if p == q or q in FRIENDS.get(p, ()):
        return 1
    return -1 if q in ENEMIES.get(p, ()) else 0


def graha_maitri(lord_b: str, lord_g: str) -> float:
    return GRAHA_MAITRI_PTS[SEVEN.index(lord_g)][SEVEN.index(lord_b)]


def mutual_friends(p: str, q: str) -> bool:
    return p == q or (_rel(p, q) == 1 and _rel(q, p) == 1)


def vashya_group(moon_lon: float) -> str:
    s, d = sign_of(moon_lon), deg_in_sign(moon_lon)
    if s == 8:
        return "Manava" if d < 15 else "Chatushpada"
    if s == 9:
        return "Chatushpada" if d < 15 else "Jalachara"
    return _VASHYA_OF_SIGN[s]


def nak_count(frm: int, to: int) -> int:
    """Inclusive count of nakshatra `to` from nakshatra `frm` (1..27)."""
    return (to - frm) % 27 + 1


def tara_of(count: int) -> int:
    """Tara number 1..9 for a nakshatra count."""
    return (count - 1) % 9 + 1


def _rel_word(r: int) -> str:
    return {1: tr("a friend"), 0: tr("neutral"), -1: tr("an enemy")}[r]


# ----------------------------------------------------------------------------- Ashtakoota
def ashtakoota(b: _Moon, g: _Moon) -> dict:
    """Guna Milan (36 points) with original and parihara-adjusted score per koota."""
    kootas = []
    same_rashi, same_nak = b.sign == g.sign, b.nak == g.nak
    gm = graha_maitri(b.lord, g.lord)
    n_bg = nak_count(b.nak, g.nak)          # girl's star counted from the boy's

    def add(name, mx, score, boy, girl, note, adjusted=None, **extra):
        kootas.append({"name": name, "max": mx, "score": _num(score),
                       "adjusted": _num(score if adjusted is None else adjusted),
                       "boy": boy, "girl": girl, "note": note, **extra})

    # 1. Varna
    vb, vg = SIGN_VARNA[b.sign], SIGN_VARNA[g.sign]
    ok = VARNA_RANK[vb] >= VARNA_RANK[vg]
    add("Varna", 1, 1 if ok else 0, vb, vg,
        tr("The boy's varna ({b}) is equal to or higher than the girl's ({g}), so the point is earned.", b=vb, g=vg) if ok else
        tr("The girl's varna ({g}) is higher than the boy's ({b}), so the point is lost; Varna is the lightest koota.", b=vb, g=vg))

    # 2. Vashya
    wb, wg = vashya_group(b.lon), vashya_group(g.lon)
    pts = VASHYA_PTS[VASHYA_GROUPS.index(wg)][VASHYA_GROUPS.index(wb)]
    add("Vashya", 2, pts, wb, wg,
        tr("Boy's Moon sign is {b}, girl's is {g}: {p} of 2 points for mutual attraction and influence.", b=wb, g=wg, p=_num(pts)))

    # 3. Tara (Dina): both directions, 1.5 points each when auspicious
    n_gb = nak_count(g.nak, b.nak)
    tb, tg = tara_of(n_gb), tara_of(n_bg)
    good = [t not in BAD_TARAS for t in (tb, tg)]
    pts = 1.5 * sum(good)
    note = tr("The boy's star is {nb} from the girl's ({tb} tara) and the girl's star is {ng} from the boy's ({tg} tara).",
              nb=ordinal(n_gb), tb=TARA_NAMES[tb - 1], ng=ordinal(n_bg), tg=TARA_NAMES[tg - 1])
    note += " " + (tr("Both taras are auspicious.") if all(good) else
                   tr("Both taras are inauspicious (Vipat, Pratyari or Vadha).") if not any(good) else
                   tr("One tara is inauspicious (Vipat, Pratyari or Vadha), so half the points are earned."))
    add("Tara", 3, pts, TARA_NAMES[tb - 1], TARA_NAMES[tg - 1], note)

    # 4. Yoni
    yb, yg = NAK_YONI[b.nak], NAK_YONI[g.nak]
    pts = YONI_PTS[YONIS.index(yg)][YONIS.index(yb)]
    sb = "male" if b.nak in YONI_MALE else "female"
    sg = "male" if g.nak in YONI_MALE else "female"
    add("Yoni", 4, pts, yb, yg,
        tr("Boy's yoni is {b} ({sb}), girl's is {g} ({sg}): {rel}, {p} of 4 points.",
           b=yb, sb=tr(sb), g=yg, sg=tr(sg), rel=tr(YONI_RELATION[pts]), p=pts))

    # 5. Graha Maitri
    if b.lord == g.lord:
        note = tr("Both Moon signs are ruled by {p}, so mental harmony is full.", p=b.lord)
    else:
        note = tr("The Moon-sign lords are {b} (boy) and {g} (girl): {b} treats {g} as {r1} and {g} treats {b} as {r2}.",
                  b=b.lord, g=g.lord, r1=_rel_word(_rel(b.lord, g.lord)), r2=_rel_word(_rel(g.lord, b.lord)))
    add("Graha Maitri", 5, gm, b.lord, g.lord, note)

    # 6. Gana (+ parihara)
    gb, gg = NAK_GANA[b.nak], NAK_GANA[g.nak]
    pts = GANA_PTS[GANAS.index(gg)][GANAS.index(gb)]
    note = tr("Boy is {b} gana, girl is {g} gana: {p} of 6 points.", b=gb, g=gg, p=pts)
    dosha, reasons = pts <= 1, []
    if dosha:
        note += " " + tr("This is Gana dosha.")
        if same_rashi and not same_nak:
            reasons.append(tr("Same Moon sign with different nakshatras removes Gana dosha (Jyotirnibandha)."))
        if same_nak and not same_rashi:
            reasons.append(tr("Same nakshatra in different Moon signs removes Gana dosha (Jyotirnibandha)."))
        if gm >= 4:
            reasons.append(tr("The Moon-sign lords {b} and {g} are the same or friendly (Graha Maitri {p}), which cancels Gana dosha.",
                              b=b.lord, g=g.lord, p=_num(gm)))
        if not reasons and n_bg > 14:
            # Raman's 14th-star rule belongs to the South Indian Gana porutham; noted only here.
            note += " " + tr("The girl's nakshatra is beyond the 14th from the boy's ({n}), which B.V. Raman counts as relief in the South Indian Gana porutham.",
                             n=ordinal(n_bg))
    add("Gana", 6, pts, gb, gg, " ".join([note] + reasons), 6 if dosha and reasons else pts,
        dosha=dosha, cancelled=bool(dosha and reasons))

    # 7. Bhakoot (+ parihara)
    cnt = (b.sign - g.sign) % 12 + 1
    pair = BHAKOOT_BAD.get(cnt)
    reasons = []
    if pair is None:
        pts = 7
        note = tr("The boy's Moon sign is {n} from the girl's ({b} and {g}), an auspicious relation: 7 points.",
                  n=ordinal(cnt), b=SIGNS[b.sign], g=SIGNS[g.sign])
    else:
        pts = 0
        effect = {"2/12": tr("loss of wealth"), "5/9": tr("trouble regarding children"),
                  "6/8": tr("strife and danger to health")}[pair]
        note = tr("The Moon signs {b} and {g} are {pair} from each other: Bhakoot dosha ({e}).",
                  b=SIGNS[b.sign], g=SIGNS[g.sign], pair=pair, e=effect)
        if b.lord == g.lord:
            reasons.append(tr("Both signs are ruled by {p}, which cancels Bhakoot dosha (Muhurta Pradipa).", p=b.lord))
        elif gm >= 4:
            reasons.append(tr("The sign lords {b} and {g} are friendly (Graha Maitri {p}), which cancels Bhakoot dosha (Muhurta Pradipa, Kala Prakasika).",
                              b=b.lord, g=g.lord, p=_num(gm)))
        if pair == "2/12" and (b.sign in VASYA_RASI[g.sign] or g.sign in VASYA_RASI[b.sign]):
            reasons.append(tr("One Moon sign is vashya to the other, which removes the 2/12 dosha (Kala Prakasika)."))
    add("Bhakoot", 7, pts, SIGNS[b.sign], SIGNS[g.sign], " ".join([note] + reasons),
        7 if pair and reasons else pts, dosha=pair is not None, cancelled=bool(pair and reasons))

    # 8. Nadi (+ parihara)
    nb, ng = NAK_NADI[b.nak], NAK_NADI[g.nak]
    reasons = []
    if nb != ng:
        pts = 8
        note = tr("Different Nadis (boy {b}, girl {g}): full 8 points.", b=nb, g=ng)
    else:
        pts = 0
        note = tr("Both are of {n} Nadi: Nadi dosha, traditionally the most serious koota fault.", n=nb)
        if same_rashi and not same_nak:
            reasons.append(tr("Same Moon sign with different nakshatras removes Nadi dosha (Jyotirnibandha, Muhurta Chintamani)."))
        if same_nak and not same_rashi:
            reasons.append(tr("Same nakshatra in different Moon signs removes Nadi dosha (Jyotirnibandha, Muhurta Chintamani)."))
        if same_nak and same_rashi and b.pada != g.pada:
            reasons.append(tr("Same nakshatra in different padas ({pb} and {pg}) is auspicious, so Nadi dosha does not apply (Muhurta Chintamani).",
                              pb=b.pada, pg=g.pada))
        if not same_rashi and mutual_friends(b.lord, g.lord):
            reasons.append(tr("The Moon-sign lords {b} and {g} are mutual friends, which cancels Nadi dosha (Muhurta Ganapati, B.V. Raman).",
                              b=b.lord, g=g.lord))
        if same_nak and b.pada == g.pada:
            note += " " + tr("Same nakshatra and same pada: the texts give no relief for this.")
        elif not reasons:
            # Single-source reliefs: reported as mitigation, not counted as a cancellation.
            lb, lg = SIGN_LORD[b.navamsa], SIGN_LORD[g.navamsa]
            if mutual_friends(lb, lg):
                note += " " + tr("The Navamsa lords of the two Moons ({b} and {g}) are friendly, which Muhurta Ganapati counts as relief; it is shown as a mitigation only.",
                                 b=lb, g=lg)
            if b.nak in NADI_NARADA_EXEMPT and g.nak in NADI_NARADA_EXEMPT:
                note += " " + tr("Narada Samhita excuses Eka-Nadi for these nakshatras; some astrologers treat the dosha as mild here.")
    add("Nadi", 8, pts, nb, ng, " ".join([note] + reasons), 8 if nb == ng and reasons else pts,
        dosha=nb == ng, cancelled=bool(nb == ng and reasons))

    total = sum(k["score"] for k in kootas)
    adjusted = sum(k["adjusted"] for k in kootas)
    rating_raw, rating = band(total), band(adjusted)
    left = [k["name"] for k in kootas if k.get("dosha") and not k.get("cancelled")]
    if adjusted == total:
        verdict = tr("{t} of 36 points: {r}.", t=_num(total), r=tr(rating))
    else:
        verdict = tr("{t} of 36 points ({r0}); {a} after parihara, since the cancelled doshas no longer count against the match ({r}).",
                     t=_num(total), r0=tr(rating_raw), a=_num(adjusted), r=tr(rating))
    verdict += " " + tr("Bands used: below 18 not recommended, 18-24 average, 25-32 good, 33 and above excellent.")
    if left:
        verdict += " " + tr("Uncancelled dosha: {d}; a detailed horoscope study is advised whatever the score.", d=", ".join(left))
    return {"kootas": kootas, "total": _num(total), "adjusted_total": _num(adjusted), "max": 36,
            "rating": rating, "rating_raw": rating_raw, "uncancelled_doshas": left,
            "verdict": verdict,
            "bands": [{"min": lo, "max": hi, "label": lbl} for lo, hi, lbl in ASHTA_BANDS]}


def band(points: float) -> str:
    """Guna Milan band label for a total out of 36 (scores move in half points)."""
    return next(lbl for lo, hi, lbl in ASHTA_BANDS if points <= hi)


# ----------------------------------------------------------------------------- Dashakoota
def dashakoota(b: _Moon, g: _Moon) -> dict:
    """South Indian 10 poruthams; Rajju and Vedha are the critical ones."""
    rows = []
    n = nak_count(g.nak, b.nak)          # boy's star from the girl's (the usual count)
    n_bg = nak_count(b.nak, g.nak)

    def add(name, result, note, boy=NAKSHATRAS[b.nak], girl=NAKSHATRAS[g.nak]):
        rows.append({"name": name, "result": result, "ok": result in OK_RESULTS,
                     "boy": boy, "girl": girl, "note": note})

    # 1. Dina: count girl -> boy, remainder /9 of 2, 4, 6, 8 or 0 is good
    if b.nak == g.nak:
        res = ("Uttama" if b.nak in EKA_NAK_UTTAMA else "Adhama" if b.nak in EKA_NAK_ADHAMA
               else "Madhyama")
        note = tr("Both are born in {nk}; for the same nakshatra the almanacs rate it {r}.", nk=NAKSHATRAS[b.nak], r=tr(res))
        if b.pada == g.pada:
            res = {"Uttama": "Madhyama", "Madhyama": "Adhama"}.get(res, res)
            note += " " + tr("The pada is also the same, which lowers it one grade.")
        else:
            note += " " + tr("The padas differ ({pb} and {pg}), which the texts call auspicious.", pb=b.pada, pg=g.pada)
    else:
        r = n % 9
        res = "Uttama" if r in (0, 2, 4, 6, 8) else "Adhama"
        note = tr("The boy's star is {n} from the girl's (remainder {r} on dividing by 9): {x}.",
                  n=ordinal(n), r=r, x=tr("agrees") if res == "Uttama" else tr("does not agree"))
    add("Dina", res, note, NAKSHATRAS[b.nak], NAKSHATRAS[g.nak])

    # 2. Gana
    gb, gg = NAK_GANA[b.nak], NAK_GANA[g.nak]
    if gb == gg:
        res, note = "Uttama", tr("Both are {g} gana.", g=gb)
    elif "Rakshasa" not in (gb, gg):
        res, note = "Madhyama", tr("Deva and Manushya ganas are compatible (boy {b}, girl {g}).", b=gb, g=gg)
    else:
        res = "Adhama"
        note = tr("A Rakshasa gana with a {o} gana does not agree (boy {b}, girl {g}).",
                  o=gb if gg == "Rakshasa" else gg, b=gb, g=gg)
        if n_bg > 14:
            res = "Madhyama"
            note += " " + tr("The girl's star is beyond the 14th from the boy's ({n}), so the fault is ignored (B.V. Raman).", n=ordinal(n_bg))
    add("Gana", res, note, gb, gg)

    # 3. Mahendra
    ok = n in MAHENDRA_COUNTS
    add("Mahendra", "Yes" if ok else "No",
        tr("The boy's star is {n} from the girl's; Mahendra needs the 4th, 7th, 10th, 13th, 16th, 19th, 22nd or 25th.", n=ordinal(n)))

    # 4. Stree Deergha: beyond 13 best, beyond 7 acceptable
    res = "Uttama" if n > 13 else "Madhyama" if n > 7 else "Adhama"
    add("Stree Deergha", res,
        tr("The boy's star is {n} from the girl's: beyond the 13th is best, beyond the 7th is acceptable.", n=ordinal(n)))

    # 5. Yoni
    yb, yg = NAK_YONI[b.nak], NAK_YONI[g.nak]
    pts = YONI_PTS[YONIS.index(yg)][YONIS.index(yb)]
    male_b, male_g = b.nak in YONI_MALE, g.nak in YONI_MALE
    if pts == 0:
        res = "Adhama"
    elif yb == yg or (pts == 3 and male_b and not male_g):
        res = "Uttama"
    else:
        res = "Madhyama"
    note = tr("Boy's yoni is {b}, girl's is {g} ({rel}).", b=yb, g=yg, rel=tr(YONI_RELATION[pts]))
    if pts and male_b and male_g:
        note += " " + tr("Both are male-yoni stars, which can bring quarrels.")
    add("Yoni", res, note, yb, yg)

    # 6. Rasi: count girl -> boy
    c = (b.sign - g.sign) % 12 + 1
    if c == 7:
        res, note = "Uttama", tr("The Moon signs are mutually 7th: health, agreement and happiness.")
    elif c == 1:
        res = "Uttama" if b.nak != g.nak else "Madhyama"
        note = tr("Same Moon sign ({s}); it is good when the nakshatras differ (Narada).", s=SIGNS[b.sign])
    elif c > 8:
        res, note = "Uttama", tr("The boy's Moon sign is {n} from the girl's (beyond the 6th): agrees.", n=ordinal(c))
    elif c == 8:
        res = "Madhyama"
        note = tr("The boy's Moon sign is 8th from the girl's: B.V. Raman accepts it but many almanacs avoid this 6/8 relation.")
    else:
        res = "Adhama"
        note = tr("The boy's Moon sign is {n} from the girl's, which does not agree.", n=ordinal(c))
        if graha_maitri(b.lord, g.lord) >= 4:
            res = "Madhyama"
            note += " " + tr("The sign lords {b} and {g} are the same or friendly, which removes the fault.", b=b.lord, g=g.lord)
    add("Rasi", res, note, SIGNS[b.sign], SIGNS[g.sign])

    # 7. Rasyadhipati (lords of the Moon signs)
    gm = graha_maitri(b.lord, g.lord)
    res = "Uttama" if gm == 5 else "Madhyama" if gm >= 3 else "Adhama"
    note = (tr("Both Moon signs are ruled by {p}.", p=b.lord) if b.lord == g.lord else
            tr("{b} treats {g} as {r1} and {g} treats {b} as {r2}.", b=b.lord, g=g.lord,
               r1=_rel_word(_rel(b.lord, g.lord)), r2=_rel_word(_rel(g.lord, b.lord))))
    add("Rasyadhipati", res, note, b.lord, g.lord)

    # 8. Vasya (vashya rashis)
    bg, gb_ = b.sign in VASYA_RASI[g.sign], g.sign in VASYA_RASI[b.sign]
    if bg and gb_:
        res, note = "Uttama", tr("{b} and {g} are vashya to each other.", b=SIGNS[b.sign], g=SIGNS[g.sign])
    elif bg or gb_:
        x, y = (b.sign, g.sign) if bg else (g.sign, b.sign)
        res, note = "Madhyama", tr("{x} is vashya to {y} (one-way attraction).", x=SIGNS[x], y=SIGNS[y])
    elif b.sign == g.sign:
        res, note = "Madhyama", tr("Same Moon sign: no separate vashya relation, treated as neutral.")
    else:
        res, note = "Adhama", tr("Neither {b} nor {g} is vashya to the other.", b=SIGNS[b.sign], g=SIGNS[g.sign])
    add("Vasya", res, note, SIGNS[b.sign], SIGNS[g.sign])

    # 9. Rajju (critical)
    rb, rg = RAJJU_OF[b.nak], RAJJU_OF[g.nak]
    if rb == rg:
        note = tr("Both stars are in {r} rajju: Rajju dosha ({e}).", r=rb, e=tr(RAJJU_EFFECT[rb]))
        others = {x["name"]: x["ok"] for x in rows}
        if all(others.get(k) for k in ("Dina", "Rasi", "Mahendra")) and gm >= 4:
            note += " " + tr("B.V. Raman allows it to be ignored when Dina, Rasi, Mahendra and Rasyadhipati all agree, as they do here; most Tamil almanacs still reject it.")
        add("Rajju", "No", note, rb, rg)
    else:
        add("Rajju", "Yes", tr("The stars are in different rajjus (boy {b}, girl {g}).", b=rb, g=rg), rb, rg)

    # 10. Vedha (critical)
    if frozenset((b.nak, g.nak)) in VEDHA_PAIRS:
        add("Vedha", "No", tr("{b} and {g} are a vedha (mutually obstructing) pair.", b=NAKSHATRAS[b.nak], g=NAKSHATRAS[g.nak]))
    else:
        add("Vedha", "Yes", tr("The stars do not afflict each other (no vedha)."))

    count = sum(r["ok"] for r in rows)
    critical = rows[8]["ok"] and rows[9]["ok"]
    if not critical:
        bad = ", ".join(r["name"] for r in rows[8:] if not r["ok"])
        rating = "Not recommended"
        verdict = tr("{n} of 10 poruthams agree, but {d} dosha is present; traditionally the match is not advised.", n=count, d=bad)
    else:
        rating = "Uttama" if count >= 8 else "Madhyama" if count >= 6 else "Adhama"
        verdict = tr("{n} of 10 poruthams agree and Rajju and Vedha are clear: {r}.", n=count,
                     r={"Uttama": tr("excellent match"), "Madhyama": tr("acceptable match"),
                        "Adhama": tr("weak match")}[rating])
    verdict += " " + tr("Bands used: 8 or more excellent, 6-7 acceptable, below 6 weak; a Rajju or Vedha failure overrides the count.")
    return {"poruthams": rows, "count_ok": count, "critical_ok": critical, "rating": rating,
            "verdict": verdict}


# ----------------------------------------------------------------------------- Kuja dosha
def kuja_dosha(chart) -> dict:
    """Mars in 1/2/4/7/8/12 from the Lagna, Moon and Venus, with the standard cancellations."""
    ms = chart.sign("Mars")
    refs = {"Lagna": chart.lagna_sign, "Moon": chart.sign("Moon"), "Venus": chart.sign("Venus")}
    frm = {k: (ms - s) % 12 + 1 for k, s in refs.items()}
    detected = [k for k, h in frm.items() if h in KUJA_HOUSES]
    cancellations, active = [], []
    for k in detected:
        h = frm[k]
        if ms in KUJA_SIGN_EXCEPTIONS.get(h, ()):
            cancellations.append(tr("Mars in the {h} from the {ref} in {sg} is a classical exception, so there is no dosha from the {ref}.",
                                    h=ordinal(h), ref=k, sg=SIGNS[ms]))
        else:
            active.append(k)
    general = []
    if active:
        if ms in (4, 10):
            general.append(tr("Mars in Leo or Aquarius produces no Kuja dosha (B.V. Raman)."))
        if ms in (0, 7, 9):
            general.append(tr("Mars is in its own sign or exalted ({sg}).", sg=SIGNS[ms]))
        js = chart.sign("Jupiter")
        if js == ms:
            general.append(tr("Mars is conjunct Jupiter."))
        elif "Jupiter" in aspects_on_signs({"Jupiter": js})[ms]:
            general.append(tr("Jupiter aspects Mars."))
        if chart.sign("Moon") == ms:
            general.append(tr("Mars is conjunct the Moon (Chandra-Mangala yoga)."))
        for p in ("Jupiter", "Venus"):
            if chart.house(p) == 1:
                general.append(tr("{p} occupies the Lagna.", p=p))
        if chart.lagna_sign in (3, 4):
            general.append(tr("For a {sg} Lagna Mars is a yogakaraka, so its placement is not considered harmful.",
                              sg=SIGNS[chart.lagna_sign]))
    present = bool(active) and not general
    # strength = number of reference points (Lagna, Moon, Venus) with an uncancelled dosha
    return {"present": present, "detected": bool(detected), "from": frm, "dosha_from": active,
            "strength": len(active) if present else 0, "mars_sign": SIGNS[ms],
            "cancellations": cancellations + general}


def _malefics_in_dosha_houses(chart) -> list[str]:
    """Saturn/Rahu/Ketu in 1/2/4/7/8/12 from the Lagna (papa samya check)."""
    return [p for p in ("Saturn", "Rahu", "Ketu") if chart.house(p) in KUJA_HOUSES]


def kuja_match(boy, girl) -> dict:
    """Kuja dosha of both charts and the samya (balancing) verdict."""
    kb, kg = kuja_dosha(boy), kuja_dosha(girl)
    if kb["present"] and kg["present"]:
        verdict = tr("Both partners have Kuja dosha, so it cancels out (dosha samya); this is acceptable.")
    elif not kb["present"] and not kg["present"]:
        verdict = tr("Neither partner has an active Kuja dosha.")
        if kb["detected"]:
            verdict += " " + tr("The boy's Mars is in a dosha house, but the dosha is cancelled.")
        if kg["detected"]:
            verdict += " " + tr("The girl's Mars is in a dosha house, but the dosha is cancelled.")
    else:
        other = girl if kb["present"] else boy
        verdict = (tr("Only the boy has an active Kuja dosha; traditionally this is a mismatch.") if kb["present"]
                   else tr("Only the girl has an active Kuja dosha; traditionally this is a mismatch."))
        samya = _malefics_in_dosha_houses(other)
        if samya:
            verdict += " " + tr("The other chart has {pl} in a dosha house from the Lagna, which partly balances it (papa samya).",
                                pl=terms(samya))
        else:
            verdict += " " + tr("The other chart has no balancing malefic, so remedies or a detailed study are advised.")
    return {"boy": kb, "girl": kg, "verdict": verdict,
            "balanced": kb["present"] == kg["present"]}


# ----------------------------------------------------------------------------- notes
def seventh_lord(chart) -> dict:
    s7 = (chart.lagna_sign + 6) % 12
    lord = SIGN_LORD[s7]
    signs = {p: chart.sign(p) for p in SEVEN}
    return {"sign": SIGNS[s7], "lord": lord, "house": chart.house(lord),
            "lord_sign": SIGNS[chart.sign(lord)],
            "dignity": dignity(lord, chart.bodies[lord].lon, signs),
            "occupants": [p for p in GRAHAS if chart.house(p) == 7]}


def _seventh_note(name: str, s: dict) -> str:
    out = tr("{n}: the 7th house is {s7}; its lord {l} is in house {h} ({sg}, {dg}).", n=name,
             s7=s["sign"], l=s["lord"], h=s["house"], sg=s["lord_sign"], dg=s["dignity"])
    if s["house"] in (1, 4, 5, 7, 9, 10):
        out += " " + tr("A 7th lord in a kendra or trikona supports marriage.")
    elif s["house"] in (6, 8, 12):
        out += " " + tr("A 7th lord in a dusthana can bring delays or strain; judge with the full chart.")
    else:
        out += " " + tr("A 7th lord in the 2nd, 3rd or 11th gives moderate results.")
    if s["occupants"]:
        out += " " + tr("Planets in the 7th: {pl}.", pl=terms(s["occupants"]))
    return out


def _person(m: _Moon, chart) -> dict:
    return {"name": m.name, "moon_sign": SIGNS[m.sign], "nakshatra": NAKSHATRAS[m.nak],
            "pada": m.pada, "moon_lon": round(m.lon, 4), "rashi_lord": m.lord,
            "nakshatra_lord": NAK_LORD[m.nak], "lagna": SIGNS[chart.lagna_sign],
            "varna": SIGN_VARNA[m.sign], "vashya": vashya_group(m.lon), "gana": NAK_GANA[m.nak],
            "yoni": NAK_YONI[m.nak], "nadi": NAK_NADI[m.nak], "rajju": RAJJU_OF[m.nak],
            "navamsa_sign": SIGNS[m.navamsa]}


# ----------------------------------------------------------------------------- public API
def match(boy, girl, boy_inp, girl_inp) -> dict:
    """Full marriage-compatibility report for a boy's and a girl's SiderealChart."""
    bn, gn = boy_inp.name or tr("Boy"), girl_inp.name or tr("Girl")
    b = moon_of(bn, boy.bodies["Moon"].lon)
    g = moon_of(gn, girl.bodies["Moon"].lon)
    ak, dk, kj = ashtakoota(b, g), dashakoota(b, g), kuja_match(boy, girl)
    s7b, s7g = seventh_lord(boy), seventh_lord(girl)

    notes = [tr("{n}'s Moon is in {s} in {nk} pada {p} (nakshatra lord {nl}, sign lord {sl}).", n=x.name,
                s=SIGNS[x.sign], nk=NAKSHATRAS[x.nak], p=x.pada, nl=NAK_LORD[x.nak], sl=x.lord)
             for x in (b, g)]
    if b.nak == g.nak:
        notes.append(tr("Both are born in the same nakshatra ({nk}); the same-star rules of Dina, Nadi and Rajju apply.",
                        nk=NAKSHATRAS[b.nak]))
    notes += [_seventh_note(bn, s7b), _seventh_note(gn, s7g)]

    concerns = list(ak["uncancelled_doshas"])
    if ak["adjusted_total"] < 18:
        concerns.append(tr("low guna score"))
    concerns += [r["name"] for r in dk["poruthams"][8:] if not r["ok"]]
    if not kj["balanced"]:
        concerns.append(tr("Kuja dosha mismatch"))
    summary = [
        tr("{b} ({bs}, {bnk}) and {g} ({gs}, {gnk}).", b=bn, bs=SIGNS[b.sign], bnk=NAKSHATRAS[b.nak],
           g=gn, gs=SIGNS[g.sign], gnk=NAKSHATRAS[g.nak]),
        tr("Ashtakoota: {t} of 36 points ({r}).", t=ak["total"], r=tr(ak["rating"]))
        if ak["total"] == ak["adjusted_total"] else
        tr("Ashtakoota: {t} of 36 points ({r0}), {a} after parihara ({r}).", t=ak["total"],
           r0=tr(ak["rating_raw"]), a=ak["adjusted_total"], r=tr(ak["rating"])),
        tr("Dashakoota: {n} of 10 poruthams agree; Rajju and Vedha are {c}.", n=dk["count_ok"],
           c=tr("clear") if dk["critical_ok"] else tr("not clear")),
        kj["verdict"],
        tr("Overall the match is favourable on the traditional checks.") if not concerns else
        tr("Points needing a detailed study: {c}.", c=", ".join(concerns)),
    ]
    return {"boy": _person(b, boy), "girl": _person(g, girl), "ashtakoota": ak, "dashakoota": dk,
            "kuja": kj, "seventh_lord": {"boy": s7b, "girl": s7g}, "notes": notes,
            "summary": summary}

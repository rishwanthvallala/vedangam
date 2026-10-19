"""Yoga & dosha detection (Parashari / Phaladeepika / BPHS / Nabhasa)."""
from __future__ import annotations

from .constants import (DEBILITATION, EXALTATION, GRAHAS, OWN_SIGNS, SEVEN, SIGN_LORD,
                        SIGNS, norm)
from .ephemeris import angdiff
from .vedic import aspects_on_signs, dignity, graha_aspects
from ..i18n import tr

KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}
DUSTHANA = {6, 8, 12}


def _yoga(name, category, present, desc, planets=None, strength=None):
    return {"name": name, "category": category, "present": present, "description": desc,
            "planets": planets or [], "strength": strength}


def detect(chart) -> list[dict]:
    L = chart.lagna_sign
    s = {p: chart.sign(p) for p in GRAHAS}
    h = {p: chart.house(p) for p in GRAHAS}
    lord = lambda house: SIGN_LORD[(L + house - 1) % 12]
    signs7 = {p: s[p] for p in SEVEN}
    dig = {p: dignity(p, chart.bodies[p].lon, signs7) for p in GRAHAS}
    asp = aspects_on_signs(s)
    moon_s = s["Moon"]
    out = []

    def conj(a, b):
        return s[a] == s[b]

    def aspects(a, b):  # a aspects b (whole sign)
        return a in asp[s[b]]

    def related(a, b):
        """Conjunction, mutual aspect, or exchange (sambandha)."""
        if a == b:
            return False
        if conj(a, b):
            return True
        if aspects(a, b) and aspects(b, a):
            return True
        if SIGN_LORD[s[a]] == b and SIGN_LORD[s[b]] == a:
            return True
        return False

    strong = lambda p: dig[p] in ("Exalted", "Own", "Moolatrikona")

    # ---- Pancha Mahapurusha
    pmp = {"Mars": ("Ruchaka Yoga", "Gives courage, command, an athletic build and leadership in martial or technical fields."),
           "Mercury": ("Bhadra Yoga", "Gives a sharp intellect, eloquence, learning, commercial skill and a lasting reputation."),
           "Jupiter": ("Hamsa Yoga", "Gives wisdom, righteousness, respect from the learned and a spiritual inclination."),
           "Venus": ("Malavya Yoga", "Gives beauty, comforts, vehicles, artistic refinement and a happy marriage."),
           "Saturn": ("Sasa Yoga", "Gives authority over people, discipline, organising power and endurance.")}
    for p, (nm, d) in pmp.items():
        ok = h[p] in KENDRA and strong(p)
        okm = ((s[p] - moon_s) % 12 + 1) in KENDRA and strong(p)
        where = tr("from the Lagna") if ok else tr("from the Moon") if okm else tr("not formed")
        out.append(_yoga(tr(nm), "Pancha Mahapurusha", ok or okm,
                         tr("{p} in its own or exaltation sign in a kendra ({where}).", p=p, where=where) + " " + tr(d),
                         [p], "Strong" if ok and dig[p] == "Exalted" else None))

    # ---- Lunar yogas
    jm = (s["Jupiter"] - moon_s) % 12 + 1
    gk = jm in KENDRA
    out.append(_yoga(tr("Gaja Kesari Yoga"), "Lunar", gk,
                     tr("Jupiter in a kendra from the Moon: intelligence, lasting fame, prosperity, victory over rivals.")
                     + ("" if dig["Jupiter"] != "Debilitated" else " " + tr("Jupiter is debilitated, so the yoga is weakened.")),
                     ["Moon", "Jupiter"]))
    nonlum = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    sec = [p for p in nonlum if s[p] == (moon_s + 1) % 12]
    twe = [p for p in nonlum if s[p] == (moon_s - 1) % 12]
    out.append(_yoga(tr("Sunapha Yoga"), "Lunar", bool(sec) and not twe,
                     tr("Planets other than the Sun in the 2nd from the Moon: self-earned wealth, intelligence, good reputation."), sec))
    out.append(_yoga(tr("Anapha Yoga"), "Lunar", bool(twe) and not sec,
                     tr("Planets other than the Sun in the 12th from the Moon: good health, charm, renunciation in later life."), twe))
    out.append(_yoga(tr("Durudhara Yoga"), "Lunar", bool(sec) and bool(twe),
                     tr("Planets on both sides of the Moon: wealth, vehicles, generosity, comforts."), sec + twe))
    kendras_moon = [p for p in nonlum if ((s[p] - moon_s) % 12 + 1) in KENDRA]
    kendras_lag = [p for p in nonlum if h[p] in KENDRA]
    kema = not sec and not twe and not [p for p in nonlum if s[p] == moon_s]
    kema_cancel = bool(kendras_moon or kendras_lag)
    out.append(_yoga(tr("Kemadruma Yoga"), "Dosha", kema and not kema_cancel,
                     tr("No planets in the 2nd or 12th from the Moon, or with it, and none in kendras: emotional isolation, fluctuating finances.")
                     + (" " + tr("Cancelled by planets in kendras.") if kema and kema_cancel else ""), ["Moon"]))
    ben_6_7_8 = [p for p in ("Mercury", "Jupiter", "Venus")
                 if ((s[p] - moon_s) % 12 + 1) in (6, 7, 8)]
    out.append(_yoga(tr("Adhi Yoga"), "Lunar", len(ben_6_7_8) >= 2,
                     tr("Benefics in the 6th, 7th and 8th from the Moon: leadership, a ministerial position, a long and healthy life."),
                     ben_6_7_8))
    out.append(_yoga(tr("Chandra-Mangala Yoga"), "Lunar", conj("Moon", "Mars"),
                     tr("Moon conjoined with Mars: earning power through enterprise, sometimes harsh speech or impulsive spending."),
                     ["Moon", "Mars"]))
    sun_s = s["Sun"]
    sv2 = [p for p in nonlum if s[p] == (sun_s + 1) % 12 and p != "Moon"]
    sv12 = [p for p in nonlum if s[p] == (sun_s - 1) % 12 and p != "Moon"]
    out.append(_yoga(tr("Vesi Yoga"), "Solar", bool(sv2) and not sv12,
                     tr("A planet in the 2nd from the Sun: balanced outlook, truthful, industrious."), sv2))
    out.append(_yoga(tr("Vasi Yoga"), "Solar", bool(sv12) and not sv2,
                     tr("A planet in the 12th from the Sun: skilful, charitable, liked by those in authority."), sv12))
    out.append(_yoga(tr("Ubhayachari Yoga"), "Solar", bool(sv2) and bool(sv12),
                     tr("Planets on both sides of the Sun: eloquent, wealthy, king-like status."), sv2 + sv12))
    comb = abs(angdiff(chart.bodies['Sun'].lon, chart.bodies['Mercury'].lon)) < 14
    out.append(_yoga(tr("Budha-Aditya Yoga"), "Solar", conj("Sun", "Mercury"),
                     tr("Sun with Mercury: intelligence, analytical ability, skill in communication.")
                     + (" " + tr("Mercury is combust, so the results are reduced.") if comb else ""),
                     ["Sun", "Mercury"]))
    amala = [p for p in ("Mercury", "Jupiter", "Venus") if h[p] == 10 or ((s[p] - moon_s) % 12 + 1) == 10]
    out.append(_yoga(tr("Amala Yoga"), "Benefic", bool(amala),
                     tr("A natural benefic in the 10th from the Lagna or the Moon: spotless reputation, ethical conduct, lasting fame."), amala))

    # ---- Raja yogas: kendra lord + trikona lord sambandha
    rj = []
    for k in (1, 4, 7, 10):
        for t in (1, 5, 9):
            a, b = lord(k), lord(t)
            if a == b and k != t:
                if a not in rj:
                    out.append(_yoga(tr("Yogakaraka {a}", a=a), "Raja", True,
                                     tr("{a} owns both a kendra ({k}) and a trikona ({t}), making it a yogakaraka; its periods bring a rise in status.", a=a, k=k, t=t),
                                     [a], "Strong"))
                    rj.append(a)
            elif a != b and related(a, b):
                key = tuple(sorted([a, b]))
                if key in rj:
                    continue
                rj.append(key)
                out.append(_yoga(tr("Raja Yoga ({k}L–{t}L)", k=k, t=t), "Raja", True,
                                 tr("The lord of kendra {k} ({a}) is linked with the lord of trikona {t} ({b}) by conjunction, aspect or exchange: power, authority and success during their periods.", k=k, a=a, t=t, b=b),
                                 [a, b]))
    # Dhana yogas: 2/11 with 1/5/9
    dy = set()
    for w in (2, 11):
        for t in (1, 5, 9):
            a, b = lord(w), lord(t)
            if a != b and related(a, b) and (a, b) not in dy:
                dy.add((a, b))
                out.append(_yoga(tr("Dhana Yoga ({w}L–{t}L)", w=w, t=t), "Dhana", True,
                                 tr("Wealth lord {a} (house {w}) is associated with {b} (house {t}): accumulation of wealth.", a=a, w=w, b=b, t=t),
                                 [a, b]))
    # Viparita raja yogas
    for nm, hh in (("Harsha Viparita Raja Yoga", 6), ("Sarala Viparita Raja Yoga", 8), ("Vimala Viparita Raja Yoga", 12)):
        lp = lord(hh)
        ok = h[lp] in DUSTHANA
        out.append(_yoga(tr(nm), "Viparita", ok,
                         tr("The lord of house {hh} ({lp}) is placed in a dusthana (6, 8 or 12): success emerging from adversity, victory over enemies.", hh=hh, lp=lp),
                         [lp]))
    # Parivartana
    seen = set()
    for a in SEVEN:
        b = SIGN_LORD[s[a]]
        if b != a and b in SEVEN and SIGN_LORD[s[b]] == a and (b, a) not in seen:
            seen.add((a, b))
            houses = sorted([h[a], h[b]])
            if any(x in DUSTHANA for x in houses):
                kind = "Dainya"
            elif 3 in houses:
                kind = "Khala"
            else:
                kind = "Maha"
            desc = {"Maha": "an exchange between good houses: wealth, status, prosperity",
                    "Khala": "it involves the 3rd house: fluctuating fortune, gains through initiative",
                    "Dainya": "it involves a dusthana: struggles that transform, with mixed results"}[kind]
            out.append(_yoga(tr(f"{kind} Parivartana Yoga"), "Parivartana", True,
                             tr("{a} and {b} exchange signs (houses {h1} and {h2}); {desc}.", a=a, b=b, h1=houses[0], h2=houses[1], desc=tr(desc)),
                             [a, b]))
    # Neecha bhanga
    for p in SEVEN:
        if dig[p] != "Debilitated":
            continue
        ds = s[p]
        dl = SIGN_LORD[ds]
        ex_lord = SIGN_LORD[EXALTATION[p][0]]
        reasons = []
        if chart.house(dl) in KENDRA or ((s[dl] - moon_s) % 12 + 1) in KENDRA:
            reasons.append(tr("the lord of the debilitation sign, {dl}, is in a kendra", dl=dl))
        if chart.house(ex_lord) in KENDRA or ((s[ex_lord] - moon_s) % 12 + 1) in KENDRA:
            reasons.append(tr("the lord of the exaltation sign, {x}, is in a kendra", x=ex_lord))
        if dl in asp[ds] and dl != p:
            reasons.append(tr("it is aspected by its dispositor {dl}", dl=dl))
        exalted_here = [q for q in SEVEN if q != p and s[q] == ds and EXALTATION[q][0] == ds]
        if exalted_here:
            reasons.append(tr("it is conjoined with an exalted planet ({q})", q=exalted_here[0]))
        from .vargas import varga_sign
        if varga_sign(chart.bodies[p].lon, 9) == EXALTATION[p][0]:
            reasons.append(tr("it is exalted in the Navamsa"))
        desc = (tr("{p} is debilitated, but the debilitation is cancelled because {reasons}. Early setbacks turn into a notable rise.", p=p, reasons="; ".join(reasons))
                if reasons else tr("{p} is debilitated with no cancellation; its significations need conscious effort.", p=p))
        out.append(_yoga(tr("Neecha Bhanga Raja Yoga ({p})", p=p), "Raja", bool(reasons), desc, [p]))
    # Lakshmi yoga
    l9 = lord(9)
    out.append(_yoga(tr("Lakshmi Yoga"), "Dhana", strong(l9) and h[l9] in KENDRA | TRIKONA and
                     dig[lord(1)] not in ("Debilitated", "Enemy", "Great Enemy"),
                     tr("The 9th lord {l9} is strong in a kendra or trikona with a sound Lagna lord: wealth, nobility, the grace of Lakshmi.", l9=l9),
                     [l9]))
    # Saraswati
    goodh = KENDRA | TRIKONA | {2}
    sar = all(h[p] in goodh for p in ("Jupiter", "Venus", "Mercury")) and \
        dig["Jupiter"] in ("Exalted", "Own", "Moolatrikona", "Great Friend", "Friend")
    out.append(_yoga(tr("Saraswati Yoga"), "Knowledge", sar,
                     tr("Jupiter, Venus and Mercury in kendras, trikonas or the 2nd, with Jupiter strong: learning, poetry, eloquence, scholarship."),
                     ["Jupiter", "Venus", "Mercury"]))
    # Kahala
    l4 = lord(4)
    out.append(_yoga(tr("Kahala Yoga"), "Raja", (((s[l4] - s["Jupiter"]) % 12 + 1) in KENDRA) and
                     strong(lord(1)) and l4 != "Jupiter",
                     tr("The 4th lord and Jupiter in mutual kendras with a strong Lagna lord: boldness, leadership of a group."),
                     [l4, "Jupiter"]))
    # Shankha / Parvata / Chamara
    l5, l6 = lord(5), lord(6)
    out.append(_yoga(tr("Shankha Yoga"), "Benefic", ((s[l5] - s[l6]) % 12 + 1) in KENDRA and strong(lord(1)),
                     tr("The 5th and 6th lords in mutual kendras with a strong Lagna lord: humane, long-lived, fortunate."),
                     [l5, l6]))
    par = all(h[p] not in DUSTHANA for p in ("Mercury", "Jupiter", "Venus", "Moon")) and \
        any(h[p] in KENDRA for p in ("Mercury", "Jupiter", "Venus"))
    out.append(_yoga(tr("Parvata Yoga"), "Benefic", par and not any(h[p] in (6, 8) for p in SEVEN),
                     tr("Benefics in kendras with the 6th and 8th free of planets: prosperity, charity, fame."), []))
    ll = lord(1)
    cham = (dig[ll] == "Exalted" and h[ll] in KENDRA and "Jupiter" in asp[s[ll]])
    out.append(_yoga(tr("Chamara Yoga"), "Raja", cham,
                     tr("An exalted Lagna lord in a kendra, aspected by Jupiter: honoured by rulers, eloquent, learned."), [ll]))

    # ---- Nabhasa (selected)
    occ_signs = {s[p] for p in SEVEN}
    mov = {0, 3, 6, 9}
    fix = {1, 4, 7, 10}
    dua = {2, 5, 8, 11}
    if occ_signs <= mov:
        out.append(_yoga(tr("Rajju Yoga (Nabhasa)"), "Nabhasa", True,
                         tr("All planets in movable signs: fond of travel, restless, earns abroad."), []))
    if occ_signs <= fix:
        out.append(_yoga(tr("Musala Yoga (Nabhasa)"), "Nabhasa", True,
                         tr("All planets in fixed signs: proud, steady, wealthy, determined."), []))
    if occ_signs <= dua:
        out.append(_yoga(tr("Nala Yoga (Nabhasa)"), "Nabhasa", True,
                         tr("All planets in dual signs: skilful, versatile, resourceful."), []))
    houses_occ = {h[p] for p in SEVEN}
    n = len({s[p] for p in SEVEN})
    sankhya = {7: ("Vallaki Yoga (Sankhya)", "musical, many friends, happy"),
               6: ("Damini Yoga (Sankhya)", "helpful, wealthy, famous"),
               5: ("Pasha Yoga (Sankhya)", "a skilled earner with a large circle"),
               4: ("Kedara Yoga (Sankhya)", "wealth from land, useful to others"),
               3: ("Shoola Yoga (Sankhya)", "sharp, brave, faces conflict"),
               2: ("Yuga Yoga (Sankhya)", "unorthodox, struggles with wealth"),
               1: ("Gola Yoga (Sankhya)", "little formal learning, a wandering life")}
    nm, d = sankhya[n]
    out.append(_yoga(tr(nm), "Nabhasa", True,
                     tr("The seven planets occupy {n} signs: {d}.", n=n, d=tr(d)), []))
    if houses_occ <= KENDRA:
        out.append(_yoga(tr("Kamala Yoga (Nabhasa)"), "Nabhasa", True,
                         tr("All planets in kendras: renowned, virtuous, long-lived, commands respect."), []))
    if houses_occ <= {2, 3, 5, 6, 8, 9, 11, 12} and not houses_occ & KENDRA:
        out.append(_yoga(tr("Vapi Yoga (Nabhasa)"), "Nabhasa", True,
                         tr("No planets in kendras (all in panaphara or apoklima houses): accumulates wealth, enjoys comforts."), []))
    # Shakata
    jm_ = (s["Jupiter"] - moon_s) % 12 + 1
    out.append(_yoga(tr("Shakata Yoga"), "Dosha", jm_ in (6, 8, 12) and h["Jupiter"] not in KENDRA,
                     tr("Jupiter in the 6th, 8th or 12th from the Moon and not in a kendra from the Lagna: ups and downs of fortune, like a turning cart wheel."),
                     ["Jupiter", "Moon"]))

    # ---- Doshas
    mars_h = h["Mars"]
    mars_from_moon = (s["Mars"] - moon_s) % 12 + 1
    mars_from_ven = (s["Mars"] - s["Venus"]) % 12 + 1
    md_houses = {1, 2, 4, 7, 8, 12}
    md = mars_h in md_houses
    cancel = []
    if dig["Mars"] in ("Own", "Exalted", "Moolatrikona"):
        cancel.append(tr("Mars is in its own or exaltation sign"))
    if s["Mars"] in (4, 10) and mars_h in (1, 4, 7, 8, 12):  # Leo/Aquarius exceptions
        cancel.append(tr("Mars is in Leo or Aquarius"))
    if conj("Mars", "Jupiter") or "Jupiter" in asp[s["Mars"]]:
        cancel.append(tr("Jupiter conjoins or aspects Mars"))
    desc = tr("Mars is in house {h} from the Lagna ({m} from the Moon, {v} from Venus).", h=mars_h, m=mars_from_moon, v=mars_from_ven)
    if cancel and md:
        desc += " " + tr("Mitigating factors: {c}.", c="; ".join(cancel))
    desc += " " + tr("This is traditionally checked for marriage compatibility.")
    out.append({"name": tr("Mangal (Kuja) Dosha"), "category": "Dosha", "present": md,
                "description": desc,
                "planets": ["Mars"], "strength": "Mild (cancelled)" if md and cancel else ("Present" if md else None),
                "from_moon": mars_from_moon in md_houses, "from_venus": mars_from_ven in md_houses})
    # Kaal Sarp
    r = chart.bodies["Rahu"].lon
    side = [norm(chart.bodies[p].lon - r) < 180 for p in SEVEN]
    ks = all(side) or not any(side)
    names = ["Anant", "Kulik", "Vasuki", "Shankhapal", "Padma", "Mahapadma", "Takshak",
             "Karkotak", "Shankhachur", "Ghatak", "Vishdhar", "Sheshnag"]
    ksn = names[h["Rahu"] - 1]
    out.append(_yoga(tr("Kaal Sarp Dosha ({t})", t=ksn) if ks else tr("Kaal Sarp Dosha"), "Dosha", ks,
                     tr("All seven planets are hemmed between Rahu and Ketu: karmic intensity, delays followed by a sudden rise.")
                     + (" " + tr("Rahu in house {h} makes it the {t} type.", h=h["Rahu"], t=ksn) if ks else ""), ["Rahu", "Ketu"]))
    for nm, a, b, d in (("Guru Chandala Yoga", "Jupiter", "Rahu", "Jupiter with Rahu: unorthodox beliefs and issues with teachers or ethics, though it can also give unconventional wisdom."),
                        ("Grahan Dosha (Sun–Rahu)", "Sun", "Rahu", "Sun with Rahu: challenges with the father or authority, confusion about the ego."),
                        ("Grahan Dosha (Sun–Ketu)", "Sun", "Ketu", "Sun with Ketu: detachment from status, spiritual seeking."),
                        ("Grahan Dosha (Moon–Rahu)", "Moon", "Rahu", "Moon with Rahu: an anxious mind and a strong imagination."),
                        ("Grahan Dosha (Moon–Ketu)", "Moon", "Ketu", "Moon with Ketu: emotional detachment, intuition."),
                        ("Shrapit Dosha", "Saturn", "Rahu", "Saturn with Rahu: karmic delays; persistence is required."),
                        ("Angarak Yoga", "Mars", "Rahu", "Mars with Rahu: aggression, risk of accidents, strong drive."),
                        ("Pitru Dosha indication", "Sun", "Saturn", "Sun with Saturn: friction with the father, responsibilities toward ancestors.")):
        out.append(_yoga(tr(nm), "Dosha", conj(a, b), tr(d), [a, b]))
    return out


def sade_sati(chart, inp, years: int = 100) -> dict:
    """Saturn transits through 12th, 1st, 2nd from natal Moon sign (Sade Sati) and 4th/8th
    (Dhaiya/Kantaka) across the native's life."""
    from . import ephemeris as E
    moon_s = chart.sign("Moon")
    start = inp.jd
    end = start + years * 365.25
    step = 5.0
    t = start
    prev = E.calc_body(t, "Saturn", chart.ayanamsa).lon // 30
    changes = [(t, int(prev))]
    while t < end:
        t2 = t + step
        cur = E.calc_body(t2, "Saturn", chart.ayanamsa).lon // 30
        if cur != prev:
            boundary = (cur if (cur - prev) % 12 == 1 else prev) * 30.0
            f = lambda x: E.angdiff(E.calc_body(x, "Saturn", chart.ayanamsa).lon, boundary)
            tc = E.find_crossing(f, t, t2)
            changes.append((tc, int(cur)))
            prev = cur
        t = t2
    periods = []
    for i, (tc, sg) in enumerate(changes):
        te = changes[i + 1][0] if i + 1 < len(changes) else end
        rel = (sg - moon_s) % 12 + 1
        phase = {12: "Sade Sati – Rising (12th)", 1: "Sade Sati – Peak (1st)",
                 2: "Sade Sati – Setting (2nd)", 4: "Ardhashtama / Kantaka Shani (4th)",
                 8: "Ashtama Shani (8th)"}.get(rel)
        if phase:
            periods.append({"phase": phase, "sign": SIGNS[sg], "start": inp.fmt_jd(tc, False),
                            "end": inp.fmt_jd(te, False), "_s": tc, "_e": te})
    # merge consecutive identical phases (retrograde re-entries)
    merged = []
    for p in periods:
        if merged and merged[-1]["phase"] == p["phase"] and p["_s"] - merged[-1]["_e"] < 400:
            merged[-1]["end"] = p["end"]
            merged[-1]["_e"] = p["_e"]
        else:
            merged.append(p)
    from .clock import now_jd
    now = now_jd()
    current = next((p["phase"] for p in merged if p["_s"] <= now < p["_e"]), None)
    for p in merged:
        p.pop("_s"), p.pop("_e")
    return {"moon_sign": SIGNS[moon_s], "periods": merged, "current": current}

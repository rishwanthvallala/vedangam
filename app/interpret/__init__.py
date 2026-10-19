"""Assembles readable interpretations from the text library + computed chart facts."""
from __future__ import annotations

import glob
import json
import os
from functools import lru_cache

from ..core.constants import GRAHAS, SIGN_LORD, SIGNS
from ..i18n import LANG, ordinal, term, terms, tr

DATA = os.path.join(os.path.dirname(__file__), "data")


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


@lru_cache(maxsize=None)
def _load(name: str, lang: str) -> dict:
    with open(os.path.join(DATA, f"{name}.json"), encoding="utf-8") as f:
        data = json.load(f)
    if lang != "en":
        # translated parts live in data/<lang>/<name>*.json; missing entries fall back to English
        for path in sorted(glob.glob(os.path.join(DATA, lang, f"{name}*.json"))):
            with open(path, encoding="utf-8") as f:
                data = _merge(data, json.load(f))
    return data


def lib(name: str) -> dict:
    return _load(name, LANG.get())


def _get(d, *keys, default=""):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


# ------------------------------------------------------------------ Vedic
def vedic(chart, planets: list[dict], pan: dict, dasha: dict, yogas: list[dict],
          shadbala: dict | None = None) -> dict:
    nat, lords, tm = lib("vedic_natal"), lib("vedic_lords"), lib("vedic_time")
    L = chart.lagna_sign
    moon = next(p for p in planets if p["name"] == "Moon")
    sections = []
    sections.append({"title": tr("Ascendant (Lagna): {s}", s=SIGNS[L]),
                     "text": _get(nat, "lagna", SIGNS[L])})
    sections.append({"title": tr("Moon sign (Rashi): {s}", s=moon["sign_name"]),
                     "text": _get(nat, "moon_sign", moon["sign_name"])})
    nk = _get(nat, "nakshatra", moon["nakshatra"], default={})
    if nk:
        sections.append({"title": tr("Birth star (Janma Nakshatra): {n} pada {p}", n=moon["nakshatra"], p=moon["pada"]),
                         "meta": {tr(k): nk.get(k) for k in ("deity", "symbol", "gana", "animal")},
                         "text": nk.get("text", "")})
    planet_texts = []
    for p in planets:
        if p["name"] not in GRAHAS:
            continue
        tags = [term(p.get("dignity", ""))]
        if p.get("combust"):
            tags.append(term("combust"))
        if p.get("retro") and p["name"] not in ("Rahu", "Ketu"):
            tags.append(term("retrograde"))
        planet_texts.append({
            "planet": p["name"],
            "headline": tr("{p} in {s}, {h} house", p=p["name"], s=p["sign_name"], h=ordinal(p["house"]))
                        + (f" ({', '.join(t for t in tags if t)})" if any(tags) else ""),
            "house_text": _get(nat, "planet_in_house", p["name"], str(p["house"])),
            "sign_text": _get(tm, "planet_in_sign", p["name"], p["sign_name"]),
        })
    lord_texts = []
    for h in range(1, 13):
        lord = SIGN_LORD[(L + h - 1) % 12]
        lh = chart.house(lord)
        lord_texts.append({"house": h, "lord": lord, "placed": lh,
                           "headline": tr("{h} lord {lord} in the {lh} house", h=ordinal(h), lord=lord, lh=ordinal(lh)),
                           "meaning": _get(lords, "house_meaning", str(h)),
                           "text": _get(lords, "lord_in_house", str(h), str(lh))})
    cur = dasha.get("current") or []
    dasha_text = []
    if cur:
        md = cur[0]["lord"]
        dasha_text.append({"title": tr("Mahadasha of {md} ({a} to {b})", md=md, a=cur[0]["start"][:10], b=cur[0]["end"][:10]),
                           "text": _get(tm, "mahadasha", md)})
        if len(cur) > 1:
            ad = cur[1]["lord"]
            dasha_text.append({"title": tr("{md}–{ad} Antardasha ({a} to {b})", md=md, ad=ad, a=cur[1]["start"][:10], b=cur[1]["end"][:10]),
                               "text": _get(tm, "antardasha", md, ad)})
    panchang = [
        {"title": tr("Tithi: {x}", x=pan["tithi"]), "text": _get(tm, "tithi", pan["tithi"])},
        {"title": tr("Vara: {x}", x=pan["vara"]), "text": _get(tm, "vara", pan["vara"])},
        {"title": tr("Yoga: {x}", x=pan["yoga"]), "text": _get(tm, "yoga", pan["yoga"])},
        {"title": tr("Karana: {x}", x=pan["karana"]), "text": _get(tm, "karana", pan["karana"])},
    ]
    highlights = _highlights(chart, planets, yogas, shadbala, cur)
    return {"core": sections, "planets": planet_texts, "lords": lord_texts,
            "dasha": dasha_text, "panchang": panchang, "highlights": highlights}


def _highlights(chart, planets, yogas, shadbala, cur) -> list[str]:
    out = []
    L = chart.lagna_sign
    ll = SIGN_LORD[L]
    llrow = next(p for p in planets if p["name"] == ll)
    out.append(tr("Lagna lord {ll} is placed in the {h} house in {s} ({d}), so the life's focus gravitates to that house's matters.",
                  ll=ll, h=ordinal(llrow["house"]), s=llrow["sign_name"], d=llrow.get("dignity", "")))
    ex = [p["name"] for p in planets if p.get("dignity") == "Exalted"]
    de = [p["name"] for p in planets if p.get("dignity") == "Debilitated"]
    own = [p["name"] for p in planets if p.get("dignity") in ("Own", "Moolatrikona")]
    if ex:
        out.append(tr("Exalted: {ps}. These planets deliver their significations powerfully.", ps=terms(ex)))
    if own:
        out.append(tr("In own sign or moolatrikona: {ps}. Dependable, self-reliant results.", ps=terms(own)))
    if de:
        out.append(tr("Debilitated: {ps}. Check for Neecha Bhanga; their themes require conscious effort.", ps=terms(de)))
    comb = [p["name"] for p in planets if p.get("combust")]
    if comb:
        out.append(tr("Combust: {ps}. Their independent expression is subdued by the Sun.", ps=terms(comb)))
    retro = [p["name"] for p in planets if p.get("retro") and p["name"] in
             ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")]
    if retro:
        out.append(tr("Retrograde: {ps}. Internalised and revisiting karma; results often come later but run deeper.", ps=terms(retro)))
    if shadbala:
        rows = sorted(shadbala["planets"], key=lambda r: -r["ratio"])
        out.append(tr("Strongest planet by Shadbala: {a} ({r} rupas, {pa}% of the requirement). Weakest: {b} ({pb}%).",
                      a=rows[0]["planet"], r=rows[0]["rupa"], pa=round(rows[0]["ratio"] * 100),
                      b=rows[-1]["planet"], pb=round(rows[-1]["ratio"] * 100)))
    good = [y["name"] for y in yogas if y["present"] and y["category"] not in ("Dosha", "Nabhasa")]
    bad = [y["name"] for y in yogas if y["present"] and y["category"] == "Dosha"]
    if good:
        out.append(tr("Yogas formed ({n}): {ys}.", n=len(good), ys=", ".join(good[:10]) + ("…" if len(good) > 10 else "")))
    if bad:
        out.append(tr("Doshas and afflictions to note: {ys}.", ys=", ".join(bad)))
    if cur:
        out.append(tr("Running period: {chain}.", chain=" › ".join(f"{term(c['lord'])} ({term(c['level'])})" for c in cur[:3])))
    return out


# ------------------------------------------------------------------ Jaimini
def jaimini(j: dict) -> dict:
    t = lib("jaimini_kp")
    ak = j["atmakaraka"]
    kk = j["karakamsha"]["sign"]
    al = j["arudhas"]["AL"]["sign_name"]
    ul = j["arudhas"]["UL"]["sign_name"]
    return {
        "atmakaraka": {"title": tr("Atmakaraka: {p}", p=ak), "text": _get(t, "atmakaraka", ak)},
        "karakas": [{"karaka": k["karaka"], "planet": k["planet"],
                     "text": _get(t, "karaka_roles", k["karaka"])} for k in j["karakas"]],
        "karakamsha": {"title": tr("Karakamsha in {s}", s=kk), "text": _get(t, "karakamsha_sign", kk)},
        "planets_in_karakamsha": [{"planet": p, "text": _get(t, "planet_in_karakamsha", p)}
                                  for p in j["karakamsha"]["planets_in"]],
        "arudha_lagna": {"title": tr("Arudha Lagna in {s}", s=al), "text": _get(t, "arudha_lagna_sign", al)},
        "upapada": {"title": tr("Upapada Lagna in {s}", s=ul), "text": _get(t, "upapada_sign", ul)},
    }


# ------------------------------------------------------------------ KP
def kp_house(h: int) -> str:
    return _get(lib("jaimini_kp"), "kp_houses", str(h))


def kp_star(p: str) -> str:
    return _get(lib("jaimini_kp"), "kp_star_lord", p)


def prashna_lagna(sign: str) -> str:
    return _get(lib("jaimini_kp"), "prashna_lagna", sign)


# ------------------------------------------------------------------ Western
PAIR_ORDER = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus",
              "Neptune", "Pluto", "Chiron", "North Node", "Ascendant", "Midheaven"]


def western(w: dict) -> dict:
    nat, asp = lib("western_natal"), lib("western_aspects")
    pts = {p["name"]: p for p in w["planets"]}
    asc = w["angles"]["Ascendant"]["sign"]
    mc = w["angles"]["Midheaven"]["sign"]
    core = [
        {"title": tr("{p} in {s}", p="Sun", s=pts["Sun"]["sign_name"]), "text": _get(nat, "planet_in_sign", "Sun", pts["Sun"]["sign_name"])},
        {"title": tr("{p} in {s}", p="Moon", s=pts["Moon"]["sign_name"]), "text": _get(nat, "planet_in_sign", "Moon", pts["Moon"]["sign_name"])},
        {"title": tr("Ascendant in {s}", s=asc), "text": _get(nat, "ascendant", asc)},
        {"title": tr("Midheaven in {s}", s=mc), "text": _get(nat, "midheaven", mc)},
    ]
    planets = []
    for b in PAIR_ORDER[:12]:
        if b not in pts:
            continue
        p = pts[b]
        head = tr("{p} in {s}, house {h}", p=b, s=p["sign_name"], h=p["house"])
        if p.get("retro") and b != "North Node":
            head += f" ({term('retrograde')})"
        lbl = p.get("dignity", {}).get("label", "—")
        if lbl != "—":
            head += f"; {', '.join(term(x.strip()) for x in lbl.split(','))}"
        planets.append({"planet": b, "headline": head,
                        "sign_text": _get(nat, "planet_in_sign", b, p["sign_name"]),
                        "house_text": _get(nat, "planet_in_house", b, str(p["house"]))})
    aspects = []
    for a in sorted(w["aspects"], key=lambda x: x["orb"]):
        x, y = a["a"], a["b"]
        if x not in PAIR_ORDER or y not in PAIR_ORDER:
            continue
        if PAIR_ORDER.index(x) > PAIR_ORDER.index(y):
            x, y = y, x
        mode = "fusion" if a["aspect"] == "Conjunction" else (
            "flow" if a["nature"] == "harmonious" else "tension")
        txt = _get(asp, "pairs", f"{x}|{y}", mode)
        if not txt:
            continue
        phase = tr("applying") if a["applying"] else tr("separating")
        aspects.append({"title": tr("{a} {asp} {b} (orb {orb}, {phase})", a=a["a"], asp=a["aspect"], b=a["b"],
                                    orb=a["orb_dms"], phase=phase),
                        "text": txt, "aspect_note": _get(asp, "aspect_types", a["aspect"])})
    patterns = [{"title": tr("{pat}: {ps}", pat=p["pattern"], ps=terms(p["planets"]))
                 + (f" ({p['where']})" if p.get("where") else ""),
                 "text": _get(asp, "patterns", p["pattern"])} for p in w["patterns"]]
    bal = []
    tot = sum(w["elements"].values())
    for k, v in w["elements"].items():
        if v / tot >= 0.35:
            bal.append({"title": tr("Strong {x} ({n} points)", x=k, n=f"{v:g}"), "text": _get(asp, "elements", k, "strong")})
        elif v / tot <= 0.1:
            bal.append({"title": tr("Weak {x} ({n} points)", x=k, n=f"{v:g}"), "text": _get(asp, "elements", k, "weak")})
    tot = sum(w["modalities"].values())
    for k, v in w["modalities"].items():
        if v / tot >= 0.45:
            bal.append({"title": tr("Strong {x} ({n} points)", x=k, n=f"{v:g}"), "text": _get(asp, "modalities", k, "strong")})
        elif v / tot <= 0.12:
            bal.append({"title": tr("Weak {x} ({n} points)", x=k, n=f"{v:g}"), "text": _get(asp, "modalities", k, "weak")})
    h = w["hemispheres"]
    for a, b in (("East", "West"), ("North", "South")):
        if h[a] >= 7:
            bal.append({"title": tr("{x} hemisphere emphasis ({n} planets)", x=a, n=h[a]), "text": _get(asp, "hemispheres", a)})
        elif h[b] >= 7:
            bal.append({"title": tr("{x} hemisphere emphasis ({n} planets)", x=b, n=h[b]), "text": _get(asp, "hemispheres", b)})
    return {"core": core, "planets": planets, "aspects": aspects, "patterns": patterns,
            "balance": bal}

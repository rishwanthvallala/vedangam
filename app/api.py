"""Framework-free API: every endpoint as a plain function over dicts.

The FastAPI server (app/main.py) and the in-browser engine (Pyodide, see
static/js/engine-worker.js) both call `handle()`, so the website computes exactly the
same results whether it runs on a server or entirely in the browser.
"""
from __future__ import annotations

import json
import math
import traceback
from datetime import datetime, timezone

from .core import ashtakavarga, dasha as D, geo, kp as K, methods as M, panchang as P, transits as T, yogas as Y
from .core.chart import BirthInput, SiderealChart
from .core.clock import frozen, now_jd, utcnow
from .core.constants import NAKSHATRAS, SEVEN, SIGNS, nakshatra_of
from .core.ephemeris import AYANAMSAS, HOUSE_SYSTEMS, jd_from_utc
from .core.prashna import QUESTIONS
from .core.vedic import dignity
from .i18n import LANG, LANGS, bundle


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


# ---------------------------------------------------------------- helpers
def clean(o):
    """Round floats and drop NaN so the payload is compact JSON."""
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return None
        return round(o, 6)
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [clean(v) for v in o]
    return o


def parse_dt(date: str, time: str) -> datetime:
    t = (time or "").strip()
    if len(t) == 5:
        t += ":00"
    return datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M:%S")


def birth_of(req: dict, what: str = "birth details") -> BirthInput:
    try:
        pl = req["place"]
        return BirthInput(name=req.get("name") or "", gender=req.get("gender") or "",
                          local_dt=parse_dt(req["date"], req["time"]), lat=float(pl["lat"]),
                          lon=float(pl["lon"]), tz=pl.get("tz"), offset=req.get("offset"),
                          place=pl.get("label") or "")
    except Exception as e:
        raise ApiError(400, f"Invalid {what}: {e}")


def _lang(req: dict | None):
    lg = (req or {}).get("lang") or "en"
    LANG.set(lg if lg in LANGS else "en")


def _opts(req: dict) -> dict:
    return req.get("options") or {}


def _chart(req: dict, b: BirthInput) -> SiderealChart:
    o = _opts(req)
    return SiderealChart(b, ayanamsa=o.get("ayanamsa") or "lahiri", node=o.get("node", "mean"))


# ---------------------------------------------------------------- endpoints
def places(q: str) -> list:
    return geo.search(q)


def meta() -> dict:
    try:
        from .core.muhurta import EVENTS as ME
        muhurta_events = {k: v["label"] for k, v in ME.items()}
    except Exception:
        muhurta_events = {}
    return {"ayanamsas": {k: v[1] for k, v in AYANAMSAS.items()}, "house_systems": HOUSE_SYSTEMS,
            "kp_events": {k: v["label"] for k, v in K.EVENTS.items()},
            "prashna_questions": {k: v["label"] for k, v in QUESTIONS.items()},
            "muhurta_events": muhurta_events}


def kp_subtable() -> list:
    return [{k: r[k] for k in ("no", "sign", "nakshatra", "star_lord", "sub_lord", "from", "to")}
            for r in K.sub_table()]


def i18n(lang: str) -> dict:
    if lang not in LANGS:
        raise ApiError(404, "Unknown language")
    b = bundle(lang)
    # the browser uses one dictionary for UI text and backend sentences (e.g. meta labels)
    return {"ui": {**b["sentences"], **b["ui"]}, "terms": b["terms"], "chart": b.get("chart", {})}


def varshaphal(req: dict) -> dict:
    _lang(req)
    b = birth_of(req)
    year = req.get("year") or utcnow().year
    return clean(M.annual(b, _opts(req), year, req.get("residence")))


def transits(req: dict) -> dict:
    _lang(req)
    b = birth_of(req)
    ch = _chart(req, b)
    signs = {p: ch.sign(p) for p in SEVEN}
    signs["Lagna"] = ch.lagna_sign
    av = ashtakavarga.compute(signs, ch.lagna_sign)
    start = now_jd() - 15
    return clean({"year": T.year_ingresses(ch, b, start, 365),
                  "strength": T.strength_series(ch, b, av, start, 365),
                  "frames": T.frames(ch, b, start, 365)})


def dasha_calendar(req: dict) -> dict:
    _lang(req)
    b = birth_of(req)
    ch = _chart(req, b)
    now = utcnow()
    y, m = req.get("year") or now.year, req.get("month") or now.month
    lo = jd_from_utc(datetime(y, m, 1, tzinfo=timezone.utc)) - 0.5
    hi = jd_from_utc(datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=timezone.utc)) + 0.5
    yd = float(_opts(req).get("year_days", 365.25))
    events = D.change_events(ch.bodies["Moon"].lon, b.jd, lambda jd: b.fmt_jd(jd), yd, lo, hi, 4)
    running = [{"level": lv, "lords": lords, "start": b.fmt_jd(s), "end": b.fmt_jd(e)}
               for lv, lords, s, e in D.running_jds(ch.bodies["Moon"].lon, b.jd, yd, lo + 0.5, 4)]
    return clean({"year": y, "month": m, "events": events, "running_at_start": running})


def now(q: dict) -> dict:
    """Sky right now: sidereal positions and today's panchanga at a place."""
    _lang(q)
    from zoneinfo import ZoneInfo
    lat, lon = float(q.get("lat", 17.38405)), float(q.get("lon", 78.45636))
    tz, label = q.get("tz") or "Asia/Kolkata", q.get("label") or ""
    local = utcnow().astimezone(ZoneInfo(tz)).replace(tzinfo=None, microsecond=0)
    b = BirthInput(name="", gender="", local_dt=local, lat=lat, lon=lon, tz=tz, place=label)
    ch = SiderealChart(b)
    pan = P.compute(ch, b)
    return clean({"local": local.strftime("%Y-%m-%d %H:%M"), "place": label,
                  "planets": T.now_snapshot(b.jd, lat, lon), "lagna": SIGNS[ch.lagna_sign],
                  "panchang": {k: v for k, v in pan.items() if not k.startswith("_")}})


def search(req: dict) -> dict:
    """Search saved charts for a feature (yoga, placement, lagna, nakshatra, dignity, dasha)."""
    _lang(req)
    jn = now_jd()
    out = []
    kind, p, v = req.get("kind"), req.get("planet"), (req.get("value") or "").strip()
    for c in (req.get("charts") or [])[:200]:
        try:
            b = birth_of(c)
            ch = SiderealChart(b)
        except ApiError:
            continue
        hit, detail = False, ""
        if kind == "yoga":
            found = [y["name"] for y in Y.detect(ch) if y["present"] and v.lower() in y["name"].lower()]
            hit, detail = bool(found), ", ".join(found)
        elif kind == "planet_sign" and p:
            s = SIGNS[ch.sign(p)]
            hit, detail = s == v, s
        elif kind == "planet_house" and p:
            hh = ch.house(p)
            hit, detail = str(hh) == v, str(hh)
        elif kind == "lagna":
            s = SIGNS[ch.lagna_sign]
            hit, detail = s == v, s
        elif kind == "moon_nakshatra":
            n = NAKSHATRAS[nakshatra_of(ch.bodies["Moon"].lon)[0]]
            hit, detail = n == v, n
        elif kind == "dignity" and p:
            sg = {q: ch.sign(q) for q in SEVEN}
            d = dignity(p, ch.bodies[p].lon, sg)
            hit, detail = d == v, d
        elif kind == "dasha_now":
            run = D.running_jds(ch.bodies["Moon"].lon, b.jd, 365.25, jn, 2)
            md = run[0][1][0] if run else ""
            hit, detail = md == v, " – ".join(run[-1][1]) if run else ""
        out.append({"name": c.get("name"), "date": c.get("date"), "time": c.get("time"),
                    "match": hit, "detail": detail})
    return clean({"results": out, "matches": sum(1 for r in out if r["match"])})


def chart(req: dict) -> dict:
    _lang(req)
    birth = birth_of(req)
    m = req.get("method") or "parashara"
    opts = _opts(req)
    if m in ("kp_horary", "prashna"):
        q = req.get("query")
        if q:
            qq = {**q, "name": req.get("name"), "gender": req.get("gender"),
                  "place": q.get("place") or req["place"]}
            qi = birth_of(qq, "query details")
        else:
            qi = birth
        if m == "kp_horary":
            res = M.kp_horary(qi, opts, req.get("horary_number") or 1, req.get("question") or "")
        else:
            res = M.prashna(qi, opts, req.get("question") or "general", req.get("prashna_number"))
        res["query"] = qi.summary()
    elif m == "parashara":
        res = M.parashara(birth, opts)
    elif m == "kp":
        res = M.kp(birth, opts)
    elif m == "jaimini":
        res = M.jaimini(birth, opts)
    elif m in ("western", "paschatya"):
        res = M.western(birth, opts, paschatya=(m == "paschatya"))
    elif m == "varshaphal":
        res = M.varshaphal(birth, opts, req.get("year") or utcnow().year, req.get("residence"))
    elif m == "matching":
        pp = req.get("partner")
        if not pp:
            raise ApiError(400, "Partner details are missing.")
        partner = birth_of(pp, "partner details")
        boy, girl = (birth, partner) if birth.gender != "Female" else (partner, birth)
        res = M.matching(boy, girl, opts)
    elif m == "muhurta":
        mq = req.get("muhurta") or {}
        res = M.muhurta(birth, opts, mq, birth if mq.get("use_native") else None)
        res["query"] = {**birth.summary(), "local": f"{mq.get('start_date')} (+{mq.get('days', 30)} d)"}
    elif m == "calendar":
        now_ = utcnow()
        c = req.get("calendar") or {"year": now_.year, "month": now_.month}
        res = M.calendar(birth, opts, c)
        res["query"] = {**birth.summary(), "local": f"{c['year']}-{int(c['month']):02d}"}
    else:
        raise ApiError(400, f"Unknown method {m}")
    res["birth"] = birth.summary()
    return clean(res)


# ---------------------------------------------------------------- router
POST_ROUTES = {"/api/chart": chart, "/api/transits": transits, "/api/dasha_calendar": dasha_calendar,
               "/api/search": search, "/api/varshaphal": varshaphal}


def handle(path: str, query: dict | None = None, body: dict | None = None) -> tuple[int, object]:
    """Route an API call. Returns (status, payload). `body["now"]` (ISO UTC) freezes the clock."""
    query, body = query or {}, body or {}
    try:
        with frozen(body.get("now") or query.get("now")):
            if path == "/api/places":
                return 200, places(query.get("q", ""))
            if path == "/api/meta":
                return 200, meta()
            if path == "/api/kp/subtable":
                return 200, kp_subtable()
            if path.startswith("/api/i18n/"):
                return 200, i18n(path.rsplit("/", 1)[-1])
            if path == "/api/now":
                return 200, now(query)
            if path in POST_ROUTES:
                return 200, POST_ROUTES[path](body)
            return 404, {"detail": f"Unknown endpoint {path}"}
    except ApiError as e:
        return e.status, {"detail": e.detail}
    except Exception as e:  # never crash the caller; report like the server does
        traceback.print_exc()
        return 500, {"detail": f"Calculation error: {e}"}


def handle_json(path: str, query_json: str, body_json: str) -> str:
    """JSON-in/JSON-out wrapper used by the browser worker."""
    status, payload = handle(path, json.loads(query_json or "{}"), json.loads(body_json or "{}"))
    return json.dumps({"status": status, "body": payload}, ensure_ascii=False)

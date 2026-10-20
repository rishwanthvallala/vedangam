// Result renderers for every method.
import { h, table, kv, section, tag, dignityTag, houses, tabs, ord, fixed, dmsSign } from "./ui.js";
import { indianChart, wheel, aspectGrid, SIGNS, SHORT, glyph } from "./charts.js";
import { t, tx } from "./i18n.js";
import { apiFetch } from "./api.js";
import { annualTab, calendarDefs, chakrasTab, dashaCalendar, matchingDefs, muhurtaDefs, setStyle, transitTools, varshaphalDefs, worksheet } from "./features.js";

const GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"];
let STYLE = "south";
let ACTION = async () => null;
let CTX = null;
let BIRTH = null;   // birth date (YYYY-MM-DD) for ages in dasha tables

function ageAt(dateStr) {
  if (!BIRTH || !dateStr) return "";
  const a = (new Date(dateStr.slice(0, 10)) - new Date(BIRTH)) / (365.2425 * 864e5);
  return a >= 0 ? t("age {n}", { n: Math.floor(a) }) : "";
}

// ================================================================= common bits
function header(res, onAction) {
  const b = res.birth;
  const q = res.query;
  const tool = ["muhurta", "calendar"].includes(res.method);
  const facts = tool ? [["Time period", q.local.replace(/ \(UTC.*$/, "")], ["Place", q.place || `${q.lat_dms}, ${q.lon_dms}`], ["Coordinates", `${q.lat_dms}, ${q.lon_dms}`]] : q ? [
    ["Query time", `${q.local} (${q.offset})`], ["Query place", q.place || `${q.lat_dms}, ${q.lon_dms}`],
    ["Coordinates", `${q.lat_dms}, ${q.lon_dms}`],
  ] : [
    ["Born", `${b.local}, ${b.weekday}`], ["Place", b.place || "Custom coordinates"],
    ["Coordinates", `${b.lat_dms}, ${b.lon_dms}`], ["Time zone", `${b.tz || t("manual")} (${b.offset}${b.dst ? ", DST" : ""})`],
    ["UTC", b.utc],
  ];
  const s = res.settings || {};
  const settings = Object.entries(s).map(([k, v]) => `${t(k.replace(/_/g, " "))}: ${tx(String(v))}`).join("; ");
  return h("div", { class: "r-head" },
    h("div", {},
      ["muhurta", "calendar"].includes(res.method) ? h("h2", {}, res.title)
        : h("h2", { class: b.name ? "no-tr" : null }, b.name || (q ? "Horary query" : "Unnamed chart")),
      ["muhurta", "calendar"].includes(res.method) ? null : h("div", { class: "method-name" }, res.title),
      h("dl", { class: "r-facts" }, facts.map(([k, v]) => h("div", {}, h("dt", {}, k), h("dd", { class: /place/i.test(k) ? "no-tr" : null }, v)))),
      h("p", { class: "sub", style: "margin:8px 0 0;font-size:12.5px;color:var(--ink-3)" }, settings)),
    h("div", { class: "r-actions" },
      logoImg(),
      h("select", { class: "print-size", "aria-label": "Print size", onchange: (e) => setPrintSize(e.target.value) },
        ["A4", "Book (A5)", "Pocket (A6)"].map((x, i) => h("option", { value: ["a4", "a5", "a6"][i], selected: (getPrintSize() === ["a4", "a5", "a6"][i]) || null }, x))),
      h("button", { class: "ghost", type: "button", onclick: () => onAction("print") }, "Print report"),
      h("button", { class: "ghost", type: "button", onclick: () => onAction("json") }, "Download data")),
    TIME_METHODS.has(res.method) ? timeToolbar(onAction) : null,
    notesBox(res));
}

const TIME_METHODS = new Set(["parashara", "kp", "jaimini", "western", "paschatya", "kp_horary", "prashna", "varshaphal"]);

function timeToolbar(onAction) {
  const steps = [["−1d", -1440], ["−1h", -60], ["−5m", -5], ["−1m", -1], ["+1m", 1], ["+5m", 5], ["+1h", 60], ["+1d", 1440]];
  return h("div", { class: "time-bar", role: "group", "aria-label": t("Change the time") },
    h("span", {}, t("Change time")), steps.map(([l, m]) => h("button", { type: "button", class: "ghost", onclick: () => onAction("shift", m) }, l)));
}

function getPrintSize() { try { return localStorage.getItem("js.print") || "a4"; } catch (_) { return "a4"; } }
function setPrintSize(v) {
  try { localStorage.setItem("js.print", v); } catch (_) { /* ignore */ }
  let st = document.getElementById("printSize");
  if (!st) { st = document.createElement("style"); st.id = "printSize"; document.head.appendChild(st); }
  st.textContent = `@page { size: ${v.toUpperCase()}; margin: ${v === "a6" ? "6mm" : v === "a5" ? "10mm" : "14mm"}; }`
    + (v !== "a4" ? `@media print { body { font-size: ${v === "a6" ? 10 : 12}px; } }` : "");
}
setPrintSize(getPrintSize());

function logoImg() {
  let src = null;
  try { src = localStorage.getItem("js.logo"); } catch (_) { /* ignore */ }
  return src ? h("img", { src, alt: "", class: "logo" }) : null;
}

function notesBox(res) {
  const b = res.birth;
  const key = `${b.name}|${b.local}|${res.method === "matching" ? "match" : ""}`;
  let all = {};
  try { all = JSON.parse(localStorage.getItem("js.notes") || "{}"); } catch (_) { /* ignore */ }
  const ta = h("textarea", { rows: 3, placeholder: t("Notes about this person or chart…"), class: "no-tr" });
  ta.value = all[key] || "";
  let timer;
  ta.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => { all[key] = ta.value; try { localStorage.setItem("js.notes", JSON.stringify(all)); } catch (_) { /* ignore */ } }, 300);
  });
  return h("details", { class: "notes", open: ta.value ? true : null }, h("summary", {}, t("Notes")), ta);
}

function chartFromVarga(v, title, sub, extra = {}) {
  const signs = { ...v.signs };
  return h("figure", { class: "chart-card" },
    h("figcaption", {}, title, sub ? h("small", {}, sub) : null),
    indianChart({ style: STYLE, lagnaSign: signs.Lagna, signs, center: tx(title), ...extra }));
}

// noDeg: points placed by sign only (Arudhas), whose longitude is just the start of the sign
function chartFromPoints(points, title, sub, { lagnaSign, houseOf, houseSigns, cusps, withDeg = true, special = [], noDeg = [] } = {}) {
  const signs = {}, degs = {}, retro = {};
  for (const [n, p] of Object.entries(points)) {
    signs[n] = p.sign;
    if (withDeg && p.lon !== undefined && p.lon !== null && !noDeg.includes(n)) degs[n] = p.lon % 30;
    if (p.retro && !["Rahu", "Ketu"].includes(n)) retro[n] = true;
  }
  const ls = lagnaSign ?? points.Lagna.sign;
  return h("figure", { class: "chart-card" },
    h("figcaption", {}, title, sub ? h("small", {}, sub) : null),
    indianChart({ style: STYLE, lagnaSign: ls, signs, degs, retro,
      special: new Set(special), houseOf, houseSigns, cusps, center: tx(title).replace(/ \(/, "\n(") }));
}

function planetName(r) {
  const short = SHORT[r.name] ? ` (${SHORT[r.name]})` : "";
  return h("span", { class: "planet" }, r.name, r.retro && !["Rahu", "Ketu", "Lagna"].includes(r.name) ? h("span", { class: "r", title: "Retrograde" }, "R") : null);
}

function planetsTable(rows, { kp = false } = {}) {
  const cols = [
    { label: "Planet", render: planetName },
    { label: "Sign", key: "sign_name" },
    { label: "Longitude", key: "dms", cls: "num" },
    { label: "Nakshatra", render: (r) => `${r.nakshatra} ${r.pada}` },
  ];
  if (kp) {
    cols.push({ label: "Sign lord", key: "sign_lord" }, { label: "Star lord", key: "star_lord" },
      { label: "Sub lord", key: "sub_lord" }, { label: "Sub-sub", key: "sub_sub_lord" },
      { label: "Cusp house", render: (r) => r.name === "Lagna" ? 1 : r.kp_house });
  } else {
    cols.push({ label: "Star lord", key: "nak_lord" }, { label: "House", key: "house", cls: "num" },
      { label: "Dignity", render: (r) => r.name === "Lagna" ? "–" : dignityTag(r.dignity) },
      { label: "State", render: (r) => [r.combust ? tag("Combust", "warn") : null,
        r.retro && !["Rahu", "Ketu", "Lagna"].includes(r.name) ? tag("Retrograde", "bad") : null] },
      { label: "Speed °/day", render: (r) => r.speed === null || r.speed === undefined ? "–" : fixed(r.speed, 4), cls: "num" },
      { label: "Declination", render: (r) => r.decl === undefined ? "–" : fixed(r.decl, 2), cls: "num" },
      { label: "Magnitude", render: (r) => r.magnitude === undefined || r.magnitude === null ? "–" : fixed(r.magnitude, 2), cls: "num" },
      { label: "Pushkar", render: (r) => [r.pushkar_navamsa ? tag("Navamsa", "good") : null, r.pushkar_bhaga ? tag("Bhaga", "good") : null] });
  }
  return table(cols, rows, { rowClass: (r) => (r.name === "Lagna" ? "lagna" : null) });
}

function avasthaTable(rows) {
  return table([
    { label: "Planet", render: planetName },
    { label: "Baladi (age)", key: "avastha_baladi" },
    { label: "Jagradadi (alertness)", key: "avastha_jagradadi" },
    { label: "Deeptadi (mood)", key: "avastha_deeptadi" },
    { label: "Distance from Sun", render: (r) => ["Sun", "Rahu", "Ketu"].includes(r.name) ? "–" : `${fixed(r.sun_dist, 1)}°`, cls: "num" },
  ], rows.filter((r) => GRAHAS.includes(r.name)));
}

function panchangSection(p, title = "Panchanga at birth") {
  const a = p.avakahada || {};
  return h("div", { class: "cols" },
    section(title, null, kv([
      ["Tithi", t("{tithi} ({paksha}), {pct}% left", { tithi: p.tithi, paksha: p.paksha, pct: p.tithi_left_pct })],
      ["Tithi span", t("{a} to {b}", { a: p.tithi_start, b: p.tithi_end })],
      ["Vara", t("{x} (lord {l})", { x: p.vara, l: p.vara_lord })],
      ["Nakshatra", t("{n} pada {p}, lord {l}", { n: p.nakshatra, p: p.nakshatra_pada, l: p.nakshatra_lord })],
      ["Nakshatra span", t("{a} to {b}", { a: p.nakshatra_start, b: p.nakshatra_end })],
      ["Yoga", p.yoga], ["Karana", p.karana],
      ["Lunar month (Amanta)", p.masa], ["Samvatsara", p.samvatsara],
      ["Hora lord", t("{l} (hora {n})", { l: p.hora_lord, n: p.hora_number })],
      ["Janma ghati", p.birth_ghati_vighati], ["Day or night", p.day_birth ? "Day birth" : "Night birth"],
    ])),
    section("Sun, Moon and time", null, kv([
      ["Sunrise", p.sunrise], ["Sunset", p.sunset], ["Next sunrise", p.next_sunrise],
      ["Day length", t("{n} hours", { n: fixed(p.day_duration_h, 2) })],
      ["Moonrise", p.moonrise], ["Moonset", p.moonset],
      ["Rahu kaal", p.rahu_kaal && t("{a} to {b}", { a: p.rahu_kaal[0], b: p.rahu_kaal[1] })], ["Yamaganda", p.yamaganda && t("{a} to {b}", { a: p.yamaganda[0], b: p.yamaganda[1] })],
      ["Gulika kaal", p.gulika_kaal && t("{a} to {b}", { a: p.gulika_kaal[0], b: p.gulika_kaal[1] })],
      ["Ayanamsa", p.ayanamsa_dms], ["Local sidereal time", p.sidereal_time],
      ["Obliquity", `${fixed(p.obliquity, 4)}°`], ["Delta T", `${p.delta_t_sec} s`],
    ])),
    section("Avakahada chakra", "Used for naming and compatibility (Ashtakoota) matching.", kv([
      ["Rashi", t("{x} (lord {l})", { x: a.rashi, l: a.rashi_lord })], ["Nakshatra", a.nakshatra], ["Name syllable", a.namakshar],
      ["Varna", a.varna], ["Vashya", a.vashya], ["Yoni", a.yoni], ["Gana", a.gana], ["Nadi", a.nadi],
      ["Tatva", a.tatva], ["Paya", a.paya], ["Lagna", t("{x} (lord {l})", { x: a.lagna, l: a.lagna_lord })],
    ])));
}

function dashaTree(vim, { years = true } = {}) {
  const cur = vim.current || [];
  const curLords = cur.map((c) => c.lord);
  const today = new Date().toISOString().slice(0, 10);
  const isNow = (n) => n.start <= today && today < n.end;
  const row = (label, n) => [h("span", {}, label), h("span", {}, n.start, h("small", { class: "age" }, " ", ageAt(n.start))), h("span", {}, n.end)];
  const tree = h("div", { class: "dasha" },
    h("div", { class: "dasha-head" }, h("span", {}, "Period"), h("span", {}, "Starts"), h("span", {}, "Ends")),
    vim.periods.map((md) => h("details", { class: isNow(md) ? "now" : "", open: isNow(md) || null },
      h("summary", {}, row(h("b", {}, `${md.lord}${md.planet ? ` (${md.planet})` : ""}`), md)),
      (md.children || []).map((ad) => h("details", { class: "lvl2" + (isNow(ad) ? " now" : "") },
        h("summary", {}, row(`${md.lord} – ${ad.lord}${ad.planet ? ` (${ad.planet})` : ""}`, ad)),
        (ad.children || []).map((pd) => h("div", { class: "lvl3" + (isNow(pd) ? " now" : "") },
          row(`${ad.lord} – ${pd.lord}`, pd))))))));
  return h("div", {},
    cur.length ? h("div", { class: "chain" }, cur.map((c) => h("div", {}, h("small", {}, c.level), h("b", {}, c.lord + (c.planet ? ` (${c.planet})` : "")), h("small", {}, t("{a} to {b}", { a: c.start.slice(0, 10), b: c.end.slice(0, 10) }))))) : null,
    tree);
}

function readingBlocks(items) {
  return h("div", { class: "reading" }, items.filter((x) => x && x.text).map((x) => h("article", {},
    h("h4", {}, x.title), x.meta ? h("p", { class: "meta" }, Object.entries(x.meta).map(([k, v]) => `${k}: ${v}`).join("; ")) : null,
    h("p", {}, x.text))));
}

function transitTable(g, title = "Current transits (Gochara)") {
  return section(title, t("Positions for {d}; results judged from the natal Moon sign as in classical Gochara.", { d: g.date }),
    table([
      { label: "Planet", render: (r) => h("span", { class: "planet" }, r.planet, r.retro && !["Rahu", "Ketu"].includes(r.planet) ? h("span", { class: "r" }, "R") : null) },
      { label: "Sign", key: "sign" }, { label: "Longitude", key: "dms", cls: "num" },
      { label: "Nakshatra", key: "nakshatra" },
      { label: "From Lagna", key: "house_from_lagna", cls: "num" },
      { label: "From Moon", key: "house_from_moon", cls: "num" },
      { label: "Effect", render: (r) => tag(r.result, r.result === "Favourable" ? "good" : "warn") },
    ], g.planets));
}

// ================================================================= PARASHARA
function parashara(res) {
  const lagna = res.planets[0];
  const moonSign = res.points.Moon.sign;
  const ov = () => h("div", {},
    h("div", { class: "grid-charts" },
      chartFromPoints(res.points, "Rasi chart (D1)", t("Lagna {s} {d}", { s: lagna.sign_name, d: lagna.dms })),
      chartFromVarga(res.vargas.D9, "Navamsa (D9)", "Spouse, dharma, inner strength"),
      chartFromPoints(res.points, "Chandra lagna", "Rasi chart read from the Moon", { lagnaSign: moonSign }),
      chartFromPoints(res.points, "Bhava chalit", "Sripati bhava placement",
        { houseOf: res.bhava_chalit, withDeg: false })),
    section("Key highlights", null, h("ul", { class: "highlights" }, res.reading.highlights.map((x) => h("li", {}, x)))),
    section("Planetary positions", t("Sidereal longitudes, {a} ayanamsa ({v}).", { a: res.settings.ayanamsa, v: res.panchang.ayanamsa_dms }),
      planetsTable(res.planets)),
    panchangSection(res.panchang));
  const planets = () => h("div", {},
    section("Planetary positions", null, planetsTable(res.planets)),
    section("Avasthas (planetary states)", null, avasthaTable(res.planets)),
    section("Special lagnas and upagrahas", "Bhava, Hora and Ghati lagnas use the Sun at sunrise; Gulika and Mandi follow the Saturn portion of the day or night; Dhuma to Upaketu are the aprakasha grahas.", table([
      { label: "Point", render: (r) => r[0] }, { label: "Sign", render: (r) => r[1].sign },
      { label: "Longitude", render: (r) => r[1].dms, cls: "num" }], Object.entries(res.special_lagnas))),
    section("Graha drishti (aspects)", "Full Parashari aspects: all planets 7th; Mars 4/8, Jupiter 5/9, Saturn 3/10, nodes 5/9.",
      table([{ label: "Planet", render: (r) => r[0] },
        { label: "Aspects houses", render: (r) => r[1].map((x) => `${x.house} (${x.sign.slice(0, 3)})`).join(", ") },
        { label: "Aspects planets", render: (r) => r[1].flatMap((x) => x.planets).join(", ") || "–" }],
      Object.entries(res.aspects))),
    section("Planetary relationships (Panchadha maitri)", "Compound = natural + temporal friendship.", relTable(res.relationships.compound)),
    section("Beeja and Kshetra sphuta", "Classical fertility indicators: Beeja = Sun + Venus + Jupiter (male), Kshetra = Moon + Mars + Jupiter (female).",
      table([{ label: "Sphuta", render: (r) => r[0] }, { label: "Sign", render: (r) => r[1].sign }, { label: "Longitude", render: (r) => r[1].dms, cls: "num" },
        { label: "Navamsa", render: (r) => r[1].navamsa }, { label: "Status", render: (r) => tag(r[1].status, r[1].status === "Favourable" ? "good" : r[1].status === "Weak" ? "bad" : "warn") },
        { label: "Rule", render: (r) => r[1].rule, cls: "wrap" }], Object.entries(res.fertility))),
    section("Shashtiamsa (D60) deities", null, table([{ label: "Planet", render: (r) => r[0] },
      { label: "Deity", render: (r) => r[1].deity }, { label: "Nature", render: (r) => tag(r[1].benefic ? "Benefic" : "Malefic", r[1].benefic ? "good" : "bad") }],
    Object.entries(res.d60))));
  const housesTab = () => h("div", {},
    section("Bhava table", "Whole-sign houses from the Lagna, with Sripati bhava start and midpoint, occupants, aspects and Sarvashtakavarga.",
      table([{ label: "House", key: "house", cls: "num" }, { label: "Sign", key: "sign" }, { label: "Lord", key: "lord" },
        { label: "Lord in", render: (r) => `${r.lord_in_house} (${r.lord_in_sign})` },
        { label: "Occupants", render: (r) => r.occupants.join(", ") || "–" },
        { label: "Aspected by", render: (r) => r.aspected_by.join(", ") || "–" },
        { label: "Bhava start", key: "bhava_start", cls: "num" }, { label: "Bhava madhya", key: "bhava_madhya", cls: "num" },
        { label: "SAV", key: "sav", cls: "num" }], res.houses)));
  const vargas = () => h("div", {},
    section("Shodashavarga charts", "All sixteen divisional charts of Parashara.",
      h("div", { class: "grid-charts small" }, Object.entries(res.vargas).filter(([, v]) => !v.extra).map(([k, v]) => chartFromVarga(v, k, v.name.split("–")[1]?.trim())))),
    section("Additional divisional charts", "D5, D6, D8, D11, D81, D108 (Ashtottaramsa), D144 and D150 (Nadiamsa).",
      h("div", { class: "grid-charts small" }, Object.entries(res.vargas).filter(([, v]) => v.extra).map(([k, v]) => chartFromVarga(v, k, v.name.split("–")[1]?.trim())))),
    section("Varga table", null, vargaTable(res.vargas)),
    section("Vimshopaka bala (Shodashavarga)", "Strength from dignity across all sixteen vargas, out of 20.",
      table([{ label: "Planet", key: "planet" }, { label: "Score", render: (r) => `${r.score} / 20`, cls: "num" },
        { label: "Grade", key: "grade" }, ...["D1", "D9", "D10", "D60"].map((d) => ({ label: d, render: (r) => r.detail[d] }))], res.vimshopaka)));
  return [
    { id: "overview", label: "Overview", render: ov },
    { id: "reading", label: "Reading", render: () => vedicReading(res.reading) },
    { id: "planets", label: "Planets", render: planets },
    { id: "houses", label: "Houses", render: housesTab },
    { id: "vargas", label: "Divisional charts", render: vargas },
    { id: "dasha", label: "Dashas", render: () => h("div", {},
      section("Vimshottari dasha", t("Moon in {nak}; balance at birth {bal} of {lord}. Year = {yd} days. Open a period to see sub-periods.", { nak: res.dasha.vimshottari.moon_nakshatra, bal: res.dasha.vimshottari.balance, lord: res.dasha.vimshottari.starting_lord, yd: res.dasha.vimshottari.year_days }), dashaTree(res.dasha.vimshottari)),
      section("Yogini dasha", t("Starts with {s}; balance {b}.", { s: res.dasha.yogini.starting, b: res.dasha.yogini.balance }), dashaTree(res.dasha.yogini)),
      ashtottariSection(res.dasha.ashtottari)) },
    { id: "strength", label: "Shadbala", render: () => shadbalaSection(res.shadbala) },
    { id: "av", label: "Ashtakavarga", render: () => ashtakavargaSection(res.ashtakavarga) },
    { id: "yogas", label: "Yogas & doshas", render: () => yogaSection(res.yogas) },
    { id: "chakras", label: "Chakras", render: () => chakrasTab(res) },
    { id: "annual", label: "Annual charts", render: () => annualTab(res, CTX) },
    { id: "transit", label: "Transits & Sade Sati", render: () => h("div", {}, transitTable(res.transits), sadeSati(res.sade_sati), transitTools(res, CTX)) },
    { id: "dcal", label: "Dasha calendar", render: () => dashaCalendar(res, CTX) },
    { id: "worksheet", label: "Worksheet", render: () => worksheet(parasharaPanels(res)) },
    { id: "panchang", label: "Panchanga", render: () => h("div", {}, panchangSection(res.panchang), readingBlocks(res.reading.panchang)) },
  ];
}

function parasharaPanels(res) {
  const cat = {};
  for (const [k, v] of Object.entries(res.vargas)) cat[k] = { title: `${k} ${v.name.split("–")[0].trim()}`, render: () => chartFromVarga(v, k) };
  cat.chandra = { title: "Chandra lagna", render: () => chartFromPoints(res.points, "Chandra lagna", null, { lagnaSign: res.points.Moon.sign }) };
  cat.chalit = { title: "Bhava chalit", render: () => chartFromPoints(res.points, "Bhava chalit", null, { houseOf: res.bhava_chalit, withDeg: false }) };
  cat.planets = { title: "Planetary positions", render: () => planetsTable(res.planets) };
  cat.highlights = { title: "Key highlights", render: () => h("ul", { class: "highlights" }, res.reading.highlights.map((x) => h("li", {}, x))) };
  cat.dasha = { title: "Running dasha", render: () => h("div", { class: "chain" }, res.dasha.vimshottari.current.map((c) => h("div", {}, h("small", {}, c.level), h("b", {}, c.lord), h("small", {}, c.end.slice(0, 10))))) };
  cat.panchang = { title: "Panchanga", render: () => kv([["Tithi", res.panchang.tithi], ["Vara", res.panchang.vara], ["Nakshatra", `${res.panchang.nakshatra} ${res.panchang.nakshatra_pada}`], ["Yoga", res.panchang.yoga], ["Karana", res.panchang.karana], ["Sunrise", res.panchang.sunrise]]) };
  cat.shadbala = { title: "Shadbala summary", render: () => table([{ label: "Planet", key: "planet" }, { label: "Rupa", key: "rupa", cls: "num" }, { label: "Ratio", key: "ratio", cls: "num" }, { label: "Rank", key: "rank", cls: "num" }], res.shadbala.planets) };
  cat.sav = { title: "SAV by house", render: () => table([{ label: "House", key: "house", cls: "num" }, { label: "Sign", key: "sign" }, { label: "Bindus", key: "bindus", cls: "num" }], res.ashtakavarga.sav_by_house) };
  cat.yogas = { title: "Yogas and doshas present", render: () => h("ul", { class: "highlights" }, res.yogas.filter((y) => y.present).map((y) => h("li", {}, y.name))) };
  cat.transits = { title: "Current transits (Gochara)", render: () => table([{ label: "Planet", key: "planet" }, { label: "Sign", key: "sign" }, { label: "From Moon", key: "house_from_moon", cls: "num" }, { label: "Effect", key: "result" }], res.transits.planets) };
  cat.special = { title: "Special lagnas and upagrahas", render: () => table([{ label: "Point", render: (r) => r[0] }, { label: "Sign", render: (r) => r[1].sign }, { label: "Longitude", render: (r) => r[1].dms, cls: "num" }], Object.entries(res.special_lagnas)) };
  return cat;
}

function relTable(comp) {
  const ps = Object.keys(comp);
  return table([{ label: "Planet", render: (r) => r }, ...ps.map((q) => ({ label: q.slice(0, 3), render: (p) => p === q ? "–" : comp[p][q] }))], ps);
}

function vargaTable(vargas) {
  const names = ["Lagna", ...GRAHAS];
  const keys = Object.keys(vargas);
  return table([{ label: "Varga", render: (k) => k }, ...names.map((n) => ({ label: SHORT[n] || n, render: (k) => SIGNS[vargas[k].signs[n]].slice(0, 3) }))], keys);
}

function vedicReading(r) {
  return h("div", {},
    section("Core nature", null, readingBlocks(r.core)),
    r.dasha.length ? section("Running dasha", null, readingBlocks(r.dasha)) : null,
    section("Planets in houses and signs", "Each planet's placement from the Lagna and in its sidereal sign.",
      h("div", { class: "reading" }, r.planets.map((p) => h("article", {}, h("h4", {}, p.headline),
        h("p", {}, p.house_text), p.sign_text ? h("p", { class: "alt" }, p.sign_text) : null)))),
    section("House lords (Bhavesha phala)", "Where each house's lord is placed, and what it means for that house.",
      h("div", { class: "reading" }, r.lords.map((l) => h("article", {}, h("h4", {}, l.headline),
        h("p", { class: "meta" }, l.meaning), h("p", {}, l.text))))));
}

function shadbalaSection(sb) {
  const rows = sb.planets;
  const maxR = Math.max(...rows.map((r) => r.rupa), 9);
  return h("div", {},
    section("Shadbala summary", "Six-fold strength in rupas (60 virupas = 1 rupa), compared with the minimum required by BPHS.",
      table([
        { label: "Planet", key: "planet" },
        { label: "Sthana", render: (r) => fixed(r.sthana.total, 1), cls: "num" },
        { label: "Dig", render: (r) => fixed(r.dig, 1), cls: "num" },
        { label: "Kala", render: (r) => fixed(r.kala.total, 1), cls: "num" },
        { label: "Chesta", render: (r) => fixed(r.chesta, 1), cls: "num" },
        { label: "Naisargika", render: (r) => fixed(r.naisargika, 1), cls: "num" },
        { label: "Drik", render: (r) => fixed(r.drik, 1), cls: "num" },
        { label: "Total (virupa)", render: (r) => fixed(r.total_virupa, 1), cls: "num" },
        { label: "Rupa", render: (r) => fixed(r.rupa, 2), cls: "num" },
        { label: "Required", render: (r) => fixed(r.required, 1), cls: "num" },
        { label: "Ratio", render: (r) => fixed(r.ratio, 2), cls: "num" },
        { label: "Strength", render: (r) => h("div", { class: "bar", title: t("{a} of {b} rupas", { a: r.rupa, b: r.required }) },
          h("i", { class: r.ratio >= 1 ? "ok" : "low", style: `width:${Math.min(100, (r.rupa / maxR) * 100)}%` }),
          h("span", { class: "req", style: `left:${(r.required / maxR) * 100}%` })) },
        { label: "Rank", key: "rank", cls: "num" },
        { label: "Ishta", render: (r) => fixed(r.ishta, 1), cls: "num" },
        { label: "Kashta", render: (r) => fixed(r.kashta, 1), cls: "num" },
      ], rows)),
    section("Sthana bala detail", null, table([{ label: "Planet", key: "planet" },
      ...["uchcha", "saptavargaja", "ojayugma", "kendradi", "drekkana", "total"].map((k) => ({ label: k[0].toUpperCase() + k.slice(1), render: (r) => fixed(r.sthana[k], 2), cls: "num" }))], rows)),
    section("Kala bala detail", t("Year lord {a}, month lord {m}, weekday lord {v}, hora lord {h}, tribhaga lord {tb}.", { a: sb.meta.abda_lord, m: sb.meta.masa_lord, v: sb.meta.vara_lord, h: sb.meta.hora_lord, tb: sb.meta.tribhaga_lord }),
      table([{ label: "Planet", key: "planet" },
        ...["natonnata", "paksha", "tribhaga", "abda", "masa", "vara", "hora", "ayana", "yuddha", "total"].map((k) => ({ label: k[0].toUpperCase() + k.slice(1), render: (r) => fixed(r.kala[k], 2), cls: "num" }))], rows)),
    sb.wars.length ? section("Graha yuddha (planetary war)", null, table([{ label: "Winner", key: "winner" }, { label: "Loser", key: "loser" }, { label: "Transfer (virupa)", key: "value", cls: "num" }], sb.wars)) : null,
    section("Bhava bala", "House strength: lord's Shadbala + directional strength + aspects on the bhava madhya.",
      table([{ label: "House", key: "house", cls: "num" }, { label: "Lord", key: "lord" },
        { label: "Adhipati", render: (r) => fixed(r.adhipati, 1), cls: "num" }, { label: "Dig", render: (r) => fixed(r.dig, 1), cls: "num" },
        { label: "Drishti", render: (r) => fixed(r.drishti, 1), cls: "num" }, { label: "Total (virupa)", render: (r) => fixed(r.total_virupa, 1), cls: "num" },
        { label: "Rupa", render: (r) => fixed(r.rupa, 2), cls: "num" }, { label: "Rank", key: "rank", cls: "num" }], sb.bhava)));
}

function ashtakavargaSection(av) {
  const planets = Object.keys(av.bav);
  const signCols = SIGNS.map((s, i) => ({ label: s.slice(0, 3), render: (r) => r.vals[i], cls: "num" }));
  const rows = planets.map((p) => ({ name: p, vals: av.bav[p].bindus, total: av.bav[p].total }));
  rows.push({ name: "Sarva (SAV)", vals: av.sav, total: av.sav_total });
  const hiLo = (v, isSav) => (isSav ? (v >= 30 ? "hi" : v < 25 ? "lo" : "") : (v >= 5 ? "hi" : v <= 2 ? "lo" : ""));
  const bavTable = h("div", { class: "tw av" }, h("table", {},
    h("thead", {}, h("tr", {}, h("th", {}, "Planet"), SIGNS.map((s) => h("th", { class: "num" }, s.slice(0, 3))), h("th", { class: "num" }, "Total"))),
    h("tbody", {}, rows.map((r) => h("tr", { class: r.name.startsWith("Sarva") ? "lagna" : null }, h("td", {}, r.name),
      r.vals.map((v) => h("td", { class: "num " + hiLo(v, r.name.startsWith("Sarva")) }, v)), h("td", { class: "num" }, r.total))))));
  const detail = h("div", {}, planets.map((p) => h("details", {}, h("summary", {}, t("{p}: contributions from each reference", { p })),
    table([{ label: "From", render: (r) => r[0] }, ...SIGNS.map((s, i) => ({ label: s.slice(0, 3), render: (r) => r[1][i] || "", cls: "num" }))],
      Object.entries(av.bav[p].detail)))));
  return h("div", {},
    section("Bhinnashtakavarga and Sarvashtakavarga", "Bindus by sign. SAV of 28 or more favours a sign; 30+ is strong, below 25 is weak.", bavTable),
    section("SAV by house", t("Kendras {k}, trikonas {tr}, dusthanas {d}. 11th vs 12th: {w}.", { k: av.notes.kendra_total, tr: av.notes.trikona_total, d: av.notes.dusthana_total, w: av.notes.wealth_ratio_11_vs_12 }),
      table([{ label: "House", key: "house", cls: "num" }, { label: "Sign", key: "sign" }, { label: "Bindus", key: "bindus", cls: "num" },
        { label: "Quality", render: (r) => tag(r.quality, r.quality === "Strong" ? "good" : r.quality === "Weak" ? "bad" : "") }], av.sav_by_house)),
    section("Reductions and Shodhya pinda", "After Trikona and Ekadhipatya shodhana, used for Ashtakavarga-based timing.",
      table([{ label: "Planet", render: (r) => r[0] }, { label: "After reductions", render: (r) => r[1].ekadhipatya.join(" ") },
        { label: "Rashi pinda", render: (r) => r[1].rashi_pinda, cls: "num" }, { label: "Graha pinda", render: (r) => r[1].graha_pinda, cls: "num" },
        { label: "Shodhya pinda", render: (r) => r[1].shodhya_pinda, cls: "num" }], Object.entries(av.reductions))),
    section("Contribution detail", null, detail));
}

function yogaSection(yogas) {
  const present = yogas.filter((y) => y.present);
  const absent = yogas.filter((y) => !y.present);
  const cats = [...new Set(present.map((y) => y.category))];
  return h("div", {},
    section(t("Yogas and doshas present ({n})", { n: present.length }), "Detected by classical rules from BPHS, Phaladeepika and the Nabhasa yogas.",
      ...cats.map((c) => h("div", { class: "sec" }, h("h4", { style: "font-size:18px;margin-bottom:6px" }, c),
        table([{ label: "Yoga", render: (y) => h("span", { class: "planet" }, y.name) },
          { label: "Planets", render: (y) => y.planets.join(", ") || "–" },
          { label: "Meaning", render: (y) => y.description, cls: "wrap" },
          { label: "Strength", render: (y) => y.strength || "–" }], present.filter((y) => y.category === c))))),
    h("details", {}, h("summary", {}, t("Checked but not formed ({n})", { n: absent.length })),
      table([{ label: "Yoga", key: "name" }, { label: "Rule", render: (y) => y.description, cls: "wrap" }], absent)));
}

function sadeSati(s) {
  return section("Sade Sati and Saturn transits", t("Natal Moon in {s}.", { s: s.moon_sign }) + " " + (s.current ? t("Running now: {x}.", { x: s.current }) : t("No Sade Sati, Kantaka or Ashtama Shani running today.")),
    table([{ label: "Phase", key: "phase" }, { label: "Saturn in", key: "sign" }, { label: "From", key: "start" }, { label: "To", key: "end" }], s.periods,
      { rowClass: (r) => (r.start <= new Date().toISOString().slice(0, 10) && new Date().toISOString().slice(0, 10) < r.end ? "cur" : null) }));
}

function ashtottariSection(a) {
  if (!a) return null;
  return section("Ashtottari dasha", t("108-year cycle. Starts with {s}; balance at birth {b}.", { s: a.starting_lord, b: a.balance }) + " " + a.applicability, dashaTree(a));
}

// ================================================================= KP
const HOUSE_NUMS = Array.from({ length: 12 }, (_, i) => i + 1);

function customEventForm(res, onAction) {
  const cat = res.event_catalog || {};
  const out = h("div", {});
  const pick = (name) => h("div", { class: "house-picks", role: "group", "aria-label": name },
    HOUSE_NUMS.map((n) => h("label", { class: "check" }, h("input", { type: "checkbox", name, value: n }), n)));
  const preset = h("select", { "aria-label": "Start from a listed event" }, h("option", { value: "" }, "Start from a listed event (optional)"),
    Object.entries(cat).map(([k, v]) => h("option", { value: k }, v.label)));
  const label = h("input", { placeholder: "Event name, e.g. Government job" });
  const cusp = h("select", {}, HOUSE_NUMS.map((n) => h("option", { value: n }, t("Cusp {n}", { n }))));
  const good = pick("good"), bad = pick("bad");
  const err = h("p", { class: "form-error", hidden: true });
  const set = (box, list) => box.querySelectorAll("input").forEach((i) => { i.checked = list.includes(+i.value); });
  preset.addEventListener("change", () => {
    const v = cat[preset.value];
    if (!v) return;
    label.value = v.label; cusp.value = v.cusp; set(good, v.good); set(bad, v.bad);
  });
  const btn = h("button", { type: "button", class: "primary" }, "Analyse event");
  btn.addEventListener("click", async () => {
    const g = [...good.querySelectorAll("input:checked")].map((i) => +i.value);
    const b = [...bad.querySelectorAll("input:checked")].map((i) => +i.value);
    if (!g.length) { err.textContent = "Tick at least one favourable house."; err.hidden = false; return; }
    err.hidden = true; btn.disabled = true; btn.textContent = "Analysing…";
    try {
      const v = await onAction("custom", { label: label.value.trim(), cusp: +cusp.value, good: g, bad: b });
      out.replaceChildren(eventsSection([v]));
    } catch (e) { err.textContent = e.message; err.hidden = false; }
    btn.disabled = false; btn.textContent = "Analyse event";
  });
  return section("Analyse your own event", "Choose the main cusp, the houses that support the event and the houses that negate it, as in the Andrew Dutta/KSK event tables.",
    h("div", { class: "custom-event" },
      h("div", { class: "row two" }, h("label", {}, "Preset", preset), h("label", {}, "Event", label)),
      h("label", {}, "Main cusp (its sub lord decides)", cusp),
      h("div", { class: "pick-label" }, "Favourable (main and supporting) houses"), good,
      h("div", { class: "pick-label" }, "Negating houses"), bad,
      btn, err), out);
}

function rectificationSection(rc) {
  return section("Birth-time rectification by ruling planets", t("K.S. Krishnamurti's method: within ±{w} minutes of the recorded time, these are the spans where the Lagna's sign, star and sub lords are all ruling planets now ({rps}). Cast this at the moment you are judging the chart; results change as the ruling planets change.", { w: rc.window_min, rps: rc.ruling_planets.map(tx).join(", ") }),
    rc.candidates.length ? table([
      { label: "Lagna sign / star / sub", render: (c) => `${c.sign_lord} / ${c.star_lord} / ${c.sub_lord}` },
      { label: "From", key: "start" }, { label: "To", key: "end" },
      { label: "Ascendant span", render: (c) => t("{a} to {b}", { a: c.asc_from, b: c.asc_to }) },
      { label: "Offset from recorded time", render: (c) => t("{n} min", { n: `${c.offset_min > 0 ? "+" : ""}${c.offset_min}` }), cls: "num" }], rc.candidates)
      : h("p", {}, "No span in this window has the Lagna's sign, star and sub lords all among the current ruling planets. Try a wider window, or recast at another moment."));
}

function kpCuspTable(cusps) {
  return table([{ label: "Cusp", key: "cusp", cls: "num" }, { label: "Sign", key: "sign" }, { label: "Degree", key: "dms", cls: "num" },
    { label: "Sign lord", key: "sign_lord" }, { label: "Star lord", key: "star_lord" }, { label: "Sub lord", key: "sub_lord" },
    { label: "Sub-sub", key: "sub_sub_lord" },
    { label: "CSL signifies (via its star lord)", render: (r) => houses(r.via_star) },
    { label: "CSL own", render: (r) => houses(r.own) }], cusps);
}

function significatorTables(sig, fourStep) {
  const pRows = Object.entries(sig.planet);
  const hRows = Object.entries(sig.house).sort((a, b) => +a[0] - +b[0]);
  return h("div", {},
    section("Planet-wise significations", "A: houses occupied by the planet's star lord (strongest). B: house occupied by the planet. C: houses owned by its star lord. D: houses it owns. Rahu and Ketu also carry their sign lord and conjoined planets.",
      table([{ label: "Planet", render: (r) => h("span", { class: "planet" }, r[0], r[1].self_strength ? tag("own star", "own") : null) },
        { label: "Star lord", render: (r) => r[1].star_lord },
        { label: "A", render: (r) => houses(r[1].A_star_occ) }, { label: "B", render: (r) => houses(r[1].B_occ) },
        { label: "C", render: (r) => houses(r[1].C_star_own) }, { label: "D", render: (r) => houses(r[1].D_own) },
        { label: "Node agency", render: (r) => houses(r[1].node_agent) },
        { label: "All houses", render: (r) => h("b", {}, houses(r[1].all)) }], pRows)),
    fourStep ? section("Four-step theory", "Step 1: the planet's own houses. Step 2: its star lord's houses (the result). Step 3: its sub lord's houses (whether the result is good or bad). Step 4: the sub lord's star lord.",
      table([{ label: "Planet", key: "planet" }, { label: "Step 1", render: (r) => houses(r.step1) },
        { label: "Star lord", key: "star_lord" }, { label: "Step 2", render: (r) => h("b", {}, houses(r.step2)) },
        { label: "Sub lord", key: "sub_lord" }, { label: "Step 3", render: (r) => houses(r.step3) },
        { label: "Sub's star lord", key: "sub_star_lord" }, { label: "Step 4", render: (r) => h("b", {}, houses(r.step4)) }], fourStep)) : null,
    section("House-wise significators", "Level 1 is strongest: planets in the star of the occupants, then the occupants, planets in the star of the owner, and the owner.",
      table([{ label: "House", render: (r) => r[0], cls: "num" },
        { label: "L1: in star of occupants", render: (r) => r[1].L1_in_star_of_occupants.join(", ") || "–" },
        { label: "L2: occupants", render: (r) => r[1].L2_occupants.join(", ") || "–" },
        { label: "L3: in star of owner", render: (r) => r[1].L3_in_star_of_owner.join(", ") || "–" },
        { label: "L4: owner", render: (r) => r[1].L4_owner.join(", ") || "–" }], hRows)));
}

function rpBlock(rp, title, sub) {
  return section(title, sub, kv([
    ["Ascendant", rp.asc_dms], ["Moon", rp.moon_dms],
    ["Lagna sign lord", rp.lagna_sign_lord], ["Lagna star lord", rp.lagna_star_lord], ["Lagna sub lord", rp.lagna_sub_lord],
    ["Moon sign lord", rp.moon_sign_lord], ["Moon star lord", rp.moon_star_lord], ["Moon sub lord", rp.moon_sub_lord],
    ["Day lord", rp.day_lord],
    ["Ruling planets (strength order)", h("b", {}, rp.ordered.join(", "))],
    ["Nodes as RP", rp.nodes.join(", ") || "None"],
  ]));
}

function eventsSection(events, { horary = false } = {}) {
  return h("div", { class: "events" }, events.map((e) => {
    const kind = e.verdict.startsWith("Promised") ? "good" : e.verdict.startsWith("Not") ? "bad" : "warn";
    return h("article", { class: "event" },
      h("h4", {}, e.event, tag(e.verdict, kind)),
      h("div", { class: "line" }, t("Cusp {c} sub lord {csl} is in the star of {st}", { c: e.cusp, csl: e.csl, st: e.csl_star })),
      h("div", { class: "line" }, t("Signifies via star lord: {a}; own: {b}", { a: houses(e.via_star), b: houses(e.own) })),
      h("div", { class: "line" }, "Favourable houses hit: ", h("b", { style: "color:var(--leaf)" }, houses(e.favourable_hits)),
        "; adverse: ", h("b", { style: "color:var(--kumkum)" }, houses(e.adverse_hits))),
      h("p", {}, e.rule),
      e.rp_agreement ? h("div", { class: "line" }, t("Significators agreeing with ruling planets: {x}", { x: e.rp_agreement.map(tx).join(", ") || t("none") })) : null,
      h("div", { class: "line" }, t("Significators of favourable houses: {x}", { x: e.significators.map(tx).join(", ") || t("none") })),
      e.windows && e.windows.length ? h("div", {}, h("div", { class: "line" }, h("b", {}, horary ? "Likely timing" : "Supportive periods ahead (Dasha–Bhukti)")),
        h("ul", {}, e.windows.map((w) => h("li", {}, h("b", {}, `${tx(w.md)}–${tx(w.ad)}`), " " + t("{a} to {b}", { a: w.start, b: w.end }),
          w.antaras.length ? h("div", {}, t("Best antaras: {x}", { x: w.antaras.map((a) => `${tx(a.lord)} (${t("{a} to {b}", { a: a.start, b: a.end })})`).join("; ") })) : null)))) :
        h("div", { class: "line", style: "color:var(--ink-3)" }, t("No supportive Dasha–Bhukti in the next {n} years.", { n: horary ? 5 : 25 })));
  }));
}

function kpOverview(res, isHorary) {
  const lag = res.planets[0];
  const houseSigns = res.cusp_lons.map((c) => Math.floor(c / 30) % 12);
  return h("div", {},
    h("div", { class: "grid-charts" },
      chartFromPoints(res.points, "Rasi chart", t("Lagna {s} {d}", { s: lag.sign_name, d: lag.dms })),
      chartFromPoints(res.points, "Bhava (cuspal) chart", res.rotation > 1 ? t("Rotated: house {n} as the 1st", { n: res.rotation }) : "Roman numerals I–XII mark the Placidus cusps",
        { houseOf: res.bhava_of, houseSigns, cusps: res.cusp_lons })),
    rpBlock(res.ruling_planets.now, isHorary ? "Ruling planets at judgment" : "Ruling planets now",
      isHorary ? null : "Computed for this moment at the birth place. KP uses these to fix timing."),
    section("Planets: star, sub and sub-sub lords", null, planetsTable(res.planets, { kp: true })),
    section("Cusps (Placidus)", null, kpCuspTable(res.cusps)));
}

function kp(res) {
  return [
    { id: "overview", label: "Overview", render: () => kpOverview(res, false) },
    { id: "events", label: "Event analysis", render: () => h("div", {},
      section("Cuspal sub-lord verdicts", "KP rule: the sub lord of a cusp, through the houses signified by its star lord, decides whether that house's matters are promised. Timing uses Vimshottari periods of planets that signify the favourable houses.", eventsSection(res.events)),
      customEventForm(res, ACTION)) },
    { id: "rectify", label: "Rectification", render: () => rectificationSection(res.rectification) },
    { id: "sig", label: "Significators", render: () => significatorTables(res.significators, res.four_step) },
    { id: "cusps", label: "Cusps", render: () => h("div", {}, section("Cusp table", null, kpCuspTable(res.cusps)),
      section("What each house signifies in KP", null, readingBlocks(Object.entries(res.house_texts || {}).map(([k, tt]) => ({ title: t("House {n}", { n: k }), text: tt }))))) },
    { id: "dasha", label: "Dasha", render: () => h("div", {},
      section("Vimshottari dasha (KP)", t("Balance at birth: {b} of {l}.", { b: res.dasha.vimshottari.balance, l: res.dasha.vimshottari.starting_lord }), dashaTree(res.dasha.vimshottari)),
      ashtottariSection(res.dasha.ashtottari)) },
    { id: "rp", label: "Ruling planets", render: () => h("div", { class: "cols" }, rpBlock(res.ruling_planets.now, "Ruling planets now", null), rpBlock(res.ruling_planets.birth, "Ruling planets at birth", "Useful for birth-time rectification: the Lagna sub lord should be among them.")) },
    { id: "stars", label: "Star lords", render: () => section("How each planet colours results as a star lord", null, readingBlocks(Object.entries(res.star_texts).map(([p, t]) => ({ title: p, text: t })))) },
    { id: "sub", label: "249 sub table", render: subTable },
    { id: "transit", label: "Transits", render: () => transitTable(res.transits) },
    { id: "panchang", label: "Panchanga", render: () => panchangSection(res.panchang) },
  ];
}

function subTable() {
  const box = h("div", {}, h("p", { class: "sub" }, "Loading the KP sub table…"));
  apiFetch("/api/kp/subtable").then((r) => r.json()).then((rows) => {
    box.replaceChildren(section("KP 249 sub divisions", "Horary numbers 1 to 249 map to these divisions, starting at 0° Aries.",
      table([{ label: "No.", key: "no", cls: "num" }, { label: "Sign", key: "sign" }, { label: "From", key: "from", cls: "num" },
        { label: "To", key: "to", cls: "num" }, { label: "Nakshatra", key: "nakshatra" }, { label: "Star lord", key: "star_lord" },
        { label: "Sub lord", key: "sub_lord" }], rows)));
  });
  return box;
}

function kpHorary(res) {
  const hz = res.horary;
  const ev = res.events;
  return [
    { id: "verdict", label: "Verdict", render: () => h("div", {},
      section(t("Horary number {n}: {q}", { n: hz.number, q: hz.question }), t("Ascendant fixed at {a} ({nak}, star {s}, sub {sub}). Other cusps by Placidus for the place of judgment.", { a: hz.ascendant, nak: hz.sub.nakshatra, s: hz.sub.star_lord, sub: hz.sub.sub_lord }),
        eventsSection(ev, { horary: true })),
      res.reflection && res.reflection.question_houses ? section("Reflection of mind", "KP checks that the chart answers the question asked: the Moon or the Lagna sub lord should signify the houses of the matter.",
        h("p", {}, tag(res.reflection.reflects ? "Question reflected" : "Not reflected", res.reflection.reflects ? "good" : "warn"), " ", res.reflection.note),
        kv([["Houses of the matter", houses(res.reflection.question_houses)],
          ["Moon signifies", t("{a} (matches: {b})", { a: houses(res.reflection.moon_houses), b: houses(res.reflection.moon_hits) })],
          [t("Lagna sub lord {l} signifies", { l: res.reflection.lagna_csl }), t("{a} (matches: {b})", { a: houses(res.reflection.lagna_csl_houses), b: houses(res.reflection.lagna_csl_hits) })]])) : null,
      section("The querent's mind (Moon)", "In KP horary the Moon's significations show what the querent is really concerned about.",
        kv([["Moon's star lord", res.moon_significations.star_lord], ["Houses signified", houses(res.moon_significations.all)]]))) },
    { id: "overview", label: "Charts & cusps", render: () => kpOverview(res, true) },
    { id: "sig", label: "Significators", render: () => significatorTables(res.significators, res.four_step) },
    { id: "dasha", label: "Dasha at judgment", render: () => section("Vimshottari from the Moon at judgment", "Used in KP horary to time the event.", dashaTree(res.dasha.vimshottari)) },
    { id: "sub", label: "249 sub table", render: subTable },
    { id: "panchang", label: "Panchanga", render: () => panchangSection(res.panchang, "Panchanga at judgment") },
  ];
}

// ================================================================= PRASHNA
function dial(pct) {
  const r = 50, c = 2 * Math.PI * r;
  const NSs = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(NSs, "svg");
  s.setAttribute("viewBox", "0 0 120 120"); s.setAttribute("class", "dial");
  s.innerHTML = `<circle cx="60" cy="60" r="${r}" fill="none" stroke-width="10" class="track"/>
    <circle cx="60" cy="60" r="${r}" fill="none" stroke-width="10" class="val" stroke-dasharray="${(pct / 100) * c} ${c}" transform="rotate(-90 60 60)"/>
    <text x="60" y="66" text-anchor="middle" font-size="26">${pct}%</text>`;
  return s;
}

function prashna(res) {
  const a = res.analysis;
  const verdict = () => h("div", {},
    h("div", { class: "verdict" }, dial(a.probability),
      h("div", {}, h("h4", {}, a.verdict), h("p", {}, t("{q}. Karya bhava {kh} ({ks}); Lagna {l}, {nat} and {ris}. Lagna lord {ll}, karya lord {kl}.", { q: a.question.replace(/\?$/, ""), kh: a.karya_house, ks: a.karya_sign, l: a.lagna, nat: a.lagna_nature, ris: a.rising, ll: a.lagna_lord, kl: a.karya_lord })),
        a.timing ? h("p", {}, h("b", {}, "Timing: "), a.timing) : null,
        a.extra && a.extra.direction ? h("p", {}, t("Direction to search: {d}.", { d: a.extra.direction }) + ` ${a.extra.recovery} ${a.extra.thief_or_misplaced}.`) : null)),
    section("Factors weighed", "Positive scores support the matter; negative scores obstruct it.",
      h("ul", { class: "factors" }, a.factors.map((f) => h("li", {}, h("span", { class: "sc " + (f.score >= 0 ? "pos" : "neg") }, (f.score > 0 ? "+" : "") + f.score), h("span", {}, f.text))))),
    section(t("Rising sign {s}", { s: a.lagna }), null, h("div", { class: "reading" }, h("p", {}, res.lagna_text))),
    a.arudha ? section("Arudha (number)", null, kv([["Number", a.arudha.number], ["Arudha sign", a.arudha.sign], ["Navamsa", a.arudha.navamsa], ["House from Udaya lagna", a.arudha.house_from_lagna]])) : null);
  const chartTab = () => h("div", {},
    h("div", { class: "grid-charts" },
      chartFromPoints(res.points, "Prashna chart (D1)", "Gk marks Gulika", { special: ["Gk"] }),
      chartFromVarga(res.vargas.D9, "Navamsa (D9)")),
    section("Planetary positions", null, planetsTable(res.planets)),
    section("Bhavas", null, table([{ label: "House", key: "house", cls: "num" }, { label: "Sign", key: "sign" }, { label: "Lord", key: "lord" },
      { label: "Lord in", key: "lord_in_house", cls: "num" }, { label: "Occupants", render: (r) => r.occupants.join(", ") || "–" },
      { label: "Aspected by", render: (r) => r.aspected_by.join(", ") || "–" }], res.houses)));
  const tajika = () => h("div", {},
    section("Tajika aspects between planets", "Ithasala (applying within the combined deeptamsha orb) promises results; Ishrafa (separating) shows the matter slipping away.",
      table([{ label: "Planets", render: (r) => `${r.a} – ${r.b}` }, { label: "Aspect", key: "aspect" }, { label: "Type", render: (r) => tag(r.type, r.applying ? "good" : "warn") },
        { label: "Gap", render: (r) => `${r.gap}°`, cls: "num" }, { label: "Orb", render: (r) => `${r.orb}°`, cls: "num" },
        { label: "Days to exact", key: "days_to_exact", cls: "num" }], a.tajika_matrix)),
    section("Sphutas (Prashna Marga)", "Trisphuta = Lagna + Moon + Gulika; Chatussphuta adds the Sun; Panchasphuta adds Rahu.",
      table([{ label: "Sphuta", render: (r) => r[0] }, { label: "Sign", render: (r) => r[1].sign }, { label: "Degree", render: (r) => `${fixed(r[1].deg, 2)}°`, cls: "num" },
        { label: "Nakshatra", render: (r) => `${r[1].nakshatra} ${r[1].pada}` }], Object.entries(a.sphutas))),
    section("Special lagnas", null, table([{ label: "Point", render: (r) => r[0] }, { label: "Sign", render: (r) => r[1].sign }, { label: "Longitude", render: (r) => r[1].dms, cls: "num" }], Object.entries(res.special_lagnas))));
  return [
    { id: "verdict", label: "Verdict", render: verdict },
    { id: "chart", label: "Chart & planets", render: chartTab },
    { id: "tajika", label: "Tajika & sphutas", render: tajika },
    { id: "panchang", label: "Panchanga", render: () => panchangSection(res.panchang, "Panchanga at query") },
  ];
}

// ================================================================= JAIMINI
function jaimini(res) {
  const j = res.jaimini;
  const r = res.reading;
  const AL = j.arudhas.AL.sign, UL = j.arudhas.UL.sign;
  const ov = () => h("div", {},
    h("div", { class: "grid-charts" },
      chartFromPoints(res.points, "Rasi with Arudhas", "AL Arudha lagna, UL Upapada, HL Hora lagna, GL Ghati lagna", { special: ["AL", "UL", "HL", "GL"], noDeg: ["AL", "UL"] }),
      chartFromVarga(res.vargas.D9, "Navamsa (Karakamsha)", t("Karakamsha in {s}", { s: j.karakamsha.sign })),
      chartFromVarga({ signs: { ...res.vargas.D9.signs, Lagna: j.karakamsha.sign_index } }, "Swamsha chart", "Navamsa read from the Karakamsha")),
    section("Chara karakas", t("Ranked by degree within sign ({x}).", { x: res.settings.karaka_scheme }),
      table([{ label: "Karaka", key: "karaka" }, { label: "Meaning", key: "full" }, { label: "Planet", render: (k) => h("span", { class: "planet" }, k.planet) },
        { label: "Degree in sign", render: (k) => `${fixed(k.degree, 2)}°`, cls: "num" }], j.karakas)),
    section("Karakamsha", null, kv([["Sign", j.karakamsha.sign], ["Planets in Karakamsha", j.karakamsha.planets_in.join(", ") || "None"],
      ["House from Rasi lagna", j.karakamsha.house_from_rasi_lagna], ["House from Navamsa lagna", j.karakamsha.house_from_navamsa_lagna],
      ["Planets from Karakamsha (D9)", Object.entries(j.karakamsha.planets_from_karakamsha).map(([p, hh]) => `${p} ${hh}`).join(", ")]])),
    section("Jaimini yogas", null, table([{ label: "Yoga", key: "name" }, { label: "Formed", render: (y) => tag(y.present ? "Yes" : "No", y.present ? "good" : "") },
      { label: "Meaning", render: (y) => y.description, cls: "wrap" }], j.raja_yogas)));
  const arudha = () => h("div", {},
    section("Arudha padas", "The image of each house in the world. Scorpio and Aquarius use the stronger of their two lords.",
      table([{ label: "Pada", render: (r) => r[0] }, { label: "Of house", render: (r) => r[1].house, cls: "num" },
        { label: "Sign", render: (r) => r[1].sign_name }, { label: "House from Lagna", render: (r) => r[1].house_from_lagna, cls: "num" },
        { label: "Lord used", render: (r) => r[1].lord_used }], Object.entries(j.arudhas))),
    section("Special lagnas", null, table([{ label: "Lagna", render: (x) => x[0] }, { label: "Sign", render: (x) => x[1].sign },
      { label: "Degree", render: (x) => `${fixed(x[1].deg, 2)}°`, cls: "num" }], Object.entries(j.special_lagnas))));
  const drishti = () => h("div", {},
    section("Rashi drishti (sign aspects)", "Movable signs aspect fixed signs except the adjacent one, fixed aspect movable except the adjacent one, and dual signs aspect each other.",
      table([{ label: "Planet", render: (x) => x[0] }, { label: "Aspects signs", render: (x) => x[1].signs.join(", ") },
        { label: "Aspects planets", render: (x) => x[1].planets.join(", ") || "–" }], Object.entries(j.planet_rashi_drishti))),
    section("Argala on the Lagna", null, argalaTable(j.argala_lagna)),
    section("Argala on the Arudha lagna", null, argalaTable(j.argala_al)));
  const signDasha = (ds, title) => section(title, t("{sys}, {dir} order.", { sys: ds.system, dir: ds.direction }) + " " + (ds.current ? t("Running now: {x}.", { x: ds.current }) : "") + (ds.padanatha ? " " + t("Padanatha {p}; starts from {s}.", { p: ds.padanatha, s: ds.start_sign }) : ""),
    h("div", { class: "dasha" }, ds.periods.map((p) => {
      const today = new Date().toISOString().slice(0, 10);
      const now = p.start <= today && today < p.end;
      return h("details", { class: now ? "now" : "", open: now || null }, h("summary", {}, h("span", {}, h("b", {}, t("{s} ({n} yrs)", { s: p.sign, n: p.years }))), h("span", {}, p.start), h("span", {}, p.end)),
        p.children.map((c) => h("div", { class: "lvl3" + (c.start <= today && today < c.end ? " now" : "") }, h("span", {}, `${p.sign} – ${c.sign}`), h("span", {}, c.start), h("span", {}, c.end))));
    })));
  const dasha = () => h("div", {}, signDasha(j.chara_dasha, "Chara dasha"),
    j.chara_dasha_lagna ? signDasha(j.chara_dasha_lagna, "Chara dasha (Lagna-footed variant)") : null,
    j.padanadhamsa ? signDasha(j.padanadhamsa, "Padanadhamsa dasha") : null);
  const reading = () => h("div", {},
    readingBlocks([r.atmakaraka, r.karakamsha]),
    r.planets_in_karakamsha.length ? section("Planets in Karakamsha", null, readingBlocks(r.planets_in_karakamsha.map((p) => ({ title: p.planet, text: p.text })))) : null,
    readingBlocks([r.arudha_lagna, r.upapada]),
    section("Karaka roles in this chart", null, readingBlocks(r.karakas.map((k) => ({ title: `${k.karaka}: ${k.planet}`, text: k.text })))));
  return [
    { id: "overview", label: "Overview", render: ov },
    { id: "reading", label: "Reading", render: reading },
    { id: "arudha", label: "Arudhas & lagnas", render: arudha },
    { id: "drishti", label: "Drishti & argala", render: drishti },
    { id: "dasha", label: "Chara dasha", render: dasha },
    { id: "vargas", label: "Vargas", render: () => h("div", { class: "grid-charts small" }, Object.entries(res.vargas).map(([k, v]) => chartFromVarga(v, k, v.name.split("–")[1]?.trim()))) },
    { id: "planets", label: "Planets", render: () => section("Planetary positions", null, planetsTable(res.planets)) },
    { id: "panchang", label: "Panchanga", render: () => panchangSection(res.panchang) },
  ];
}

function argalaTable(rows) {
  return table([{ label: "Argala", key: "type" }, { label: "From house", key: "from", cls: "num" }, { label: "Planets", render: (r) => r.planets.join(", ") || "–" },
    { label: "Obstruction from", key: "obstruction_from", cls: "num" }, { label: "Obstructing", render: (r) => r.obstructing.join(", ") || "–" },
    { label: "Status", render: (r) => r.status === "Unobstructed" ? tag(r.status, "good") : r.status === "Obstructed" ? tag(r.status, "warn") : "–" }], rows);
}

// ================================================================= WESTERN
const W_ORDER = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron", "North Node", "Ascendant", "Midheaven"];

function western(res, paschatya) {
  const w = res.western;
  const rd = res.reading;
  const wheelFig = (title, points, cusps, aspects) => h("figure", { class: "chart-card" }, h("figcaption", {}, title), wheel({ points, cusps, aspects }));
  const wp = (r) => h("span", { class: "planet" }, h("span", { class: "glyph" }, glyph(r.name)), " ", r.name, r.retro && !["North Node", "South Node"].includes(r.name) ? h("span", { class: "r" }, "R") : null);
  const pTable = () => table([{ label: "Body", render: wp }, { label: "Sign", key: "sign_name" }, { label: "Position", key: "dms", cls: "num" },
    { label: "House", key: "house", cls: "num" }, { label: "Dignity", render: (r) => r.dignity ? r.dignity.label : "–" },
    { label: "Term", render: (r) => r.dignity?.term || "–" }, { label: "Face", render: (r) => r.dignity?.face || "–" },
    { label: "Score", render: (r) => r.dignity && r.dignity.score !== undefined ? r.dignity.score : "–", cls: "num" },
    { label: "Speed", render: (r) => r.speed === undefined ? "–" : fixed(r.speed, 4), cls: "num" },
    { label: "Declination", render: (r) => r.decl === undefined ? "–" : fixed(r.decl, 2), cls: "num" }], w.planets);
  const big3 = h("div", { class: "chain" }, ["Sun", "Moon"].map((n) => {
    const p = w.planets.find((x) => x.name === n);
    return h("div", {}, h("small", {}, n), h("b", {}, `${p.sign_name} ${Math.floor(p.deg)}°`), h("small", {}, t("house {n}", { n: p.house })));
  }), h("div", {}, h("small", {}, "Ascendant"), h("b", {}, `${w.angles.Ascendant.sign} ${w.angles.Ascendant.dms.split("°")[0]}°`), h("small", {}, t("chart ruler {p}", { p: w.chart_ruler.modern }))),
  h("div", {}, h("small", {}, "Midheaven"), h("b", {}, `${w.angles.Midheaven.sign} ${w.angles.Midheaven.dms.split("°")[0]}°`), h("small", {}, w.house_system)),
  h("div", {}, h("small", {}, "Moon phase"), h("b", {}, w.moon_phase.name), h("small", {}, `${w.moon_phase.angle}°`)),
  h("div", {}, h("small", {}, "Chart shape"), h("b", {}, w.shape.name), h("small", {}, w.day_chart ? "Day chart" : "Night chart")));
  const ov = () => h("div", {}, big3,
    h("div", { class: "cols", style: "align-items:start" },
      wheelFig("Natal wheel", res.wheel.points, res.wheel.cusps, w.aspects),
      paschatya && res.points ? chartFromPoints(res.points, "Sayana chart (Indian style)", "Tropical longitudes in a kundali layout", { withDeg: true }) : null),
    section("Positions", t("{z} zodiac, {h} houses.", { z: w.zodiac, h: w.house_system }) + " " + (w.intercepted.length ? t("Intercepted signs: {x}.", { x: w.intercepted.map(tx).join(", ") }) : ""), pTable()),
    section("Angles", null, kv(Object.entries(w.angles).map(([k, v]) => [k, `${v.dms} ${v.sign}`]))));
  const housesTab = () => section("House cusps", null, table([{ label: "House", key: "house", cls: "num" }, { label: "Cusp", render: (r) => `${r.dms} ${r.sign}`, cls: "num" },
    { label: "Ruler (modern)", key: "ruler" }, { label: "Ruler (traditional)", key: "ruler_trad" },
    { label: "Planets", render: (r) => r.planets.join(", ") || "–" }], w.houses));
  const aspectsTab = () => {
    const names = W_ORDER;
    return h("div", {},
      section("Aspect grid", "Blue: harmonious; red: challenging; brass: neutral. Hover a symbol for the orb.", h("div", { class: "tw", style: "display:inline-block" }, aspectGrid(names, w.aspects))),
      section(t("Aspect list ({n})", { n: w.aspects.length }), null, table([{ label: "Aspect", render: (a) => `${a.a} ${a.symbol}︎ ${a.b}` }, { label: "Type", key: "aspect" },
        { label: "Orb", key: "orb_dms", cls: "num" }, { label: "Phase", render: (a) => a.applying ? "Applying" : "Separating" },
        { label: "Nature", render: (a) => tag(a.nature, a.nature === "harmonious" ? "own" : a.nature === "challenging" ? "bad" : "warn") }],
      [...w.aspects].sort((a, b) => a.orb - b.orb))));
  };
  const balanceTab = () => h("div", {},
    h("div", { class: "cols" },
      section("Elements", null, table([{ label: "Element", render: (r) => r[0] }, { label: "Weight", render: (r) => r[1], cls: "num" },
        { label: "Planets", render: (r) => w.elements_planets[r[0]].join(", ") || "–" }], Object.entries(w.elements))),
      section("Modalities", null, table([{ label: "Modality", render: (r) => r[0] }, { label: "Weight", render: (r) => r[1], cls: "num" },
        { label: "Planets", render: (r) => w.modalities_planets[r[0]].join(", ") || "–" }], Object.entries(w.modalities))),
      section("Hemispheres", null, kv(Object.entries(w.hemispheres).map(([k, v]) => [k, t("{n} planets", { n: v })])))),
    section("Chart shape", null, h("p", {}, `${w.shape.name}: ${w.shape.meaning}`)),
    section("Moon phase", null, h("p", {}, `${w.moon_phase.name} (${w.moon_phase.angle}°): ${w.moon_phase.meaning}.`)),
    section(t("Aspect patterns ({n})", { n: w.patterns.length }), null, w.patterns.length ? readingBlocks(rd.patterns) : h("p", {}, "No major configurations such as Grand Trines, T-squares or Yods are formed.")),
    rd.balance.length ? section("Emphasis", null, readingBlocks(rd.balance)) : null);
  const reading = () => h("div", {},
    section("The big picture", null, readingBlocks(rd.core)),
    section("Planets in signs and houses", null, h("div", { class: "reading" }, rd.planets.map((p) => h("article", {}, h("h4", {}, p.headline), h("p", {}, p.sign_text), h("p", { class: "alt" }, p.house_text))))),
    section("Aspects", "Tightest aspects first.", readingBlocks(rd.aspects)));
  const timeTab = () => {
    const tr = w.transits, p = w.progressions, s = w.solar_return;
    const srPts = Object.fromEntries(s.planets.map((x) => [x.name, x.lon]));
    srPts.Ascendant = s.asc.lon; srPts.Midheaven = s.mc.lon;
    return h("div", {},
      section("Transits", t("Sky for {d}, aspects to natal positions within tight orbs.", { d: tr.date }),
        table([{ label: "Body", render: (r) => h("span", {}, h("span", { class: "glyph" }, glyph(r.name)), " ", r.name, r.retro ? h("span", { class: "r" }, "R") : null) },
          { label: "Sign", key: "sign_name" }, { label: "Position", key: "dms", cls: "num" }, { label: "Natal house", key: "natal_house", cls: "num" }], tr.positions),
        h("div", { style: "height:12px" }),
        table([{ label: "Transit aspect", render: (a) => t("{a} {asp} natal {b}", { a: a.a, asp: a.aspect, b: a.b }) }, { label: "Orb", key: "orb_dms", cls: "num" },
          { label: "Phase", render: (a) => a.applying ? "Applying" : "Separating" }], tr.aspects)),
      section("Secondary progressions", t("Age {a}. Progressed lunar phase: {p}.", { a: p.age, p: p.progressed_lunar_phase }),
        table([{ label: "Progressed", key: "name" }, { label: "Sign", key: "sign_name" }, { label: "Position", key: "dms", cls: "num" }], p.positions),
        h("div", { style: "height:12px" }),
        table([{ label: "Progressed aspect", render: (a) => t("P. {a} {asp} natal {b}", { a: a.a, asp: a.aspect, b: a.b }) }, { label: "Orb", key: "orb_dms", cls: "num" }], p.aspects)),
      section("Solar return", t("Sun returns to its natal degree on {d}.", { d: s.moment }) + " " + s.note,
        h("div", { class: "cols", style: "align-items:start" }, wheelFig("Solar return wheel", srPts, s.cusps, []),
          table([{ label: "Body", key: "name" }, { label: "Sign", key: "sign_name" }, { label: "Position", key: "dms", cls: "num" }, { label: "SR house", key: "house", cls: "num" }], s.planets))));
  };
  const out = [
    { id: "overview", label: "Overview", render: ov },
    { id: "reading", label: "Reading", render: reading },
    { id: "aspects", label: "Aspects", render: aspectsTab },
    { id: "houses", label: "Houses", render: housesTab },
    { id: "balance", label: "Patterns & balance", render: balanceTab },
    { id: "time", label: "Transits & progressions", render: timeTab },
  ];
  if (paschatya) {
    out.splice(1, 0, { id: "sayana", label: "Sayana nakshatras", render: () => section("Sayana (tropical) nakshatras", "Nakshatras computed on tropical longitudes, as used in some Paschatya practice.",
      table([{ label: "Body", key: "name" }, { label: "Nakshatra", key: "nakshatra" }, { label: "Pada", key: "pada", cls: "num" }, { label: "Star lord", key: "nak_lord" }], res.sayana_nakshatras)) });
  }
  return out;
}

// ================================================================= entry
export function renderResult(res, { style = "south", onAction, ctx }) {
  STYLE = style;
  setStyle(style);
  ACTION = onAction;
  CTX = ctx;
  BIRTH = res.birth?.local?.slice(0, 10) || null;
  let defs;
  switch (res.method) {
    case "parashara": defs = parashara(res); break;
    case "kp": defs = kp(res); break;
    case "kp_horary": defs = kpHorary(res); break;
    case "prashna": defs = prashna(res); break;
    case "jaimini": defs = jaimini(res); break;
    case "western": defs = western(res, false); break;
    case "paschatya": defs = western(res, true); break;
    case "varshaphal": defs = varshaphalDefs(res); break;
    case "matching": defs = matchingDefs(res); break;
    case "muhurta": defs = muhurtaDefs(res); break;
    case "calendar": defs = calendarDefs(res); break;
    default: defs = [{ id: "raw", label: "Data", render: () => h("pre", {}, JSON.stringify(res, null, 1)) }];
  }
  let home = null;
  try { home = localStorage.getItem("js.homeTab"); } catch (_) { /* ignore */ }
  const tb = tabs(defs, home && defs.some((d) => d.id === home) ? home : undefined);
  const root = h("div", {}, header(res, onAction), tb);
  root.renderAll = tb.renderAll;
  return root;
}

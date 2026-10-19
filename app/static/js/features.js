// Renderers for the Parashara's Light–class tools: chakras, annual charts (Tithi Pravesha,
// Dasha Pravesh, Varshaphal), transit tools, dasha calendar, matching, muhurta, monthly
// panchanga and the custom worksheet.
import { h, table, kv, section, tag, houses, tabs, fixed } from "./ui.js";
import { indianChart, SIGNS, SHORT } from "./charts.js";
import { LANG, t, tx } from "./i18n.js";

const NS = "http://www.w3.org/2000/svg";
const svgEl = (tag_, attrs = {}, parent) => {
  const e = document.createElementNS(NS, tag_);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
};
const today = () => new Date().toISOString().slice(0, 10);
let STYLE = "south";
export function setStyle(s) { STYLE = s; }

function pointsChart(points, title, sub, opts = {}) {
  const signs = {}, degs = {}, retro = {};
  for (const [n, p] of Object.entries(points)) {
    signs[n] = p.sign;
    if (p.lon !== undefined && opts.withDeg !== false) degs[n] = p.lon % 30;
    if (p.retro && !["Rahu", "Ketu"].includes(n)) retro[n] = true;
  }
  return h("figure", { class: "chart-card" }, h("figcaption", {}, title, sub ? h("small", {}, sub) : null),
    indianChart({ style: STYLE, lagnaSign: points.Lagna.sign, signs, degs, retro, center: tx(title),
      special: new Set(opts.special || []) }));
}

function loading(msg = "Calculating…") {
  return h("div", { class: "loading small" }, h("p", {}, t(msg)));
}

function errorBox(e) {
  return h("p", { class: "form-error" }, `${t("This section could not be loaded:")} ${e.message || e}`);
}

/** Lazily fetch with the last chart request and render into a box. */
function lazy(ctx, url, extra, render) {
  const box = h("div", {}, loading());
  ctx.post(url, extra).then((d) => box.replaceChildren(render(d))).catch((e) => box.replaceChildren(errorBox(e)));
  return box;
}

// ================================================================ CHAKRAS
export function chakrasTab(res) {
  const c = res.chakras;
  if (!c) return h("p", {}, t("Chakras are not available for this chart."));
  return h("div", {}, sbc(c.sarvatobhadra), kota(c.kota), sanghatta(c.sanghatta), sudarshan(c.sudarshan), ghata(c.ghata));
}

function sbc(s) {
  if (!s) return null;
  const native = Object.fromEntries(Object.entries(s.native_points || {}).filter(([, v]) => v).map(([k, v]) => [v, k]));
  const planets = [...new Set((s.vedha || []).map((v) => v.planet))];
  const sel = h("select", { "aria-label": t("Show vedha of") }, h("option", { value: "" }, t("Show vedha of…")),
    planets.map((p) => h("option", { value: p }, p)));
  const grid = h("table", { class: "sbc" }, h("tbody", {}, s.grid.map((row) => h("tr", {}, row.map((cell) => {
    const nat = (s.natal || {})[cell.id] || [], tr_ = (s.transit || {})[cell.id] || [];
    const lbl = LANG === "te" && cell.te ? cell.te : (cell.deva && ["vowel", "consonant"].includes(cell.kind) ? `${cell.label} ${cell.deva}` : cell.label);
    return h("td", { class: `k-${cell.kind}${native[cell.id] ? " native" : ""}`, "data-id": cell.id, title: native[cell.id] || null },
      h("div", { class: "lbl" + (cell.te ? " no-tr" : "") }, lbl),
      cell.weekdays?.length ? h("div", { class: "wd" }, cell.weekdays.map((w) => tx(w).slice(0, 3)).join(" ")) : null,
      nat.length ? h("div", { class: "nat" }, nat.map((p) => SHORT[p] || p).join(" ")) : null,
      tr_.length ? h("div", { class: "trn" }, tr_.map((p) => SHORT[p] || p).join(" ")) : null);
  })))));
  sel.addEventListener("change", () => {
    grid.querySelectorAll("td").forEach((td) => td.classList.remove("vedha", "vedha-src"));
    for (const v of s.vedha || []) {
      if (v.planet !== sel.value || v.active === false) continue;
      v.cells.forEach((id) => grid.querySelector(`td[data-id="${id}"]`)?.classList.add("vedha"));
      grid.querySelector(`td[data-id="${v.from}"]`)?.classList.add("vedha-src");
    }
  });
  return section("Sarvatobhadra chakra", "Nakshatras on the outer ring, with vowels, consonants, rashis, tithis and weekdays inside. Natal planets are in ink, current transits in blue; outlined cells are your janma nakshatra, name letter, rashi, tithi and weekday. Choose a planet to see the cells its vedha pierces.",
    h("div", { class: "sbc-tools" }, sel), h("div", { class: "tw sbc-wrap" }, grid),
    (s.hits || []).length ? h("div", { style: "margin-top:12px" }, table([{ label: "Point", key: "point" }, { label: "Planet", key: "planet" },
      { label: "Nature", render: (r) => tag(r.nature, r.nature === "benefic" ? "good" : "bad") }, { label: "Vedha", key: "type" }], s.hits)) : null,
    h("p", { class: "sub", style: "margin-top:8px" }, t("Only the vedha matching each planet's motion is counted: normal speed casts front vedha, fast casts left, retrograde casts right; Sun, Moon, Rahu and Ketu cast all three.")),
    (s.summary || []).length ? h("ul", { class: "highlights" }, s.summary.map((x) => h("li", {}, x))) : null);
}

function kota(k) {
  if (!k) return null;
  const cell = (ring, dir) => (k.cells[`${ring}|${dir}`] || []).map((n) => h("div", { class: "kota-n" },
    h("span", {}, n.nakshatra), h("small", {}, n.entering ? t("entering") : t("exiting")),
    n.natal?.length ? h("b", {}, " ", n.natal.map((p) => SHORT[p] || p).join(" ")) : null,
    n.transit?.length ? h("b", { class: "trn" }, " ", n.transit.map((p) => SHORT[p] || p).join(" ")) : null));
  return section("Kota chakra", t("Kota Swami: {s}; Kota Pala: {p}. The fort runs from the outer Bahya ring to the inner Stambha; malefics moving inward by transit signal pressure, benefics there protect.", { s: k.swami, p: k.pala }),
    h("div", { class: "tw" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, t("Ring")), k.directions.map((d) => h("th", {}, d)))),
      h("tbody", {}, k.rings.map((r) => h("tr", {}, h("th", {}, r), k.directions.map((d) => h("td", {}, cell(r, d)))))))),
    h("ul", { class: "highlights" }, (k.assessment || []).map((x) => h("li", {}, x))));
}

function sanghatta(s) {
  if (!s) return null;
  return section("Sanghatta chakra", "Special nakshatras counted from the janma nakshatra. Malefic transits over them mark periods of arishta (strain); benefic transits ease them.",
    table([{ label: "Special nakshatra", key: "name" }, { label: "Count", key: "count", cls: "num" }, { label: "Nakshatra", key: "nakshatra" }], s.special),
    h("h4", { class: "mini" }, t("Transits now")),
    s.now?.length ? table([{ label: "Special", key: "special" }, { label: "Nakshatra", key: "nakshatra" },
      { label: "Planets", render: (r) => r.planets.join(", ") }, { label: "Nature", render: (r) => tag(r.malefic ? "Malefic" : "Benefic", r.malefic ? "bad" : "good") }], s.now)
      : h("p", {}, t("No planet is transiting a special nakshatra today.")),
    h("h4", { class: "mini" }, t("Next 12 months")),
    s.upcoming?.length ? table([{ label: "Planet", key: "planet" }, { label: "Special", key: "special" }, { label: "Nakshatra", key: "nakshatra" },
      { label: "From", key: "start" }, { label: "To", key: "end" }], s.upcoming, { rowClass: (r) => (r.start <= today() && today() <= r.end ? "cur" : null) })
      : h("p", {}, t("No malefic transits over the special nakshatras in the next 12 months.")),
    (s.notes || []).length ? h("ul", { class: "highlights" }, s.notes.map((x) => h("li", {}, x))) : null);
}

function sudarshan(s) {
  if (!s) return null;
  const size = 460, c = size / 2, R = [205, 150, 95, 40];
  const root = svgEl("svg", { viewBox: `0 0 ${size} ${size}`, class: "sudarshan", role: "img", "aria-label": t("Sudarshan chakra") });
  R.slice(0, 3).forEach((r) => svgEl("circle", { cx: c, cy: c, r, class: "ring" }, root));
  svgEl("circle", { cx: c, cy: c, r: R[3], class: "ring" }, root);
  const rings = [["Sun", R[0], R[1]], ["Moon", R[1], R[2]], ["Lagna", R[2], R[3]]];
  const curHouse = s.current?.house;
  for (let hIdx = 0; hIdx < 12; hIdx++) {
    // house 1 on the left (like a horoscope wheel), counter-clockwise
    const a0 = Math.PI - (hIdx * Math.PI) / 6 - Math.PI / 12, a1 = a0 - Math.PI / 6;
    const x = (r, a) => c + r * Math.cos(a), y = (r, a) => c - r * Math.sin(a);
    svgEl("line", { x1: x(R[3], a0), y1: y(R[3], a0), x2: x(R[0], a0), y2: y(R[0], a0), class: "spoke" }, root);
    if (hIdx + 1 === curHouse) {
      const p = svgEl("path", { d: `M${x(R[3], a0)} ${y(R[3], a0)} L${x(R[0], a0)} ${y(R[0], a0)} A${R[0]} ${R[0]} 0 0 1 ${x(R[0], a1)} ${y(R[0], a1)} L${x(R[3], a1)} ${y(R[3], a1)} A${R[3]} ${R[3]} 0 0 0 ${x(R[3], a0)} ${y(R[3], a0)}Z`, class: "cur" }, root);
      root.insertBefore(p, root.firstChild);
    }
    for (const [ref, ro, ri] of rings) {
      const sign = s.rings[ref][hIdx];
      const mid = (a0 + a1) / 2, rm = (ro + ri) / 2;
      const pl = Object.entries(s.planets).filter(([, sg]) => sg === sign).map(([p]) => SHORT[p] || p);
      const tx_ = svgEl("text", { x: x(rm, mid), y: y(rm, mid) - (pl.length ? 6 : 0), class: "sno", "text-anchor": "middle", "dominant-baseline": "central" }, root);
      tx_.textContent = String(sign + 1);
      if (pl.length) {
        const pt = svgEl("text", { x: x(rm, mid), y: y(rm, mid) + 8, class: "spl", "text-anchor": "middle", "dominant-baseline": "central" }, root);
        pt.textContent = pl.join(" ");
      }
    }
    const lt = svgEl("text", { x: x(R[0] + 12, (a0 + a1) / 2), y: y(R[0] + 12, (a0 + a1) / 2), class: "hno", "text-anchor": "middle", "dominant-baseline": "central" }, root);
    lt.textContent = String(hIdx + 1);
  }
  return section("Sudarshan chakra", t("Three rings read together: Lagna (inner), Moon (middle) and Sun (outer); numbers are signs, the outer figures are houses. Sudarshana dasha: year {a} of life ({f} to {to}) activates house {h} (shaded).", { a: s.current?.year ?? s.current?.age, f: s.current?.from, to: s.current?.to, h: s.current?.house }),
    h("div", { class: "cols", style: "align-items:start" }, h("div", {}, root),
      h("div", {}, kv(Object.entries(s.current?.signs || {}).map(([k, v]) => [t("{r}: active sign", { r: k }), SIGNS[v] || v])),
        s.current?.month ? h("p", { class: "sub", style: "margin-top:10px" }, t("This month (month {n} of the year) activates house {h}.", { n: s.current.month.n, h: s.current.month.house })) : null,
        (s.notes || []).length ? h("ul", { class: "highlights" }, s.notes.map((x) => h("li", {}, x))) : null)));
}

function ghata(g) {
  if (!g) return null;
  return section("Ghata chakra", t("Inauspicious factors for janma rashi {r}. Avoid starting important work when they coincide.", { r: g.rashi }),
    table([{ label: "Factor", key: "factor" }, { label: "Ghata (avoid)", key: "value" },
      { label: "Detail", render: (r) => [r.detail, (r.variants || []).length ? t("other readings: {x}", { x: r.variants.map(tx).join(", ") }) : null].filter(Boolean).join("; ") || "–", cls: "wrap" }], g.items),
    h("h4", { class: "mini" }, t("Today")),
    g.today?.length ? table([{ label: "Factor", key: "factor" }, { label: "Value", key: "value" },
      { label: "Status", render: (r) => r.active === false ? tag("Later today", "warn") : tag("Active now", "bad") },
      { label: "Window", render: (r) => (r.window || []).map((x) => x.slice(11, 16)).join("–") || "–" }], g.today)
      : h("p", {}, t("None of the ghata factors applies today.")),
    (g.notes || []).length ? h("ul", { class: "highlights" }, g.notes.map((x) => h("li", {}, x))) : null);
}

// ================================================================ ANNUAL CHARTS
export function annualTab(res, ctx) {
  const yr = new Date().getFullYear();
  const yearSel = h("input", { type: "number", value: yr, min: 1900, max: 2100, style: "max-width:120px", "aria-label": t("Year") });
  const out = h("div", {});
  const load = () => {
    out.replaceChildren(lazy(ctx, "/api/varshaphal", { year: +yearSel.value }, (d) => tithiPravesha(d.tithi_pravesha)));
  };
  yearSel.addEventListener("change", load);
  load();
  const dp = res.dasha_pravesh || [];
  return h("div", {},
    section("Tithi Pravesha chart", "The Vedic annual chart: the moment the Sun–Moon angle repeats your birth tithi while the Sun is in its birth sign. The weekday lord of that day rules the year.",
      h("label", { class: "inline" }, t("Year"), yearSel), out),
    section("Dasha Pravesh charts", "Charts cast for the moment each running period began; read them like an annual chart for that period.",
      h("div", { class: "grid-charts" }, dp.map((d) => pointsChart(d.points, `${tx(d.level)}: ${d.lords.map(tx).join("–")}`,
        t("Began {m}; ends {e}; Lagna {l}", { m: d.moment, e: d.end, l: d.lagna }))))));
}

function tithiPravesha(tp) {
  if (!tp) return h("p", {}, t("Tithi Pravesha is not available."));
  return h("div", {},
    kv([["Moment", tp.moment], ["Place", tp.place], ["Tithi", tx(tp.tithi?.name || tp.tithi)], ["Weekday", tx(tp.weekday)], ["Year lord", tx(tp.year_lord)]]),
    h("div", { class: "grid-charts", style: "margin-top:14px" }, pointsChart(tp.points, "Tithi Pravesha chart", tp.moment)),
    planetRows(tp.planets),
    (tp.notes || []).length ? h("ul", { class: "highlights" }, tp.notes.map((x) => h("li", {}, x))) : null);
}

function planetRows(rows) {
  if (!rows) return null;
  return table([{ label: "Planet", render: (r) => h("span", { class: "planet" }, r.name, r.retro && !["Rahu", "Ketu"].includes(r.name) ? h("span", { class: "r" }, "R") : null) },
    { label: "Sign", key: "sign_name" }, { label: "Longitude", key: "dms", cls: "num" },
    { label: "Nakshatra", render: (r) => `${r.nakshatra || ""} ${r.pada || ""}` }, { label: "House", key: "house", cls: "num" }], rows);
}

// ================================================================ VARSHAPHAL (method view)
export function varshaphalDefs(res) {
  const v = res.varshaphal, tp = res.tithi_pravesha;
  return [
    { id: "vchart", label: "Varsha chart", render: () => h("div", {},
      section(t("Varshaphal {y} (age {a})", { y: v.year, a: v.age }), t("Varsha Pravesha {m} at {p}.", { m: v.moment, p: v.place }),
        h("div", { class: "grid-charts" }, pointsChart(v.points, "Varsha chart", v.moment, { special: ["Muntha"] })),
        kv([["Muntha", t("{s} in house {h}, lord {l}", { s: v.muntha.sign_name, h: v.muntha.house, l: v.muntha.lord })],
          ["Year lord (Varshesha)", h("b", {}, tx(v.year_lord.planet))]]),
        h("p", { class: "sub", style: "margin-top:8px" }, v.year_lord.reason)),
      section("Planets in the Varsha chart", null, planetRows(v.planets)),
      (v.notes || []).length ? section("Notes", null, h("ul", { class: "highlights" }, v.notes.map((x) => h("li", {}, x)))) : null) },
    { id: "office", label: "Office-bearers", render: () => h("div", {},
      section("Pancha-adhikaris (five office-bearers)", "The year lord is chosen from these by strength and aspect to the Varsha lagna.",
        table([{ label: "Office", key: "role" }, { label: "Planet", key: "planet" }], v.office_bearers)),
      section("Pancha-vargiya bala", "Tajika five-fold strength; vimshopaka out of 20.",
        table([{ label: "Planet", key: "planet" }, ...["kshetra", "uchcha", "hadda", "drekkana", "navamsa", "total", "vimshopaka"]
          .map((k) => ({ label: k[0].toUpperCase() + k.slice(1), render: (r) => fixed(r[k], 2), cls: "num" }))], v.pvb))) },
    { id: "tajika", label: "Tajika yogas", render: () => h("div", {},
      section("Tajika yogas", null, v.tajika_yogas?.length ? table([{ label: "Yoga", key: "name" }, { label: "Planets", render: (r) => (r.planets || []).join(", ") },
        { label: "Meaning", key: "description", cls: "wrap" }], v.tajika_yogas) : h("p", {}, t("No major Tajika yoga is formed."))),
      section("Tajika aspects", null, table([{ label: "Planets", render: (r) => `${tx(r.a)} – ${tx(r.b)}` },
        { label: "Aspect", render: (r) => r.aspect || r.sign_aspect }, { label: "Nature", render: (r) => r.nature ? tag(r.nature, r.friendly ? "good" : "warn") : "–" },
        { label: "Type", render: (r) => r.type ? tag(r.type, r.applying ? "good" : "") : "–" },
        { label: "Gap", render: (r) => (r.gap !== undefined && r.gap !== null ? `${r.gap}°` : "–"), cls: "num" }], v.tajika_aspects || []))) },
    { id: "sahams", label: "Sahams", render: () => section("Sahams", "Sensitive points of the year; a saham strengthened by its lord and benefics fulfils that theme.",
      table([{ label: "Saham", key: "name" }, { label: "Sign", key: "sign" }, { label: "Longitude", key: "dms", cls: "num" }, { label: "House", key: "house", cls: "num" }], v.sahams)) },
    { id: "mudda", label: "Mudda dasha", render: () => section("Mudda dasha", "Vimshottari compressed into the year.",
      h("div", { class: "dasha" }, v.mudda_dasha.map((p) => h("details", { class: p.start <= today() && today() < p.end ? "now" : "", open: (p.start <= today() && today() < p.end) || null },
        h("summary", {}, h("span", {}, h("b", {}, p.lord)), h("span", {}, p.start), h("span", {}, p.end)),
        (p.children || []).map((c) => h("div", { class: "lvl3" + (c.start <= today() && today() < c.end ? " now" : "") }, h("span", {}, `${p.lord} – ${c.lord}`), h("span", {}, c.start), h("span", {}, c.end))))))) },
    { id: "patyayini", label: "Patyayini dasha", render: () => section("Patyayini dasha", "Periods from the krishamsha (degrees in sign) of the Lagna and planets.",
      table([{ label: "Planet", key: "planet" }, { label: "From", key: "start" }, { label: "To", key: "end" }, { label: "Days", render: (r) => fixed(r.days, 1), cls: "num" }],
        v.patyayini_dasha, { rowClass: (r) => (r.start <= today() && today() < r.end ? "cur" : null) })) },
    { id: "tp", label: "Tithi Pravesha", render: () => section("Tithi Pravesha chart", null, tithiPravesha(tp)) },
  ];
}

// ================================================================ TRANSIT TOOLS
export function transitTools(res, ctx) {
  return lazy(ctx, "/api/transits", {}, (d) => h("div", {},
    section("Animated transits", "Planets moving through your chart over the coming year. Your Lagna is marked Asc.", animator(d.frames)),
    section("Year at a glance", t("Sign of each planet from {a} to {b}. Hover a bar for dates.", { a: d.year.from, b: d.year.to }), gantt(d.year)),
    section("Transit strength (Ashtakavarga)", d.strength.note, heatmap(d.strength)),
    section("Ingresses and stations", null, table([{ label: "Date", key: "date" }, { label: "Planet", key: "planet" },
      { label: "Event", key: "event" }, { label: "Sign", key: "sign" },
      { label: "From Lagna", key: "house_from_lagna", cls: "num" }, { label: "From Moon", key: "house_from_moon", cls: "num" }], d.year.events))));
}

function animator(fr) {
  const box = h("div", { class: "anim" });
  const chartBox = h("div", { class: "anim-chart" });
  const label = h("div", { class: "anim-date" });
  const slider = h("input", { type: "range", min: 0, max: fr.dates.length - 1, value: 0, "aria-label": t("Date") });
  const play = h("button", { type: "button", class: "ghost" }, t("Play"));
  let timer = null, i = 0;
  const draw = () => {
    const signs = { Lagna: fr.natal_lagna }, retro = {};
    for (const [p, arr] of Object.entries(fr.lon)) { signs[p] = Math.floor(arr[i] / 30) % 12; if (fr.retro[p][i]) retro[p] = true; }
    chartBox.replaceChildren(indianChart({ style: STYLE, lagnaSign: fr.natal_lagna, signs, retro, center: fr.dates[i] }));
    label.textContent = fr.dates[i];
    slider.value = i;
  };
  slider.addEventListener("input", () => { i = +slider.value; draw(); });
  play.addEventListener("click", () => {
    if (timer) { clearInterval(timer); timer = null; play.textContent = t("Play"); return; }
    play.textContent = t("Pause");
    timer = setInterval(() => { i = (i + 1) % fr.dates.length; draw(); if (!box.isConnected) clearInterval(timer); }, 120);
  });
  draw();
  return h("div", { class: "anim-wrap" }, chartBox, h("div", { class: "anim-controls" }, play, slider, label));
}

const tip = (() => {
  let el = null;
  return {
    show(ev, html) {
      if (!el) { el = h("div", { class: "viz-tip", role: "tooltip" }); document.body.appendChild(el); }
      el.innerHTML = html; el.hidden = false;
      const x = Math.min(ev.clientX + 14, innerWidth - el.offsetWidth - 8);
      el.style.left = `${x}px`; el.style.top = `${ev.clientY + 14}px`;
    },
    hide() { if (el) el.hidden = true; },
  };
})();
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function gantt(y) {
  const planets = Object.keys(y.segments);
  const W = 900, rowH = 30, left = 84, top = 26, H = top + planets.length * rowH + 8;
  const root = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "gantt", role: "img", "aria-label": t("Year at a glance") });
  // month ticks
  const start = new Date(y.from), end = new Date(y.to), span = end - start;
  for (let d = new Date(start.getFullYear(), start.getMonth() + 1, 1); d < end; d.setMonth(d.getMonth() + 1)) {
    const x = left + ((d - start) / span) * (W - left - 8);
    svgEl("line", { x1: x, y1: top - 6, x2: x, y2: H - 6, class: "grid" }, root);
    const lt = svgEl("text", { x: x + 3, y: top - 10, class: "axis" }, root);
    lt.textContent = d.toLocaleDateString(document.documentElement.lang === "te" ? "te-IN" : "en", { month: "short" });
  }
  planets.forEach((p, r) => {
    const yy = top + r * rowH;
    const nl = svgEl("text", { x: left - 10, y: yy + rowH / 2, class: "rowlbl", "text-anchor": "end", "dominant-baseline": "central" }, root);
    nl.textContent = tx(p);
    y.segments[p].forEach((sg, k) => {
      const x0 = left + sg.frac_start * (W - left - 8), x1 = left + sg.frac_end * (W - left - 8);
      const w = Math.max(1, x1 - x0 - 2);
      const rect = svgEl("rect", { x: x0 + 1, y: yy + 4, width: w, height: rowH - 8, rx: 4, class: `seg s${k % 2}` }, root);
      rect.addEventListener("mousemove", (ev) => tip.show(ev, `<b>${esc(tx(p))}</b> ${esc(tx(sg.sign))}<br>${esc(sg.start)} – ${esc(sg.end)}`));
      rect.addEventListener("mouseleave", tip.hide);
      if (w > 34) {
        const st = svgEl("text", { x: x0 + w / 2 + 1, y: yy + rowH / 2, class: "seglbl", "text-anchor": "middle", "dominant-baseline": "central" }, root);
        st.textContent = tx(sg.sign.slice(0, 3));
      }
    });
  });
  return h("div", { class: "viz" }, root);
}

function heatmap(sr) {
  const planets = Object.keys(sr.series);
  const n = sr.dates.length;
  const W = 900, left = 84, top = 22, cell = (W - left - 8) / n, rowH = 26, H = top + planets.length * rowH + 40;
  const root = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "heat", role: "img", "aria-label": t("Transit strength (Ashtakavarga)") });
  let lastMonth = "";
  sr.dates.forEach((d, i) => {
    const m = d.slice(0, 7);
    if (m !== lastMonth) {
      lastMonth = m;
      const lt = svgEl("text", { x: left + i * cell + 2, y: top - 8, class: "axis" }, root);
      lt.textContent = new Date(d).toLocaleDateString(document.documentElement.lang === "te" ? "te-IN" : "en", { month: "short" });
    }
  });
  planets.forEach((p, r) => {
    const yy = top + r * rowH;
    const nl = svgEl("text", { x: left - 10, y: yy + rowH / 2, class: "rowlbl", "text-anchor": "end", "dominant-baseline": "central" }, root);
    nl.textContent = tx(p);
    sr.series[p].forEach((v, i) => {
      const rect = svgEl("rect", { x: left + i * cell, y: yy + 2, width: Math.max(1, cell - 1), height: rowH - 4, class: `b${v}` }, root);
      rect.addEventListener("mousemove", (ev) => tip.show(ev, `<b>${esc(tx(p))}</b> ${esc(sr.dates[i])}<br>${esc(t("{n} bindus", { n: v }))}`));
      rect.addEventListener("mouseleave", tip.hide);
    });
  });
  // legend: diverging scale 0..8
  const ly = top + planets.length * rowH + 14;
  const lt = svgEl("text", { x: left, y: ly + 9, class: "axis" }, root);
  lt.textContent = t("Difficult");
  for (let v = 0; v <= 8; v++) svgEl("rect", { x: left + 70 + v * 22, y: ly, width: 20, height: 12, class: `b${v}` }, root);
  const rt = svgEl("text", { x: left + 70 + 9 * 22 + 6, y: ly + 9, class: "axis" }, root);
  rt.textContent = t("Favourable");
  // table view: monthly average per planet
  const months = [...new Set(sr.dates.map((d) => d.slice(0, 7)))];
  const avg = (p, m) => {
    const vals = sr.series[p].filter((_, i) => sr.dates[i].startsWith(m));
    return vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1) : "–";
  };
  return h("div", {}, h("div", { class: "viz" }, root),
    h("details", {}, h("summary", {}, t("Show as a table")),
      table([{ label: "Planet", render: (p) => p }, ...months.map((m) => ({ label: m, render: (p) => avg(p, m), cls: "num" }))], planets)));
}

// ================================================================ DASHA CALENDAR
export function dashaCalendar(res, ctx) {
  const now = new Date();
  let y = now.getFullYear(), m = now.getMonth() + 1;
  const title = h("h4", { class: "cal-title" });
  const box = h("div", {});
  const load = () => {
    title.textContent = new Date(y, m - 1, 1).toLocaleDateString(document.documentElement.lang === "te" ? "te-IN" : "en", { month: "long", year: "numeric" });
    box.replaceChildren(lazy(ctx, "/api/dasha_calendar", { year: y, month: m }, (d) => calendarGrid(y, m, (day) =>
      d.events.filter((e) => e.date.slice(0, 10) === day).map((e) => h("div", { class: `ev l${e.level}` },
        h("small", {}, `${e.date.slice(11, 16)} ${tx(e.level_name)}`), " ", e.lords.slice(-1).map(tx).join(""))),
    h("p", { class: "sub", style: "margin-top:8px" }, t("Running at the start of the month: {x}", { x: d.running_at_start.map((r) => tx(r.lords.slice(-1)[0])).join(" › ") })))));
  };
  const nav = h("div", { class: "cal-nav" },
    h("button", { type: "button", class: "ghost", onclick: () => { m -= 1; if (!m) { m = 12; y -= 1; } load(); } }, t("Previous month")),
    title,
    h("button", { type: "button", class: "ghost", onclick: () => { m += 1; if (m > 12) { m = 1; y += 1; } load(); } }, t("Next month")));
  load();
  return section("Dasha calendar", "Every Vimshottari change in the month, down to Sookshma level.", nav, box);
}

function calendarGrid(y, m, cellFn, footer) {
  const first = new Date(Date.UTC(y, m - 1, 1));
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const lead = first.getUTCDay();
  const names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const cells = [];
  for (let i = 0; i < lead; i++) cells.push(h("div", { class: "cal-cell blank" }));
  for (let d = 1; d <= days; d++) {
    const iso = `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push(h("div", { class: "cal-cell" + (iso === today() ? " today" : "") }, h("div", { class: "cal-d" }, d), cellFn(iso)));
  }
  return h("div", {}, h("div", { class: "cal" }, names.map((n) => h("div", { class: "cal-h" }, tx(n).slice(0, 3))), cells), footer || null);
}

// ================================================================ MATCHING
export function matchingDefs(res) {
  const mt = res.matching;
  const a = mt.ashtakoota, d = mt.dashakoota, k = mt.kuja;
  const score = h("div", { class: "verdict" },
    dial(a.adjusted_total ?? a.total, a.max),
    h("div", {}, h("h4", {}, a.verdict),
      h("p", {}, t("{b} ({bn}) and {g} ({gn}): {s} of {m} gunas.", { b: mt.boy.name || t("Groom"), bn: `${mt.boy.nakshatra} ${mt.boy.pada}`, g: mt.girl.name || t("Bride"), gn: `${mt.girl.nakshatra} ${mt.girl.pada}`, s: a.adjusted_total ?? a.total, m: a.max })),
      h("p", {}, t("Dashakoota: {n} of 10 poruthams agree.", { n: d.count_ok }), " ", tag(d.critical_ok ? "Rajju and Vedha agree" : "Rajju or Vedha fails", d.critical_ok ? "good" : "bad"))));
  return [
    { id: "msum", label: "Summary", render: () => h("div", {}, score,
      section("Summary", null, h("ul", { class: "highlights" }, (mt.summary || []).map((x) => h("li", {}, x)))),
      h("div", { class: "grid-charts" }, res.boy_points ? pointsChart(res.boy_points, mt.boy.name || "Groom", tx(mt.boy.moon_sign)) : null,
        res.girl_points ? pointsChart(res.girl_points, mt.girl.name || "Bride", tx(mt.girl.moon_sign)) : null)) },
    { id: "ashta", label: "Ashtakoota", render: () => section("Ashtakoota (Guna Milan)", a.verdict,
      table([{ label: "Koota", key: "name" }, { label: "Groom", key: "boy" }, { label: "Bride", key: "girl" },
        { label: "Score", render: (r) => `${r.score} / ${r.max}`, cls: "num" },
        { label: "After exceptions", render: (r) => (r.adjusted ?? r.score) !== r.score ? h("b", {}, `${r.adjusted} / ${r.max}`) : "–", cls: "num" },
        { label: "Note", key: "note", cls: "wrap" }], a.kootas),
      h("p", { style: "margin-top:10px" }, h("b", {}, t("Total: {s} of {m}", { s: a.adjusted_total ?? a.total, m: a.max })))) },
    { id: "dasha10", label: "Dashakoota", render: () => section("Dashakoota (10 poruthams)", d.verdict,
      table([{ label: "Porutham", key: "name" }, { label: "Result", render: (r) => tag(r.result, /Uttama|Yes/.test(r.result) ? "good" : /Madhyama/.test(r.result) ? "warn" : "bad") },
        { label: "Note", key: "note", cls: "wrap" }], d.poruthams)) },
    { id: "kuja", label: "Kuja dosha", render: () => section("Kuja (Mangal) dosha", k.verdict,
      table([{ label: "Person", render: (r) => r[0] }, { label: "Present", render: (r) => tag(r[1].present ? "Yes" : "No", r[1].present ? "warn" : "good") },
        { label: "Mars from Lagna / Moon / Venus", render: (r) => Object.values(r[1].from || {}).join(" / ") },
        { label: "Cancellations", render: (r) => (r[1].cancellations || []).join("; ") || "–", cls: "wrap" }],
      [[mt.boy.name || t("Groom"), k.boy], [mt.girl.name || t("Bride"), k.girl]])) },
  ];
}

function dial(v, max) {
  const r = 50, c = 2 * Math.PI * r, pct = Math.max(0, Math.min(1, v / max));
  const s = document.createElementNS(NS, "svg");
  s.setAttribute("viewBox", "0 0 120 120"); s.setAttribute("class", "dial");
  s.innerHTML = `<circle cx="60" cy="60" r="${r}" fill="none" stroke-width="10" class="track"/>
    <circle cx="60" cy="60" r="${r}" fill="none" stroke-width="10" class="val" stroke-dasharray="${pct * c} ${c}" transform="rotate(-90 60 60)"/>
    <text x="60" y="60" text-anchor="middle" font-size="26">${v}</text><text x="60" y="82" text-anchor="middle" font-size="12">/ ${max}</text>`;
  return s;
}

// ================================================================ MUHURTA
export function muhurtaDefs(res) {
  const m = res.muhurta;
  return [
    { id: "windows", label: "Best times", render: () => section(t("{e}: best windows", { e: m.event }), t("{a} to {b} at {p}. Higher scores are better; each window lists what supports it and what to watch.", { a: m.range[0], b: m.range[1], p: m.place }),
      m.windows.length ? h("div", { class: "events" }, m.windows.map((w) => h("article", { class: "event" },
        h("h4", {}, `${w.start.slice(0, 10)}`, tag(t("score {n}", { n: w.score }), w.score >= 70 ? "good" : w.score >= 50 ? "warn" : "")),
        h("div", { class: "line" }, h("b", {}, `${w.start.slice(11)} – ${w.end.slice(11)}`), ` ${tx(w.weekday)}`, w.duration_min ? h("small", { class: "age" }, " " + t("{n} min", { n: w.duration_min })) : null),
        h("div", { class: "line" }, `${tx(w.tithi)}, ${tx(w.nakshatra)}, ${tx(w.yoga)}, ${tx(w.karana)}; ${t("Lagna")} ${tx(w.lagna)}`),
        w.reasons?.length ? h("ul", {}, w.reasons.map((x) => h("li", {}, x))) : null,
        w.warnings?.length ? h("ul", { class: "warns" }, w.warnings.map((x) => h("li", {}, x))) : null)))
        : h("p", {}, t("No window in this range meets the rules. Try a longer range."))) },
    { id: "rules", label: "Rules applied", render: () => section("Rules applied", null, h("ul", { class: "highlights" }, (m.rules || []).map((x) => h("li", {}, x)))) },
  ];
}

// ================================================================ PANCHANGA CALENDAR
const specialName = (x) => (typeof x === "string" ? tx(x) : tx(x.name));

export function calendarDefs(res) {
  const c = res.calendar;
  const grid = calendarGrid(c.year, c.month, (iso) => {
    const d = c.days.find((x) => x.date === iso);
    if (!d) return null;
    return h("div", { class: "pc" }, h("div", {}, tx(d.tithi)), h("div", { class: "pc-n" }, tx(d.nakshatra)),
      h("small", {}, `${t("Sunrise")} ${d.sunrise || ""}`),
      (d.special || []).length ? h("div", { class: "pc-s" }, d.special.map(specialName).join(", ")) : null);
  });
  return [
    { id: "month", label: "Month", render: () => section(t("Panchanga for {m}", { m: `${c.year}-${String(c.month).padStart(2, "0")}` }), t("At {p}; values at local sunrise.", { p: c.place }), grid) },
    { id: "days", label: "Daily details", render: () => section("Daily details", null, table([
      { label: "Date", key: "date" }, { label: "Weekday", key: "weekday" }, { label: "Sunrise", key: "sunrise" },
      { label: "Sunset", key: "sunset" }, { label: "Moonrise", key: "moonrise" }, { label: "Tithi", render: (d) => `${tx(d.tithi)} (${t("till {x}", { x: d.tithi_end?.slice(5, 16) })})` },
      { label: "Nakshatra", render: (d) => `${tx(d.nakshatra)} (${t("till {x}", { x: d.nakshatra_end?.slice(5, 16) })})` },
      { label: "Yoga", key: "yoga" }, { label: "Karana", key: "karana" }, { label: "Moon sign", key: "moon_sign" },
      { label: "Rahu kaal", render: (d) => (d.rahu_kaal || []).join("–") },
      { label: "Yamaganda", render: (d) => (d.yamaganda || []).join("–") },
      { label: "Masa", key: "masa" },
      { label: "Special", render: (d) => (d.special || []).map((x) => specialName(x) + (x.time ? ` ${x.time.slice(11)}` : "")).join(", ") || "–" }], c.days)) },
  ];
}

// ================================================================ WORKSHEET
export function worksheet(catalog) {
  const KEY = "js.worksheet";
  let layout;
  try { layout = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (_) { layout = null; }
  if (!Array.isArray(layout) || !layout.length) layout = [{ id: "D1", size: "m" }, { id: "D9", size: "m" }, { id: "planets", size: "l" }, { id: "dasha", size: "s" }];
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(layout)); } catch (_) { /* ignore */ } };
  const grid = h("div", { class: "ws-grid" });
  const add = h("select", { "aria-label": t("Add a panel") }, h("option", { value: "" }, t("Add a panel…")),
    Object.entries(catalog).map(([id, p]) => h("option", { value: id }, tx(p.title))));
  add.addEventListener("change", () => { if (add.value) { layout.push({ id: add.value, size: "m" }); save(); draw(); add.value = ""; } });
  let dragFrom = null;
  const draw = () => {
    grid.replaceChildren(...layout.filter((x) => catalog[x.id]).map((item, i) => {
      const p = catalog[item.id];
      const card = h("div", { class: `ws-card ws-${item.size}`, draggable: "true" },
        h("div", { class: "ws-head" }, h("span", { class: "ws-grip", "aria-hidden": "true" }, "⠿"), h("b", {}, tx(p.title)),
          h("span", { class: "ws-btns" },
            ["s", "m", "l"].map((sz) => h("button", { type: "button", class: "ghost" + (item.size === sz ? " on" : ""), "aria-label": t("Size") + " " + sz.toUpperCase(),
              onclick: () => { item.size = sz; save(); draw(); } }, sz.toUpperCase())),
            h("button", { type: "button", class: "ghost", "aria-label": t("Remove"), onclick: () => { layout.splice(i, 1); save(); draw(); } }, "×"))),
        h("div", { class: "ws-body" }, p.render()));
      card.addEventListener("dragstart", (e) => { dragFrom = i; e.dataTransfer.effectAllowed = "move"; card.classList.add("dragging"); });
      card.addEventListener("dragend", () => card.classList.remove("dragging"));
      card.addEventListener("dragover", (e) => { e.preventDefault(); card.classList.add("over"); });
      card.addEventListener("dragleave", () => card.classList.remove("over"));
      card.addEventListener("drop", (e) => {
        e.preventDefault(); card.classList.remove("over");
        if (dragFrom === null || dragFrom === i) return;
        const [moved] = layout.splice(dragFrom, 1);
        layout.splice(i, 0, moved); dragFrom = null; save(); draw();
      });
      return card;
    }));
  };
  draw();
  const home = h("label", { class: "check" }, h("input", { type: "checkbox", checked: localStorage.getItem("js.homeTab") === "worksheet" || null,
    onchange: (e) => { try { localStorage.setItem("js.homeTab", e.target.checked ? "worksheet" : ""); } catch (_) { /* ignore */ } } }), t("Open the worksheet first"));
  return section("Worksheet", "Build your own screen: add panels, drag them to reorder, and choose a size. The layout is remembered.",
    h("div", { class: "ws-tools" }, add, home,
      h("button", { type: "button", class: "ghost", onclick: () => { layout = []; save(); draw(); } }, t("Clear"))), grid);
}

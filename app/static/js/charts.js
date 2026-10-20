// SVG chart renderers: North Indian, South Indian, Western wheel, aspect grid.
const NS = "http://www.w3.org/2000/svg";
export const SIGN_SHORT = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"];
export const SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
  "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
const VS = "︎";
export const GLYPH = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂", Jupiter: "♃", Saturn: "♄",
  Uranus: "♅", Neptune: "♆", Pluto: "♇", Chiron: "⚷", "North Node": "☊", "South Node": "☋",
  Lilith: "⚸", "Part of Fortune": "⊗", Fortune: "⊗", Vertex: "Vx",
};
export const SIGN_GLYPH = "♈♉♊♋♌♍♎♏♐♑♒♓".split("");
export const glyph = (n) => (GLYPH[n] || n) + (GLYPH[n] && GLYPH[n].length === 1 ? VS : "");
export const signGlyph = (i) => SIGN_GLYPH[i] + VS;
export const SHORT = {
  Lagna: "As", Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju", Venus: "Ve",
  Saturn: "Sa", Rahu: "Ra", Ketu: "Ke", Uranus: "Ur", Neptune: "Ne", Pluto: "Pl", Fortuna: "Fo", Muntha: "Mu",
};

function svg(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function text(parent, x, y, s, cls, attrs = {}) {
  const t = svg("text", { x, y, class: cls, ...attrs }, parent);
  t.textContent = s;
  return t;
}

const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];

/** Position within a sign as D°MM', the tables' D°MM'SS" without the seconds. */
export function degMin(x) {
  const s = Math.round(x * 3600);
  return `${Math.floor(s / 3600)}°${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}'`;
}

/** One chart entry: label, then degrees (D°MM', or whole degrees when the box is crowded), then R. */
function drawItem(root, x, y, it, { size, short }, attrs = {}) {
  const cls = "pl" + (it.retro ? " retro" : "") + (it.special ? " special" : "") + (it.cusp ? " cusp no-tr" : "");
  const t = svg("text", { x, y, class: cls, "text-anchor": "middle", style: `font-size:${size}px`, ...attrs }, root);
  t.textContent = it.label;
  if (it.deg !== undefined && it.deg !== null) {
    const d = svg("tspan", { class: "deg", dx: 2, style: `font-size:${(size * 0.76).toFixed(1)}px` }, t);
    d.textContent = short ? `${Math.floor(it.deg)}°` : degMin(it.deg);
  }
  if (it.retro) {
    const rr = svg("tspan", { dx: 1, "font-size": 9, "baseline-shift": "super" }, t);
    rr.textContent = "R";
  }
  return t;
}

// ------------------------------------------------------------------ North Indian
const N_POLY = {
  1: [[200, 0], [100, 100], [200, 200], [300, 100]], 2: [[0, 0], [200, 0], [100, 100]],
  3: [[0, 0], [100, 100], [0, 200]], 4: [[0, 200], [100, 100], [200, 200], [100, 300]],
  5: [[0, 200], [100, 300], [0, 400]], 6: [[0, 400], [100, 300], [200, 400]],
  7: [[200, 400], [100, 300], [200, 200], [300, 300]], 8: [[200, 400], [300, 300], [400, 400]],
  9: [[400, 400], [300, 300], [400, 200]], 10: [[400, 200], [300, 300], [200, 200], [300, 100]],
  11: [[400, 200], [300, 100], [400, 0]], 12: [[400, 0], [300, 100], [200, 0]],
};
const N_ANCHOR = { 1: [200, 88], 2: [100, 34], 3: [36, 100], 4: [96, 200], 5: [36, 300], 6: [100, 362],
  7: [200, 300], 8: [300, 362], 9: [364, 300], 10: [304, 200], 11: [364, 100], 12: [300, 34] };
const N_SIGNNO = { 1: [200, 182], 2: [100, 84], 3: [84, 104], 4: [182, 204], 5: [84, 304],
  6: [100, 324], 7: [200, 232], 8: [300, 324], 9: [316, 304], 10: [218, 204], 11: [316, 104], 12: [300, 84] };
const NARROW = new Set([2, 3, 5, 6, 8, 9, 11, 12]);

/**
 * houseSigns: array[12] sign index (0-11) for houses 1..12
 * items: {house: [{label, retro, special, cusp, deg}]}
 */
export function northChart({ houseSigns, items, center, size = 400 }) {
  const root = svg("svg", { viewBox: "-2 -2 404 404", class: "kundali", role: "img",
    "aria-label": center || "North Indian chart" });
  svg("polygon", { points: N_POLY[1].map((p) => p.join(",")).join(" "), class: "house-lagna" }, root);
  svg("rect", { x: 0, y: 0, width: 400, height: 400, class: "frame" }, root);
  svg("path", { d: "M0 0L400 400M400 0L0 400M200 0L400 200L200 400L0 200Z", class: "frame" }, root);
  for (let h = 1; h <= 12; h++) {
    const [sx, sy] = N_SIGNNO[h];
    text(root, sx, sy, String(houseSigns[h - 1] + 1), "signno", { "text-anchor": "middle", "dominant-baseline": "middle" });
    placeItems(root, N_ANCHOR[h], items[h] || [], NARROW.has(h));
  }
  return root;
}

// Box layout: entries with D°MM' need a single column, so crowded boxes shrink the type and,
// past what fits, fall back to two columns with whole degrees.
function northLayout(n, narrow, withDeg) {
  if (!withDeg) return { cols: n > 4 ? 2 : 1, size: n > 6 ? 11.5 : 13.5, lh: n > 6 ? 13 : 15.5, colW: narrow ? 34 : 44 };
  if (n <= (narrow ? 4 : 6)) return { cols: 1, size: n <= 4 ? 13.5 : 12, lh: n <= 3 ? 15.5 : n === 4 ? 14.5 : 13.5 };
  if (narrow) return { cols: 2, size: 11.5, lh: 13, colW: 36, short: true };
  return { cols: 2, size: 12.5, lh: n > 8 ? 13 : 14.5, colW: 56, short: true };
}

function placeItems(root, [ax, ay], list, narrow) {
  if (!list.length) return;
  const n = list.length;
  const L = northLayout(n, narrow, list.some((it) => it.deg !== undefined && it.deg !== null));
  const rows = Math.ceil(n / L.cols);
  const y0 = ay - ((rows - 1) * L.lh) / 2;
  list.forEach((it, i) => {
    const c = L.cols === 1 ? 0 : i % 2;
    const r = L.cols === 1 ? i : Math.floor(i / 2);
    const x = L.cols === 1 ? ax : ax + (c === 0 ? -L.colW / 2 : L.colW / 2);
    drawItem(root, x, y0 + r * L.lh, it, L, { "dominant-baseline": "middle" });
  });
}

// ------------------------------------------------------------------ South Indian
const S_CELL = { 11: [0, 0], 0: [1, 0], 1: [2, 0], 2: [3, 0], 3: [3, 1], 4: [3, 2], 5: [3, 3],
  6: [2, 3], 7: [1, 3], 8: [0, 3], 9: [0, 2], 10: [0, 1] };

function southLayout(n, withDeg) {
  if (!withDeg) return { cols: n > 4 ? 2 : 1, size: n > 6 ? 11.5 : 13.5, lh: n > 8 ? 12 : 15, y0: 26 };
  if (n <= 4) return { cols: 1, size: 13.5, lh: 15, y0: 26 };
  if (n === 5) return { cols: 1, size: 12.5, lh: 13.5, y0: 24 };
  if (n === 6) return { cols: 1, size: 11.5, lh: 11.6, y0: 21 };
  if (n <= 8) return { cols: 2, size: 12, lh: 14.5, y0: 26, short: true };
  if (n <= 10) return { cols: 2, size: 11.5, lh: 12.5, y0: 24, short: true };
  return { cols: 2, size: 11, lh: 11, y0: 21, short: true };
}

/** items: {signIndex: [{label, retro, special, cusp, deg}]} */
export function southChart({ lagnaSign, items, center, cellNotes = {} }) {
  const root = svg("svg", { viewBox: "-2 -2 404 404", class: "kundali", role: "img",
    "aria-label": center || "South Indian chart" });
  const [lx, ly] = S_CELL[lagnaSign];
  svg("rect", { x: lx * 100, y: ly * 100, width: 100, height: 100, class: "house-lagna" }, root);
  svg("rect", { x: 0, y: 0, width: 400, height: 400, class: "frame" }, root);
  svg("path", { d: "M100 0V400M300 0V400M0 100H400M0 300H400M200 0V100M200 300V400M0 200H100M300 200H400", class: "frame" }, root);
  svg("rect", { x: 100, y: 100, width: 200, height: 200, fill: "var(--surface)", stroke: "none" }, root);
  svg("path", { d: "M100 100H300V300H100Z", class: "frame" }, root);
  svg("line", { x1: lx * 100, y1: ly * 100 + 22, x2: lx * 100 + 22, y2: ly * 100, class: "frame" }, root);
  for (let s = 0; s < 12; s++) {
    const [cx, cy] = S_CELL[s];
    text(root, cx * 100 + 94, cy * 100 + 94, SIGN_SHORT[s], "signno", { "text-anchor": "end" });
    if (cellNotes[s]) text(root, cx * 100 + 6, cy * 100 + 94, cellNotes[s], "signno cusp-note");
    const list = items[s] || [];
    const L = southLayout(list.length, list.some((it) => it.deg !== undefined && it.deg !== null));
    list.forEach((it, i) => {
      const c = L.cols === 1 ? 0 : i % 2;
      const r = L.cols === 1 ? i : Math.floor(i / 2);
      drawItem(root, cx * 100 + (L.cols === 1 ? 50 : 27 + c * 46), cy * 100 + L.y0 + r * L.lh, it, L);
    });
  }
  if (center) {
    // wrap long titles so they stay inside the 200px centre square
    const lines = center.split("\n").flatMap((ln) => {
      if (ln.length <= 22) return [ln];
      const out = [];
      let cur = "";
      for (const w of ln.split(" ")) {
        if ((cur + " " + w).trim().length > 22 && cur) { out.push(cur); cur = w; } else cur = (cur + " " + w).trim();
      }
      if (cur) out.push(cur);
      return out;
    });
    lines.forEach((ln, i) => text(root, 200, 200 + (i - (lines.length - 1) / 2) * 20, ln, "center",
      { "text-anchor": "middle", "dominant-baseline": "middle" }));
  }
  return root;
}

/**
 * Generic: build an Indian chart from {name: signIndex} placements.
 * style: 'north' | 'south'. lagnaSign: sign of the first house. degs: {name: degInSign}
 * houseOf: {name: house} places planets by house (Bhava chalit, KP). cusps: the twelve cusp
 * longitudes, drawn as I–XII with their degrees (KP cuspal chart).
 */
export function indianChart({ style, lagnaSign, signs, degs = {}, retro = {}, special = new Set(),
  center = "", houseOf = null, houseSigns = null, cusps = null }) {
  const label = (n) => SHORT[n] || n;
  const order = ["Lagna", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu",
    "Ketu", "Uranus", "Neptune", "Pluto"];
  const names = Object.keys(signs).filter((n) => n !== "Lagna").sort((a, b) => {
    const ia = order.indexOf(a), ib = order.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
  const item = (n) => ({ label: label(n), retro: retro[n], special: special.has(n), deg: degs[n] });
  const cusp = (c, i) => ({ label: ROMAN[i], cusp: true, deg: c % 30 });
  // the Ascendant sits in its own sign; lagnaSign may differ (Chandra lagna is read from the Moon)
  const asc = { label: "Asc", special: true, deg: degs.Lagna };
  const ascSign = signs.Lagna ?? lagnaSign;
  const hs = houseSigns || Array.from({ length: 12 }, (_, i) => (lagnaSign + i) % 12);
  if (style === "south") {
    const items = {};
    if (cusps) {
      // KP chart: planets in their own signs and the cusps I–XII in theirs, each box in zodiac order,
      // so a planet's house reads off the cusp degrees beside it
      for (const n of names) (items[signs[n]] ||= []).push(item(n));
      cusps.forEach((c, i) => (items[Math.floor(c / 30) % 12] ||= []).push(cusp(c, i)));
      for (const list of Object.values(items)) list.sort((a, b) => a.deg - b.deg);
      return southChart({ lagnaSign: Math.floor(cusps[0] / 30) % 12, items, center });
    }
    if (houseOf) {
      // Bhava chalit: each planet moves to the sign of its house, so the box is no longer its
      // sign and degrees would mislead; each box is labelled with the houses that fall in it
      for (const n of names) if (houseOf[n]) (items[hs[houseOf[n] - 1]] ||= []).push({ ...item(n), deg: undefined });
      items[hs[0]] = [{ label: "Asc", special: true }, ...(items[hs[0]] || [])];
      const cellNotes = {};
      hs.forEach((sg, i) => { cellNotes[sg] = (cellNotes[sg] ? cellNotes[sg] + "," : "H") + (i + 1); });
      return southChart({ lagnaSign: hs[0], items, center, cellNotes });
    }
    for (const n of names) (items[signs[n]] ||= []).push(item(n));
    items[ascSign] = [asc, ...(items[ascSign] || [])];
    return southChart({ lagnaSign, items, center });
  }
  const items = {};
  if (cusps) cusps.forEach((c, i) => { items[i + 1] = [cusp(c, i)]; });
  else if (!houseOf && degs.Lagna !== undefined) items[((ascSign - lagnaSign + 12) % 12) + 1] = [asc];
  for (const n of names) {
    const h = houseOf ? houseOf[n] : ((signs[n] - lagnaSign + 12) % 12) + 1;
    if (!h) continue;
    (items[h] ||= []).push(item(n));
  }
  return northChart({ houseSigns: hs, items, center });
}

// ------------------------------------------------------------------ Western wheel
export function wheel({ points, cusps, aspects = [], size = 640, labels = {} }) {
  const c = size / 2;
  const R1 = c - 12, R2 = R1 - 40, R3 = R2 - 22, RP = R3 - 30, RD = RP - 22, RA = RD - 30;
  const asc = points.Ascendant;
  const ang = (lon) => ((180 + (lon - asc)) * Math.PI) / 180;
  const xy = (lon, r) => [c + r * Math.cos(ang(lon)), c - r * Math.sin(ang(lon))];
  const root = svg("svg", { viewBox: `-22 -22 ${size + 44} ${size + 44}`, class: "wheel", role: "img",
    "aria-label": "Western natal wheel" });
  // sign ring
  for (let s = 0; s < 12; s++) {
    const a0 = s * 30, a1 = s * 30 + 30;
    const [x0, y0] = xy(a0, R1), [x1, y1] = xy(a1, R1), [x2, y2] = xy(a1, R2), [x3, y3] = xy(a0, R2);
    svg("path", { d: `M${x0} ${y0} A${R1} ${R1} 0 0 0 ${x1} ${y1} L${x2} ${y2} A${R2} ${R2} 0 0 1 ${x3} ${y3} Z`,
      class: "signseg" + (s % 2 ? " alt" : "") }, root);
    const [gx, gy] = xy(a0 + 15, (R1 + R2) / 2);
    text(root, gx, gy, signGlyph(s), "sg", { "text-anchor": "middle", "dominant-baseline": "central" });
  }
  svg("circle", { cx: c, cy: c, r: R1, class: "ring outer" }, root);
  svg("circle", { cx: c, cy: c, r: R2, class: "ring" }, root);
  svg("circle", { cx: c, cy: c, r: R3, class: "ring" }, root);
  svg("circle", { cx: c, cy: c, r: RA, class: "ring" }, root);
  for (let d = 0; d < 360; d += 5) {
    const [a, b] = xy(d, R2), [e, f] = xy(d, R2 - (d % 10 === 0 ? 7 : 4));
    svg("line", { x1: a, y1: b, x2: e, y2: f, class: "tick" }, root);
  }
  // houses
  cusps.forEach((cl, i) => {
    const isAngle = i % 3 === 0;
    const [a, b] = xy(cl, isAngle ? R1 + 6 : R3), [e, f] = xy(cl, RA);
    svg("line", { x1: a, y1: b, x2: e, y2: f, class: isAngle ? "angle" : "cusp" }, root);
    const next = cusps[(i + 1) % 12];
    const mid = cl + (((next - cl) % 360) + 360) % 360 / 2;
    const [hx, hy] = xy(mid, (R2 + R3) / 2);
    text(root, hx, hy, String(i + 1), "hn", { "text-anchor": "middle", "dominant-baseline": "central" });
  });
  const [ax, ay] = xy(asc, R1 + 4);
  text(root, ax, ay - 8, "AC", "axis-label", { "text-anchor": "end" });
  if (points.Midheaven !== undefined) {
    const [mx, my] = xy(points.Midheaven, R1 + 10);
    text(root, mx + 6, my, "MC", "axis-label", { "dominant-baseline": "central" });
  }
  // aspects
  for (const a of aspects) {
    if (!(a.a in points) || !(a.b in points) || a.a === "Ascendant" || a.b === "Ascendant" ||
      a.a === "Midheaven" || a.b === "Midheaven") continue;
    if (!["Conjunction", "Opposition", "Trine", "Square", "Sextile", "Quincunx"].includes(a.aspect) || a.aspect === "Conjunction") continue;
    const [x1, y1] = xy(points[a.a], RA), [x2, y2] = xy(points[a.b], RA);
    svg("line", { x1, y1, x2, y2, class: "asp " + a.nature, "stroke-dasharray": a.aspect === "Quincunx" ? "4 3" : null }, root);
  }
  // planets with collision avoidance
  const bodies = Object.entries(points).filter(([n]) => n !== "Ascendant" && n !== "Midheaven")
    .map(([n, lon]) => ({ n, lon, disp: lon })).sort((p, q) => p.lon - q.lon);
  const minSep = 7.5;
  for (let iter = 0; iter < 60; iter++) {
    let moved = false;
    for (let i = 0; i < bodies.length; i++) {
      const p = bodies[i], q = bodies[(i + 1) % bodies.length];
      let d = (((q.disp - p.disp) % 360) + 360) % 360;
      if (bodies.length > 1 && d < minSep) {
        const push = (minSep - d) / 2;
        p.disp -= push; q.disp += push; moved = true;
      }
    }
    if (!moved) break;
  }
  for (const b of bodies) {
    const [t1x, t1y] = xy(b.lon, R3), [t2x, t2y] = xy(b.lon, R3 - 7);
    svg("line", { x1: t1x, y1: t1y, x2: t2x, y2: t2y, class: "tick" }, root);
    const [gx, gy] = xy(b.disp, RP);
    const [cx2, cy2] = xy(b.disp, RP + 11);
    svg("line", { x1: t2x, y1: t2y, x2: cx2, y2: cy2, class: "cusp" }, root);
    const g = text(root, gx, gy, glyph(b.n), "pg", { "text-anchor": "middle", "dominant-baseline": "central" });
    const title = svg("title", {}, g);
    title.textContent = `${b.n} ${Math.floor(b.lon % 30)}° ${SIGNS[Math.floor(b.lon / 30) % 12]}${labels[b.n] || ""}`;
    const [dx, dy] = xy(b.disp, RD);
    text(root, dx, dy, `${Math.floor(b.lon % 30)}°${labels[b.n] || ""}`, "pd",
      { "text-anchor": "middle", "dominant-baseline": "central" });
  }
  return root;
}

// ------------------------------------------------------------------ aspect grid
export function aspectGrid(names, aspects) {
  const idx = Object.fromEntries(names.map((n, i) => [n, i]));
  const m = {};
  for (const a of aspects) {
    if (!(a.a in idx) || !(a.b in idx)) continue;
    const [i, j] = idx[a.a] > idx[a.b] ? [idx[a.a], idx[a.b]] : [idx[a.b], idx[a.a]];
    m[`${i},${j}`] = a;
  }
  const tbl = document.createElement("table");
  tbl.className = "agrid";
  const tb = document.createElement("tbody");
  names.forEach((n, i) => {
    const tr = document.createElement("tr");
    for (let j = 0; j < i; j++) {
      const td = document.createElement("td");
      const a = m[`${i},${j}`];
      if (a) {
        td.textContent = a.symbol + VS;
        td.className = a.nature === "harmonious" ? "h" : a.nature === "challenging" ? "c" : "n";
        td.title = `${a.a} ${a.aspect} ${a.b} (orb ${a.orb_dms}${a.applying ? ", applying" : ", separating"})`;
      }
      tr.appendChild(td);
    }
    const self = document.createElement("th");
    self.textContent = n === "Ascendant" ? "AC" : n === "Midheaven" ? "MC" : glyph(n);
    self.title = n;
    self.className = "self";
    tr.appendChild(self);
    tb.appendChild(tr);
  });
  tbl.appendChild(tb);
  return tbl;
}

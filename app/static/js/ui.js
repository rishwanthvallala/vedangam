// Small DOM helpers shared by renderers.
export function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "html") e.innerHTML = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat(Infinity)) {
    if (k === null || k === undefined || k === false) continue;
    e.appendChild(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return e;
}

/** cols: [{key|render, label, cls}] */
export function table(cols, rows, { rowClass } = {}) {
  const thead = h("thead", {}, h("tr", {}, cols.map((c) => h("th", { class: c.cls, scope: "col" }, c.label))));
  const tbody = h("tbody", {}, rows.map((r, i) => h("tr", { class: rowClass ? rowClass(r, i) : null },
    cols.map((c) => {
      const v = c.render ? c.render(r, i) : r[c.key];
      return h("td", { class: c.cls }, v === undefined || v === null || v === "" ? "–" : v);
    }))));
  return h("div", { class: "tw" }, h("table", {}, thead, tbody));
}

export function kv(pairs) {
  return h("dl", { class: "kv" }, pairs.filter((p) => p && p[1] !== undefined && p[1] !== null && p[1] !== "")
    .map(([k, v]) => [h("dt", {}, k), h("dd", {}, v)]));
}

export function section(title, sub, ...content) {
  return h("section", { class: "sec" }, h("h3", {}, title), sub ? h("p", { class: "sub" }, sub) : null, ...content);
}

export function tag(text, kind = "") {
  return h("span", { class: `tag ${kind}` }, text);
}

const GOOD = new Set(["Exalted", "Moolatrikona", "Great Friend"]);
const OWN = new Set(["Own"]);
const BAD = new Set(["Debilitated", "Great Enemy"]);
export function dignityTag(d) {
  if (!d) return "–";
  return tag(d, GOOD.has(d) ? "good" : OWN.has(d) ? "own" : BAD.has(d) ? "bad" : d === "Enemy" ? "warn" : "");
}

export function houses(list) {
  if (!list || !list.length) return "–";
  return list.join(", ");
}

/** Tabs: defs [{id, label, render: () => Node}] — panels render lazily */
export function tabs(defs, initial) {
  const bar = h("div", { class: "tabs", role: "tablist" });
  const panels = h("div", {});
  const built = {};
  const buttons = {};
  const show = (id) => {
    for (const d of defs) {
      const on = d.id === id;
      buttons[d.id].setAttribute("aria-selected", on ? "true" : "false");
      buttons[d.id].tabIndex = on ? 0 : -1;
      if (on && !built[d.id]) {
        const p = h("div", { class: "tabpanel", role: "tabpanel", id: `panel-${d.id}` });
        try { p.appendChild(d.render()); } catch (e) { console.error(e); p.appendChild(h("p", { class: "form-error" }, `This section could not be displayed: ${e.message}`)); }
        panels.appendChild(p);
        built[d.id] = p;
      }
      if (built[d.id]) built[d.id].hidden = !on;
    }
    try { localStorage.setItem("js.tab", id); } catch (_) { /* ignore */ }
  };
  defs.forEach((d, i) => {
    const b = h("button", { role: "tab", type: "button", "aria-controls": `panel-${d.id}`, onclick: () => show(d.id),
      onkeydown: (e) => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        const j = (i + (e.key === "ArrowRight" ? 1 : defs.length - 1)) % defs.length;
        buttons[defs[j].id].focus(); show(defs[j].id);
      } }, d.label);
    buttons[d.id] = b;
    bar.appendChild(b);
  });
  let start = defs[0].id;
  try {
    const saved = localStorage.getItem("js.tab");
    if (initial) start = initial;
    else if (saved && defs.some((d) => d.id === saved)) start = saved;
  } catch (_) { /* ignore */ }
  show(start);
  const wrap = h("div", {}, bar, panels);
  wrap.renderAll = () => defs.forEach((d) => { if (!built[d.id]) { show(d.id); } });
  wrap.show = show;
  return wrap;
}

export const ord = (n) => (n === 1 ? "1st" : n === 2 ? "2nd" : n === 3 ? "3rd" : `${n}th`);
export const fixed = (x, n = 2) => (x === null || x === undefined ? "–" : Number(x).toFixed(n));
export function dmsSign(lon) {
  const SH = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"];
  lon = ((lon % 360) + 360) % 360;
  const s = Math.floor(lon / 30);
  let d = lon % 30;
  let deg = Math.floor(d), m = Math.floor((d - deg) * 60), sec = Math.round(((d - deg) * 60 - m) * 60);
  if (sec === 60) { sec = 0; m += 1; }
  if (m === 60) { m = 0; deg += 1; }
  return `${deg}°${String(m).padStart(2, "0")}'${String(sec).padStart(2, "0")}" ${SH[s]}`;
}

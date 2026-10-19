// Language layer. English strings in the code are the keys; in another language the UI
// dictionary, the term dictionary (planets, signs, nakshatras, dignities…) and the chart
// abbreviation map are applied to everything that gets rendered.
import { apiFetch } from "./api.js";
export let LANG = "en";
let UI = {}, TERMS = {}, CHART = {};
let termRe = null;

export async function setLang(lang) {
  LANG = lang === "te" ? "te" : "en";
  document.documentElement.lang = LANG;
  if (LANG === "en") { UI = {}; TERMS = {}; CHART = {}; termRe = null; return; }
  const b = await (await apiFetch(`/api/i18n/${LANG}`)).json();
  UI = b.ui || {}; TERMS = b.terms || {}; CHART = b.chart || {};
  const keys = Object.keys(TERMS).filter((k) => /[A-Za-z]/.test(k)).sort((a, b) => b.length - a.length)
    .map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  termRe = keys.length ? new RegExp(`(?<![A-Za-z])(${keys.join("|")})(?![A-Za-z])`, "g") : null;
}

/** Translate a UI template; placeholder values are passed through tx(). */
export function t(s, vars) {
  let out = (LANG !== "en" && UI[s]) || s;
  if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (vars[k] === undefined || vars[k] === null ? "" : tx(String(vars[k]))));
  return out;
}

/** Translate a data value: exact UI/term match, else replace known terms inside it. */
export function tx(s) {
  if (LANG === "en" || s === null || s === undefined) return s;
  const str = String(s);
  if (UI[str]) return UI[str];
  if (TERMS[str]) return TERMS[str];
  if (!termRe || !/[A-Za-z]/.test(str)) return str;
  return str.replace(termRe, (m) => TERMS[m] || m);
}

function translateText(raw, inSvg) {
  const lead = raw.match(/^\s*/)[0], trail = raw.match(/\s*$/)[0];
  const core = raw.trim();
  if (!core || !/[A-Za-z]/.test(core)) return raw;
  if (inSvg && CHART[core]) return lead + CHART[core] + trail;
  const out = UI[core] || TERMS[core] || (termRe ? core.replace(termRe, (m) => TERMS[m] || m) : core);
  return lead + out + trail;
}

const ATTRS = ["placeholder", "title", "aria-label"];
const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA"]);

export function translateTree(root) {
  if (LANG === "en" || !root) return;
  const walk = (node, inSvg) => {
    if (node.nodeType === 3) {
      const v = translateText(node.data, inSvg);
      if (v !== node.data) node.data = v;
      return;
    }
    if (node.nodeType !== 1 || SKIP.has(node.tagName) || node.classList?.contains("no-tr")) return;
    const svg = inSvg || node.tagName.toLowerCase() === "svg";
    for (const a of ATTRS) {
      const v = node.getAttribute && node.getAttribute(a);
      if (v) { const nv = translateText(v, false); if (nv !== v) node.setAttribute(a, nv); }
    }
    if (node.tagName === "TITLE" && svg) { node.textContent = translateText(node.textContent, false); return; }
    node.childNodes.forEach((c) => walk(c, svg));
  };
  walk(root, root.closest ? !!root.closest("svg") : false);
}

let observer = null;
/** Keep translating whatever gets added to the page (lazy tabs, dropdowns, saved list). */
export function watch(root = document.body) {
  if (observer) observer.disconnect();
  if (LANG === "en") return;
  observer = new MutationObserver((muts) => {
    for (const m of muts) m.addedNodes.forEach((n) => translateTree(n.nodeType === 3 ? n.parentNode : n));
  });
  observer.observe(root, { childList: true, subtree: true });
}

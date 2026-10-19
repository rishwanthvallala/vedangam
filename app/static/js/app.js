// Form handling, place search, saved charts, API calls.
import { h } from "./ui.js";
import { renderResult } from "./render.js";
import { LANG, setLang, t, translateTree, watch } from "./i18n.js";
import { apiFetch, MODE, onEngineStatus } from "./api.js";

const $ = (id) => document.getElementById(id);
const METHODS = [
  { id: "parashara", name: "Parashari", desc: "Classical Vedic: vargas, Shadbala, Ashtakavarga, yogas, Vimshottari" },
  { id: "kp", name: "KP Stellar", desc: "Krishnamurti Paddhati: sub lords, significators, event timing" },
  { id: "kp_horary", name: "KP Horary", desc: "Number 1–249 question chart with ruling planets" },
  { id: "prashna", name: "Prashna Shastra", desc: "Vedic horary per Prashna Marga and Tajika" },
  { id: "jaimini", name: "Jaimini", desc: "Chara karakas, arudhas, rashi drishti, Chara dasha" },
  { id: "paschatya", name: "Paschatya", desc: "Western methods on the Sayana zodiac with an Indian chart view" },
  { id: "western", name: "Western", desc: "Tropical wheel, aspects, dignities, transits, progressions" },
  { id: "varshaphal", name: "Varshaphal", desc: "Tajika annual chart: Muntha, year lord, Sahams, Mudda dasha, Tithi Pravesha" },
  { id: "matching", name: "Marriage matching", desc: "Ashtakoota guna milan, 10 poruthams and Kuja dosha for two charts" },
  { id: "muhurta", name: "Muhurta", desc: "Find auspicious dates and times for an event" },
  { id: "calendar", name: "Panchanga calendar", desc: "Monthly panchanga with festivals and Rahu kaal" },
];
const NO_BIRTH = new Set(["calendar"]);   // methods that don't need a birth date/time
const QUERY_METHODS = new Set(["kp_horary", "prashna"]);
const state = { place: null, method: "parashara", last: null, meta: null };

// ------------------------------------------------------------ theme
function applyTheme(theme) {
  if (theme) document.documentElement.setAttribute("data-theme", theme);
  else document.documentElement.removeAttribute("data-theme");
  const dark = theme === "dark" || (!theme && matchMedia("(prefers-color-scheme: dark)").matches);
  $("themeToggle").textContent = t(dark ? "Light mode" : "Dark mode");
}
try { applyTheme(localStorage.getItem("js.theme")); } catch (_) { applyTheme(null); }
$("themeToggle").addEventListener("click", () => {
  const dark = document.documentElement.getAttribute("data-theme") === "dark" ||
    (!document.documentElement.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
  const next = dark ? "light" : "dark";
  try { localStorage.setItem("js.theme", next); } catch (_) { /* ignore */ }
  applyTheme(next);
});

// ------------------------------------------------------------ methods
const list = $("methodList");
for (const m of METHODS) {
  list.appendChild(h("label", { class: "method" },
    h("input", { type: "radio", name: "method", value: m.id, checked: m.id === state.method || null }),
    h("b", {}, m.name), h("small", {}, m.desc)));
}
list.addEventListener("change", (e) => setMethod(e.target.value));

function setMethod(m) {
  const wasQuery = QUERY_METHODS.has(state.method);
  state.method = m;
  const q = QUERY_METHODS.has(m);
  // Horary/Prashna are judged for the moment of the question: keep the birth date/time aside
  if (q && !wasQuery) {
    state.birthDT = { date: $("f_date").value, time: $("f_time").value };
    setNow();
  } else if (!q && wasQuery && state.birthDT) {
    $("f_date").value = state.birthDT.date;
    $("f_time").value = state.birthDT.time;
  }
  document.querySelectorAll(".method-extra").forEach((f) => f.classList.toggle("on", f.dataset.for === m));
  $("detailsLegend").textContent = t(q ? "Query details" : "Birth details");
  $("dateLabel").textContent = t(q ? "Date of query" : "Date of birth");
  $("timeLabel").textContent = t(q ? "Time of query" : "Time of birth");
  $("placeLabel").textContent = t(q ? "Place of query" : ["muhurta", "calendar"].includes(m) ? "Place" : "Place of birth");
  if (m === "calendar") $("detailsLegend").textContent = t("Place");
  $("setNow").classList.toggle("hidden", !q);
  document.querySelectorAll(".birth-only").forEach((el) => el.classList.toggle("hidden", NO_BIRTH.has(m)));
  $("castBtn").textContent = t(q ? "Judge the question" : m === "muhurta" ? "Find muhurtas" : m === "calendar" ? "Show calendar" : m === "matching" ? "Match charts" : "Cast chart");
  const d = new Date(), pad = (n) => String(n).padStart(2, "0");
  if (m === "muhurta" && !$("m_start").value) $("m_start").value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  if (m === "calendar" && !$("c_month").value) $("c_month").value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
  if (m === "varshaphal" && !$("f_vyear").value) $("f_vyear").value = d.getFullYear();
}

function setNow() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  $("f_date").value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  $("f_time").value = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
$("setNow").addEventListener("click", setNow);
$("randomHorary").addEventListener("click", () => { $("f_horary").value = 1 + Math.floor(Math.random() * 249); });
$("f_useOffset").addEventListener("change", (e) => { $("f_offset").disabled = !e.target.checked; });

// ------------------------------------------------------------ meta (selects)
apiFetch("/api/meta").then((r) => r.json()).then((meta) => {
  state.meta = meta;
  const add = (sel, obj) => { for (const [k, v] of Object.entries(obj)) sel.appendChild(h("option", { value: k }, v)); };
  add($("o_ayanamsa"), meta.ayanamsas);
  add($("f_hq"), meta.kp_events);
  add($("f_pq"), meta.prashna_questions);
  if (meta.muhurta_events) add($("m_event"), meta.muhurta_events);
  for (const p of ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]) $("s_planet").appendChild(h("option", { value: p }, p));
  translateTree($("birthForm")); translateTree($("savedBox"));
  const hs = $("o_hsys");
  for (const [k, v] of Object.entries(meta.house_systems)) if (k !== "S") hs.appendChild(h("option", { value: k }, v));
  restoreForm();
});

// ------------------------------------------------------------ place search
/** Autocomplete for a place input; onChoose(r) receives {label, lat, lon, tz}. */
function placeWidget(input, pl, onChoose) {
  let timer = null, active = -1, results = [];
  const mark = () => {
    [...pl.children].forEach((li, i) => li.setAttribute("aria-selected", i === active ? "true" : "false"));
    if (active >= 0) input.setAttribute("aria-activedescendant", `${pl.id}-${active}`);
  };
  const close = () => { pl.hidden = true; input.setAttribute("aria-expanded", "false"); };
  const choose = (r) => { if (!r) return; input.value = r.label; onChoose(r); close(); };
  const show = () => {
    pl.replaceChildren();
    active = results.length ? 0 : -1;
    if (!results.length) pl.appendChild(h("li", { "aria-disabled": "true" }, t("No matching city. Enter coordinates under ‘Edit coordinates and time zone’.")));
    results.forEach((r, i) => pl.appendChild(h("li", { role: "option", id: `${pl.id}-${i}`, class: "no-tr", onmousedown: (e) => { e.preventDefault(); choose(r); } },
      r.name, h("small", {}, `${[r.admin, r.country].filter(Boolean).join(", ")}; ${r.lat.toFixed(2)}, ${r.lon.toFixed(2)}; ${r.tz}`))));
    pl.hidden = false;
    input.setAttribute("aria-expanded", "true");
    mark();
  };
  input.addEventListener("input", () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { close(); return; }
    timer = setTimeout(async () => {
      try { results = await (await apiFetch(`/api/places?q=${encodeURIComponent(q)}`)).json(); } catch (_) { results = []; }
      show();
    }, 160);
  });
  input.addEventListener("keydown", (e) => {
    if (pl.hidden) return;
    if (e.key === "ArrowDown") { active = Math.min(active + 1, results.length - 1); mark(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { active = Math.max(active - 1, 0); mark(); e.preventDefault(); }
    else if (e.key === "Enter" && active >= 0) { choose(results[active]); e.preventDefault(); }
    else if (e.key === "Escape") close();
  });
  input.addEventListener("blur", () => setTimeout(close, 150));
}

const input = $("f_place");
placeWidget(input, $("placeList"), (r) => {
  state.place = { label: r.label, lat: r.lat, lon: r.lon, tz: r.tz };
  $("f_lat").value = r.lat; $("f_lon").value = r.lon; $("f_tz").value = r.tz;
  updateGeoLine();
  loadSkyNow();
});
placeWidget($("p_place"), $("pList"), (r) => {
  state.partnerPlace = { label: r.label, lat: r.lat, lon: r.lon, tz: r.tz };
  $("pGeo").textContent = `${r.lat.toFixed(4)}°, ${r.lon.toFixed(4)}°, ${r.tz}`;
});
placeWidget($("f_res"), $("resList"), (r) => { state.residence = { label: r.label, lat: r.lat, lon: r.lon, tz: r.tz }; });
$("f_res").addEventListener("input", () => { if (!$("f_res").value.trim()) state.residence = null; });

function updateGeoLine() {
  const lat = parseFloat($("f_lat").value), lon = parseFloat($("f_lon").value), tz = $("f_tz").value;
  if (isNaN(lat) || isNaN(lon)) { $("geoLine").textContent = t("No place selected"); return; }
  const f = (v, p, n) => `${Math.abs(v).toFixed(4)}°${v >= 0 ? p : n}`;
  $("geoLine").textContent = `${f(lat, "N", "S")}, ${f(lon, "E", "W")}${tz ? `, ${tz}` : ""}`;
}
["f_lat", "f_lon", "f_tz"].forEach((id) => $(id).addEventListener("input", updateGeoLine));

// ------------------------------------------------------------ request
function collect() {
  const lat = parseFloat($("f_lat").value), lon = parseFloat($("f_lon").value);
  const tz = $("f_tz").value.trim() || null;
  const useOff = $("f_useOffset").checked;
  const offset = useOff ? parseFloat($("f_offset").value) : null;
  const err = [];
  if (!NO_BIRTH.has(state.method) && !$("f_date").value) err.push(t("Enter a date."));
  if (!NO_BIRTH.has(state.method) && !$("f_time").value) err.push(t("Enter a time."));
  if (isNaN(lat) || isNaN(lon)) err.push(t("Choose a place from the list, or enter latitude and longitude."));
  if (!tz && (offset === null || isNaN(offset))) err.push(t("Choose a place so the time zone is known, or override the UTC offset."));
  const m = state.method;
  const options = {
    ayanamsa: $("o_ayanamsa").value || undefined,
    node: $("o_node").value || undefined,
    year_days: parseFloat($("o_year").value),
    sunrise: $("o_sunrise").value, karakas: parseInt($("o_karakas").value, 10),
    hsys: $("o_hsys").value || "P", zodiac: $("o_zodiac").value, minor: $("o_minor").checked,
    rotate: parseInt($("o_rotate").value, 10) || 1, rectify_window: parseInt($("o_rectify").value, 10) || 60,
  };
  if (m === "paschatya") options.zodiac = "tropical";
  const body = {
    name: $("f_name").value.trim(), gender: $("f_gender").value,
    date: $("f_date").value || new Date().toISOString().slice(0, 10), time: $("f_time").value || "12:00:00",
    place: { label: input.value.trim(), lat, lon, tz }, offset: useOff ? offset : null,
    method: m, options, lang: LANG,
  };
  if (m === "kp_horary") {
    const n = parseInt($("f_horary").value, 10);
    if (!(n >= 1 && n <= 249)) err.push(t("Horary number must be between 1 and 249."));
    body.horary_number = n; body.question = $("f_hq").value;
  }
  if (m === "prashna") {
    body.question = $("f_pq").value;
    const n = parseInt($("f_pnum").value, 10);
    body.prashna_number = n >= 1 && n <= 108 ? n : null;
  }
  if (m === "varshaphal") {
    body.year = parseInt($("f_vyear").value, 10) || new Date().getFullYear();
    if (state.residence) body.residence = state.residence;
  }
  if (m === "matching") {
    const pp = state.partnerPlace;
    if (!$("p_date").value || !$("p_time").value || !pp) err.push(t("Enter the partner's date, time and place of birth."));
    else body.partner = { name: $("p_name").value.trim(), gender: $("p_gender").value, date: $("p_date").value, time: $("p_time").value, place: pp };
  }
  if (m === "muhurta") {
    body.muhurta = { event: $("m_event").value, start_date: $("m_start").value, days: parseInt($("m_days").value, 10) || 30, use_native: $("m_native").checked };
  }
  if (m === "calendar") {
    const [yy, mm] = ($("c_month").value || "").split("-").map(Number);
    body.calendar = { year: yy || new Date().getFullYear(), month: mm || new Date().getMonth() + 1 };
  }
  return { body, err };
}

$("birthForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const { body, err } = collect();
  const fe = $("formError");
  if (err.length) { fe.textContent = err.join(" "); fe.hidden = false; return; }
  fe.hidden = true;
  persistForm();
  await cast(body);
});

async function cast(body) {
  body = { ...body, lang: LANG };
  state.lastBody = body;
  try { sessionStorage.setItem("js.lastBody", JSON.stringify(body)); } catch (_) { /* ignore */ }
  const out = $("output");
  $("emptyState").hidden = true;
  out.hidden = false;
  out.replaceChildren(document.getElementById("tplLoading").content.cloneNode(true));
  try {
    const r = await apiFetch("/api/chart", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || t("The calculation failed."));
    state.last = data;
    const node = renderResult(data, { style: $("o_style").value, onAction, ctx: CTX });
    out.replaceChildren(node);
    if (matchMedia("(max-width: 900px)").matches) out.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (ex) {
    out.replaceChildren(h("div", { class: "empty" }, h("h2", {}, t("Chart could not be calculated")),
      h("p", {}, String(ex.message || ex)), h("p", {}, t("Check the date, time and coordinates, then cast again."))));
  }
}

const CTX = {
  /** POST the last chart request plus `extra` to a feature endpoint. */
  async post(url, extra = {}) {
    const r = await apiFetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...state.lastBody, ...extra, lang: LANG }) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || t("The calculation failed."));
    return d;
  },
};

function shiftTime(minutes) {
  const d = new Date(`${$("f_date").value}T${$("f_time").value.length === 5 ? $("f_time").value + ":00" : $("f_time").value}`);
  if (isNaN(d)) return;
  d.setMinutes(d.getMinutes() + minutes);
  const pad = (n) => String(n).padStart(2, "0");
  $("f_date").value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  $("f_time").value = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  $("birthForm").requestSubmit();
}

async function onAction(kind, payload) {
  if (kind === "shift") { shiftTime(payload); return null; }
  if (kind === "custom") {
    // Re-run the KP chart with a user-defined event and return just that verdict
    const body = { ...state.lastBody, options: { ...state.lastBody.options, custom_event: payload } };
    const r = await apiFetch("/api/chart", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || t("The calculation failed."));
    return data.custom_event;
  }
  if (kind === "print") {
    const node = $("output").firstElementChild;
    if (node && node.renderAll) node.renderAll();
    setTimeout(() => window.print(), 50);
  } else if (kind === "json" && state.last) {
    const blob = new Blob([JSON.stringify(state.last, null, 1)], { type: "application/json" });
    const a = h("a", { href: URL.createObjectURL(blob), download: `${(state.last.birth.name || "chart").replace(/\s+/g, "_")}_${state.last.method}.json` });
    document.body.appendChild(a); a.click(); a.remove();
  }
}

// ------------------------------------------------------------ persistence
const FIELDS = ["f_name", "f_gender", "f_date", "f_time", "f_place", "f_lat", "f_lon", "f_tz", "f_offset", "f_horary",
  "o_ayanamsa", "o_node", "o_year", "o_sunrise", "o_karakas", "o_hsys", "o_zodiac", "o_rotate", "o_rectify",
  "p_name", "p_gender", "p_date", "p_time", "p_place", "f_res", "m_event", "m_days"];
function snapshot() {
  const s = Object.fromEntries(FIELDS.map((f) => [f, $(f).value]));
  s.f_useOffset = $("f_useOffset").checked; s.o_minor = $("o_minor").checked; s.method = state.method;
  s.partnerPlace = state.partnerPlace || null; s.residence = state.residence || null;
  return s;
}
function apply(s) {
  for (const f of FIELDS) if (s[f] !== undefined && $(f)) $(f).value = s[f];
  $("f_useOffset").checked = !!s.f_useOffset; $("f_offset").disabled = !s.f_useOffset;
  if (s.o_minor !== undefined) $("o_minor").checked = s.o_minor;
  if (s.partnerPlace) { state.partnerPlace = s.partnerPlace; $("pGeo").textContent = `${s.partnerPlace.lat.toFixed(4)}°, ${s.partnerPlace.lon.toFixed(4)}°, ${s.partnerPlace.tz}`; }
  if (s.residence) state.residence = s.residence;
  if (s.method) {
    const r = document.querySelector(`input[name=method][value="${s.method}"]`);
    if (r) { r.checked = true; setMethod(s.method); }
  }
  updateGeoLine();
}
function persistForm() { try { localStorage.setItem("js.form.v2", JSON.stringify(snapshot())); } catch (_) { /* ignore */ } }
function restoreForm() {
  try { const s = JSON.parse(localStorage.getItem("js.form.v2") || "null"); if (s) apply(s); } catch (_) { /* ignore */ }
  try { const st = localStorage.getItem("js.style"); if (st) $("o_style").value = st; } catch (_) { /* ignore */ }
  renderSaved();
}
$("o_style").addEventListener("change", () => {
  try { localStorage.setItem("js.style", $("o_style").value); } catch (_) { /* ignore */ }
  if (state.last) $("output").replaceChildren(renderResult(state.last, { style: $("o_style").value, onAction, ctx: CTX }));
});

function getSaved() { try { return JSON.parse(localStorage.getItem("js.saved") || "[]"); } catch (_) { return []; } }
function setSaved(v) { try { localStorage.setItem("js.saved", JSON.stringify(v)); } catch (_) { /* ignore */ } }
$("saveBtn").addEventListener("click", () => {
  const s = snapshot();
  if (!s.f_date || !s.f_lat) { $("formError").textContent = t("Fill in the date and place before saving."); $("formError").hidden = false; return; }
  const all = getSaved().filter((x) => !(x.f_name === s.f_name && x.f_date === s.f_date && x.f_time === s.f_time));
  all.unshift(s);
  setSaved(all.slice(0, 40));
  renderSaved();
  $("saveBtn").textContent = t("Saved");
  setTimeout(() => { $("saveBtn").textContent = t("Save"); }, 1400);
});
function renderSaved() {
  const all = getSaved();
  $("savedBox").hidden = !all.length;
  $("savedList").replaceChildren(...all.map((s, i) => h("li", {},
    h("button", { type: "button", class: "no-tr", onclick: () => { apply(s); $("birthForm").requestSubmit(); } },
      s.f_name || t("Unnamed"), h("small", {}, `${s.f_date} ${s.f_time}, ${(s.f_place || "").split(",")[0]}`)),
    h("button", { type: "button", class: "del", "aria-label": `Remove ${s.f_name || "chart"}`, onclick: () => { const a = getSaved(); a.splice(i, 1); setSaved(a); renderSaved(); } }, "Remove"))));
}

// ------------------------------------------------------------ home: sky right now
async function loadSkyNow() {
  const box = $("skyNow");
  if (!box || !$("emptyState") || $("emptyState").hidden) return;
  const lat = parseFloat($("f_lat").value), lon = parseFloat($("f_lon").value), tz = $("f_tz").value.trim();
  const q = !isNaN(lat) && !isNaN(lon) && tz ? `?lat=${lat}&lon=${lon}&tz=${encodeURIComponent(tz)}&label=${encodeURIComponent(input.value)}&lang=${LANG}` : `?lang=${LANG}&label=Hyderabad`;
  try {
    const d = await (await apiFetch(`/api/now${q}`)).json();
    const p = d.panchang;
    box.replaceChildren(h("h3", {}, t("The sky right now")),
      h("p", { class: "sub" }, `${d.local}, ${d.place || "Hyderabad"}. ${t("Lagna")} ${d.lagna}; ${p.tithi}, ${p.nakshatra}, ${p.yoga}, ${p.vara}.`),
      h("div", { class: "tw" }, h("table", {}, h("thead", {}, h("tr", {}, ["Planet", "Sign", "Longitude", "Nakshatra"].map((x) => h("th", {}, x)))),
        h("tbody", {}, d.planets.map((r) => h("tr", {}, h("td", {}, r.planet, r.retro ? h("span", { class: "r" }, "R") : null), h("td", {}, r.sign), h("td", { class: "num" }, r.dms), h("td", {}, `${r.nakshatra} ${r.pada}`)))))));
  } catch (_) { /* offline: leave the intro alone */ }
}

// ------------------------------------------------------------ search saved charts
const SEARCH_VALUES = {
  planet_sign: ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"],
  lagna: ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"],
  planet_house: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
  dignity: ["Exalted", "Debilitated", "Moolatrikona", "Own", "Great Friend", "Friend", "Neutral", "Enemy", "Great Enemy"],
  dasha_now: ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"],
  yoga: ["Gaja Kesari", "Raja Yoga", "Dhana Yoga", "Budha-Aditya", "Neecha Bhanga", "Kaal Sarp", "Mangal", "Hamsa", "Malavya", "Ruchaka", "Bhadra", "Sasa", "Lakshmi", "Saraswati", "Kemadruma", "Parivartana", "Viparita"],
  moon_nakshatra: ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"],
};
function updateSearchForm() {
  const k = $("s_kind").value;
  $("s_planet_l").classList.toggle("hidden", !["planet_sign", "planet_house", "dignity"].includes(k));
  $("s_values").replaceChildren(...(SEARCH_VALUES[k] || []).map((v) => h("option", { value: v })));
}
$("s_kind").addEventListener("change", updateSearchForm);
updateSearchForm();
$("s_go").addEventListener("click", async () => {
  const saved = getSaved();
  const charts = saved.filter((x) => x.f_date && x.f_lat).map((x) => ({ name: x.f_name, gender: x.f_gender, date: x.f_date, time: x.f_time || "12:00:00",
    place: { label: x.f_place, lat: parseFloat(x.f_lat), lon: parseFloat(x.f_lon), tz: x.f_tz || null }, offset: x.f_useOffset ? parseFloat(x.f_offset) : null }));
  const out = $("s_results");
  out.replaceChildren(h("li", {}, t("Searching…")));
  try {
    const r = await apiFetch("/api/search", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ charts, kind: $("s_kind").value, planet: $("s_planet").value, value: $("s_value").value, lang: LANG }) });
    const d = await r.json();
    const hits = d.results.filter((x) => x.match);
    out.replaceChildren(h("li", {}, t("{n} of {m} saved charts match.", { n: hits.length, m: d.results.length })),
      ...hits.map((x) => h("li", {}, h("span", { class: "no-tr" }, x.name || t("Unnamed")), h("small", {}, `${x.date}; ${x.detail}`))));
  } catch (e) { out.replaceChildren(h("li", {}, String(e.message || e))); }
});

// ------------------------------------------------------------ logo
$("o_logo").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) return;
  if (f.size > 400000) { $("formError").textContent = t("Choose an image smaller than 400 KB."); $("formError").hidden = false; return; }
  const rd = new FileReader();
  rd.onload = () => { try { localStorage.setItem("js.logo", rd.result); } catch (_) { /* ignore */ } };
  rd.readAsDataURL(f);
});
$("o_logo_clear").addEventListener("click", () => { try { localStorage.removeItem("js.logo"); } catch (_) { /* ignore */ } });

// ------------------------------------------------------------ language
async function initLang() {
  let lang = "en";
  try { lang = localStorage.getItem("js.lang") || "en"; } catch (_) { /* ignore */ }
  await setLang(lang);
  document.querySelectorAll(".lang-switch button").forEach((b) => {
    b.setAttribute("aria-pressed", b.dataset.lang === LANG ? "true" : "false");
    b.addEventListener("click", () => {
      if (b.dataset.lang === LANG) return;
      try { localStorage.setItem("js.lang", b.dataset.lang); } catch (_) { /* ignore */ }
      location.reload();  // re-renders the form and the open chart in the new language
    });
  });
  translateTree(document.body);
  watch(document.body);
  loadSkyNow();
}

$("privacyNote").hidden = MODE !== "browser";

// in-browser engine: show loading progress on the first visit
onEngineStatus((st) => {
  const bar = $("engineBar");
  if (MODE !== "browser" || st.state === "ready") { bar.hidden = true; return; }
  bar.hidden = false;
  bar.classList.toggle("error", st.state === "error");
  bar.replaceChildren(st.state === "error"
    ? h("span", {}, t("The calculation engine could not start: {e}. Reload the page to try again.", { e: st.message || "" }))
    : h("span", {}, h("b", {}, t("Preparing the calculation engine…")), " ",
        t("Step {n} of 4: {s}.", { n: st.step || 1, s: t(st.message || "Downloading the calculation engine") }), " ",
        h("small", {}, t("This happens once; later visits start instantly and work offline."))));
});

setMethod(state.method);
initLang().then(() => {
  try {
    const body = JSON.parse(sessionStorage.getItem("js.lastBody") || "null");
    if (body) cast(body);
  } catch (_) { /* ignore */ }
});

# Jyotish Studio

A local web app that casts charts and produces in-depth analysis for seven methods:
**Parashari, KP Stellar, KP Horary, Prashna Shastra, Jaimini, Paschatya and Western**.

Positions come from the **Swiss Ephemeris** (`pyswisseph` with the `.se1` data files). It is
the same engine used by Jagannatha Hora, Astrodienst and most professional KP software.

## Run

Jyotish Studio runs **entirely in the browser**. The same Python engine is executed by
[Pyodide](https://pyodide.org) (Python compiled to WebAssembly) in a background Web Worker, with
the Swiss Ephemeris compiled to WebAssembly too. No server is needed.

```bash
tools/preview_static.sh      # build dist/ and serve it at http://localhost:8080
```

The first visit downloads about 10 MB: the Python runtime, the ephemeris, the engine and the city
list. A service worker caches it, so later visits start in about a second and work offline.

Optional server mode, which is handy while developing:

```bash
./run.sh            # FastAPI at http://127.0.0.1:8000 (creates .venv on first run)
```

Both modes run the same code (`app/api.py`), so they produce the same results.

## Hosting on GitHub Pages (no backend)

Live site: **https://rishwanthvallala.github.io/vedangam/**

Every push to `main` runs `.github/workflows/pages.yml`, which:
1. builds the static site (`python tools/build_static.py` → `dist/`),
2. runs the 377-case check against the native engine (it stops here if anything differs), and
3. publishes `dist/` to GitHub Pages.

One-time setup: in the repository on GitHub, open **Settings → Pages** and set **Source** to
**GitHub Actions**.

The same `dist/` folder also works on any other static host if you ever need one.

## Correctness of the browser build

`tools/verify_static.sh` builds the site and runs **377 golden cases** through both the native
engine and the in-browser (WebAssembly) engine, then compares every field of the output. The
cases cover every method and endpoint, both languages, alternative settings, births from 1850
to 2049, polar latitudes, both hemispheres, DST and war-time offsets, and a frozen clock for
transits and running dashas. Current result: **all 377 agree within 0.036 arc-seconds, and 349
are bit-for-bit identical.** The rest differ only in the 6th decimal of a degree, from
floating-point rounding in the WebAssembly math library. The GitHub Pages workflow refuses to
deploy if this check fails.

The WebAssembly Swiss Ephemeris wheel is committed in `vendor/wheels/`.
`tools/build_pyswisseph_wasm.sh` rebuilds it, which is only needed when upgrading Pyodide.

## What each method gives you

| Method | Output |
|---|---|
| **Parashari** | Rasi, Navamsa, Chandra lagna and Bhava chalit charts; full planet table (nakshatra, pada, dignity, combustion, speed, declination); avasthas; special lagnas (Bhava, Hora, Ghati, Indu, Sree), Gulika/Mandi and the aprakasha grahas; all 16 vargas + Vimshopaka; bhava table; graha drishti; Panchadha maitri; **Shadbala** (all sub-components, Ishta/Kashta) and **Bhava bala**; **Ashtakavarga** (BAV, SAV, Trikona/Ekadhipatya shodhana, Shodhya pinda); ~60 yogas and doshas (Mahapurusha, Raja, Dhana, Viparita, Neecha bhanga, Parivartana, Nabhasa, Kemadruma, Kuja dosha, Kaal Sarp…); **Vimshottari** to 3 levels with the running chain to Prana, Yogini and **Ashtottari** (with its BPHS applicability rule); Beeja/Kshetra sphuta; Gochara and lifetime **Sade Sati** dates; panchanga with tithi/nakshatra end times, masa, samvatsara, Rahu kaal and Avakahada chakra; a written reading (lagna, rashi, nakshatra, planets in houses and signs, all 12 house lords, running dasha). |
| **KP Stellar** | KP ayanamsa and Placidus cusps; sign, star, sub and sub-sub lords for planets, cusps and Pars Fortuna; Rasi and cuspal charts; four-level significators (planet-wise A–D and house-wise L1–L4, with node agency); **four-step theory**; ruling planets now and at birth; cuspal sub-lord verdicts for 21 life matters with **Dasha–Bhukti timing and best antaras**; a **custom event** builder (main cusp plus favourable and negating houses); **ruling-planet birth-time rectification**; **house rotation** (e.g. 7th as 1st for the spouse); Vimshottari and **Ashtottari** dashas; the 249 sub table. |
| **KP Horary** | Number 1–249 fixes the ascendant at the start of that sub, and the other cusps are Placidus for the place of judgment. Shows planets at judgment, significators, ruling planets and their agreement with significators, the **reflection-of-mind** check, the verdict for the chosen matter, the querent's Moon, and timing. |
| **Prashna Shastra** | Prashna Marga and Tajika: rising-sign type (Shirshodaya and the others), lagna lord and karya lord strength, Ithasala/Ishrafa, Moon, benefic/malefic distribution, panchanga at query, Arudha from a number 1–108, Trisphuta/Chatussphuta/Panchasphuta, lost-article direction, and a weighted verdict with every factor listed. |
| **Jaimini** | 7 or 8 chara karakas, Karakamsha and Swamsha, Arudha padas (A1–A12, with dual-lordship rules), Hora/Ghati/Bhava lagnas, rashi drishti, argala on Lagna and AL, **Chara dasha (K.N. Rao)** with antardashas, Jaimini raja yogas and a written reading. |
| **Western** | Tropical wheel, Placidus or any of 10 house systems, essential dignities (domicile, exaltation, triplicity, Egyptian terms, faces, peregrine), major and minor aspects with applying/separating, aspect grid, patterns (Grand Trine, T-square, Grand Cross, Yod, Kite, Mystic Rectangle, stelliums), element/modality/hemisphere balance, chart shape, Moon phase, Part of Fortune, Vertex, Lilith, Chiron, transits, secondary progressions with solar arc angles, solar return, and a written reading. |
| **Paschatya** | The Western engine on the Sayana zodiac, plus a kundali-style Sayana chart and Sayana nakshatras. |
| **Varshaphal** | Tajika annual chart: Varsha Pravesha, Muntha, the five office-bearers, Pancha-vargiya bala, year lord, Tajika aspects and yogas, Sahams, Mudda and Patyayini dashas, plus the Tithi Pravesha chart. An optional current residence gives the local chart. |
| **Marriage matching** | Ashtakoota guna milan (36 points, with the classical exceptions), South Indian Dashakoota (10 poruthams with Rajju and Vedha) and a Kuja dosha comparison. |
| **Muhurta** | Searches up to 90 days for auspicious windows for marriage, griha pravesha, vehicle, travel, business, education, property, naming, medical or general events. Uses Tara and Chandra bala when your birth details are given. |
| **Panchanga calendar** | A month of daily panchanga at sunrise, with tithi and nakshatra end times, Rahu kaal and special days (Ekadashi, Pradosha, Purnima, Amavasya, Sankranti…). |

**Also added, in the style of Parashara's Light 9.0:**
- Parashari **Chakras** tab: Sarvatobhadra (with vedha), Kota, Sanghatta, Sudarshan (with Sudarshana dasha) and Ghata chakra.
- **Annual charts** tab: Tithi Pravesha for any year, and Dasha Pravesh charts for the running periods.
- **Transits**: an animated year-ahead transit chart, a year-at-a-glance sign timeline, an Ashtakavarga transit-strength heatmap, and an ingress/station table.
- **Dasha calendar**: every Vimshottari change in a month, down to Sookshma.
- **Extra vargas**: D5, D6, D8, D11, D81, D108 (Ashtottaramsa), D144, D150. Bhrigu Bindu, planetary magnitudes, Pushkar navamsha/bhaga flags, and ages on every dasha period.
- **Jaimini**: a Lagna-footed Chara dasha variant and Padanadhamsa dasha.
- **Workflow**: a ±1 minute/5 minutes/1 hour/1 day time toolbar that recasts instantly, notes per chart, search across saved charts by yoga, placement, dignity, nakshatra or running dasha, a "sky right now" home screen, a drag-and-drop worksheet that can be your home tab, your own logo on screen and print, and A4, book (A5) or pocket (A6) printing.

## Telugu (తెలుగు)

Use the **English / తెలుగు** switch at the top of the page. In Telugu mode, everything is shown
in Telugu: the form, every table heading and value (planets, signs, nakshatras, tithis, dignities…),
chart labels (రవి, చం, కు …), the sentences the engine generates (yogas, KP verdicts, Prashna
factors) and the full interpretation library. The choice is remembered, and switching re-renders
the open chart.

- Interpretation texts: `app/interpret/data/te/*.json` (same keys as the English files; anything
  missing falls back to English)
- Interface, generated sentences and terms: `app/i18n/te.json`; chart abbreviations:
  `app/i18n/te_chart.json`

## Defaults, and how they match common software

| Setting | Default | Notes |
|---|---|---|
| Ayanamsa | Lahiri (Parashari, Jaimini, Prashna); Krishnamurti (KP) | Change it under Calculation settings: KP New VP291, Raman, True Chitra, True Pushya, Yukteshwar, Fagan-Bradley… |
| Rahu/Ketu | Mean node (Vedic), true node (Western) | Selectable |
| Dasha year | 365.25 days | 365.2425, 365.2564 and 360 are selectable |
| Sunrise | Upper limb with refraction | "Disc centre, no refraction" matches some traditional panchangas |
| Vedic houses | Whole sign + Sripati bhava chalit; KP uses Placidus | |
| Chart style | South Indian | North Indian under Calculation settings. Bhava and cuspal charts in South style place each planet in the sign of its house cusp, with cusp numbers marked H1–H12 |
| Time zone | IANA database, historical DST and war time applied (e.g. India 1942–45 = +6:30) | Use *Override UTC offset* for charts recorded in local mean time or pre-1947 city times (e.g. Calcutta time +5:53:20) |

Small differences from other programs usually come from these settings, especially the node type,
ayanamsa variant and dasha year length. Shadbala follows BPHS and B.V. Raman's *Graha and Bhava
Balas*. Programs disagree on minor conventions there (Moon's paksha bala doubling, chesta kendra
via mean longitudes, abda/masa lords), so expect totals within a few virupas rather than exact
agreement.

## How this compares with LOKPA (Light of KP Astrology)

LOKPA is commercial KP software, not a different system. It uses the Swiss Ephemeris, KP
ayanamsa and Placidus cusps, just like the KP mode here, so positions and sub lords should agree
for the same settings. The LOKPA-style tools added to the KP mode are the 4-step table, extended
event list with custom main/supporting/negating houses, RP rectification, reflection of mind,
Ashtottari, Pars Fortuna and house rotation. Not reproduced here: LOKPA's 3.5-step theory,
Theory of Short Prediction, transit-hit engine, KPDP/Ashtakoota matching, AstroDatabank and its
AI modules.

## Project layout

```
app/
  api.py                  every endpoint as plain functions; used by the server AND the browser
  main.py                 optional FastAPI wrapper around api.handle()
  static/js/api.js        browser transport: routes /api/* to the in-browser engine
  static/js/engine-worker.js  Web Worker that boots Pyodide and runs app/api.py
  core/
    ephemeris.py          Swiss Ephemeris wrapper (positions, houses, rise/set) — thread-safe
    chart.py              birth input + sidereal base chart
    geo.py                offline city search, historical time zones
    panchang.py           panchanga, special lagnas, Gulika, upagrahas
    vedic.py              dignity, relationships, aspects, avasthas
    vargas.py             16 divisional charts
    shadbala.py           Shadbala and Bhava bala
    ashtakavarga.py       BAV/SAV, reductions, pindas
    yogas.py              yogas, doshas, Sade Sati
    dasha.py              Vimshottari, Yogini
    kp.py                 sub lords, 249 table, significators, ruling planets, events, timing
    jaimini.py            karakas, arudhas, argala, Chara dasha
    prashna.py            Prashna Marga / Tajika analysis
    western.py            tropical astrology, transits, progressions, solar return
    methods.py            assembles each method's payload
  interpret/              text library (JSON) + reading assembly
  data/ephe/              Swiss Ephemeris files (1800–2400 CE)
  data/cities.tsv         GeoNames cities ≥ 5,000 population
  static/                 web UI (no build step)
tests/                  engine and module tests; tests/golden/ compares browser vs native
tools/build_static.py   builds the serverless site into dist/
vendor/wheels/          pyswisseph compiled to WebAssembly (+ tzdata)
```

Readings are traditional interpretive text keyed to chart factors. Treat them as guidance, not
certainty.

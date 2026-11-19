---
phase: 03-iana-timezones
plan: 04
type: summary
status: complete
description: "The other 26 multi-zone countries, Kosovo and the AN successors placed from zone1970 and tzdata; the tz gate on the seed build prints US lines only, and zone_regions.csv now maps every multi-zone country except US and AQ."
about: "aeronav-db"
tags: [timezone, iana, argentina, china, greenland, polynesia, crimea, uzbekistan]
relatedTo: [03-04-PLAN.md, 03-03-SUMMARY.md]
---

# 03-04 Summary: the other multi-zone countries

Checked by sqwkd 2026-11-19, verbatim: "sqwkd review of the 03-04 SUMMARY (2916455, code ef949cc): OK to unify after three fixes." The three fixes (Labuan, the TNCM count, the CY note wording) are applied below; the build was re-run.

## Build (AC-1, AC-7)
- **Inputs:** 2026-10-29 built from the seed (e92fa5fe…) with the tz4 inputs.
- **Output:** sha256 2418b7a5…, at scratchpad tz5/navigation.sqlite3.
- **`verify --previous`:** exits 0. All canaries pass, including the 25 new ones. Present 27,226: placed 26,425 (03-03: 24,894), unplaced 801.
- **`tz gate`:** exits 1, with only US lines left (03-05):

  ```
  present 27226, placed 26425, NULL 801
  FAIL item 1: US has 3 airports with multi_zone_country
  FAIL item 2: US has 63 scheduled airports unplaced and unlisted
  ```

- **Checks:** ruff clean; 178 tests pass.
- **AC-3a lint:** 678 municipality-placed airports. Five flags, the same five confirmed in 03-02; no new ones.

Columns: present, placed, NULL, then scheduled-service airports split into placed, unplaced_by_design, and unlisted.

| Country | Present | Placed | NULL | Scheduled placed | Scheduled UBD | Unlisted |
|---|---|---|---|---|---|---|
| AR | 108 | 108 | 0 | 46 | 0 | 0 |
| CD | 61 | 3 | 58 | 2 | 18 | 0 |
| CL | 52 | 52 | 0 | 19 | 0 | 0 |
| CN | 411 | 411 | 0 | 261 | 0 | 0 |
| CY | 5 | 3 | 2 | 3 | 0 | 0 |
| DE | 110 | 110 | 0 | 38 | 0 | 0 |
| EC | 29 | 29 | 0 | 15 | 0 | 0 |
| ES | 58 | 58 | 0 | 44 | 0 | 0 |
| FM | 5 | 5 | 0 | 4 | 0 | 0 |
| GL | 60 | 59 | 1 | 55 | 1 | 0 |
| KI | 21 | 21 | 0 | 4 | 0 | 0 |
| KZ | 35 | 34 | 1 | 23 | 1 | 0 |
| MH | 42 | 42 | 0 | 16 | 0 | 0 |
| MN | 25 | 21 | 4 | 11 | 2 | 0 |
| MY | 60 | 59 | 1 | 33 | 1 | 0 |
| NZ | 59 | 59 | 0 | 28 | 0 | 0 |
| PF | 51 | 13 | 38 | 11 | 27 | 0 |
| PG | 345 | 345 | 0 | 37 | 0 | 0 |
| PS | 1 | 1 | 0 | 0 | 0 | 0 |
| PT | 32 | 32 | 0 | 19 | 0 | 0 |
| UA | 45 | 45 | 0 | 0 | 0 | 0 |
| UZ | 17 | 17 | 0 | 13 | 0 | 0 |
| VN | 29 | 1 | 28 | 1 | 21 | 0 |
| XK | 1 | 1 | 0 | 1 | 0 | 0 |

TNCE and TNCM (NASR "AN") now place. Checked on tz5: placement_inputs gives BQ (BQ-SE) for TNCE and SX for TNCM, and both resolve on the country basis to America/Puerto_Rico. Identity's iso_country for both stays "AN" (AP0019780, AP0019781). That is an open Phase 1 issue, recorded in STATE.md. The draft's "count under BQ" was a misreading: the BQ row in the table covers two other airports. AQ stays NULL by design.

## AC results
| AC | Result |
|---|---|
| AC-1 gate | PASS (US lines only) |
| AC-2 zone_regions everywhere + R2 | PASS, with deviation D1 |
| AC-3 AN / XK | PASS |
| AC-4 region rules | PASS, with deviation D2 (UZ) |
| AC-5 named places | PASS |
| AC-6 CD / UZ / VN | PASS (CD and VN name-cited only; UZ per D2) |
| AC-7 checks | PASS; no independent check for any 03-04 country (Q2 of 03-03 is still the operator's) |

## AC-2
- zone_regions.csv maps all 26 countries. TF has no ISO 3166-2 subdivisions, so its rows are empty. Region codes are OurAirports' codes, matched to names via its regions.csv (hash in SOURCES).
- R2 is enforced verbatim. RU's empty Simferopol row is valid only because UA maps it (UA-43, UA-40). The tests show that a shared zone no other country maps still fails.
- Regions the check required as partial: CL-VS, CY-01/02/03, GL-NE, MN-057, MN-065, NZ-WGN and VN-NC. GL-SM was a stale code and became GL-SE.
- Two partial rows from 03-01, CY-01 and CY-04, were dropped. They used ISO's district numbering, but OurAirports' codes differ: its CY-04 is Larnaca (LCLK), south of the line. Larnaca now places by the CY-04 region rule.
- **D1 (sqwkd: option (a)):** US is exempt beside AQ (`ZONE_REGIONS_EXEMPT`). This deviates from AC-2's wording ("except AQ"). The reasons:
  - US is placed by the 03-01 county rules;
  - `_load_partial` already exempts US;
  - the US remainder is 03-05's scope.

  A test asserts the list is exactly {US, AQ}. **03-05's plan must decide whether US stays exempt** when the gate closes.

## Placements and rulings
- **CN (Q1):** CN-65 is partial. 34 Xinjiang airports → Asia/Shanghai by airport-keyed overrides. Each quotes "All planes, trains, and schools function on what is called 'Beijing time.'" and says Urumqi documents an unofficial local clock. Added to the README L4 list with distinct wording.
- **UZ (D2, sqwkd: accepted with conditions; replaces the Q2 "name-cited only" ruling):**
  - **Rules:**
    - AN, JI, NG, SI, TK, TO, FA → Tashkent;
    - BU, NW, QA, QR, SA, SU, XO → Samarkand.
  - **Each note quotes:**
    - the USSR 1991 transition list, as tzdata cites it from Izvestia No. 68, 1991-03-20;
    - tzdata's caveat "Apparently there were last minute changes." The changes it names are for Kazakhstan, Nenets, Komi and Kaliningrad, none for the Uzbek SSR;
    - the R1 reasoning: the 1991-03-31 step matches Tashkent's 6:00→5:00, while Samarkand shows no break.
  - **Boundary differences between the 1991 oblasts and today's regions** (as sqwkd gave them; not checked against a source):
    - Navoiy (NW) was folded into Bukhara and Samarkand in 1988–92. Both of those are "other territories", so NW goes to Samarkand.
    - Jizzakh (JI) and Sirdaryo (SI) were re-formed in 1990, and both are named on the moving side. They go to Tashkent.
    - Tashkent City (TK) was part of the Tashkent oblast listed, so it goes to Tashkent.
    - Each goes to the side its 1991 territory was on.
  - **Outcome:** UZ unplaced_by_design is 0 against the plan's expected ~11. All 13 scheduled airports are placed.
- **KZ:** placed from tzdata asia's Almaty list, which gives ISO codes, including the 2022 regions Abai, Jetisu and Ulytau. Baikonur (UAOL) isn't listed and goes to unplaced_by_design.
- **CD (Q2):** Kinshasa (CD-KN) → Lagos and Lubumbashi → Maputo, via the `backward` links. Every other province is SPLIT, so 18 scheduled airports go to unplaced_by_design. Searched: tzdata only; no DRC provincial list was found.
- **VN (Q2):** tzdata states no north/south boundary; it says only "South Vietnam (after 1954)". The Bến Hải line was therefore **not used**. Only Ho Chi Minh City (VVTS) is placed; the other 21 scheduled airports go to unplaced_by_design.
- **PF (Q4):** Society Islands airports (8) → Tahiti, Marquesas (4) → Marquesas, Totegegie → Gambier, all by airport-keyed overrides (no ISO region). For Tuamotu and the Austral Islands:
  - Décret 2017-292 art. 5 (seen as a Légifrance search result) keeps the 1978/79 decrees for French Polynesia.
  - Décret 79-896 wasn't fetched: Légifrance returned 403, and that was not bypassed.
  - The 27 scheduled Tuamotu and Austral airports go to unplaced_by_design.
- **Q3 (Crimea precedent):** UA-43 and UA-40 → Simferopol; Ercan (LCEN) → Famagusta; Ramallah heliport → Hebron. The Ramallah note cites tzdata's line that the PA "got hold of most towns in the West Bank" and records the clock observed there. All join the README list. Akrotiri (OA CY-XX, the UK Sovereign Base Areas) is SPLIT and stays NULL; it isn't scheduled.
- **Other:**
  - **GL:** named places Pituffik → Thule, Ittoqqortoormiit → Scoresbysund and Danmarkshavn; the Nuuk residual has S2 boxes. Neerlerit Inaat (BGCO) is 0.68° from Ittoqqortoormiit, so it goes to unplaced_by_design (R1).
  - **NZ:** NZ-WGN is SPLIT with Chatham as a named place (OurAirports files NZCI under WGN). Paraparaumu has a blank municipality and is placed by an override.
  - **MN:** Zavkhan and Govi-Altai are SPLIT because tzdata records two configurations. ZMAT and ZMDN go to unplaced_by_design.
  - **MY:** Labuan (MY-15) is SPLIT, and WBKL goes to unplaced_by_design (sqwkd). zone1970 names only "Sabah, Sarawak", and tzdata doesn't state Labuan's history. sqwkd notes, from recollection and not source-checked, that Labuan may have followed Singapore before 1946. The draft's Labuan → Kuching inference was reverted.
  - **MH:** 11 NASR-only atolls are placed by overrides. Dyess AAF → Kwajalein; the others → Tarawa.
  - **XK:** BKPR → Belgrade, from tzdata europe's Kosovo heading.
  - **UA:** Kharkiv has no region in OurAirports and is placed by an override.

## Deviations
1. **D1:** the US exemption (above).
2. **D2:** UZ reverses the Q2 ruling (above). sqwkd is telling the operator.
3. **tzdata-only citations:** no national statute was fetched for any 03-04 country; SOURCES.md says so.
4. **PF:** Légifrance returned 403; it wasn't worked around.
5. **CY:** the 03-01 ISO-coded partial rows were removed (above). Every note that relies on OurAirports' CY codes now says the numbering differs from ISO 3166-2:CY.

## Carried forward
- To 03-05: whether US stays in `ZONE_REGIONS_EXEMPT` when the gate closes (sqwkd D1).
- The Q2 of 03-03 (AIPs as a check) is still the operator's decision.

---
phase: 03-iana-timezones
plan: 02
type: summary
status: draft
description: "Gate tooling, per-region partial guard, municipality key, Mexico and Canada placed from cited statutes; CA and MX have no scheduled airport unplaced outside unplaced_by_design."
about: "aeronav-db"
tags: [timezone, iana, tzdata, mexico, canada, cgndb, cfs]
relatedTo: [03-02-PLAN.md, 03-01-SUMMARY.md]
---

# 03-02 Summary: gate, Mexico, Canada

DRAFT. sqwkd checks it before unify; items marked OPEN are still with sqwkd.

## Delivered
- **aeronav_db/tz.py**
  - `partial_regions.csv` guard is per region, not per zone comment (AC-2). A region rule is refused for a partial region; `CC-*` rows exempt country-level qualifiers.
  - Outside the US the sub-region key is the OurAirports municipality, upper-cased (AC-3).
  - `gate` CLI: `python -m aeronav_db.tz gate DB OURAIRPORTS_CSV` (AC-1).
  - Fix found by the 03-02 build: NASR lists 72 Canadian airports with no ISO region. When OurAirports agrees on the country, its region and municipality now place them (952fc29).
- **aeronav_db/verify.py:** canaries MMUN Cancun, MMMX/MMOX/MMQT Mexico_City, MMSD/MMMZ Mazatlan, CYYC Edmonton, CYYZ Toronto, CYVR Vancouver, CYHZ Halifax.
- **identity/tz/:**
  - rules.csv gains 33 MX state rules (5 SPLIT) plus 18 municipality rows, and CA region rules for AB, MB, NB and PE.
  - Every other province and territory is SPLIT with municipality rows: 266 rule-cited, 32 name-cited and 3 by D1 membership.
  - overrides.csv gains 4 airport-keyed rows: CYGL, CZEM, CYIF and CYNL.
  - Also: partial_regions.csv, unplaced_by_design.csv (33), the vendored tzdata `northamerica`, and SOURCES.md.
- **README:** a municipality-key misplacement caveat and the AC-3a lint; the observed-clock rows (L4).

## Build (AC-6)
2026-10-29 was built from the pinned seed (`identity/seed.json`, sha256 e92fa5fe…) with NASR 2026-10-29 and OurAirports 2026-10-29.
- Output sha256 59c06c87…, 35,346 airports. `verify --previous` exits 0, and all 14 tz canaries pass.
- Present 27,226: placed 23,565 (03-01: 23,053), unplaced 3,661 (03-01: 4,173).
- CA: 504 present, 410 placed (county 313, region 93, override 4). 94 unplaced: no_county_match 84, no_region 10 (no OurAirports row).
- MX: all 102 present placed (region 84, county 18).
- Gate (`tz gate`) still fails overall, as planned: the multi-zone countries for 03-03 and 03-04 and the US remainder for 03-05 remain. **CA and MX produce no gate failure:**
  - no multi_zone_country;
  - CA has 275 scheduled airports: 242 placed, 33 in unplaced_by_design, 0 unlisted.

## AC results
| AC | Result | Evidence |
|----|--------|----------|
| AC-1 gate | PASS for the tooling; the phase gate closes in 03-05 | `tz gate`; CA/MX clean, see Build |
| AC-2 per-region guard | PASS | tests; 27 partial regions + CC-* exemptions |
| AC-3 municipality key | PASS | tests; README caveat |
| AC-3a lint | PASS (see below) | 6 flagged: 1 fixed, 5 confirmed, 0 set NULL |
| AC-4 Mexico | PASS | 102/102 placed; canaries pass |
| AC-5 Canada | PASS, with deviations | below |
| AC-6 checks/coverage | PASS | build, verify, canaries, CFS check |

## AC-3a lint (331 municipality-placed non-US airports)
- **Flagged: 6.**
  - **Fixed (1):** CYJN "ST JEAN". The row cited CGNDB EIABI (a Saint-Jean township at 70.17°W), but the airport serves Saint-Jean-sur-Richelieu. The note now cites EJIXZ at 73.254°W. Both positions are well west of 63.5°W, so the zone is unchanged (b4c94f8).
  - **Confirmed (5):**
    - CTK6 Côte-Nord-du-Golfe-du-Saint-Laurent, 61.27°W, and CTT5 Le Golfe-du-Saint-Laurent, 60.67°W. Each cited record is the seat or MRC centroid (59.62°W), and the airport lies in the same municipality or MRC. Both are more than 1.6° east of 63°W and outside Minganie, so QC Act s.2 applies.
    - CYPL Pickle Lake (90.21°W) and CYTL Big Trout Lake (89.90°W): name-cited tzdata anomalies (O3), so the meridian doesn't apply.
    - YBJ Baie-Johan-Beetz (62.81°W): name-cited by MRC Minganie under QC Act s.1, which covers all of Minganie whatever the meridian.
- **Not checkable for span:** 35 rows cite no gazetteer coordinate.
  - MX 18: name-cited from the LHHEUM municipality lists. No public-domain gazetteer was used for Mexico.
  - CA: NL 9 (SGC CSD only), BC 5, ON 3 and QC 1 (named places).
- Statutory meridians checked: ON 90°W, QC 63°W, NU 85°W/102°W, YT 138°W. The ON 85°W line is our cut-off, not statute. The SK and NS lines are margins.

## Canada: citation basis
- **Counts:** rule-cited 266, name-cited 32 (including D1 Cranbrook), D1 membership 3 (Castlegar, Trail, Revelstoke), region rules 4 (AB, MB, NB, PE), airport-keyed overrides 4.
- **O1 (Ontario):** the easternmost tzdata anomaly is the Big Trout Lake area (lake FAIIZ, 90.007°W). Others: Pickle Lake 90.140°W, Mishkeegogamang 90.229°W, Upsala 90.498°W, Atikokan 91.622°W. The margin to 85.5°W is about 4.5°, so the 85°W cut-off holds.
- **O4:** 28 scheduled northwestern Ontario airports are in unplaced_by_design, including YQT Thunder Bay.
- **NS:** Glace_Bay and Halifax differ only before 1972.
- **Labrador (sqwkd L1–L4):**
  - Observed clock per tzdata, over the statute (RSNL c S-23 s.2(1)).
  - Goose_Bay covers SGC CD 1010 and 1011, except the named NST corner.
  - Wabush → Halifax, per northamerica line 1489 ("west Labrador"). Halifax and Goose_Bay have been identical since 2011 and differ only before 1966.
  - St. Lewis, Williams Harbour, Charlottetown and Churchill Falls are in unplaced_by_design.
- **SK (S1–S4):**
  - Regina and Swift_Current have been identical since 1972. Pre-1972 timestamps for western SK towns may follow Swift_Current's history.
  - The 0.5° box around Swift Current caught 0 airports. No Creighton-type row was written.
- **NT:** Edmonton is the residual and Inuvik is named. "NT (west)" is undefined geography, so pre-1980 timestamps for Aklavik, Fort McPherson and Tuktoyaktuk may follow Inuvik's PST history.
- **NU:** SOR/2001-182 meridians, with Kitikmeot by SGC CD 6208. Arctic Bay is in unplaced_by_design: within 0.5° of 85°W, and the observed-practice sources predate the proclamation.
- **YT:** the 138°W split from Commissioner's Order 1967/59 as quoted in tzdata. Whitehorse and Dawson have been identical since 1973. Haines Junction stays NULL.
- **D1 same-CD confirmation: OPEN.**
  - StatCan's CD boundary file returns 403, so no official polygon was used.
  - Evidence: each airport's distance from its municipality's CGNDB record. Cranbrook CYXC 11.7 km, Castlegar YCG 4.0 km, Trail YZZ 8.5 km, Revelstoke YRV 4.2 km.

## Observed clock over statute (L4)
Labrador: Goose Bay, Black Tickle, Cartwright, Natuashish, Rigolet, Postville, Makkovik, Hopedale and Nain (America/Goose_Bay), and Wabush (America/Halifax). Crimea will be added in 03-04.

## Independent check: Canada Flight Supplement
- **The source:** the current eCFS (2026-10-29) is paid, so it was not purchased. The operator allowed a check against the older eCFS that NAV CANADA hosts free (navcanada.ca/en/ecfs_0{1,2,3,4,5,7}_en.pdf; pages dated **2020-11-23**, Last-Modified 2021-04-26).
- **Age caveat:** this edition is six years old.
- **Method:** the printed standard and DST offsets are compared with the zone's offsets on **2021-01-15 and 2021-07-15**. Nothing from the CFS is stored, and **no airport was placed from it**.
- **Results:** 1,556 entries parsed.
  - 340 match.
  - 71 appear in the CFS but are unplaced.
  - 73 present CA airports are not in the CFS.
  - 10 mismatch:
    - 9 YT airports print UTC-8(7). This edition predates Yukon's 2020-11-01 move to UTC-7.
    - CBX5 Tungsten NT (not scheduled) prints UTC-8 with no DST. OPEN with sqwkd.
- **Mexico:** no independent check exists.

## Deviations
1. Some citations rest on tzdata alone because the statute couldn't be fetched (403 or a landing page):
   - AB, MB, NB, PE;
   - NT (R-090-2026);
   - YT (OIC 2020/125);
   - NU DST (R-033-2021).
2. Quebec's Legal Time Act was supplied by the operator. Only its citation and hash are stored.
3. Airport-keyed overrides (CYGL, CZEM, CYIF, CYNL) apply a statute's own rule to one airport, as sqwkd approved.
4. Name-matching normalisations are lookup-only: Sault Ste Marie, St Thomas, Saltspring Island, and the Saint/St and accent forms in QC.
5. The AC-3a lint script lives in the scratchpad. It reads the CGNDB zips, which are not vendored.

## Next
03-03: AU, BR, RU, ID, reviewed before APPLY.

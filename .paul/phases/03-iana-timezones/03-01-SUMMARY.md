---
phase: 03-iana-timezones
plan: 01
type: summary
status: complete
description: "Per-airport IANA zone from a pinned-tzdata rules table; 23,053 of 27,226 present airports placed, none guessed; US placements checked against the 2026-10-29 Chart Supplement."
about: "aeronav-db"
tags: [timezone, iana, tzdata, chart-supplement]
relatedTo: [03-01-PLAN.md, 02-03-SUMMARY.md]
---

# 03-01 Summary: IANA time zones

## Delivered
- **aeronav_db/tz.py**
  - `Rules.load` validates rules.csv and overrides.csv against the vendored zone1970.tab.
  - `resolve` returns (tz, tz_basis, tz_unplaced).
  - `placement_inputs`: NASR STATE/COUNTY first, then OurAirports iso_region. NASR files PR, VI, GU, AS and MP under US; they are placed as their own countries.
  - `seed-rules` regenerates the single-zone country rows.
- **identity/tz/:**
  - zone1970.tab and TZDATA_VERSION (2026f), vendored per T1;
  - rules.csv: 214 single-zone countries, 38 whole US states, 15 SPLIT US states placed by county (1,177 US rows);
  - overrides.csv: 8 cited `source_conflict` rows.
- **Schema:** `airport_identity.tz_unplaced TEXT`, the only DDL change; it goes to cv-aviation.
- **Build:** `assign_timezones` fills tz, tz_basis and tz_unplaced for every identity. An absent airport keeps its previous value.
  - Metadata gains tzdata_version, tz_placed and tz_unplaced.
  - The manifest gains `tz: {tzdata_version, placed, unplaced}`.
- **Verify:**
  - `check_timezones`: every zone is in the vendored tab; tz and tz_basis are NULL together; tz_unplaced is set exactly when tz is NULL and is a known reason; a country basis must be a single-zone country's zone.
  - Canaries: KDJT America/New_York, PHNL Pacific/Honolulu, KELP America/Denver, PANC America/Anchorage.
  - Coverage notes, including the change in unplaced since the previous file.
- **Tests:** tests/test_tz.py, 13 tests. Full suite: 161 passed; ruff clean.
- **README:** a "Time zones" section.

## AC results
| AC | Result | Evidence |
|----|--------|----------|
| AC-1 rules table | PASS | identity/tz/rules.csv and overrides.csv |
| AC-2 resolution | PASS | Tests; conflicting same-key rules are a load error |
| AC-3 never guessed | PASS | Refusals tested: a country rule in a multi-zone country, a zone of another country, no citation, a county rule under a region rule, a partial zone (non-US) |
| AC-4 build/verify | PASS | 2026-10-29 built from the seed; verify --previous exit 0; all 4 canaries pass |
| AC-5 Chart Supplement | PASS | See below |
| AC-6 coverage | PASS | See below |
| AC-7 unplaced visible | PASS | tz_unplaced plus manifest counts (cv-aviation) |
| AC-8 pinned tzdata | PASS | Vendored 2026f; validation never reads the host's zoneinfo (verify's offset comparison script did, for display only) |
| AC-9 AZ/NV, measured split set | PASS | AZ: Apache, Navajo and Coconino are NULL (no_county_match); the other 12 counties are America/Phoenix. NV: Elko is NULL. Measured: states with more than one printed offset are AK, IN, MI, KS, NE, ND, SD, OR, ID, TX, FL, KY, TN, NV and MT (MT is one airport, a conflict). All but MT were already SPLIT |
| AC-10 non-US splits | PARTIAL, as designed | No non-US region rules were written, so all 33 multi-zone countries' airports outside single-zone territories stay NULL (multi_zone_country). **No independent offset check exists for them.** Cited region rules are a follow-up plan |

## AC-5: Chart Supplement, 2026-10-29 edition (DCS_20261029.zip, the FAA's digital edition)
- Method: the airport header text was extracted from all 3,184 page PDFs (Type0 fonts, Identity encoding), giving 5,114 airport entries with a printed UTC offset. Each was matched to the build by FAA LID. The printed standard offset and the DT flag were compared with the resolved zone (January and July 2026 offsets).
- **4,462 match.** 3 differ only by a print typo with the right offset: H63 "(5-5DT)", X50 "(-4)", HZD "(-5)". 649 had no faa code match or are unplaced.
- First pass, 12 mismatches. They resolved as follows:
  - **Rule error, fixed:** Y27 Fort Yates (Sioux County ND straddles the line). Sioux County ND is now a split county (NULL).
  - **Conflicts, now unplaced (`source_conflict`, both sources cited in overrides.csv):** I20 (Knox Co IN), 01L (Starke Co IN), 1V2 (Grant Co NE), 4E8 (Stark Co ND), 7Q7 (Mellette Co SD), M35 (MT), C64 (Clearwater Co ID), I45 (Lewis Co ID). In each case the Chart Supplement's printed offset contradicts the county rule. Without a third source, neither side is picked.
  - **Parser artefact, fixed:** NEN (Whitehouse NOLF) prints no UTC; the regex no longer reaches into the next entry.
- Not every sampled state reached ≥5 *conflict-free* airports through matching alone: AZ's three Navajo counties are unplaced by design. Every other split state had dozens of matched airports.

## AC-6: coverage (present airports, 2026-10-29 build)
- 27,226 present: placed 23,053 (region 11,769; county 7,346; country 3,938). Unplaced 4,173: multi_zone_country 3,652; no_county_match 348; no_region 162; source_conflict 8; no_rule 3.
- Unplaced by country (top 10): AU 618, CA 504, CN 411, US 359, BR 357, PG 345, RU 315, ID 246, DE 110, AR 108.
- Multi-zone countries left wholly NULL: all 33 except the US (and the US territories, which are single-zone).

## Deviations
1. US split states are placed as "the state's default zone plus listed exception counties". The rules are written out as one explicit county row per county that appears in NASR. The generator lives in the scratchpad; the committed CSV is the reviewable artefact. Split counties are left out (NULL).
2. AC-10 is partial: no non-US region rules. sqwkd asked that this be said rather than implied.
3. overrides.csv accepts an empty tz as a cited conflict, which gives the new reason `source_conflict`. This wasn't in AC-7's list; cv-aviation is told.
4. The Chart Supplement was parsed with a 20-line zlib text extractor (no PDF library installed).

## Next
- Optional: 03-02, cited region rules for the large multi-zone countries (AU, CA, BR, RU, MX, ID).
- First schema-3 release via docs/RELEASE-RUNBOOK.md: operator-confirmed, between cycles (2026-11-26 is next).

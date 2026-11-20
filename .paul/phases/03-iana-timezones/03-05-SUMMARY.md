---
phase: 03-iana-timezones
plan: 05
type: summary
status: complete
description: "US remainder placed or listed by airport, the Pacific-island inputs fixed to UM, and Alaska placed from 49 CFR Part 71 and tzdata named places; the closing tz gate on the seed build passes."
about: "aeronav-db"
tags: [timezone, iana, alaska, arizona, pacific, part-71, gate]
relatedTo: [03-05-PLAN.md, 03-04-SUMMARY.md]
---

# 03-05 Summary: US remainder and the closing gate

Applied by Codex (worktree /workspace/aeronav-db-codex, two passes). aeronav-db reviewed every hunk, re-ran every check below and committed 72182d9. All numbers below are aeronav-db's own measurements.

Checked by sqwkd 2026-11-20, verbatim: "sqwkd check of 03-05 (SUMMARY 35212d8, code 72182d9): OK on (a), (b) and (c). Unify, merge locally, then hand over." sqwkd re-verified the sha256, the gate and verify --previous, and the US arithmetic. sqwkd confirmed the Sitka quote (northamerica:607) as R1 evidence: America/Sitka has no 1980 Yukon interval, and America/Juneau has one. sqwkd accepted the deviations. The L-type questions become a follow-up and don't block 03-05.

## Closing gate (AC-1, AC-6)
- **Build:** 2026-10-29 from the seed b0303/seed-run1.sqlite3 (e92fa5fe…), with the cached NASR, OurAirports and navaids 2026-10-29 inputs. Output: scratchpad tz8/navigation.sqlite3, sha256 `61d4979b0c5168ae497fa32cedf3670a5b469bd749cf2fbb1cd0dab01c27d212`. It is byte-identical to Codex's tz7 build. Manifest sha256 d094cc27….
- **`verify --previous`:** exit 0.
  ```
  time zones: 26434 present airports placed, 792 unplaced
  unplaced by country: US 350, AU 149, CA 94, CD 58, PF 38, BR 30, RU 28, VN 28, AQ 8, MN 4
  verification passed: …/tz8/navigation.sqlite3
  ```
- **`tz gate`:** exit 0.
  ```
  present 27226, placed 26434, NULL 792
  gate PASS
  ```
- **Checks:** ruff clean; 178 tests pass. In the worktree, test_chain_ci skips because it has no local seed; the test runs in the main repo.
- **AC-3a lint:** no new municipality rules, so no new flags.

**US NULL in the current cycle, before → after:**

| Reason | 03-04 (tz5) | 03-05 (tz8) |
|---|---|---|
| no_county_match | 348 (62 scheduled) | 341 (55 scheduled, all listed by design) |
| multi_zone_country | 3 (1 scheduled) | 0 |
| no_region | 0 | 1 (Palmyra, unscheduled) |
| source_conflict | 8 | 8 |

## Pacific islands (AC-4)
- **Inputs:** placement_inputs maps NASR QW, QM and XL to UM, with OurAirports' UM region; identity iso_country stays US. Tests cover all three codes.
- **Wake (AP0019560):** placed by UM-79 → Pacific/Tarawa ("Gilberts, Marshalls, Wake").
- **Midway (AP0019610):** placed by UM-71 → Pacific/Pago_Pago ("Midway"). Pacific/Wake and Pacific/Midway are backward links, so R1 holds.
- **Palmyra (AP0019547):** the only XL airport. It is NULL with no_region, and tzdata's "probably like Pacific/Kiritimati" was not used. The gate groups by identity country, so Palmyra counts under US; it is unscheduled.

## Alaska (AC-2)
- **Source:** 49 CFR Part 71 from eCFR (title 49 current as of 2026-11-18), sha256 7ca9e8d7…, recorded in SOURCES.md.
  - Fetched by aeronav-db, because Codex's sandbox has no DNS.
  - The first request returned 406: "This endpoint requires response compression." `curl --compressed` sends the standard Accept-Encoding header the server asks for. That is not a workaround of an access block, and the User-Agent was not changed.
  - §71.11 places all of Alaska in the Alaska zone, except under §71.12: "that part of the Aleutian Islands that is west of 169 degrees 30 minutes west longitude".
- **By the §71.12 line plus tzdata "America/Adak is for the Aleutian Islands … west of 169.5° W":**
  - Adak PADK, 7.142° (490.8 km) west of the line;
  - Atka PAAK, 4.706° (320.9 km) west.
- **East of the line, in Alaska time, but tzdata states no history (listed):**
  - Akutan PAKO, 0.651° (43.7 km) east;
  - Unalaska PADU, 2.955° east.
- **Named places (R1):**
  - Ketchikan (PAKT, 5KE), Petersburg (PAPG) and Wrangell (PAWG) → America/Sitka, from tzdata's "Sitka, Petersburg, Wrangell, and Ketchikan, however, would remain on Pacific Time." That is Sitka's history, not Juneau's.
  - Metlakatla (PAMM) → America/Metlakatla, from zone1970 "Alaska - Annette Island".
- **Still listed: 50 Alaska airports.** Each reason states that Part 71 gives Alaska time and names the missing fact, which IANA history applies:
  - 25 OurAirports-only airports with no borough in the inputs (Hyder is one);
  - 9 Prince of Wales airports (an L-type question);
  - 12 in other NASR areas with no sourced area-to-history match;
  - the 2 east-of-line Aleutian airports;
  - 2 Pribilof airports.

## Arizona and Nevada (AC-3)
- **Arizona:** KFLG, KGCN, KPGA and KSOW are listed.
  - Part 71 puts Arizona in Mountain time, and 15 U.S.C. 260a covers the DST exemption.
  - No cited jurisdiction fact established Navajo Nation or Hopi status for these airports, so none was inferred from position.
- **Nevada:** KEKO is listed. The pass-1 override was reverted: tzdata's "Nevada (except West Wendover)" and "Nevada border (Jackpot, Owyhee, and Mountain City)" don't name Elko city.

## Source conflicts (AC-5)
- I20, 01L, 1V2, 4E8, 7Q7, M35, C64 and I45 keep their cited blank overrides. All are unscheduled, and no independent rule resolved any of them.
- No Chart Supplement edition was fetched, so no new offset check is claimed.

## L-type questions for sqwkd (AC-5a; APPLY decided none)
1. **Hyder** (AP0019046; Hyder SPB 4Z7, AP0024208): legally Alaska time under §71.11. The reported practice is Pacific time with Stewart, BC. Both are NULL.
2. **Prince of Wales** (KCC, CGA, HYL, PAHY, KXA, PAKW, KPB, PAAP, KTB): the clock basis and the pre-1983 history aren't sourced. All are NULL.
3. **Jackpot** (AP0009620, AP0024272): tzdata names Jackpot among the Nevada border places on Mountain time. Both are NULL.
4. **West Wendover:** NASR files KENV (AP0016900) in Tooele County, Utah, so it is unchanged. Is any other airport in scope?

## Deviations
1. **AC-5:** no Chart Supplement check was run.
2. **Process:** Codex's sandbox had no network, so aeronav-db made the Part 71 fetch.
3. **Scope:** Codex re-serialised 4 Labrador UBD rows. The content was unchanged; aeronav-db restored the original lines.
4. **Codex's report:** it said 10 Prince of Wales and 11 other-area rows. The file has 9 and 12, because PAMM is placed; the figures above are counted from the file.

## Rulings carried
- **D1:** US stays in ZONE_REGIONS_EXEMPT permanently. US county rules and per-airport citations provide the placement control, gate items 1 and 2 still cover US, and the exact-set test stays.
- **Operator, verbatim 2026-11-20 (relayed by sqwkd):** "Once phase 3 closes, commit and merge, and publish to cv-aviation.  No to the current nav Canada publication. Official source checks do not hold up release."
- The AN identity issue (TNCE, TNCM) is still a release blocker for Phase 1.

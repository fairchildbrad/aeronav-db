---
phase: 03-iana-timezones
plan: 07
type: summary
status: complete
description: "L-type follow-up: Jackpot, Owyhee and Mountain City NV placed on the observed Mountain clock (L4); Hyder kept NULL; West Wendover closed; Prince of Wales deferred pending the 1979/1980 Federal Register text."
tags: [timezone, l-type, observed-clock, nevada, hyder, prince-of-wales]
relatedTo: [03-07-PLAN.md, 01-04-SUMMARY.md, 03-05-SUMMARY.md]
about: "aeronav-db"
---

# 03-07 SUMMARY: L-type follow-up

## Authority
- **sqwkd approval, verbatim:** "03-07 PLAN (5380d15) APPROVED for APPLY, with these rulings." The NASR-city rule for L1 came in a later sqwkd ruling, recorded in the PLAN.
- **sqwkd check, verbatim:** "03-07 VERIFIED. Write the SUMMARY and UNIFY."
- **Operator, verbatim, 2026-11-21:** "Access what you can and give me links if you can't see it".

## Outcome
| Item | Result |
|---|---|
| L1 Jackpot, Owyhee, Mountain City (NV) | **4 placed**, America/Denver override: AP0009620 (06U), AP0009656 (10U), AP0029026 (NV11), AP0009650 (NV08) |
| L2 Hyder AP0019046 | NULL kept. No tzdata statement of the observed clock, so L4 can't apply. Admitting a non-tzdata source is a policy change, offered to the operator by sqwkd |
| L3 West Wendover | closed, no change. 0 present NV airports in the city; KENV AP0016900 (Tooele UT) stays America/Denver |
| L4 Prince of Wales ×9 | **DEFERRED**, NULL; the 1979/1980 FR orders aren't obtainable here (STATE.md) |

## Sources
- **Order of events:** a retry of the eCFR URL was **denied by this session's permission classifier** on 2026-11-20, and APPLY paused. After the operator's answer above, on 2026-11-21, the eCFR versioner XML was fetched with `curl --compressed`. That endpoint returns HTTP 406 without compression; no User-Agent change was made. sha256 **7ca9e8d7…**, the same as the 03-05 fetch (SOURCES.md:12).
- **§71.10, verbatim:** "The fifth zone, the Pacific standard time zone, includes that part of the continental United States that is west of the boundary line between the mountain and Pacific standard time zones described in § 71.9".
- **§71.9(b), verbatim:** "From the northeast corner of the State of Nevada southerly along the Utah-Nevada boundary to the junction with the northern border of the City of West Wendover, Nevada. …"
- **Observed clock:** tzdata 2026f northamerica:474, "Nevada border (Jackpot, Owyhee, and Mountain City)", under US mountain time represented by Denver.
- **Rule (sqwkd):** NASR APT_BASE CITY must name the place. Measured on NASR 2026-10-29: 06U JACKPOT, 10U OWYHEE, NV11 OWYHEE, NV08 MOUNTAIN CITY.

## Build and checks
- **Build:** cb5f2f899115c6945db4b458b5d6924af9975566638fe9b4c20ded9bfbb09a27, from seed be416100…, with NASR 538c8219… and OA 61129867339d.
- **`verify --previous`:** exit 0.
  ```
  time zones: 26322 present airports placed, 664 unplaced
  verification passed
  ```
- **`tz gate`:** exit 0.
  ```
  present 26986, placed 26322, NULL 664
  gate PASS
  ```
  Predicted 26,322 / 664 after the census; exact.
- **tz diff against b8b96f28:** exactly the 4 ids (NULL → America/Denver, override). sqwkd confirmed this independently.
- ruff `.` clean; 201 passed.

## Predictions that were wrong
1. **Owyhee / Mountain City:** predicted 0 present NULL airports. **Wrong: there are 3** (AP0009650, AP0009656, AP0029026).
2. **Petan Ranch:** aeronav-db first reported OA's municipality as its only link to Mountain City. **Wrong: NASR CITY is MOUNTAIN CITY.**

## Deviations
1. **Id-keyed canary added.** `CANARY_TZ_BY_ID = {"AP0009620": ("America/Denver", "override")}` replaces the planned code canary, because the ICAO canaries can't see a field without an ICAO code.
2. **APPLY paused** on 2026-11-20 because sources were blocked, and resumed on the operator's answer.

## Deferred
- **L4 Prince of Wales ×9** (KCC, CGA, HYL, PAHY, KXA, PAKW, KPB, PAAP, KTB): NULL until the operator supplies the 1979 DOT order and its 1980 rescission (49 CFR Part 71, Alaska/Yukon).
- **Links given to the operator:** https://www.govinfo.gov/app/collection/fr/1979/09 , https://www.govinfo.gov/app/collection/fr/1980/09 and https://www.loc.gov/collections/federal-register/

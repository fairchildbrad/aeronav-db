---
phase: 01-identity-engine
plan: 03
type: summary
status: complete
description: "Release blocker closed in code: identity iso_country takes the ISO successor of NASR's retired 'AN' or NULL; output files refuse a retired code; the rebuild differs from tz8 by exactly two rows."
tags: [airport-identity, iso-country, release-blocker, verify]
relatedTo: [01-03-PLAN.md, 03-05-SUMMARY.md]
about: "aeronav-db"
---

# 01-03 SUMMARY: AN identity country

## Authority
- **Operator, verbatim, 2026-11-20:** "do your work, all 3 steps.  There will be gaps in history, unavoidable."
- **sqwkd plan review, verbatim:** "sqwkd review of 01-03 PLAN (5749ec2): APPROVED for APPLY, subject to the 4 conditions below." The conditions are folded in at 081c630.
- **sqwkd deviation ruling, verbatim:** "option 1 APPROVED, with one correction to your list of call sites." The plan was revised at 3b44877.

## Result

| AC | Result |
|---|---|
| AC-1 identity rule (a) OA successor, (b) previous successor, (c) NULL | PASS |
| AC-2 output sites refuse a retired code; input sites print a NOTE | PASS |
| AC-3 tests | PASS |
| AC-4 rebuild differs from tz8 by exactly 2 rows | PASS |
| AC-4a positive control on tz8 | PASS |
| AC-5 3-cycle apply_cycle fixture (NULL → SX → SX) | PASS |
| AC-6 README lines | PASS |

## AC-4 build
- **Inputs:** NASR `28DaySubscription_Effective_2026-10-29.zip` (sha256 538c8219a9c88ca35c31d3f7162870effab0a2d6c8c1ca833ef155ebf3a314be); OurAirports airports.csv and navaids.csv at commit 61129867339d; `--previous-db dist/backfill/seed.sqlite3` (e92fa5fe…).
- **Baseline:** without the change, these inputs rebuild tz8 byte for byte (61d4979b…), so they are the build of record's inputs.
- **Output:** sha256 `79f705b73b964b7f4d71b70b253f1c9366f02f42a3c84aae758dc92805a04b89`.

Build NOTE (sqwkd condition 2), verbatim:
```
NOTE: --previous-db carries 2 retired NASR country code(s) (AP0019780, AP0019781); this build rewrites them (01-03)
```
`verify OUT --previous SEED`, exit 0:
```
time zones: 26434 present airports placed, 792 unplaced
unplaced by country: US 350, AU 149, CA 94, CD 58, PF 38, BR 30, RU 28, VN 28, AQ 8, MN 4
unplaced change since previous file: +792
verification passed: …/an1/navigation.sqlite3
```
`tz gate OUT OA`, exit 0:
```
present 27226, placed 26434, NULL 792
gate PASS
```
Row-level EXCEPT diff against tz8, both directions, every table:
```
airports 0/0, navaids 0/0, fixes 0/0, airways 0/0, airway_points 0/0, boundaries 0/0,
boundary_points 0/0, metadata 0/0, airport_codes 0/0, airport_presence 0/0, airport_aliases 0/0
airport_identity new-only=2 old-only=2
AP0019780|AN|BQ
AP0019781|AN|SX
```

## AC-4a positive control
`verify` on tz8 (61d4979b…), exit 1:
```
VERIFICATION FAILED
  - 2 airport_identity rows carry a retired NASR country code (AN); iso_country must be its ISO successor or NULL
```
Plain verify on the seed e92fa5fe… fails the same way. This is expected. It ends when runbook step 1 re-runs the seed with this code.

## Code
- **`identity._identity_country`:** the AC-1 rule. The pairing gate and `placement_inputs` are unchanged.
- **`verify`:** adds `check_retired_countries`, `retired_country_ids` and `retired_country_note`. The retired-code check is separate from `check_identity`.
- **Output sites (check applies):** `verify_database` (plain verify), build `_check_staged`, backfill per-cycle `current_db`, and backfill `write_seed` staging.
- **Input sites (NOTE only):** build `_load_previous` and chain `_identity_problems`. ID shape and alias hops are still checked there.
- **Tests:** 3-cycle history; non-successor OA country gives NULL; current country unchanged; verify output-only refusal (AN refused; BQ, SX, NULL and XK pass; check_identity silent); previous file with AN chains and its output drops AN for (a) and (c); refusal at build staged, backfill per-cycle and write_seed.
- **README:** the ISO 3166-1 line with the XK exception, and the IATA history line.

ruff clean; full pytest 186 passed.

## Deviations
1. **Unpredicted refusal (sqwkd condition 4).** The first APPLY run was refused, verbatim:
   ```
   BUILD REFUSED: previous database fails its identity invariants:
     - 2 airport_identity rows carry a retired NASR country code (AN); iso_country must be its ISO successor or NULL
   ```
   build.py:1292 runs check_identity on `--previous-db`. The plan's AC-4a covered only verify --previous, and sqwkd's own review also missed this call site. Fixed as ruled: an output-only check, with a NOTE on input. sqwkd corrected aeronav-db's list of call sites: backfill write_seed is an output site and keeps the check.
2. **Census scope (sqwkd condition 1).** Scope 1 counted NASR-site rows only, so it missed the 2 OA-only XK (Kosovo) rows in the seed. XK is user-assigned, not ISO-assigned. It is documented as an exception and is not refused.

## Open after 01-03
- **Handover file:** unchanged until sqwkd OKs it. The cv-aviation note is value-only (no DDL) and carries the ISO/XK line.
- **01-04:** duplicate ids through the FAA LID, the next release blocker. The L-type plan follows it, and the AIP/ERSA check runs on the post-01-04 build.

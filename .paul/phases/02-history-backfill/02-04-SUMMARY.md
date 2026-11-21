---
phase: 02-history-backfill
plan: 04
type: summary
status: complete
description: "The format-a layout guard now reads each archive's own Layout_Data/apt_rf.txt; a cold-cache re-run of the seed-time code plus the guard reproduces e92fa5fe byte for byte."
tags: [backfill, nasr-archive, layout-guard, reproducibility, release-blocker]
relatedTo: [02-04-PLAN.md, 01-04-PLAN.md]
about: "aeronav-db"
---

# 02-04 SUMMARY: format-a layout guard and seed reproduction

## Authority
- **sqwkd, verbatim 2026-11-20:** "make it a SEPARATE plan, 02-04, with review before APPLY."
- **Approval, verbatim:** "02-04 PLAN (7bda1a3) APPROVED for APPLY, on the conditions below." The census ran before any guard code (condition 1).

## Check
sqwkd, verbatim 2026-11-20: "02-04 VERIFIED. OK to UNIFY, then resume 01-04 as you described." sqwkd re-checked the sha256 and `cmp` of the seed, the `cmp` of the report, and that b76d1b2 touches only nasr_archive.py and its test.

## Result

| AC | Result |
|---|---|
| AC-1 cache audit | P1 holds. Inferred from commit order and a cold run, not audited, because the original cache is gone (sqwkd condition 2) |
| AC-2 layout census | PASS: 66/66 (committed 98d8d1d before the guard code) |
| AC-3 guard | PASS (b76d1b2) |
| AC-4 tests | PASS: ruff clean; 201 passed |
| AC-5 reproduction | **PASS, byte for byte** |
| AC-6 record | below |

## AC-1: which guards ran on fresh bytes (inferred from commit order and a cold run)
- **Wayback-copy cycles, 32 (2017-10-12 → 2020-02-27):** first fetched after 76d0feb, so the layout guard and the zip CRC test (aa2e206, Wayback only) ran on fresh bytes.
- **FAA-served format-a cycles, 34 (2020-03-26 → 2022-10-06):** rows were cached under 5041561 on 2026-11-18, before 76d0feb added `LEGACY_APT_RECORD_LENGTH = 1529`. The guard never ran on them when e92fa5fe was built. 19 of them (2021-05-20 → 2022-10-06) have 1531-character records and fail that guard from a cold cache. Predicted 34; consistent.
- **Formats b (11) and c (41):** no record-length or layout guard exists. Deferred in STATE.md.
- **Later commits** (5c837d2, 24bb50f, b723206, aeab385) add no parse guards. 5c837d2's identity change is a pure move (sqwkd).

## AC-2 census
See the 02-04-PLAN.md `<census_results>`:
- 47 cycles at 1529 and 19 at 1531;
- stated length = actual length in 66/66;
- all 11 LEGACY_FIELDS entries have the same (start, length, name) in 66/66;
- 0 archives lack `Layout_Data/apt_rf.txt`.

The 2021-04-22 risk disclosed in the plan was a probe error: the probe read `Additional_Data/Eff_20210520/apt_rf_eff20210520.txt`, an advance layout. The guard never reads Additional_Data, and a test covers this.

## AC-3/AC-4 guard and tests
`nasr_archive.legacy_record_length(archive)` reads exactly one `Layout_Data/apt_rf.txt` and takes its `RECORD LENGTH`. It requires `LEGACY_FIELD_NAMES[field]` at each LEGACY_FIELDS (start, length). `legacy_apt_rows(raw, record_length)` refuses any APT record of another length. The hard-coded 1529 is gone.

Tests:
- a 1531 layout with unmoved fields is accepted;
- refused: a moved field, a stated length different from the records, a missing apt_rf.txt, and a layout with no RECORD LENGTH;
- an Additional_Data advance layout is never read.

ruff clean; full pytest 201 passed.

## AC-5 reproduction
- **Setup:** detached worktree at aa2e206 (the backfill code at seed time), with b76d1b2 cherry-picked (clean apply), and a **cold** cache.
- **Command:** `python -m aeronav_db.backfill --from 2017-10-12 --to 2026-10-01 --cache <fresh> --out seed-repro.sqlite3`, which took 2:05:37 and exited 0.
- **Output:**
  ```
  wrote …/seed-repro.sqlite3: 30968 ids, 14 aliases, sha256 e92fa5fe10ab637da01d3c7084668d214770dd619a47c671a1b4335b60395898
  ```
- **Comparison:** `sha256sum` of the reproduction and `dist/backfill/seed.sqlite3` are equal (e92fa5fe…), and `cmp` on the two `.report.json` files finds them identical.
- **What it proves:** the guard change is faithful, the FAA and Wayback bytes are unchanged, and aa2e206 is the seed-time code. The seed's metadata records no code commit, so this byte match is the only proof of that.
- **Next use:** this seed is 01-04's control.

## AC-6: record
- **e92fa5fe could not be reproduced from a cold cache from 76d0feb (2026-11-19 04:30Z) until 02-04.** The layout guard had never run on the 34 FAA format-a cycles, whose rows came from a cache warmed before it, and 19 of those cycles violate the hard-coded length.
- **Runbook step 1 (seed re-run) would have failed** on any machine without that cache.
- **The 02-01 and 02-02 reviews missed it**, both aeronav-db's and sqwkd's. It surfaced only when the 01-04 control run started from an empty cache.

## Deferred (STATE.md)
- No guard for formats b and c.
- Seed and release metadata carry no code commit. The fix changes bytes, so it gets its own plan.

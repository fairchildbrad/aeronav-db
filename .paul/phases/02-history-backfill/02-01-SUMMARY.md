---
phase: 02-history-backfill
plan: 01
type: summary
status: complete
description: "History backfill: 86 NASR cycles (2020-03-26 → 2026-10-01) plus OurAirports git history replayed into a reproducible seed."
about: "aeronav-db"
tags: [backfill, nasr-archive, sticky-attachment, seed]
relatedTo: [02-01-PLAN.md, 02-01-AUDIT.md]
---

# 02-01 Summary: history backfill

## Delivered
- **identity.py**
  - Sticky attachment: `_group(observations, sticky)` with `_can_pair`.
  - NASR is authoritative for the FAA/ICAO codes it assigns in a cycle; a standalone OurAirports row's claim to one is dropped.
- **nasr_archive.py**
  - Range-fetching reader for formats a, b and c, with retry and backoff; a short read raises.
  - The format-a fixed-width parser, with the layout taken from the archived apt_rf.txt.
  - `LEGACY_COUNTRY_RENAMES` = {CN: CA}; blank-status records are left out and counted.
- **backfill.py**
  - Cycle enumeration, a cache (normalised APT rows plus meta with sha256; OurAirports csv by commit), and the OurAirports commit list fetched in quarterly windows (the API returns 422 on deep paging).
  - Replay with an anomaly guard, an ALLOWLIST, and check_identity plus check_chain at every step.
  - Seed writer and JSON report.
- **Tests:** test_nasr_archive (6), test_backfill (4), plus 4 new engine tests. Full suite green; ruff clean.
- **README:** a "Where the history comes from" section.

## AC results
| AC | Result | Evidence |
|----|--------|----------|
| AC-1 sticky | PASS | PBI→DJT: faa switched 2026-07-09, iata 2026-09-03, one id (AP0003265) throughout, no alias |
| AC-2 formats | PASS | Overlap cycle 2022-12-29 (APT.txt vs CSV), all fields compared: 19,886 = 19,886 records, 0 key differences, 0 code/name/status/country differences (see the coordinates note below), 2 coordinate differences |
| AC-3 reproducible | PASS | A second run from the cache gives a byte-identical seed |
| AC-4 chain-valid | PASS | check_chain passed at all 86 steps; a 2026-10-29 build from the seed passes verify --previous and the full gate |
| AC-5 report | PASS | dist/backfill/seed.sqlite3.report.json |
| AC-6 anomaly guard | PASS | Exercised by a test. In the real run only the allowlisted 2021-11-04 exceeded it |

### AC-2 overlap differences (2022-12-29)
- **CZBB** (Vancouver/Boundary Bay, 90038.): status blank in APT.txt and absent from the CSV. It is left out, matching the FAA's CSV extract.
- **Coordinates:** BNO (~1 m) and PDT (~50 m) carry different reference points in the two publications. Identity matches by site, so ids are unaffected.
- The float-division rounding at the 6th decimal (126 latitude, 135 longitude) is fixed by exact Decimal division.
- **Country:** format a has no country column. Non-US rows carry the ISO code in the county-state field, except CN for Canada. This was validated 1:1 on the overlap cycle.

## Seed (measured)
- `dist/backfill/seed.sqlite3` (gitignored, local only). **sha256 c6c09037bc1de28a690e8bc59248f4164bc3c1a4b96f6e14e50dbbc7d42c54f4**
- Reproduced byte-identically from the cache. The cache is 258 MB, in the session scratchpad.
- Cycles: 86, 2020-03-26 → 2026-10-01, none skipped. Formats: a ×34 (from 2020-03-26), b ×11 (from 2022-11-03), c ×41 (from 2023-09-07).
- Metadata: history_start 2020-03-26; history_start_ourairports 2021-11-04; airport_id_next 30425.
- Ids: 30,424. 19,805 were minted in the first cycle, and 8,004 at 2021-11-04 (the first OurAirports snapshot, allowlisted).
- Otherwise at most 132 ids were minted in a cycle (2024-04-18), and at most 314 presence intervals closed (2022-12-01, 1.6%).
- Format boundaries passed the guard without allowlisting.
- Aliases: 14, at 2022-01-27, 2025-02-20 (5), 2025-05-15, 2025-09-04, 2026-08-06 (5) and 2026-09-03.
- Renames hold their ids: PBI→DJT and 2Y1→47IA (2026-09-03).
- ZPZT moved from the old Zhaotong field to the new one on 2026-01-22, with no overlap.
- NASR non-ISO COUNTRY_CODE across all 86 cycles: AN only (TNCE, TNCM), every cycle.
- **IATA codes held by more than one present airport** (cv-aviation): 51 distinct codes over 13 cycles, 2021-11-04 → 2022-10-06 (50 at most, falling to 22). **0 in every cycle since 2022-11-03.** All are OurAirports-side duplicates, listed per cycle in the report.

## Deviations
1. NASR-authoritative code ownership for standalone OurAirports rows. Found by AC-6: on 2024-04-18 OurAirports marked row 348516 "(Duplicate)" and moved it to (0.004, 0.008) with ident KCPF intact.
2. Format a: blank-status records are left out (CZBB), matching the FAA's CSV.
3. The OurAirports commit list is fetched in quarterly windows (API 422).
4. Format b appears from 2022-11-03, not 2022-12-29 as noted at planning.
5. The largest close count (314 at 2022-12-01, under the guard) was not investigated record by record.

## Next
- 02-02: CI chaining. The first release chains from this seed (sha256 above). It needs the 2026-11-26 cycle or 2026-10-29, and the operator confirms before publishing.
- 02-03: search for an older source (before 2020-03-26).
- Tell cv-aviation: history starts 2020-03-26 (NASR) and 2021-11-04 (OurAirports); the IATA uniqueness result is above.

---
phase: 01-identity-engine
plan: 02
type: summary
status: complete
description: "Schema 3 wired into the build: identity tables, chained build from the previous file, verify guarantees, README."
about: "aeronav-db"
tags: [schema-3, airport-identity, chained-build, verify]
relatedTo: [01-02-PLAN.md, 01-02-AUDIT.md, 01-01-SUMMARY.md]
---

# 01-02 Summary: schema 3 and the chained build

## Delivered
- **aeronav_db/build.py**
  - SCHEMA_VERSION "3"; `IDENTITY_SCHEMA` (the DDL as reviewed); `airports.airport_id NOT NULL`; NASR identifiers typed `faa`.
  - `build_airports_keyed` (the same merge, with each row's source key last); `assign_airport_ids` (an unmapped or ambiguous row raises `BuildError`).
  - `--previous-db` / `--bootstrap`, with `_load_previous` validating PREV before any source is read.
  - The database is written to `<output>.partial`, the identity invariants (and the chain checks when PREV is given) run on it, and it is renamed into place only if they pass.
  - Metadata gains `airport_id_next`, `history_start`, `previous_cycle` and `previous_db_sha256`; the manifest gains `history_start`.
- **aeronav_db/identity.py**
  - `nasr_observations` (all statuses; an unknown ARPT_STATUS raises), `ourairports_observations`, `current_key_index`, `load_state`, `dump_state`.
  - The attachment gate now also accepts a matching NASR COUNTRY_CODE, through `NASR_LEGACY_COUNTRIES` for `AN`.
  - An ICAO code taken from the ident fallback gives way to a code another row states explicitly in `icao_code`.
- **aeronav_db/verify.py**
  - `check_identity`: shape, counter, referential integrity, one-hop aliases, in_current_cycle vs presence, interval bounds, one holder per faa/icao, no overlaps, the IATA multi-holder note, and the cycle-gap warning.
  - `check_chain` / `verify_chain`: no ids lost, closed rows unchanged, open rows closed only at N, no backdated new rows, lineage and checksum.
  - The PBI/DJT canary, `--previous`, and the identity tables in REQUIRED_TABLES.
- **Tests:** tests/test_chain.py (new, 16 tests: end-to-end build() over two cycles), plus additions to test_identity, test_verify and test_build. 118 passed; ruff clean.
- **README:** the "Airport identity and history" section, and build commands updated for `--bootstrap` / `--previous-db`.

## AC results
| AC | Result | Evidence |
|----|--------|----------|
| AC-1 schema written | PASS | test_chain round trip; the real files carry all four tables plus metadata |
| AC-2 chained build | PASS | test_a_rename_keeps_its_id_across_two_files; refusal tests |
| AC-3 observations | PASS | CI/CP present with closure statuses (real Oct file: 321 closed_indefinitely, 3 closed_permanently); the airports merge is unchanged apart from airport_id and code_type |
| AC-4 verify guarantees | PASS | one failing-fixture test per guarantee in test_verify |
| AC-5 README | PASS | new section |
| AC-6 one holder (sqwkd A1) | PASS | real data: 0 violations (below) |
| AC-7 convergence (sqwkd A2) | PASS | test_convergence_across_two_files_passes_verify_previous; real Oct file has 7 convergences and passes verify --previous |
| AC-8 chain input / no half-written file | PASS | same-path, schema-2, corrupt-PREV and failed-invariant tests: the old file is left intact and no .partial remains |
| AC-9 lineage / reproducible | PASS | load/dump round trip; two builds give identical identity tables; lineage keys checked by verify_chain |

## Real-data dry run (measured 2026-11-18)
Inputs:
- NASR full subscriptions for 2026-07-09 and 2026-10-29.
- OurAirports airports.csv at git commits fb8ffe8 (2026-07-08) and 6112986 (2026-10-28).
- The current OurAirports navaids.csv.

All of it lives in the session scratchpad. The files are throwaway: never published and never used as PREV. Phase 2 re-bootstraps from 2021-12.

- **First attempt refused.** The bootstrap failed on its first attempt with `3 icao codes held by more than one airport now: ['TNCE', 'TNCM', 'ZPZT']`. The fail-safe worked. Causes and fixes are under Deviations.
- **2026-07-09 bootstrap:**
  - 27,243 ids, all minted. Codes: faa 19,436, iata 9,058, icao 9,355.
  - Statuses: 325 closed_indefinitely, 3 closed_permanently.
- **2026-10-29 chained:**
  - 27,388 ids, 27,226 present. Match basis for present ids: nasr_site 19,302; ourairports_id 7,777; minted 145; nasr_site_number 1 (40ND); faa_lid_within_1nm 1 (18AL).
  - 162 presence intervals closed. 7 aliases (converged), including AP0020907 (PBI/KPBI) → AP0003340 (DJT/KDJT).
  - The renames hold their ids: 2Y1→47IA (AP0005529) and C00→IL09 (AP0004168).
  - The DJT history: faa DJT and icao KDJT from 2026-07-09, iata DJT from 2026-10-29.
- **Verify:**
  - `verify c1029 --previous c0709` exits 0. It warns that previous_cycle is 112 days back (the dry run skips 3 cycles).
  - `verify c0709` exits 1 on the canary alone. That is real: on 2026-07-08 OurAirports still said PBI/KPBI while NASR already said DJT/KDJT. The two records share no code, so the bootstrap gives the field two ids. They converge in the next file. A Phase 2 bootstrap from 2021-12 (both PBI) does not hit this.

### sqwkd's three items
1. **The 112 after the gate fix (2026-10-29 data).**
   - 118 non-US OurAirports rows now attach to a NASR record: CA 71, BS 25, FM 5, TC 4, MH 3, and 1 each of GL, IO, SH, PW, AI, BM, VG, MF, BQ, SX. That covers the 112 ICAO collisions plus non-US fields joined by another shared code.
   - Standalone OurAirports rows still sharing an ICAO code with a NASR record: **0**. AC-6 violations: **0** in both files.
   - No residual pairs.
2. **NASR COUNTRY_CODE against ISO 3166-1.** Checked against the 249 ISO codes in OurAirports countries.csv:
   - Both cycles have 16 distinct values and 147 non-US rows.
   - Not ISO: **`AN` only, 2 rows** (TNCE F D ROOSEVELT, TNCM PRINCESS JULIANA INTL, both operational). AN is the Netherlands Antilles, dissolved in 2010.
   - This did not fail safe silently. It failed the build loudly, because the TNCE and TNCM ICAO codes then had two holders.
3. **IATA codes held by more than one present airport:** **0** in both files. NASR identifiers live in scheme `faa`, so the US-LID/IATA collisions are not counted. OurAirports carries no duplicate IATA among the selected rows.

## Deviations
1. **The `AN` → {BQ, CW, SX} mapping (`NASR_LEGACY_COUNTRIES`).** Not in the plan; it was found by AC-6 on real data. It is an explicit, tested table and not a guess. A new non-ISO code still fails safe: no attach, and the build fails if a code collides.
2. **ICAO ident fallback gives way to an explicit `icao_code`** (ZPZT, 2026-07-08 snapshot only: the old Zhaotong field's ident against the new field's code). Identity observations only; the airports-layer merge is unchanged.
3. **The canary covers PBI or DJT** (either spelling, but a single id), not DJT only. Sources switched at different cycles, so a DJT-only canary would fail every pre-rename Phase 2 file.
4. **The canary lives in `verify_database`** (the full-data publish gate), not in `check_identity`, which the build runs on every file, fixtures included.
5. **New test file tests/test_chain.py** for the end-to-end chain tests. The plan put them in test_build.py.

## Concerns / carried forward to Phase 2
- **Do not merge this branch to main before Phase 2's CI work.** The main workflow runs `python -m aeronav_db.build` without flags, which is now refused. The refusal is by design: it is the anti-re-mint guard.
- CI needs a PREV source: release N-1 for a rebuild of cycle N, checked against the published manifest's sha256 (sqwkd note).
- **A spurious mint while sources disagree on codes.** When NASR renames before OurAirports, the OurAirports row shares no code, cannot attach, and its prior id is already claimed. It gets a new id that later converges as an alias. Lookups resolve correctly through the alias, but a "sticky attachment" rule (keep a previously attached OurAirports row with its NASR partner while the keys still match) would avoid the extra id. Decide this before the backfill.
- The non-ISO COUNTRY_CODE count must be re-measured over the 2021-12+ archives.
- SonarQube scan not run in this loop.

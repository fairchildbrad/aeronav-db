---
description: "aeronav-db — milestone and phase structure"
type: Roadmap
about: "aeronav-db"
---

# Roadmap: aeronav-db

## Overview
Give airports a permanent identity and a dated code history, so long-lived records (the CerebroVault logbook) survive code changes. Then extend that history back as far as public-domain sources allow.

## Current Milestone
**v0.2 Airport identity & history** (v0.2.0, schema_version 3)
Status: In progress
Phases: 0 of 3 complete

**Release gate:** no schema-3 release ships until Phase 2's backfill has run. A backfill run after release would mint different ids, and cv-aviation was promised ids are never renamed. Timezones are also a release prerequisite. Operator, 2026-11-18: "Keep what we have and publish to cv-aviation with the time zones" (routed by sqwkd). The first schema-3 release therefore follows Phases 1, 2 and 3.

## Phases

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1 | Identity engine + schema 3 | 2 | Planning | - |
| 2 | History backfill + first schema-3 release | 2 | Not started | - |
| 3 | IANA timezones | 1-2 | Not started | - |

## Phase Details

### Phase 1: Identity engine + schema 3
**Goal:** a cycle-to-cycle identity engine and the schema-3 tables, written by a chained build and guarded by verify.
**Plans:**
- [x] 01-01: aeronav_db/identity.py, a pure engine (match, mint, intervals, aliases) with tests
- [x] 01-02: wire into build/schema/verify, add the --previous-db chain input, send the DDL to cv-aviation, update the README
- [x] 01-03: the retired NASR country AN → ISO successor or NULL (release blocker). Unified 2026-11-20
- [x] 01-04: pair OurAirports with NASR through the FAA LID (local_code); one field, one id; renumbered (operator "Renumber now"), tz re-keyed. Unified 2026-11-20

### Phase 2: History backfill + first schema-3 release
**Goal:** run the chain from the oldest reachable NASR archive (≥2021-12) to the current cycle, paired with OurAirports git snapshots; look for a source older than that; publish the first schema-3 release; switch CI to chain from the prior release.
- [x] 02-01: sticky attachment; NASR archive reader (3 formats, from 2020-03-26); resumable backfill → seed.sqlite3 + history report (planned, audited)
- [x] 02-02: CI chaining (PREV = release N-1, sha256 checked against its manifest), first schema-3 release from the seed (operator confirms the release)
- [x] 02-03: search for an older public-domain source (before 2020-03)
- [x] 02-04: format-a layout guard from each archive's own apt_rf.txt; cold-cache reproduction of e92fa5fe byte for byte. Unified 2026-11-20
**Research:** Likely (archive depth, an older public-domain source)
**cv-aviation requests (2026-11-18 review of 01-02):** verification reports whether (iata, code, date) is unique among airports present on that date. If it isn't, add a tie-break source attribute that works without a position (e.g. OurAirports scheduled_service). Note: their logbook data goes back to 2019-09, which is before the NASR archives start (2021-12); they will fall back to the earliest row and mark that link as assumed.

### Phase 3: IANA timezones
**Goal:** add an airport tz column from a hand-maintained country→region→override CSV, validated against tzdata zone1970.tab and the US Chart Supplement offsets.
- [x] 03-01: rules engine, pinned tzdata, US by county, Chart Supplement check
**Operator, 2026-11-19 (routed by sqwkd), verbatim:** "Finish all of the plan-03 before release". Phase 3 done is the release gate, defined in 03-02 AC-1 (`python -m aeronav_db.tz gate`).
- [x] 03-02: gate and mechanism (per-region partial guard, municipality key), then MX and CA. MX 102/102; CA 410/504 present, scheduled 242 placed + 33 unplaced_by_design + 0 unlisted. Unified 2026-11-19 (03-02-SUMMARY.md)
- [x] 03-03: AU, BR, RU, ID. AU 158, BR 126 (+3 unplaced_by_design), RU 129 (+20 Sakha unplaced_by_design), ID 123 scheduled placed, 0 unlisted; zone_regions.csv completes the partial list for mapped countries. Unified 2026-11-19 (03-03-SUMMARY.md)
- [x] 03-04 (unified 2026-11-19, 03-04-SUMMARY.md): the other 26 multi-zone countries (AQ NULL by design). Carried from 03-03 (sqwkd R2): AC "a zone with no rows for country X is allowed only if zone_regions maps it to a region of another country listed for it in zone1970; test included", due when UA is mapped
- [x] 03-05: US scheduled-service remainder via the Chart Supplement; closing gate run
- [x] 03-07: L-type follow-up: Jackpot, Owyhee and Mountain City NV on Mountain (L4); Hyder NULL; West Wendover closed; Prince of Wales deferred. Unified 2026-11-21
**cv-aviation requirement:** tz is never guessed. tz_basis 'country' is allowed only for single-zone countries. An airport in a multi-zone country that the region/override rules can't place gets tz NULL.

---
*Roadmap created: 2026-11-07*

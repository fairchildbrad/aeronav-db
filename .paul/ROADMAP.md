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

**Release gate:** no schema-3 release ships until Phase 2's backfill has run. A backfill run after release would mint different ids, and cv-aviation was promised ids are never renamed.

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
- [ ] 01-02: wire into build/schema/verify, add the --previous-db chain input, send the DDL to cv-aviation, update the README

### Phase 2: History backfill + first schema-3 release
**Goal:** run the chain from the oldest reachable NASR archive (≥2021-12) to the current cycle, paired with OurAirports git snapshots; look for a source older than that; publish the first schema-3 release; switch CI to chain from the prior release.
**Research:** Likely (archive depth, an older public-domain source)

### Phase 3: IANA timezones
**Goal:** add an airport tz column from a hand-maintained country→region→override CSV, validated against tzdata zone1970.tab and the US Chart Supplement offsets.

---
*Roadmap created: 2026-11-07*

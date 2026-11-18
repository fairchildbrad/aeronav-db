---
description: "Software gets a free, offline, public-domain aviation reference it can update unattended and trust across cycles, including permanent airport identities."
type: Project
about: "aeronav-db"
---

# aeronav-db

## What This Is

A public-domain aeronautical database (airports, navaids, fixes, airways, ARTCC/FIR boundaries) compiled into one SQLite file and rebuilt every AIRAC cycle by GitHub Actions. Releases ship at stable "latest" URLs with a manifest and a sha256.

## Core Value

Software gets a free, offline, public-domain aviation reference it can update unattended and trust across cycles, including permanent airport identities.

## Current State

| Attribute | Value |
|-----------|-------|
| Type | Application (data pipeline / published dataset) |
| Version | 0.1.0 (schema_version 2) |
| Status | Beta |
| Last Updated | 2026-11-07 |

## Requirements

### Core Features
- Airports, navaids, fixes, airways and boundaries merged from FAA NASR (authoritative in the US) and OurAirports (global layer)
- Automatic per-cycle build → verify gate → GitHub release
- Licence and disclaimer travel inside the database
- Permanent airport identity plus code history, dated by `effective_date` (cv-aviation request, 2026-11-06)

### Validated (Shipped)
- [x] Airports, navaids, fixes (schema 1)
- [x] Airways, ARTCC/FIR boundaries (schema 2)

### Active (In Progress)
- [ ] Schema 3: airport identity and code history

### Planned (Next)
- [ ] Backfill history from FAA NASR archives (served back to at least 2021-12) and OurAirports git history
- [ ] Find a further historical source that predates the FAA archives
- [ ] Per-airport IANA timezone (v0.2, final phase) from a self-maintained country→region→override table; validated against tzdata zone1970.tab and US Chart Supplement offsets

### Out of Scope
- Any non-public-domain source. Licensing is the one real exclusion.
- Certified navigation use

## Constraints

### Technical Constraints
- The output stays a single SQLite file. Consumers load it.
- Deterministic for a given SQLite version and the same inputs. With history, the inputs include the prior release.
- Consumers update unattended, so verify is a hard publish gate.

### Business Constraints
- cv-aviation / CerebroVault consume the dataset through the manifest and sha256 (CV ISSUE-127). Nothing in CV is blocked on this work.

## Key Decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| aeronav-db mints its own airport_id. Source keys are attributes, not the id. | Verified: NASR SITE_NO is unique only together with SITE_TYPE_CODE and does get corrected (18AL); OurAirports ids are deleted on merge with no forwarding pointer | 2026-11-06 | Active |
| airport_id format is opaque text with a prefix ("AP000123"), case-insensitive, never renamed. Merges go through airport_aliases, at most one hop. | cv-aviation's choice: the id is embedded in CV entity keys and must not look like a row number or a source code | 2026-11-07 | Active |
| Code intervals carry an `effective_date` set to the AIRAC cycle date | Operator: "use the cycle date for the change date, not necessarily 'first published in cycle N' but an 'effetive_date' field" | 2026-11-07 | Active |
| History depth: "Use the archives to fill in as much history as you can then attempt to locate another histoical source to fill in more history." | Operator, verbatim | 2026-11-07 | Active |
| Timezones are in v0.2, as a later phase. Operator: "V0.2 and build it now" | No public-domain IANA boundaries exist; a hand-maintained table needs no polygons | 2026-11-18 | Active |
| Leaving the dataset means "absent from cycle N", not "closed", unless a source says closed | cv-aviation point 3; 98 operational NASR fields vanished between 2026-07 and 2026-10 with no closure status | 2026-11-06 | Active |

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Every airport_id in release N-1 still resolves in release N | 100%, enforced by verify | - | Not started |
| Past code intervals rewritten between releases | 0, enforced by verify | - | Not started |
| Code lookup by date | One indexed query | - | Not started |

## Tech Stack / Tools

| Layer | Technology | Notes |
|-------|------------|-------|
| Language | Python 3.12, uv | ruff and pytest gate CI |
| Output | SQLite | standing exception to the global Postgres policy |
| CI/CD | GitHub Actions + Releases | weekly cycle check |
| Sources | FAA NASR 28-day, OurAirports | both public domain |

## Links

| Resource | URL |
|----------|-----|
| Repository | https://github.com/fairchildbrad/aeronav-db |

---
*Created: 2026-11-07*

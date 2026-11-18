---
description: "aeronav-db — current position and accumulated context"
type: ProjectState
about: "aeronav-db"
---

# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-11-07)

**Core value:** Software gets a free, offline, public-domain aviation reference it can update unattended and trust across cycles, including permanent airport identities.
**Current focus:** v0.2 Airport identity & history. Project initialized, ready for planning.

## Current Position

Milestone: v0.2 Airport identity & history
Phase: 1 of 3 (Identity engine + schema 3), complete
Plan: 01-02 complete (01-02-SUMMARY.md)
Status: PLAN created; apply+unify pre-approved by operator once both reviewers OK ("have both sqwkd and cv-aviation review it.  If they are okay with it, apply and unify are approved next")
Last activity: 2026-11-18. 01-02 applied + unified; real 2-cycle chain verified

Progress:
- Milestone: [███░░░░░░░] 33%
- Milestone: Phase 1 of 3 done
- Phase 1: [██████████] 100%

## Loop Position

```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [01-02 loop closed]
```

## Accumulated Context

### Decisions
- id width: AP + 7 digits ("AP0000123"). Operator, verbatim, relayed by sqwkd 2026-11-18, answering "6 or 7": "7"
- airport_id is minted text with a prefix ("AP000123"), case-insensitive, never renamed; aliases resolve in one hop (cv-aviation, 2026-11-07)
- Code intervals carry `effective_date` set to the cycle date (operator)
- Backfill from the FAA archives, then find an older source (operator)

- 2026-11-18: Enterprise audit performed on .paul/phases/01-identity-engine/01-02-PLAN.md. Applied 4 must-have, 3 strongly-recommended upgrades. Deferred 2. Verdict: conditionally acceptable, ready for APPLY (Phase 1)
- 2026-11-18: The OurAirports→NASR attachment gate also accepts a matching NASR COUNTRY_CODE. 112 non-US fields would otherwise hold duplicate ICAO intervals (found while adopting sqwkd A1)

- 2026-11-18: sqwkd approved the gate fix + audit fixes ("the gate fix is OK, and so are the audit fixes. Apply 01-02.")
- 2026-11-18: NASR COUNTRY_CODE 'AN' maps to ISO successors BQ/CW/SX; an ICAO code derived from the ident yields to an explicit icao_code (both found by AC-6 on real data)

### Deferred Issues
- (resolved 2026-11-18) Timezone: operator "V0.2 and build it now". It's a later phase of v0.2, using a self-maintained country→region→override table of IANA zones, no polygons.

### Blockers/Concerns
- DO NOT MERGE feat/airport-identity to main before Phase 2's CI chaining: the main workflow's flagless build is now refused (by design)
- Phase 2 decision: sticky OurAirports↔NASR attachment while sources disagree on codes (avoids a spurious id that later becomes an alias)
- Process: from 01-02 on, the plan goes to the operator for approval and then the audit runs (sqwkd routing, 2026-11-18). 01-01 ran under "V0.2 and build it now", with the audit skipped.
- RELEASE GATE: no schema-3 release before the Phase 2 backfill (it would re-mint ids)
- The build becomes chained (it needs release N-1). A forced rebuild of cycle N must use N-1, not the latest release.
- ourairports.com TLS certificate expired 2026-11; use the GitHub data mirror

## Session Continuity

Last session: 2026-11-07
Stopped at: 01-02 loop closed; SUMMARY sent to sqwkd
Next action: /paul:plan Phase 2 (backfill + CI chaining + first schema-3 release); send the final DDL to cv-aviation
Resume file: .paul/phases/01-identity-engine/01-02-SUMMARY.md

---
*STATE.md — Updated after every significant action*

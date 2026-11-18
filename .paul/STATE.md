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
Phase: 1 of 3 (Identity engine + schema 3), Applying
Plan: 01-01 complete (UNIFY done); 01-02 next
Status: Ready to plan 01-02
Last activity: 2026-11-18. Created phases/01-identity-engine/01-01-PLAN.md

Progress:
- Milestone: [░░░░░░░░░░] 0%
- Phase 1: [█████░░░░░] 50%

## Loop Position

```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [01-01 loop closed]
```

## Accumulated Context

### Decisions
- airport_id is minted text with a prefix ("AP000123"), case-insensitive, never renamed; aliases resolve in one hop (cv-aviation, 2026-11-07)
- Code intervals carry `effective_date` set to the cycle date (operator)
- Backfill from the FAA archives, then find an older source (operator)

### Deferred Issues
- (resolved 2026-11-18) Timezone: operator "V0.2 and build it now". It's a later phase of v0.2, using a self-maintained country→region→override table of IANA zones, no polygons.

### Blockers/Concerns
- RELEASE GATE: no schema-3 release before the Phase 2 backfill (it would re-mint ids)
- The build becomes chained (it needs release N-1). A forced rebuild of cycle N must use N-1, not the latest release.
- ourairports.com TLS certificate expired 2026-11; use the GitHub data mirror

## Session Continuity

Last session: 2026-11-07
Stopped at: 01-01 unified
Next action: /paul:plan 01-02 (schema 3 tables, builder observations, --previous-db chain, verify, DDL to cv-aviation)
Resume file: .paul/phases/01-identity-engine/01-01-SUMMARY.md

---
*STATE.md — Updated after every significant action*

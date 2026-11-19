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
Phase: 3 of 3 (IANA timezones), 03-01 unified
Plan: 03-02 APPLY in progress (sqwkd OK + M1, C1-C3; cv-aviation OK + notes). Task 1 done f769497; MX done 9f3f5a6 (102/102 placed). CA blocked: Ontario Time Act is a pure 90°W meridian rule but observed time in NW Ontario differs; asked sqwkd 2026-11-19 (proposal: rule-cited ON rows only east of 85°W, vendor tzdata northamerica for named anomalies). Operator 2026-11-19: "Finish all of the plan-03 before release". Release runbook not started
Status: PLAN created; apply+unify pre-approved by operator once both reviewers OK ("have both sqwkd and cv-aviation review it.  If they are okay with it, apply and unify are approved next")
Last activity: 2026-11-18. 02-01 applied + unified; 86-cycle backfill reproducible

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

- 2026-11-18: Sticky OurAirports↔NASR attachment adopted. Operator, verbatim: "Agree with our airports record matching.  Proceed with phase 2"

- 2026-11-19: tz stays on airport_identity only; no airports.tz. cv-aviation: "airport_identity is enough for Aviation". cv-core: "(a). Core needs no tz on `airports`, because core never reads your tables."

- 2026-11-19 03-01 apply notes: tz columns already in IDENTITY_SCHEMA (build.py:158); add tz_unplaced. Region inputs: NASR APT_BASE.csv STATE_CODE + COUNTY_NAME (build.py:1076 has nasr["APT_BASE.csv"]), OurAirports iso_region. Identity dataclass identity.py:95; dump_state identity.py:640. Vendor zone1970.tab (host tzdata 2026f) to identity/tz/. Send cv-aviation the DDL delta when done.

### Deferred Issues
- (resolved 2026-11-18) Timezone: operator "V0.2 and build it now". It's a later phase of v0.2, using a self-maintained country→region→override table of IANA zones, no polygons.

### Blockers/Concerns
- DO NOT MERGE feat/airport-identity to main except via docs/RELEASE-RUNBOOK.md (after Phase 3, operator-confirmed): merging switches CI to schema 3
- Process: from 01-02 on, the plan goes to the operator for approval and then the audit runs (sqwkd routing, 2026-11-18). 01-01 ran under "V0.2 and build it now", with the audit skipped.
- RELEASE GATE: no schema-3 release before the Phase 2 backfill (it would re-mint ids)
- The build becomes chained (it needs release N-1). A forced rebuild of cycle N must use N-1, not the latest release.
- ourairports.com TLS certificate expired 2026-11; use the GitHub data mirror

## Session Continuity

Last session: 2026-11-07
Stopped at: 01-02 loop closed; SUMMARY sent to sqwkd
Next action: /paul:plan 02-03 (older source search), then Phase 3 timezones; first release via docs/RELEASE-RUNBOOK.md (operator-confirmed)
Resume file: .paul/phases/02-history-backfill/02-02-SUMMARY.md

---
*STATE.md — Updated after every significant action*

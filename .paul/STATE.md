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
Phase: 3 of 3 (IANA timezones). 03-01 to 03-04 unified; 03-05 remains.
Plan: 03-03 unified 2026-11-19 (.paul/phases/03-iana-timezones/03-03-SUMMARY.md). sqwkd, verbatim: "sqwkd check of 03-03: OK. Unify."
  Build of record: scratchpad tz4/navigation.sqlite3, sha256 05e6892a…, same inputs as tz3b (seed e92fa5fe…, NASR/OurAirports/navaids 2026-10-29). Placed 24,894, unplaced 2,332. tz gate exit 1 only for 03-04/05 countries.
  Patterns carried into 03-04 (as for 03-03, plus): zone_regions.csv mapping per country with the AC-2 check; R1 (where zones agree today, the zone whose history matches); S2 mainland exception; L4 list now Labrador + Eucla (Crimea joins in 03-04).
  Scratch tools add: scripts/{au_rows,xingu}.py.
  Optional: Rosstat OKTMO for the 20 Sakha airports. Q2 (ERSA/AIPs as a check) is the operator's decision.
Operator 2026-11-19: "Finish all of the plan-03 before release". The release runbook is not started.
Status: 03-04 PLAN approved 2026-11-19 by cv-aviation and sqwkd (rulings recorded in the plan: Q1 Xinjiang → Shanghai via overrides; Q2 name-cited only for CD/UZ, VN Bến Hải only if tzdata states it; Q3 Crimea precedent, PS per-place; Q4 timeboxed PF search). 03-04 unified 2026-11-19 (sqwkd OK after three fixes). Build of record: scratchpad tz5/navigation.sqlite3, sha256 2418b7a5…; placed 26,425, unplaced 801; gate prints US lines only. 03-05 PLAN approved 2026-11-20 (cv-aviation OK; sqwkd OK after five changes and three edits). D1: US stays exempt permanently. Next: APPLY 03-05 (Codex in /workspace/aeronav-db-codex, owning session verifies and commits), then unify, then sqwkd checks the SUMMARY and gate output before the merge to main.
Last activity: 2026-11-19. 03-03 unified.

Progress:
- Milestone: [███████░░░] 73%
- Milestone: Phases 1-2 done; Phase 3 in progress
- Phase 3: [████████░░] 4 of 5 plans

## Loop Position

```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [03-04 loop closed]
```

## Accumulated Context

### Decisions
- 2026-11-19: Operator, verbatim (relayed by sqwkd): "Yes to both questions". (1) Q2 of 03-03: official AIPs and Australia's ERSA may be read as an independent check only, never as a placement source; only free, no-login publications; no fetch workarounds or User-Agent change; nothing stored, not even printed offsets; record the edition, number checked, match count and airport_ids of mismatches; fix each mismatch or set it NULL from a cited non-AIP source. Running the checks for AU, BR, RU, ID and the 03-04 countries needs its own plan (not 03-05). (2) The UZ reversal (03-04 D2, the 1991 decree list as R1 evidence) is confirmed.
- 2026-11-20: Operator, verbatim, on merging feat/airport-identity into main: "Verify with sqwkd then merge and commit", then "Once phase 3 closes". Order per sqwkd 2026-11-20: 03-05 unified; gate exit 0 on own re-run; SUMMARY commit and gate/verify output to sqwkd; sqwkd OK; then the merge, locally only. The Phase 1 AN release blocker is separate and still open. This does not cover push, tag, release or seed upload; each of those still needs the operator's confirmation.
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
- (open, after 03-05; cv-aviation 2026-11-19, 7d7ca8b) 3,171 historic US airports have tz NULL (no_region), including logbook stations IGX (Horace Williams, Chapel Hill NC; 13 legs 2005-2014) and NC47 (2012). Proposal: retired airports in a single-zone state take that state's rule via the NASR state. Not a gate item; needs its own plan and review.
- (resolved 2026-11-18) Timezone: operator "V0.2 and build it now". It's a later phase of v0.2, using a self-maintained country→region→override table of IANA zones, no polygons.

### Blockers/Concerns
- RELEASE BLOCKER (Phase 1, found in 03-04; sqwkd 2026-11-19: "Phase 1 handles it before release, with its own review and verify --previous"): identity iso_country stays NASR's retired "AN" for TNCE (AP0019780) and TNCM (AP0019781), although OurAirports and tz placement give BQ and SX. Tz is unaffected (both America/Puerto_Rico); the identity column needs a Phase 1 decision before release.
- DO NOT MERGE feat/airport-identity to main except via docs/RELEASE-RUNBOOK.md (after Phase 3, operator-confirmed): merging switches CI to schema 3
- Process: from 01-02 on, the plan goes to the operator for approval and then the audit runs (sqwkd routing, 2026-11-18). 01-01 ran under "V0.2 and build it now", with the audit skipped.
- RELEASE GATE: no schema-3 release before the Phase 2 backfill (it would re-mint ids)
- The build becomes chained (it needs release N-1). A forced rebuild of cycle N must use N-1, not the latest release.
- ourairports.com TLS certificate expired 2026-11; use the GitHub data mirror

## Session Continuity

Last session: 2026-11-19
Stopped at: 03-04 loop closed
Next action: /paul:plan 03-05
Resume file: .paul/phases/03-iana-timezones/03-04-SUMMARY.md

---
*STATE.md — Updated after every significant action*

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
Phase: 3 of 3 (IANA timezones). 03-01 and 03-02 unified; 03-03 to 03-05 remain.
Plan: 03-02 unified 2026-11-19 (.paul/phases/03-iana-timezones/03-02-SUMMARY.md). The sqwkd check was passed, with rulings: D1 same-CD option (a); Tungsten and the 9 YT CFS mismatches stay placed and are listed; Saltspring normalisation OK; 35 rows with no gazetteer coordinate accepted.
  Build of record: scratchpad tz3b/navigation.sqlite3, sha256 59c06c87…, from seed b0303/seed-run1.sqlite3 (e92fa5fe…), dl/nasr-2026-10-29.zip, dl/oa-2026-10-29.csv, dl/navaids.csv. Placed 23,565, unplaced 3,661. tz gate exit 1: only 03-03/04/05 countries fail (AN AR AU BR CD CL CN CY DE EC ES FM GL ID KI KZ MH MN MY NZ PF PG PT RU US UZ VN XK).
  Patterns carried into 03-03+:
    - statute + vendored tzdata anomalies (O3) + 0.5° margin (O1/C3);
    - statutory residual where a current statute gives one clock (BC s.26, SK, NT);
    - named-place S2 box;
    - L1 observed clock over statute only where tzdata addresses the legal position (L4: README + SUMMARY list; Crimea goes there in 03-04);
    - airport-keyed overrides applying a statute's rule;
    - AC-3a lint (scratch scripts/lint.py) and CFS-style independent checks used as a check, never a source;
    - blocked fetches (403 or landing page) are never bypassed and are listed as deviations.
  Scratch tools: scripts/{hextext,html2txt,cfs_compare,lint,qc_rows,sk_rows,nu_rows,ytnt_rows,terr_plan}.py; cgn/*.zip (CGNDB), sgc/structure.csv.
Operator 2026-11-19: "Finish all of the plan-03 before release". The release runbook is not started.
03-03 APPLY in progress (sqwkd + cv-aviation OK). Done: AC-2 zone_regions 29654aa; BR 0c37247.
  Progress at 73e9548:
    - AU done (4f6bf77, 16b042f; Proserpine S2 mainland exception).
    - ID done (de4e26b, 16b042f; derived provinces per sqwkd's territory ruling; UU numbers identification-only, from pasal.id).
    - RU done (73e9548; 20 Sakha scheduled airports in UBD; RU-SA and RU-SAK caught by the zone_regions check).
    - BR rules done (0c37247).
  Remaining:
    - BR AM DONE 393dbf2: IBGE centroids, not seats (the API gives none); 8 Manaus overrides; Tabatinga in UBD. sqwkd R1 (South Kurils quoted) and R2 (only a shared zone may map to no region, with a test) DONE 2a695ec. Optional: Rosstat OKTMO for the 20 Sakha airports.
    - BR PA: candidates are the ANA 'rios principais' shapefile (SNIRH metadata record a01764d3-...; SAD69) and IBGE BHB250. Each needs a minimal shapefile reader (no GIS library is installed); not yet fetched. Asked sqwkd. b44f7e3 records the AM centroid bound and carries R2 to 03-04 in ROADMAP. SUMMARY 'carried forward': the R2 check.
    - Then: canaries (YSSY YBBN YPPH YPAD YBHI SBGR SBEG SBBE SBRB SBFN UUEE UNNT UHWW UEEE UHPP WIII WADD WAJJ WIOO), the build from the seed (tz3b inputs), verify, gate, AC-3a lint, CFS-like check (none: Q2 with the operator), README L4 (add Eucla), SUMMARY, unify.
  SUMMARY must also record:
    - AC-2's check is opt-in per mapped country (CA MX BR AU ID RU mapped); it caught RU-SA and RU-SAK; the other 26 countries are mapped in 03-04.
    - Deviations: tzdata-only citations for VIC, NT, NSW (403), QLD (PDF not extractable), TAS, BR (planalto reset) and RU (107-FZ not fetched).
  SUMMARY Deviations must record:
    - planalto.gov.br resets the automated client. One browser-UA curl was made; its output was deleted unused and nothing was derived from it.
    - One WebFetch read of Lei 12.876; its content was not used for any row.
  sqwkd: "don't repeat it". BR citations rest on tzdata southamerica unless the operator supplies the laws.
  BR open items:
    - AM, option (c): IBGE seat coordinates for Tabatinga and Porto Acre; 0.5° from the great-circle segment; Tabatinga goes to UBD.
    - PA, option (a): Xingu longitude range in PA from IBGE BC250 or ANA hydrography; places north of the Amazon NULL unless named; if no fetchable source, option (b).
Status: Loop closed for 03-02. Next: /paul:plan 03-03 (AU, BR, RU, ID), reviewed by sqwkd and cv-aviation before APPLY.
Last activity: 2026-11-19. 03-02 unified.

Progress:
- Milestone: [███████░░░] 73%
- Milestone: Phases 1-2 done; Phase 3 in progress
- Phase 3: [████░░░░░░] 2 of 5 plans

## Loop Position

```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [03-02 loop closed]
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

Last session: 2026-11-19
Stopped at: 03-02 loop closed
Next action: /paul:plan 03-03 (AU, BR, RU, ID) → sqwkd + cv-aviation review → APPLY
Resume file: .paul/phases/03-iana-timezones/03-02-SUMMARY.md

---
*STATE.md — Updated after every significant action*

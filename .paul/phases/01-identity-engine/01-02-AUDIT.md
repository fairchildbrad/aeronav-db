---
type: AuditReport
status: complete
tags: [audit, schema-3, airport-identity]
relatedTo: [01-02-PLAN.md]
about: "aeronav-db"
---

# Enterprise Plan Audit Report

**Plan:** .paul/phases/01-identity-engine/01-02-PLAN.md (as amended with sqwkd's A1 and A2)
**Audited:** 2026-11-18
**Verdict:** conditionally acceptable. It is acceptable after the upgrades below, which have been applied.

## 1. Executive Verdict
Conditionally acceptable. The format guarantees are sound, but the plan left the chain's input unguarded. A wrong, stale or same-path PREV could destroy or fork history without any error. The plan also did not say what happens to an airports row that can't be mapped to an id. With the AC-8 and AC-9 upgrades applied, I would approve it for APPLY. It is not a release: the release gate (Phases 2 and 3) still stands.

## 2. What Is Solid
- The engine is pure, so the weekly build and the backfill share one code path. Determinism is tested.
- The `--bootstrap` flag makes it impossible to re-mint ids by accident.
- The verify `--previous` checks make the append-only promise mechanically enforceable, not just documented.
- The boundaries say no CI change and no release, so nothing reaches consumers from this plan.
- Absent is kept separate from closed, and closure comes only from a source.

## 3. Enterprise Gaps Identified
1. `write_database` unlinks the output path before writing. If `--previous-db` is the output path, PREV is deleted before it is read. A crash mid-write also leaves a partial file at the published path.
2. PREV was not validated: its schema version, its airport_id_next against its highest id, and its own invariants. A corrupt PREV would propagate silently.
3. The fallback for an airports row with no id was unspecified (NULL, mint, or fail?).
4. There was no lineage record of which parent file a build was chained from, so a bad id fork could not be reconstructed after an incident.
5. There was no round-trip test of load_state/dump_state. A lossy persistence layer would rewrite closed intervals one cycle later.
6. Foreign keys are declared, but SQLite does not enforce them by default.
7. A skipped cycle (PREV two cycles back) silently shifts change dates by one cycle.
8. A rebuild of the same cycle (weekly CI inside a 28-day cycle) must chain from N-1, not N. That is CI's concern.

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)
| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | Gap 1: PREV equal to the output path; non-atomic write | AC-8, Task 1, verification | Refuse when the paths are the same; write to a temp file, then rename after the invariants pass |
| 2 | Gap 2: PREV not validated | AC-8 | Schema 3 required, the counter checked, PREV invariants checked, `--bootstrap` plus PREV rejected |
| 3 | Gap 3: unmapped airports row | AC-8 | The build fails; no NULL and no mint |
| 4 | Gap 5: persistence round trip | AC-9, Task 1 | Round-trip test plus a two-build determinism test |

### Strongly Recommended
| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | Gap 4: lineage | AC-9, DDL metadata | previous_cycle and previous_db_sha256 |
| 2 | Gap 6: foreign keys not enforced | AC-9, Task 2 | Verify checks referential integrity and that in_current_cycle matches the open presence row |
| 3 | Gap 7: skipped cycle | AC-9, Task 2 | Verify warns when previous_cycle is not 28 days earlier |

### Deferred (Can Safely Defer)
| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| 1 | Gap 8: CI chaining for same-cycle rebuilds | This plan does not touch CI (a boundary). AC-2 already makes the wrong choice fail loudly, not silently. Phase 2 owns CI chaining and the sha256 manifest check (sqwkd note). |
| 2 | A hard refusal on a cycle gap | Archive gaps are possible in the Phase 2 backfill. Warn now and decide the policy there. |

## 5. Audit & Compliance Readiness
- Evidence: every file now names its parent (cycle and sha256). Verify `--previous` is the per-release proof that history was not rewritten.
- Silent failure: an unmapped row, a bad PREV, a duplicate FAA/ICAO holder, or a broken reference all fail the build.
- Reconstruction: the lineage chain plus the append-only tables let any file be traced back to history_start.
- Ownership: aeronav-db owns the format. cv-aviation and sqwkd are recorded reviewers.

## 6. Final Release Bar
This plan does not ship a release. Before the first schema-3 release: Phase 2 (backfill, plus CI chaining with a manifest-checked PREV) and Phase 3 (timezones). If 01-02 were shipped as it was before this audit, a single mistyped flag could destroy history. With the upgrades applied, I would sign off on 01-02's output as a pre-release.

---
**Summary:** Applied 4 must-have and 3 strongly-recommended upgrades. Deferred 2.
**Plan status:** updated and ready for APPLY

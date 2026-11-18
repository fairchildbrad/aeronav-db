---
type: AuditReport
status: complete
tags: [audit, ci, release-lineage]
relatedTo: [02-02-PLAN.md]
about: "aeronav-db"
---

# Enterprise Plan Audit Report

**Plan:** .paul/phases/02-history-backfill/02-02-PLAN.md
**Audited:** 2026-11-18
**Verdict:** conditionally acceptable. It is acceptable after the upgrades below, which have been applied.

## Gaps
1. **A forced rebuild of N after N+1 exists forks the lineage.** The workflow deletes and recreates tag N, so N+1's previous_db_sha256 no longer matches anything.
2. **The integrity check trusts the same release that supplies the file.** Comparing against that release's own manifest catches corruption, not a coordinated swap of the database and manifest.
3. **Silent semantic break for existing consumers.** /releases/latest moves to schema 3, NASR 3-letter identifiers flip from 'iata' to 'faa', and airports gains a column.
4. Release immutability depends on repository settings (deferred).

## Upgrades Applied
| # | Class | Finding | Change |
|---|-------|---------|--------|
| 1 | Must-have | Gap 1 | AC-2 refuses a forced rebuild of N when a newer schema-3 release exists |
| 2 | Strongly recommended | Gap 2 | AC-6: P's parent hash must chain to the previous release's manifest or the seed pin |
| 3 | Strongly recommended | Gap 3 | Migration notice in the first schema-3 release notes and the README |

## Deferred
| # | Finding | Rationale |
|---|---------|-----------|
| 1 | Turn on GitHub immutable releases / tag protection | A repository setting, not code. It is an operator decision at first release; to be raised then. |

**Summary:** Applied 1 must-have and 2 strongly-recommended upgrades. Deferred 1.
**Plan status:** ready for sqwkd review.

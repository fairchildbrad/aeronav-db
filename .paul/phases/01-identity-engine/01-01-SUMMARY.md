---
phase: 01-identity-engine
plan: 01
type: summary
status: complete
description: "Pure identity engine shipped: AP-prefixed ids, code intervals, presence, one-hop aliases."
about: "aeronav-db"
tags: [airport-identity, schema-3, identity-engine]
---

# 01-01 Summary: identity engine

## Delivered
- `aeronav_db/identity.py`: `apply_cycle`, `lookup`, `normalize_id`, plus dataclasses (Observation, Identity, CodeInterval, Presence, Alias, IdentityState). Pure, deterministic, no new dependencies.
- `tests/test_identity.py`: 19 tests covering AC-1 to AC-6. Full suite 81 passed; ruff clean.

## AC results
All of AC-1 through AC-6 pass.

## Real-data check (2026-07-09 → 2026-10-29 NASR, engine only)
- 19,436 ids minted in cycle 1. In cycle 2: 19,302 matched by site, 1 by site number (40ND type change), 1 by FAA LID within 1 nm (18AL correction), 130 minted, 132 absent.
- This reconciles with the independent manual diff (134 gone / 132 new by (site, type), less the 2 recovered).
- 2Y1→47IA and C00→IL09 keep their ids.

## Deviations
- The id is AP + **7** digits (cv-aviation's example had 6). This avoids a capacity cliff, since OurAirports alone already has 86k rows. Must be flagged to cv-aviation with the DDL in 01-02.
- Merged identities keep their identity row (history stays under the old id). Consumers resolve through the alias in one hop.
- The plan audit was skipped under the operator directive "V0.2 and build it now".

## Next
01-02: schema-3 tables + builder observations (NASR including CI/CP, OurAirports) + `--previous-db` chain input + verify guarantees + README. Send the DDL to cv-aviation. No schema-3 release before the Phase 2 backfill.

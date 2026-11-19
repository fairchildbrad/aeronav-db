---
phase: 02-history-backfill
plan: 02
type: summary
status: complete
description: "CI chains each build from release N-1 (hash-checked, one-hop lineage) or the pinned seed; prepared on the branch, nothing published."
about: "aeronav-db"
tags: [ci, chained-build, release-lineage, seed]
relatedTo: [02-02-PLAN.md, 02-02-AUDIT.md, 02-01-SUMMARY.md]
---

# 02-02 Summary: CI chaining

## Delivered
- **aeronav_db/chain.py:** `python -m aeronav_db.chain previous --cycle N --out DIR`.
  - Source (a): the newest schema-3 `cycle-D` release with D < N. Its database sha256 must match both the manifest and the .sha256 asset, it must pass check_identity, and its parent hash must chain one hop back to a release or the seed pin.
  - Source (b): the seed in `identity/seed.json`. It is refused while `published` is false, unless `--seed-path` is given (dry runs only).
  - Refuses a hash mismatch, a gap (unless `--allow-gap`), and a rebuild of N when a newer schema-3 release exists. Every network call is logged.
- **identity/seed.json:** cycle 2026-10-01, sha256 c6c09037…c54f4, url `…/identity-seed-2026-10-01/seed.sqlite3`, published false.
- **.github/workflows/build.yml:**
  - New `allow_gap` input.
  - **The build job has `concurrency: {group: aeronav-release, cancel-in-progress: false}`** (sqwkd), in addition to the existing workflow-level group.
  - New steps: chain previous → build --previous-db → verify --previous.
  - A pre-publish re-check refuses to replace an existing `cycle-N` unless force is set.
  - The release notes carry history_start and the previous cycle and sha. The first schema-3 release (source = seed) carries the migration notice.
  - The check job is unchanged.
- **build.py:** the manifest gains `previous: {cycle, sha256}`.
- **README:** CI chain and trust-model note (sqwkd). **docs/RELEASE-RUNBOOK.md:** the operator-confirmed cutover, timed between cycles (2026-11-26, 2026-12-24).
- **Tests:** tests/test_chain_ci.py, 11 tests. Full suite: 143 passed; ruff clean.

## AC results
| AC | Result | Evidence |
|----|--------|----------|
| AC-1 resolution | PASS | Tests; dry run B1 and B2 |
| AC-2 refusals | PASS | Tests; dry run A1, B3, B4 and B5 |
| AC-3 workflow | PASS | YAML parses (system PyYAML); the build job's steps in order: Install, Test, Resolve the previous file, Build, Verify, Checksum, Summarize, Publish. actionlint was not run during apply (not installed; the uvx fetch was denied). **Resolved afterwards, 2026-11-19:** sqwkd ran actionlint v1.7.12 on 67420c8 at the operator's direct request ("Download and use actionlint", relayed by sqwkd); no findings, exit 0. The shellcheck pass over `run:` scripts was skipped (shellcheck not installed) |
| AC-4 seed pin | PASS | test_the_pin_matches_the_local_seed_when_present |
| AC-5 dry run | PASS | Below |
| AC-6 one-hop lineage | PASS | test_a_swapped_database_with_an_edited_manifest_fails_lineage; dry run B5 |

## Dry run (2026-11-18)
- **A1:** real GitHub releases, unpublished seed, no override. Refused: "the first schema-3 release chains from the seed, which is not published yet". Exit 2.
- **A2:** real releases plus the local seed. Source seed (all five releases are schema 2), cycle 2026-10-01, sha c6c09037…
  - Build 2026-10-29 → verify --previous exit 0.
  - The manifest says schema 3, history_start 2020-03-26, previous {2026-10-01, c6c09037…}. Built database sha256 2ea271df…
- **Simulated release directory**, with that 2026-10-29 file as release cycle-2026-10-29:
  - B1, target 2026-11-26 → release cycle-2026-10-29 (path a; lineage to the seed pin OK).
  - B2, forced rebuild of 2026-10-29 → seed (N-1).
  - B3, rebuild of 2026-10-01 → refused: "would fork the lineage".
  - B4, target 2026-12-24 → refused: 56-day gap, "build 2026-11-26 first".
  - B5, a rogue bootstrap database with a matching manifest and .sha256 → refused: "parent '' is neither a schema-3 release nor the pinned seed". No output written.

### GitHub API calls made (read-only; identical in A1 and A2)
```
GET https://api.github.com/repos/fairchildbrad/aeronav-db/releases?per_page=100&page=1
GET https://github.com/fairchildbrad/aeronav-db/releases/download/cycle-2026-10-29/manifest.json
GET https://github.com/fairchildbrad/aeronav-db/releases/download/cycle-2026-10-01/manifest.json
GET https://github.com/fairchildbrad/aeronav-db/releases/download/cycle-2026-09-03/manifest.json
GET https://github.com/fairchildbrad/aeronav-db/releases/download/cycle-2026-08-06/manifest.json
GET https://github.com/fairchildbrad/aeronav-db/releases/download/cycle-2026-07-09/manifest.json
```
I also ran `gh api repos/:owner/:repo/releases` and `gh repo view` (read) during planning. Nothing was pushed, tagged, released or uploaded.

## Deviations
- Added the pre-publish re-check of the existing tag, alongside sqwkd's concurrency group: concurrency queues runs, and the re-check stops a queued second run from replacing N.
- The unpublished-seed guard lives in chain.py, not as a separate workflow step, so CI fails with the runbook message instead of a 404.
- actionlint was not run during apply. Operator-directed resolution, 2026-11-19: sqwkd downloaded actionlint v1.7.12 from the rhysd/actionlint release (sha256 checked against checksums.txt) and ran `actionlint -color=false .github/workflows/*.yml` on 67420c8: no findings, exit 0. Not covered: shellcheck of `run:` scripts.

## Next
- 02-03: search for an older public-domain source (before 2020-03-26).
- Phase 3: timezones. Then the runbook, which the operator confirms.

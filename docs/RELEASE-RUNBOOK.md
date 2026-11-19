---
type: doc
status: draft
tags: [release, schema-3, cutover, runbook]
relatedTo: [02-02-PLAN.md]
---

# Runbook: the first schema-3 release

**Every step here is operator-confirmed.** The release ships only after Phase 3 (timezones). Run it **between cycles**, so that no AIRAC cycle goes by without a schema-3 file. A missed cycle would force `--allow-gap`. The next AIRAC dates are 2026-11-26 and then 2026-12-24.

Let N be the cycle of the first schema-3 release, and N-1 the cycle 28 days before it.

1. **Re-run the seed to N-1.** From a warm cache this takes about 6 minutes:
   `python -m aeronav_db.backfill --from 2017-10-12 --to N-1 --cache CACHE --out seed.sqlite3`
   Run it a second time. The two seeds' sha256 must be identical.
2. **Pin the seed.** In `identity/seed.json`, set `cycle` = N-1, `sha256` = the seed hash, and `url` = `…/releases/download/identity-seed-N-1/seed.sqlite3`. Leave `published` false for now.
3. **Dry run.** `python -m aeronav_db.chain previous --cycle N --out prev --seed-path seed.sqlite3`, then build N with `--previous-db prev/previous.sqlite3`, then `verify --previous`. All three must exit 0.
4. **Upload the seed** as a non-latest prerelease. This is the first outward-facing step:
   `gh release create identity-seed-N-1 seed.sqlite3 seed.sqlite3.report.json --prerelease --latest=false --title "Airport identity seed (N-1)"`
   Confirm that `curl -L <url> | sha256sum` matches the pin.
5. **Set `published: true`** in `identity/seed.json` and commit it.
6. **Merge `feat/airport-identity` to main.** From here the weekly workflow builds schema 3.
7. **Dispatch the workflow for cycle N**, or wait for the cron run. It chains from the seed. The release notes carry the schema-3 migration notice.
8. **Check the result.** `verify --previous` passed in the run; manifest `previous.sha256` equals the seed pin; cv-aviation has been told.

**Decide at release time:** whether to enable GitHub immutable releases and tag protection for `cycle-*` and `identity-seed-*`. Until then, chain path (a) trusts each release's manifest plus its `.sha256` asset, with the one-hop lineage check as the backstop.

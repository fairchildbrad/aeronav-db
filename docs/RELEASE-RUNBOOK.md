---
type: doc
status: draft
tags: [release, schema-3, cutover, runbook]
relatedTo: [02-02-PLAN.md]
---

# Runbook: the first schema-3 release

**Every step here is operator-confirmed.** The release ships only after Phase 3 (timezones). Run it **between cycles**, so that no AIRAC cycle goes by without a schema-3 file. A missed cycle would force `--allow-gap`. The next AIRAC dates are 2026-11-26 and then 2026-12-24.

Let N be the cycle of the first schema-3 release, and N-1 the cycle 28 days before it.

**Gate:** Phase 3 must be done first. Operator, 2026-11-19, verbatim: "Finish all of the plan-03 before release". `python -m aeronav_db.tz gate` passes on the build (03-02 AC-1). AIRAC cycles that pass during Phase 3 work (2026-11-26, 2026-12-24, …) need no action, since nothing is published. N is whichever cycle the release targets, and step 1 always re-runs the seed to *that* N-1. The local seed pinned at 2026-10-01 is not reused.

1. **Re-run the seed to N-1.** From a warm cache this takes about 6 minutes:
   `python -m aeronav_db.backfill --from 2017-10-12 --to N-1 --cache CACHE --out seed.sqlite3`
   Run it a second time. The two seeds' sha256 must be identical.
2. **Pin the seed.** In `identity/seed.json`, set `cycle` = N-1, `sha256` = the seed hash, and `url` = `…/releases/download/identity-seed-N-1/seed.sqlite3`. Leave `published` false for now.
3. **Dry run.** `python -m aeronav_db.chain previous --cycle N --out prev --seed-path seed.sqlite3`, then build N with `--previous-db prev/previous.sqlite3`, then `verify --previous`. All three must exit 0.
4. **Upload the seed** as a non-latest prerelease. This is the first outward-facing step:
   `gh release create identity-seed-N-1 seed.sqlite3 seed.sqlite3.report.json --prerelease --latest=false --title "Airport identity seed (N-1)"`
   Confirm that `curl -L <url> | sha256sum` matches the pin.
5. **Set `published: true`** in `identity/seed.json` and commit it. Step 5 flips the branch taken by `tests/test_chain_ci.py::test_the_pin_matches_the_local_seed_when_present`, so run the full local suite after step 5 and before step 6's push.
6. **Merge `feat/airport-identity` to main.** From here the weekly workflow builds schema 3.
7. **Dispatch the workflow for cycle N**, or wait for the cron run. It chains from the seed. The release notes carry the schema-3 migration notice.
8. **Check the result.** `verify --previous` passed in the run; manifest `previous.sha256` equals the seed pin; cv-aviation has been told.

**Known FAA behaviour (2026-11-21):** nfdc.faa.gov answers HEAD with 503 for every cycle's NASR zip, even when it is posted. Test availability with a ranged GET (`curl -r 0-1023`), which returns 206 application/zip.

**Decide at release time:** whether to enable GitHub immutable releases and tag protection for `cycle-*` and `identity-seed-*`. Until then, chain path (a) trusts each release's manifest plus its `.sha256` asset, with the one-hop lineage check as the backstop.

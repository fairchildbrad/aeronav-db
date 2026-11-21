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
Phase: 3 of 3 (IANA timezones). COMPLETE: 03-01 to 03-05 unified 2026-11-20; closing gate PASS.
Plan: 03-03 unified 2026-11-19 (.paul/phases/03-iana-timezones/03-03-SUMMARY.md). sqwkd, verbatim: "sqwkd check of 03-03: OK. Unify."
  Build of record: scratchpad tz4/navigation.sqlite3, sha256 05e6892a…, same inputs as tz3b (seed e92fa5fe…, NASR/OurAirports/navaids 2026-10-29). Placed 24,894, unplaced 2,332. tz gate exit 1 only for 03-04/05 countries.
  Patterns carried into 03-04 (as for 03-03, plus): zone_regions.csv mapping per country with the AC-2 check; R1 (where zones agree today, the zone whose history matches); S2 mainland exception; L4 list now Labrador + Eucla (Crimea joins in 03-04).
  Scratch tools add: scripts/{au_rows,xingu}.py.
  Optional: Rosstat OKTMO for the 20 Sakha airports. Q2 (ERSA/AIPs as a check) is the operator's decision.
Operator 2026-11-19: "Finish all of the plan-03 before release". The release runbook is not started.
Status: Phase 3 complete 2026-11-20. 03-05 unified (sqwkd OK). Build of record: scratchpad tz8/navigation.sqlite3, sha256 61d4979b…; placed 26,434, unplaced 792; gate PASS. Next: merge feat/airport-identity into local main (no push), then the cv-aviation handover (evaluation candidate) at /workspace/aeronav-db-handover/2026-10-29-schema3-candidate/. Then the Phase 1 AN identity fix (release blocker), the AIP/ERSA check plan, the L-type follow-up, and the release runbook (operator-confirmed steps).
Last activity: 2026-11-20. 03-05 unified; Phase 3 complete.

Progress:
- Milestone: [███████░░░] 73%
- Milestone: Phases 1-2 done; Phase 3 in progress
- Phase 3: [██████████] 5 of 5 plans

## Loop Position

```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [03-05 loop closed; Phase 3 complete]
```

**2026-11-20 (later):** 01-03 (AN fix) applied in 24bb50f. The build is 79f705b7…, its diff against tz8 is exactly AP0019780 AN→BQ and AP0019781 AN→SX, verify --previous 0 and gate PASS; awaiting sqwkd's check before UNIFY. NEW RELEASE BLOCKER, 01-04 (sqwkd "ACCEPTED as a release blocker"): OA rows that share no IATA/ICAO code with their NASR record get a second airport_id (239 current pairs, e.g. Jackpot 06U/KPT, Hyder 4Z7/WHD). The 01-04 PLAN has its census done, and sqwkd has the R-d uniqueness question. Order (sqwkd): 01-03 UNIFY → 01-04 review/APPLY/UNIFY with a full seed re-run (the backfill cache is gone, so it is a fresh download) → L-type plan rebuilt from the post-01-04 build → 03-06 AIP/ERSA (draft c6e0ce3) APPLY on the post-01-04 build. Reproduced 2026-10-29 inputs: NASR zip sha 538c8219…, OA commit 61129867339d.

**2026-11-20 (end of session):** 01-03, 02-04 and 01-04 are unified, all sqwkd-verified.
- **New baseline (scratchpad /tmp/claude-1001/-workspace-aeronav-db/9ccaaa38-18b0-4ea3-996c-3b3cef0eb5b0/scratchpad):** seed bf/seed-run2.sqlite3 be416100…; 2026-10-29 build b0104r/navigation.sqlite3 b8b96f28…; id map b0104/airport_id_map.csv cf450fd2…, which sqwkd relays to cv-aviation. Warm backfill cache: bf/cache-repro.
- **Gate:** present 26986, placed 26318, NULL 668.
- **Next:** the L-type plan, built on b8b96f28 (Hyder AP0019046; Jackpot AP0009620; Prince of Wales ×9; KENV). It probably needs a mechanism that forces NULL while keeping the reason (deferred). Then the 03-06 AIP/ERSA check on the same build (sqwkd review pending). Then the operator-confirmed runbook. Runbook step 1 now works from a cold cache (02-04).
- **Ids:** every id in the schema3 candidate is superseded; docs keep their historic ids.

**2026-11-21:** 03-07 unified; base build cb5f2f89… (placed 26322 / NULL 664). 03-06 (AIP/ERSA check) is in APPLY, AC-1 survey:
- AU, RU, ID: not checked (use terms / captcha / DNS).
- BR: go, but first confirm the edition from the AMDT 2611A1 PDF's GEN 0 and read the DECEA Política de Uso.
- Part 2 (the 26 countries from 03-04) is not yet surveyed.
- Then: predictions before any comparison (dates 2026-01-15 / 2026-07-15). See 03-06-PLAN.md.

**2026-11-21 (hold):** candidate2 is VERIFIED by sqwkd: /workspace/aeronav-db-handover/2026-10-29-schema3-candidate2/ (a9336f52; map cf450fd2), and cv-aviation has been notified. Holding for the operator. Open, all operator-side:
- merging feat/airport-identity (9251d5f+) into local main (at 7b4387f);
- push, tag, release;
- runbook step 1 (seed re-run; works from a cold cache since 02-04).
Removing the first candidate needs sqwkd's OK after cv-aviation acknowledges.

**2026-11-21:** cv-aviation ACKNOWLEDGED candidate2 and switched to it (sqwkd relay; their sha256sum -c gave 4/4 OK). The first candidate was MOVED, unchanged, to /workspace/aeronav-db-handover/retired/2026-10-29-schema3-candidate/; its own SHA256SUMS still verify after the move (navigation.sqlite3: OK, manifest.json: OK). Deleting it needs the operator.

**2026-11-21 release:**
- **Steps 1–5 done.** Seed 8768eb4b. Prerelease https://github.com/fairchildbrad/aeronav-db/releases/tag/identity-seed-2026-10-29; its download sha256 equals the pin. Published=true in 11cd3cc.
- **Step 6:** main merged locally in 184ad3b.
- **Step 6a, a release fix and a deviation outside PAUL** (sqwkd ruling): a one-line test correction during release. tests/test_chain_ci.py asserted pin["published"] is False, a pre-release guard that step 5 flips by design. It now checks pin cycle == the local seed's airac_cycle; when published, the url must be the identity-seed-<cycle> asset; otherwise published is False.
- **Corrected reasoning (sqwkd):** dist/ is gitignored, so this test SKIPS in CI. CI would not have failed. Stopping was still right, because the local suite must be green before a push.
- **After the fix:** ruff clean; pytest 201 passed. The runbook now says to run the local suite after step 5.

**2026-11-21: FIRST SCHEMA-3 RELEASE DONE (runbook steps 1–8).**
- **Release:** cycle-2026-11-26, Latest, https://github.com/fairchildbrad/aeronav-db/releases/tag/cycle-2026-11-26. Seed prerelease: identity-seed-2026-10-29 (asset sha256 8768eb4b, equal to the pin).
- **Push:** main pushed 9b43e1d..3885745. CI run 44929964870: success. Build run https://github.com/fairchildbrad/aeronav-db/actions/runs/44929969740 (dispatch, cycle=2026-11-26): success ("Is there a new cycle?" and "Build, verify, publish").
- **Published DB:** sha256 ebea09d790b3a9653e9059d2f8c31589d9d82447ec6a63a39822edb21e7026f0. The manifest's previous is {2026-10-29, 8768eb4b}; tz is placed 26348 / unplaced 655 (tzdata 2026f). verify --previous against the local seed passes.
- **Differs from the local dry run** (7b3265d6) in bytes only. A row-level EXCEPT over every table and the metadata is empty both ways. The SQLite header shows CI wrote it with SQLite 3.46.1 and the dry run used 3.53.1; same page size and page count.
- **Next:** future weekly runs chain from release N-1. sqwkd tells cv-aviation it can load production.

## Accumulated Context

### Decisions
- 2026-11-19: Operator, verbatim (relayed by sqwkd): "Yes to both questions". (1) Q2 of 03-03: official AIPs and Australia's ERSA may be read as an independent check only, never as a placement source; only free, no-login publications; no fetch workarounds or User-Agent change; nothing stored, not even printed offsets; record the edition, number checked, match count and airport_ids of mismatches; fix each mismatch or set it NULL from a cited non-AIP source. Running the checks for AU, BR, RU, ID and the 03-04 countries needs its own plan (not 03-05). (2) The UZ reversal (03-04 D2, the 1991 decree list as R1 evidence) is confirmed.
- 2026-11-20: Operator, verbatim, on merging feat/airport-identity into main: "Verify with sqwkd then merge and commit", then "Once phase 3 closes". Order per sqwkd 2026-11-20: 03-05 unified; gate exit 0 on own re-run; SUMMARY commit and gate/verify output to sqwkd; sqwkd OK; then the merge, locally only. The Phase 1 AN release blocker is separate and still open. This does not cover push, tag, release or seed upload; each of those still needs the operator's confirmation.
- 2026-11-20: Operator, verbatim (relayed by sqwkd): "Once phase 3 closes, commit and merge, and publish to cv-aviation.  No to the current nav Canada publication. Official source checks do not hold up release." (1) The merge proceeds after 03-05 is unified, the own re-run of the gate exits 0, and sqwkd has checked the SUMMARY commit and output. (2) Publishing to cv-aviation is new authority: send sqwkd the concrete mechanism (what is handed over and how) and wait for its OK; anything leaving this machine is not covered unless sqwkd confirms it with the operator. The hand-over notes state the AN issue. (3) The eCFS 2026-10-29 is not bought; Canada's check stays the free 2020-11-23 edition. (4) Official-source checks do not gate the release; the AIP/ERSA check is planned after 03-05.
- 2026-11-20: Operator, verbatim (direct to aeronav-db): "do your work, all 3 steps.  There will be gaps in history, unavoidable." (1) aeronav-db proceeds on the agreed order: the Phase 1 AN fix (01-03), the AIP/ERSA check plan, and the L-type follow-up. Each plan still goes to sqwkd for review before APPLY, as agreed; the instruction does not cover push, tag, release or seed upload. (2) The IATA history gap is accepted as unavoidable: no search for an older IATA source; the release notes and README state that IATA history begins 2021-11-04, and nothing is back-dated.
- 2026-11-20: Operator ruling on 01-04 ids, verbatim (relayed by sqwkd). Question: "Which way should the fix go before release?" Options: "Renumber now", "Keep tz8 IDs, add aliases", "Ask cv-aviation first". Operator chose: "Renumber now". The chosen option's text: rebuild from scratch, one ID per airport, no aliases for the duplicates; the ~9,900 IDs in the schema3 candidate change; aeronav-db re-keys its tz tables by script; cv-aviation gets an old→new mapping file.
- 2026-11-21: Operator, verbatim (direct to aeronav-db): "proceed with release". Operator confirmation, verbatim (via sqwkd), to the question "Does 'proceed with release' cover all five?" (runbook steps 4–8): "Yes, run steps 4–8". Conditions (sqwkd): step 1–3 outputs go to sqwkd and are verified before step 4; the version/tag scheme is checked against repo policy before any tag; steps run in runbook order and STOP on any failure or unexpected output; the release URL, asset sha256 and workflow result go to sqwkd after step 8. N = 2026-11-26 and N-1 = 2026-10-29. The NASR 2026-11-26 zip returned 503 on 2026-11-21 (not yet posted), so the dry run waits for it.
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
- (optional; 03-06 closed 2026-11-21, 0 checked) AIP check second pass (A): URLs only from Eurocontrol AIS-online plus ICAO/national CAA sites; GEN 2.1 (and one AD 2 page) for DE, ES, GL, PF and any confirmed country; predict only where a zone is stated. Re-opens as its own plan only if the operator wants it. sqwkd is offering it, plus ROTAER (BR).
- (resolved 2026-11-21, 03-07 L4) Prince of Wales ×9 placed as America/Sitka from 44 FR 55556-55557 (1979); the 1980 rescission is still unread (optional).
- (open; sqwkd 2026-11-20) Hyder AP0019046: admitting a non-tzdata observed-clock source is a policy change, the operator's call; sqwkd is offering it.
- (open; sqwkd 2026-11-20, during 01-04) No mechanism forces tz NULL while keeping the original reason. unplaced_by_design only marks a NULL as expected; a blank-tz override forces NULL but records tz_unplaced=source_conflict. The L-type plan will probably need one; not built in 01-04.
- (open; sqwkd 2026-11-20, out of 02-04 scope) NASR formats b (11 cycles, 2022-11-03 → 2023-08-10) and c (41 cycles, 2023-09-07 → 2026-10-01) have no layout or record-length guard; only format a gets one (02-04).
- (open; sqwkd 2026-11-20/21, one future plan) pyproject.toml says 0.1.0 while the ROADMAP milestone is v0.2.0; left at 0.1.0 for the first schema-3 release (sqwkd ruling). Seed and release metadata carry no code commit (only generator=aeronav_db.backfill). The release-diagnostics rule wants the semantic version, build number and short commit recorded. Adding them changes bytes, so it needs its own plan.
- (resolved 2026-11-20 by operator ruling, option (b): "There will be gaps in history, unavoidable." README/release-notes line still to write) The earliest IATA effective_date is 2021-11-04, the first OurAirports snapshot used, although history_start is 2017-10-12. 524 of 2,152 APA station-dates (2019-09-28 to 2021-10-24, 42 stations, e.g. LGA, PHL, BOS, MEX, SJD, MBJ, STI) have no IATA code in effect. Two options: (a) find an earlier public-domain IATA history source (older ourairports-data git history, if it exists); (b) at minimum, the release notes and README say IATA history begins 2021-11-04, and nothing is back-dated (PBI→DJT shows codes get reassigned). Plan it after the AN fix; (b) goes into the release notes regardless.
- (resolved by 03-07 except Prince of Wales and Hyder, see above) L-type clock-in-use follow-up, NULL meanwhile: Hyder AP0019046 and Hyder SPB AP0024208 (Alaska legal time, Pacific in practice?); Prince of Wales KCC, CGA, HYL, PAHY, KXA, PAKW, KPB, PAAP, KTB; Jackpot AP0009620, AP0024272; West Wendover (KENV AP0016900 is filed in Tooele County, UT; is anything else in scope?). sqwkd rules when the follow-up plan comes.
- (open, after 03-05; cv-aviation 2026-11-19, 7d7ca8b) 3,171 historic US airports have tz NULL (no_region), including logbook stations IGX (Horace Williams, Chapel Hill NC; 13 legs 2005-2014) and NC47 (2012). Proposal: retired airports in a single-zone state take that state's rule via the NASR state. Not a gate item; needs its own plan and review.
- (resolved 2026-11-18) Timezone: operator "V0.2 and build it now". It's a later phase of v0.2, using a self-maintained country→region→override table of IANA zones, no polygons.

### Blockers/Concerns
- (sqwkd 2026-11-20, confirmed Phase 3 close: main 7b4387f is 91 ahead of origin/main, not pushed; the handover sha256 checks pass.) Agreed order: (1) the Phase 1 AN identity fix, as a release blocker; its plan goes to sqwkd for review before APPLY; (2) the AIP/ERSA check plan; (3) the L-type follow-up. The runbook release steps stay with the operator, one step at a time.
- PUSH CONSTRAINT (sqwkd 2026-11-20; docs/RELEASE-RUNBOOK.md step 6 comes after step 4): main was merged locally only. Local main must not be pushed before runbook steps 1–5 (seed re-run, pin, dry run, seed upload, published=true). Once main is pushed, the weekly workflow builds schema 3 and needs the published seed.
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

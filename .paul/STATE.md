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
Plan: 03-02 APPLY in progress. Task 1 f769497; MX 9f3f5a6 (102/102). sqwkd OK'd the CA-ON approach with O1-O4 (in plan); tzdata northamerica vendored 4d125b6.
  CANADA COMPLETE 8b401f4 (pending sqwkd gate check). NL 3b0381e/ae2977e/8ef141a (sqwkd L1-L4: observed clock over statute only where tzdata addresses the legal position; Labrador CD 1010+1011 Goose_Bay, Wabush Halifax, SE corner 3 + Churchill Falls UBD). SK ac78dad (S1-S4; CYNL override). NU/NT/YT 241b887 (SOR/2001-182; NT residual Edmonton via tzdata quote of R-090-2026; YT 138W per CO 1967/59; Arctic Bay UBD). BC Salt Spring 8b401f4. CA present 504: placed 410 (county 313, region 93, override 4); unplaced: no_county_match 84, no OurAirports row 10. Scheduled 275: placed 242, unplaced_by_design 33 (ON 28, NL 4, NU 1), not listed 0. CFS (2020-11-23 edition, offsets on 2021-01-15/07-15): 340 match, 10 mismatch (9 YT print UTC-8(7), Yukon's 2020-11-01 change not yet in that edition; CBX5 Tungsten prints UTC-8 no DST vs Edmonton), 71 in CFS unplaced (not placed from it), 73 not in CFS. L4 README + SUMMARY lists still to write; deviations: AB MB NB PE NT YT tzdata-only citations, NU DST from tzdata.
  2026-11-19 operator, verbatim: "Record this legal document and attempt to access the Canada flight supplement". QC DONE f36e8f5: Legal Time Act CQLR c T-5.1 (operator PDF, sha256 0292d9da…, citation+hash only in SOURCES.md) s.1 west of 63W + all MRC Minganie Eastern, s.2 east of 63W AST (DST only Îles + Listuguj). 54 rule-cited (CGNDB populated/admin places + airport west of 63.5W), Natashquan + Baie-Johan-Beetz name-cited via CGNDB Location MRC Minganie (SGC CD 2498 merges Minganie+LGSL, cannot confirm). YUL YQB CYNA placed. Pending (scheduled, no single-side CGNDB match): CYGL La Grande Rivière, CYIF St-Augustin (name also in Laurentides/Maria-Chapdelaine), CZEM Eastmain River — sqwkd 2026-11-19: "OK. Write the overrides, with the conditions below." DONE as overrides.csv rows (Act section, coords, distance ≥0.5° from 63W, not-Minganie record, O3; CYIF also cites tzdata). CFS rerun: 264 match, 0 mismatch, 157 unplaced. sqwkd on CFS: SUMMARY gives edition 2020-11-23 + age caveat, the two comparison dates, and that the unplaced-in-CFS airports were NOT placed from it (check, not source). CFS (Q2 now allowed by operator): current 2026-10-29 eCFS is paid (products.navcanada.ca, $16.50/region subscription) — not purchased; NAV CANADA hosts free older eCFS at navcanada.ca/en/ecfs_0{1,2,3,4,5,7}_en.pdf (pages dated 2020-11-23, Last-Modified 2021-04-26; 06 404s; covers all provinces/territories). Check only, nothing stored: scratch scripts/cfs_compare.py compares printed std/DST offsets with resolved zone offsets on 2021-01-15/07-15. Run at f36e8f5: 1556 CFS entries; CA present: 261 match, 0 mismatch, 160 in CFS but unplaced, 73 not in CFS. Rerun after each province; SUMMARY records edition, counts, mismatched airport_ids only.
  CA-ON DONE a61a80d; AB MB NB PE DONE 5e87d0c (tzdata-only citations: SUMMARY deviation). NS: sqwkd OK'd option (a) 2026-11-19 — rows quote zone1970 comment ('NS (Cape Breton)'/'NS (most areas)') + CGNDB records placing the place on that side of the Strait of Canso (~61.4W, 0.5° margin); ambiguous → NULL; SUMMARY: Glace_Bay and Halifax differ only before 1972. NS DONE a9bfdc8 (CGNDB county decides island side). BC DONE (except D1 lists: Cranbrook/Castlegar/Trail/Revelstoke NULL pending official membership lists; RDKB+CSRD 403). Remaining: NL SK NU NT YT; QC rest (Act 403: operator asked via sqwkd for option (a); until then only tzdata-named QC rows — Îles-de-la-Madeleine, Listuguj → Halifax, east of Natashquan → Puerto_Rico; YUL/YQB pending, NOT unplaced_by_design; if Act text supplied store only citation + sha256) NL SK NU NT YT. D1: SGC 2021 structure CSV (sha 55f6eb91…, scratch sgc/) gives CD membership: Cranbrook 5901022 (E Kootenay), Castlegar 5903045 (C Kootenay), Trail 5905014 (Kootenay Boundary), Revelstoke 5939019 (Columbia-Shuswap); no CSD type (attribute file 403). D1 DONE 2f3f709 (sqwkd accepted CGNDB generic term City/Town/Village/District Municipality as CSD type; SUMMARY must confirm each airport lies in the same CD). QC tzdata-named rows DONE 2f3f709; rest of QC pending operator (Act text). BC: Interpretation Act s.26 (Pacific Time = UTC-7, all BC); CGNDB BC Location = land district only; land-district cut-off APPROVED by sqwkd 2026-11-19 with D1 (in plan) (rule-cited Vancouver only outside Kootenay+Peace River LDs; inside, name-cited only; Chetwynd/Hudson's Hope/Taylor/Tumbler Ridge NULL). bc.zip sha 08653aca…; scratch cgn/. QC: tzdata names Îles-de-la-Madeleine + Listuguj → Halifax (citing Legal Time Act CQLR c T-5.1), east of Natashquan → Puerto_Rico; legisquebec.gouv.qc.ca returns 403 (CloudFront) to automated fetch — not bypassed; without the Act text C2 forbids rule-cited QC rows. Options: operator supplies the Act text/PDF, or QC name-cited only. Next: NL SK NU NT YT. BC notes (northamerica ~2130-2205): BC year-round -07 from 2026 (news.gov.bc.ca 2026AG0013-000209); RDEK + CSRD Area A + Town of Golden → America/Edmonton (year-round -06); Creston → Phoenix; Dawson Cr/Ft St John → Dawson_Creek; Ft Nelson → Fort_Nelson. BC release news.gov.bc.ca 2026AG0013-000209 (fetched; scratch calaw/bc_news.html) names NE BC on year-round UTC-7: Dawson Creek, Fort St. John, Fort Nelson (+Northern Rockies RM), Chetwynd, Hudson's Hope, Taylor, Tumbler Ridge; Fort Ware (Kwadacha) exception = Pacific; SE BC = East Kootenay and Golden region. Statute: Interpretation Amendment Act 2019 (not yet fetched). Need RDEK member list source, same O1-O3 pattern; scripts in scratchpad cgn/. Old notes:
  - Anomalies named in northamerica (lines ~1750-1770): Big Trout Lake area → America/Winnipeg (E of 90W); Upsala area → America/Toronto (W of 90W); Atikokan → America/Panama; Pickle Lake + Mishkeegogamang → America/Panama. Fort Severn NOT named → NULL (O2).
  - Get each anomaly's longitude from a named gazetteer (not memory) for the O1 margin; Big Trout Lake ~89.9W expected, so 85W holds if confirmed.
  - Rule-cited Toronto rows only east of 85W; anomalies name-cited (O3); the rest of NW Ontario's scheduled airports → unplaced_by_design.csv (O4).
  - Also Ontario Reg. 333/26: west of 90W becomes UTC-5 all year from 2026-11-01 (tzdata 2026f, Manitoba model).
  - Then the other provinces with the same pattern; then build, verify, gate, SUMMARY. Q2 (CFS) is with the operator.
Operator 2026-11-19: "Finish all of the plan-03 before release". Release runbook not started
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

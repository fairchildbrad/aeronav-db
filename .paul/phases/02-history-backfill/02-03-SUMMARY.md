---
phase: 02-history-backfill
plan: 03
type: summary
status: complete
description: "History extended to 2017-10-12 with FAA NASR files preserved by the Internet Archive; seed re-run, reproduced and re-pinned (unpublished)."
about: "aeronav-db"
tags: [backfill, nasr-archive, wayback, seed]
relatedTo: [02-03-PLAN.md, 02-01-SUMMARY.md, 02-02-SUMMARY.md]
---

# 02-03 Summary: older history from the Internet Archive

## Delivered
- **backfill.py**
  - When the FAA returns 404, `nasr_cycle` falls back to the newest Wayback capture of the same FAA URL, found with a CDX lookup (`wayback_captures` / `wayback_source`).
  - The Archive's "Temporarily Offline" page is retried, never parsed.
  - Each Archive file is downloaded whole. The Archive rate-limits range reads (HTTP 429), so the download pauses 60 s first, honours Retry-After and backs off 300 s per attempt.
  - Every zip member's CRC is tested before parsing (`testzip`).
  - Cache meta records source, capture, digests, captures and zip_sha256. `backfill_sources` gains `nasr_carrier` and `wayback_capture`.
- **nasr_archive.py:** a format-a layout guard. Every APT record must be 1,529 characters (apt_rf.txt), or the file is refused.
- **Tests:** 4 Wayback tests and 1 layout test; legacy fixtures padded to the real record length. Full suite: 148 passed; ruff clean.
- **identity/seed.json** re-pinned (published still false). README history section, RELEASE-RUNBOOK and the backfill default now start at 2017-10-12.

## AC results
| AC | Result | Evidence |
|----|--------|----------|
| AC-1 carrier faithful | PASS | 2020-03-26: Wayback capture 20210325204726 and the FAA copy are both 118,864,479 bytes, sha256 2ddb00d5d6271849e06e13856cc7daeb3ad06486892744ea796c148f7712709d |
| AC-2 provenance | PASS | Cache: 86 cycles from the FAA, 32 from Wayback. CRCs pass on all 32 |
| AC-2 re-posts (sqwkd) | PASS | No cycle URL has more than one distinct capture digest. Nothing to choose between |
| AC-3 format holds | PASS | All 32 parse as format a with the 1,529-character record. NASR rows 19,752 to 19,832. Max minted after the first cycle: 39 (2017-11-09). Max closed: 61 (2018-03-01). No new allowlist entry; 0 blank-status records |
| AC-4 re-run seed | PASS | 118 cycles, 2017-10-12 → 2026-10-01, none skipped. Two runs are byte-identical, sha256 **e92fa5fe10ab637da01d3c7084668d214770dd619a47c671a1b4335b60395898**. PBI→DJT is one id, AP0003237 (faa PBI from 2017-10-12). The 2026-10-29 build from the seed passes verify --previous (exit 0); its manifest has history_start 2017-10-12 and previous {2026-10-01, e92fa5fe…} |
| AC-5 report | PASS | Below; dist/backfill/seed.sqlite3.report.json |

## Seed (measured)
- Ids: 30,968 (was 30,424); 19,786 were minted at 2017-10-12. Aliases: 14 (unchanged). airport_id_next 30969.
- history_start 2017-10-12; history_start_ourairports 2021-11-04 (unchanged).
- IATA codes held by more than one present airport: 0 in all 32 new cycles. These cycles are NASR-only, so OurAirports duplicates can't arise.
- Ids are re-minted relative to the 02-01 seed (c6c09037…). Nothing was published, so no consumer holds the old ones.

## Deviations
1. The plan said Range reads would work. They do, but the Archive returns 429 under many small requests, so each file is downloaded whole. A side effect is that every member's CRC is tested, not only the members that are read. The run took 2 h 16 m because of the pacing; a run from the cache takes 6.5 min.
2. Commit 76d0feb went in with 3 failing tests (fixtures shorter than the new record-length guard). It was fixed in the following commit, before the full suite ran green.

## Next
- Phase 3, 03-01 (timezones): reviewed by sqwkd (T1–T3 adopted) and cv-aviation (AC-7).

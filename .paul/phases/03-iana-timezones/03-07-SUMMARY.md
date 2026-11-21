---
phase: 03-iana-timezones
plan: 07
type: summary
status: complete
description: "L-type follow-up: Jackpot, Owyhee and Mountain City NV placed on the observed Mountain clock (L4); Hyder kept NULL; West Wendover closed; Prince of Wales deferred pending the 1979/1980 Federal Register text."
tags: [timezone, l-type, observed-clock, nevada, hyder, prince-of-wales]
relatedTo: [03-07-PLAN.md, 01-04-SUMMARY.md, 03-05-SUMMARY.md]
about: "aeronav-db"
---

# 03-07 SUMMARY: L-type follow-up

## Authority
- **sqwkd approval, verbatim:** "03-07 PLAN (5380d15) APPROVED for APPLY, with these rulings." The NASR-city rule for L1 came in a later sqwkd ruling, recorded in the PLAN.
- **sqwkd check, verbatim:** "03-07 VERIFIED. Write the SUMMARY and UNIFY."
- **Operator, verbatim, 2026-11-21:** "Access what you can and give me links if you can't see it".

## Outcome
| Item | Result |
|---|---|
| L1 Jackpot, Owyhee, Mountain City (NV) | **4 placed**, America/Denver override: AP0009620 (06U), AP0009656 (10U), AP0029026 (NV11), AP0009650 (NV08) |
| L2 Hyder AP0019046 | NULL kept. No tzdata statement of the observed clock, so L4 can't apply. Admitting a non-tzdata source is a policy change, offered to the operator by sqwkd |
| L3 West Wendover | closed, no change. 0 present NV airports in the city; KENV AP0016900 (Tooele UT) stays America/Denver |
| L4 Prince of Wales ×9 | **9 placed**, America/Sitka override (sqwkd: "YES. The enumerated list is unambiguous enough.") |

## Sources
- **Order of events:** a retry of the eCFR URL was **denied by this session's permission classifier** on 2026-11-20, and APPLY paused. After the operator's answer above, on 2026-11-21, the eCFR versioner XML was fetched with `curl --compressed`. That endpoint returns HTTP 406 without compression; no User-Agent change was made. sha256 **7ca9e8d7…**, the same as the 03-05 fetch (SOURCES.md:12).
- **§71.10, verbatim:** "The fifth zone, the Pacific standard time zone, includes that part of the continental United States that is west of the boundary line between the mountain and Pacific standard time zones described in § 71.9".
- **§71.9(b), verbatim:** "From the northeast corner of the State of Nevada southerly along the Utah-Nevada boundary to the junction with the northern border of the City of West Wendover, Nevada. …"
- **Observed clock:** tzdata 2026f northamerica:474, "Nevada border (Jackpot, Owyhee, and Mountain City)", under US mountain time represented by Denver.
- **Rule (sqwkd):** NASR APT_BASE CITY must name the place. Measured on NASR 2026-10-29: 06U JACKPOT, 10U OWYHEE, NV11 OWYHEE, NV08 MOUNTAIN CITY.

## Build and checks
- **Build:** cb5f2f899115c6945db4b458b5d6924af9975566638fe9b4c20ded9bfbb09a27, from seed be416100…, with NASR 538c8219… and OA 61129867339d.
- **`verify --previous`:** exit 0.
  ```
  time zones: 26322 present airports placed, 664 unplaced
  verification passed
  ```
- **`tz gate`:** exit 0.
  ```
  present 26986, placed 26322, NULL 664
  gate PASS
  ```
  Predicted 26,322 / 664 after the census; exact.
- **tz diff against b8b96f28:** exactly the 4 ids (NULL → America/Denver, override). sqwkd confirmed this independently.
- ruff `.` clean; 201 passed.

## Predictions that were wrong
1. **Owyhee / Mountain City:** predicted 0 present NULL airports. **Wrong: there are 3** (AP0009650, AP0009656, AP0029026).
2. **Petan Ranch:** aeronav-db first reported OA's municipality as its only link to Mountain City. **Wrong: NASR CITY is MOUNTAIN CITY.**

## L4 Prince of Wales (2026-11-21)
- **Operator, verbatim:** "when you get it, the pertinent information is on pp.35-37". govinfo returned 502 (Retry-After 60) four times; the official Library of Congress mirror was free and needed no login: https://tile.loc.gov/storage-services/service/ll/fedreg/fr044/fr044189/fr044189.pdf, sha256 d4fed2cc….
- **Rule:** 44 FR 55556–55557, Vol. 44 No. 189, 1979-09-27, DOT OST Docket No. 9, Notice 79-18, final rule effective 1980-04-27. It begins on PDF p. 35, with the list and §71.11-1 on p. 36 and the 137° line on p. 37.
- **Verbatim:** "The revised boundary line will include the following boroughs and cities in the Yukon Time Zone: Yakutat; Skagway; Klukwan; Haines; Gustavus; Juneau and Hoonah." The rule's only stated latitude is 57°37' north.
- **OCR (pypdf 5.1.0) checked page by page** on the relied-on words; all were found on pp. 35–37. OCR flaws: "Klukivan" for Klukwan; "57037 '" for 57°37' (degree sign read as 0); "137'" for 137° (degree sign read as an apostrophe). No Prince of Wales or Baranof name appears on pp. 35–37. The matches elsewhere in the issue are unrelated people's names (Craig, Coffman) and Holliston, MA.
- **Placed:** America/Sitka by override, citing the rule (via the LoC URL and its sha256), 49 CFR 71.11 and tzdata northamerica:607. Each note says the airport's margin south of 57°37'N and that the 1980 rescission was not read.
  - Point Baker 75.9 nm, Port Alexander 82.2 (on Baranof Island, with its own note), Coffman Cove 96.1, Thorne Bay 115.7, Klawock 122.2, Kasaan 124.8, Clark Bay 127.6, Craig 128.3, Hydaburg 144.6.
  - The 9 unplaced_by_design rows were removed.
- **The 1980 rescission was not read.** The placement relies on the 9 never having moved, which the 1979 enumeration supports, and on tzdata's America/Sitka history.
- **Build** a9336f52ed54aeddf9c9b54c49531ddde708ac8e200c91aa9ef9a4196c1f7a79:
  - verify --previous exit 0: "time zones: 26331 present airports placed, 655 unplaced".
  - gate: "present 26986, placed 26331, NULL 655 / gate PASS". As predicted.
  - tz diff against cb5f2f89: exactly the 9 ids.

## Deviations
1. **Id-keyed canary added.** `CANARY_TZ_BY_ID = {"AP0009620": ("America/Denver", "override")}` replaces the planned code canary, because the ICAO canaries can't see a field without an ICAO code.
2. **APPLY paused** on 2026-11-20 because sources were blocked, and resumed on the operator's answer.
3. **A sudo install of poppler-utils (to read the PDF) was denied by the session's permission classifier.** The workspace rule is "No sudo, ever"; it was not retried in any form. The PDF's OCR text was read with pypdf in a throwaway user-level venv in the scratchpad.

## Deferred
- **Optional:** read the 1980 rescission (late-September 1980 FR) to confirm it touches only the 1979 Yukon area.

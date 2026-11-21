---
phase: 01-identity-engine
plan: 04
type: summary
status: complete
description: "One field, one airport_id: OurAirports pairs with NASR through the FAA LID (local_code). Renumbered before release (operator), tz tables re-keyed by script; gate 26318/668/26986 as predicted."
tags: [airport-identity, pairing, local-code, renumber, rekey, release-blocker]
relatedTo: [01-04-PLAN.md, 02-04-SUMMARY.md, 01-03-SUMMARY.md]
about: "aeronav-db"
---

# 01-04 SUMMARY: pairing through the FAA LID, renumbered

## Authority
- **sqwkd:** "ACCEPTED as a release blocker"; R-d gate-local, R-e narrowed, and R-f accepted (rulings verbatim in the PLAN).
- **Operator, verbatim (via sqwkd):** "Renumber now".
- **sqwkd acceptance, verbatim:** "01-04 ACCEPTED, with the 2 unpredicted triples ruled as explained."

## Code
| Commit | Change |
|---|---|
| b723206 | local_code pairing: R-a..R-d gate-local, R-e, and the R-f sticky-site guard |
| aeab385 | shared code counts only when in gate (R-e narrowed) |
| d2e052d | tz tables and canaries re-keyed; verify: no unplaced_by_design id is placed |
| this commit | `tools/rekey_0104.py` |

ruff clean; 201 passed.

## Builds (scratchpad), sha256
- **Control:** e92fa5fe… (02-04's cold reproduction).
- **Seed runs 2 and 3:** **be416100f175eb5e6b457493cbc1fc193ba180ef13401381032c50e4aefaaa18**, byte-identical, report.json identical. 30,708 ids, 2 aliases (control: 30,968 and 14). airport_id_next 30,969 → 30,709.
- **2026-10-29 build, re-keyed:** **b8b96f28a97b089cf2d5654ecfaeb4aaad2b52a75cd2d77da3d3aa5a59e40019**. Inputs: NASR 538c8219…, OA 61129867339d.
- **Map:** airport_id_map.csv **cf450fd290ac85000fd4c3a407165b2bcf16785c0d2d3412529c384c66ddac23**, 30,998 rows plus header: one_to_one 30,488, merged 494 (247 merges), alias 14, special 2. Relayed to cv-aviation by sqwkd; not in git.

`verify OUT --previous seed-run2`, exit 0:
```
IATA codes held by more than one present airport: 0
time zones: 26318 present airports placed, 668 unplaced
unplaced by country: US 228, AU 149, CA 92, CD 58, PF 38, BR 30, RU 28, VN 28, AQ 8, MN 4
verification passed: …/b0104r/navigation.sqlite3
```
`tz gate OUT OA`, exit 0:
```
present 26986, placed 26318, NULL 668
gate PASS
```
Predicted: 26,318 / 668 / 26,986. Exact.

## Census and predictions
| | Predicted | Measured |
|---|---|---|
| P1 forward pairs | 230–239; 240/240 as ruled | 240 present merges |
| P3 distance | ≥95 % <1 nm | 239 <1 nm; 1 at 1.09 nm (Port Alice SPB, same field) |
| P4 gps fallback | 0–5 | 0 |
| R-e shortfall control | 226 | superseded by the 02-04 control (e92fa5fe) |
| A1/A2/A3, alias option declined by the operator | 241 / 0 / 1–3 | 240 aliases / 0 moved / 1 override, 23 unplaced_by_design rows, 1 canary |

## Triples
- **One-to-one ids:** 30,488 checked, **0** differ from tz8.
- **Predicted changes** (3 of the 240 present merges):
  - AP0019093 → America/Sitka, override (OA-side override AP0024212);
  - AP0019670 Anahim Lake → America/Vancouver, county;
  - AP0019673 Bar River → America/Toronto, county.
- **UNPREDICTED (2), ruled as explained by sqwkd.** The prediction covered the 240 present-both merges and not the 7 history merges; the gap is aeronav-db's. In each, the field's placement equals its present OA side's tz8 triple, and only the id carrying it changed:
  - AP0010822 ROUSES POINT (NASR 16048.) ← AP0024284 OA 18531 → (America/New_York, region);
  - AP0018325 GRAND GENEVA RESORT (NASR 27316.12) ← AP0024322 OA 19432 → (America/Chicago, region).

**The 7 history merges** (one old id absent in 2026-10-29). Format: survivor ← old ids: old triples → new triple.

| Survivor ← old ids | Old triples → new triple |
|---|---|
| AP0002256 ← AP0002256, AP0024257 | (NULL, no_region) and (NULL, no_region) → (NULL, no_region) |
| AP0010822 ← AP0010822, AP0024284 | (NULL, no_region) and (America/New_York, region) → (America/New_York, region): **unpredicted** |
| AP0012423 ← AP0012423, AP0024219 | (America/Chicago, region) and (NULL, no_region) → (America/Chicago, region) |
| AP0013391 ← AP0013391, AP0024351 | (NULL, no_region) and (NULL, no_region) → (NULL, no_region) |
| AP0015339 ← AP0015339, AP0024207 | (America/Chicago, county) and (NULL, no_region) → (America/Chicago, county) |
| AP0018325 ← AP0018325, AP0024322 | (NULL, no_region) and (America/Chicago, region) → (America/Chicago, region): **unpredicted** |
| AP0019524 ← AP0019524, AP0022892 | (Pacific/Tarawa, override) and (NULL, no_region) → (Pacific/Tarawa, override) |

**Special cases:**
- Pilot Station AP0019250 ← AP0019250 (America/Anchorage, county), AP0024177 (NULL, no_region) and AP0029908 (NULL, no_county_match) → (America/Anchorage, county).
- Wendell H Ford: AP0029892 → AP0029637, (NULL, no_region) unchanged; AP0006066 → AP0006066.
- Deer Harbor SPB merges by convergence (new alias AP0029282 → AP0027621, 2023-09-07).

Every merge with both old triples is in scratchpad b0104r/merges.csv.

## Re-key
- **Literals, by occurrence:** verify.py 8, all real and re-keyed; only AP0024208 → AP0019046 changes. Tests: 37 synthetic, untouched. overrides.csv 124 → 124. unplaced_by_design.csv 182 → 163.
- **The 25 rows with reason "OurAirports-only airport: no NASR county"** (1 distinct text once the prefix is stripped):
  - **19 dropped, class (i):** AP0024202, AP0024204, AP0024205, AP0024206, AP0024209, AP0024211, AP0024214, AP0024220, AP0024239, AP0024240, AP0024241, AP0024250, AP0024259, AP0024260, AP0024401, AP0024412, AP0024420, AP0029834, AP0029908.
  - **3 kept on their NULL survivor:** AP0024185 → AP0019269, AP0024232 → AP0019200, AP0024247 → AP0019400.
  - **3 kept, not merged (one-to-one):** AP0028140 → AP0027901, AP0028141 → AP0027902, AP0028596 → AP0028357.
  - That makes 19 + 3 + 3 = 25. The 4th row kept on a survivor is AP0024208 (Hyder SPB) → AP0019046, which has a different reason text.
- **L-type airports, unchanged:** Hyder, Jackpot and the 9 Prince of Wales airports stay NULL no_county_match; KENV stays America/Denver.

## Deviations
1. **Re-key rule step added during APPLY.** The script refused, as designed: "REFUSED: AP0024314 (None, None, '19042', '2021-11-04') maps to []". OA 19042 merged into NASR AP0000009, so no OA-only new identity existed. Added step: "any new identity now carrying that OA id". In the final order it sits **third**: NASR site key, then OA id + first_cycle among OA-only identities, then any identity carrying the OA id, then IATA intervals. It resolved that one id (AP0024314 → AP0000009, merged). **A re-run of `tools/rekey_0104.py` from scratch with the final rule writes a map with the same sha256, cf450fd2….**
2. **First survivor prediction discarded.** It used the archive reader's rows, which lack STATE_CODE/COUNTY_NAME. Replaced by one using the build's own `extract_nasr_tables`.
3. **Unpredicted id renumbering consequence.** The id shift broke the airport-keyed tz tables. That led to the STOP, the operator ruling and the re-key.
4. **The 02-04 defect surfaced here.** The cold-cache control run failed and became plan 02-04.

## Hand-over
- cv-aviation gets the map through sqwkd, with this SUMMARY; the ids in the schema3 candidate are superseded.
- The handover file is untouched.
- Next: the L-type plan, on this build.

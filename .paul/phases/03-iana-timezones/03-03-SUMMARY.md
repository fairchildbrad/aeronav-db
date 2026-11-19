---
phase: 03-iana-timezones
plan: 03
type: summary
status: draft
description: "Australia, Brazil, Russia and Indonesia placed from their statutes and tzdata, so none of them appears in the tz gate; the partial-region list now enforces itself through zone_regions.csv."
about: "aeronav-db"
tags: [timezone, iana, australia, brazil, russia, indonesia]
relatedTo: [03-03-PLAN.md, 03-02-SUMMARY.md]
---

# 03-03 Summary: Australia, Brazil, Russia, Indonesia

DRAFT for sqwkd's check before unify.

## Build (AC-1, AC-7)
2026-10-29 was built from the pinned seed (e92fa5fe…) with NASR, OurAirports and navaids 2026-10-29.
- Output sha256 05e6892a…, 35,346 airports.
- `verify --previous` exits 0, and all 33 tz canaries pass, including the 19 new ones: YSSY YBBN YPPH YPAD YBHI SBGR SBEG SBBE SBRB SBFN UUEE UNNT UHWW UEEE UHPP WIII WADD WAJJ WIOO.
- Present 27,226: placed 24,894 (03-02: 23,565), unplaced 2,332 (03-02: 3,661).
- `tz gate` exits 1, as planned (03-04 and 03-05 countries remain), with header `present 27226, placed 24894, NULL 2332`. **No line names AU, BR, RU or ID** (nor CA or MX).

| Country | Present | Placed | Unplaced (reason) | Scheduled: placed / unplaced_by_design / unlisted |
|---|---|---|---|---|
| AU | 618 | 469 | 149 no_county_match | 158 / 0 / 0 |
| BR | 357 | 327 | 30 no_county_match | 126 / 3 / 0 |
| RU | 315 | 287 | 28 no_county_match | 129 / 20 / 0 |
| ID | 246 | 246 | 0 | 123 / 0 / 0 |

unplaced_by_design additions:
- BR: Tabatinga (on the statutory Amazonas line), Almeirim (north of the Amazon), Breves (Marajó: no source puts it on a side).
- RU: 20 Sakha airports, because no town-to-district source was fetched. Rosstat's OKTMO was suggested but not attempted; it is optional.

## AC results
| AC | Result | Evidence |
|---|---|---|
| AC-1 gate clear | PASS | gate output above |
| AC-2 partial list completes itself | PASS | `zone_regions.csv` (29654aa, 2a695ec); caught RU-SA and RU-SAK |
| AC-3 Australia | PASS, with deviations | below |
| AC-4 Brazil | PASS, with deviations | below |
| AC-5 Russia | PASS, with deviations | below |
| AC-6 Indonesia | PASS | Keppres 41/1987 (hash in SOURCES) |
| AC-7 checks | PASS | build, verify, canaries, lint, tests (176 passed; ruff clean) |

## AC-2: zone_regions.csv
- zone1970 comments name places in free text, so each mapped country lists the ISO regions each zone covers, with a source.
- Once a country has rows:
  - every one of its zones needs a row;
  - any region that two zones cover must be in partial_regions.csv;
  - every rule's zone must cover its region.
- **Scope:** CA, MX, BR, AU, ID and RU are mapped. The other 26 countries are mapped in 03-04, so the check doesn't yet run "anywhere".
- **Caught:** RU-SA (5 zones) and RU-SAK (2 zones). No other flag in the mapped countries.
- **Narrowed exception (R2):** a zone may cover no region of country X only when zone1970 also lists the zone for another country. Simferopol is the case: listed under RU, it covers UA-43. A test shows an ordinary unmapped zone still fails.

## Placements
- **AU (4f6bf77, 16b042f):**
  - ACT, SA, VIC and NT get region rules.
  - NSW, QLD, WA and TAS are SPLIT, with named places: Broken Hill, Lord Howe, the Hayman/Hamilton/Lindeman islands, and Eucla/Cocklebiddy/Madura (L1).
  - Statute residuals, with OurAirports positions as the only evidence. No CC-BY gazetteer was used.
  - **The WA margin of 29.0°S is self-chosen**, not given by tzdata.
  - **S2 exception:** Proserpine (YBPN) is on the mainland, outside tzdata's Whitsunday island group → Brisbane.
- **BR (0c37247, 393dbf2, 1f596c2):**
  - 24 whole-state rules. AM, PA and PE are SPLIT, using tzdata-named places and the PE mainland residual.
  - **AM:** the great-circle Tabatinga–Porto Acre line.
    - Endpoints are IBGE municipality centroids (the API gives no seats). The minimum margin of 2.3° exceeds the centroid uncertainty.
    - 8 airport-keyed Manaus overrides.
  - **PA:**
    - The Xingu spans 52.921°W–51.617°W in Pará, measured from the ANA rivers shapefile clipped to the IBGE Pará outline. Altamira and São Félix do Xingu fall inside, so the sanity check passed.
    - Placement: east of 51.117°W → Belem (4 airports); west of 53.421°W → Santarem (Itaituba).
  - **R1:** Santarem and Belem have been identical since 2008-06-24, not 2013 as the plan said (corrected per O2).
- **RU (73e9548, 2a695ec):**
  - Region rules come from tzdata europe's "Zone X covers" subject lists, which give ISO codes.
  - Sakha: only the towns zones are named for (Yakutsk, Khandyga, Ust-Nera, Srednekolymsk).
  - Sakhalin: residual west of 150°E, not Severo-Kurilsk. The Kuril rows quote tzdata ("South and Middle Kurils … with the rest of Sakhalin Oblast since at least 2011-09"). R1 caveat: their history before 2011-09 isn't stated.
- **ID (de4e26b, 16b042f):**
  - Provinces on Sumatra, Java/Madura and Sulawesi are covered directly by Keppres's "Seluruh …" wording.
  - Nine provinces created since 1987 attach to their 1987 parent's territory (sqwkd's ruling). The founding UU numbers are identification only, from pasal.id and news.
  - KB and KT → Pontianak (R1).

## AC-3a lint
- 625 non-US airports are placed by municipality rows. Five are flagged, the same five confirmed in 03-02 (CTK6, CTT5, CYPL, CYTL, YBJ). No new flags.
- No 03-03 row cites a gazetteer ID, so the span check doesn't apply to them. Their notes carry the airports' own positions instead.
- 03-03 has no statutory meridians; the Amazonas and Xingu placements are airport-keyed overrides.

## Observed clock over statute (L4)
Eucla, Cocklebiddy and Madura (Australia/Eucla, against the WA Standard Time Act 2005 s.4) join Labrador. The README list is updated at unify.

## Independent check
None for AU, BR, RU or ID. Q2 (ERSA and the AIPs as check-only) is with the operator.

## Deviations
1. **tzdata-only citations:**
   - VIC and NT (landing pages only);
   - NSW (403 at legislation.nsw.gov.au and AustLII);
   - QLD (PDF fetched, text not extractable);
   - TAS (404);
   - BR (planalto.gov.br resets the client);
   - RU (107-FZ not fetched).
2. **planalto.gov.br:**
   - **One curl with a browser-style User-Agent** was made. Its output was deleted unused, and nothing was derived from it.
   - **One WebFetch read of Lei 12.876**; its content was not used for any row.
   - sqwkd: don't repeat it. Primary sources would come from the operator, as with Quebec.
3. The IBGE centroids stand in for municipal seats.
4. The ID founding-law numbers come from secondary listings, for identification only.
5. **Airport-keyed overrides:**
   - AU: 29 (blank municipalities, the Eucla roadhouses, Proserpine);
   - BR: 13 (AM 8, PA 5).
6. The shapefile reader was a one-off scratch tool and isn't in the repo.

## Carried forward
- To 03-04 (in ROADMAP): "a zone with no rows for country X is allowed only if zone_regions maps it to a region of another country listed for it in zone1970; test included", due when UA is mapped.
- Optional: OKTMO for the 20 Sakha airports.
- Q2: AIP and ERSA checks, the operator's decision.

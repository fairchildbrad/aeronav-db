---
phase: 03-iana-timezones
plan: 06
type: summary
status: complete
description: "Independent AIP/ERSA check: closed at the availability survey with 0 airports checked; per-country reasons recorded; a bounded second pass is deferred as optional."
tags: [timezone, aip, ersa, independent-check, survey]
relatedTo: [03-06-PLAN.md, 03-07-SUMMARY.md]
about: "aeronav-db"
---

# 03-06 SUMMARY: AIP/ERSA independent check

## Authority
- **Operator, 2026-11-19 (relayed by sqwkd):** "Yes to both questions" (check-only terms). On 2026-11-20: "Official source checks do not hold up release".
- **sqwkd, verbatim:** "03-06 scope: (B) CLOSE. The result is the survey".

## Result: 0 airports checked. Base build a9336f52….
| Country | Reason |
|---|---|
| AU | **Use terms.** Airservices "Conditions of use", read 2026-11-21: "The AIS Publications may be displayed and viewed on screen in an unaltered form (which retains this notice) for personal, non-commercial purposes only." and "For the avoidance of doubt, personal use does not include use for internal business purposes." |
| NZ | **Use terms** (on the AU precedent). http://www.aip.net.nz/ redirects to its disclaimer, read 2026-11-21: "made available free-of-charge to you as an individual user", "for your personal use only"; no copying or reproduction except for personal use |
| RU | captcha on caica.ru /ANI_Official/Aip/ |
| ID | DNS failure, aimindonesia.dephub.go.id |
| BR | **checked: 0.** The AIP (AIRAC AIP A 21/2026, effective 29 OCT 2026, confirmed from its cover) states no time zones: GEN 2.1 §2 gives UTC only, and no AD 2 entry gives an offset. ROTAER is not used; sqwkd offered it to the operator. The scratch PDF and text were deleted |
| CN | timeout, then ECONNREFUSED (aischina.com) |
| DE | reachable (aip.dfs.de/basicIFR, "Effective: 29 OCT 2026"); GEN index link 404, so undetermined |
| ES, GL, PF | undetermined (ES body is only "AIP"; GL eAIP link not found; Polynésie eAIP not reached) |
| AR, CD, CL, CY, EC, FM, KI, KZ, MH, MN, MY, PG, PS, PT, UA, UZ, VN, XK | no official eAIP URL confirmed, none guessed |

## Count reconciliation (sqwkd condition 2)
"26 countries from 03-04" is zone1970's 33 multi-zone countries minus US, CA, MX, AU, BR, RU and ID. The part-2 survey covered **24** = 23 of those 26 plus **XK** (Kosovo, not in zone1970, handled in 03-04). The 3 not surveyed:
- **AQ:** NULL by design, no national AIP.
- **TF:** no present airports, so not in the 03-04 table.
- **UM:** US Minor Outlying Islands, placed in 03-05 through NASR/OA inputs; no national AIP.

## Rules kept
Only free, no-login sources; no workaround and no User-Agent change. Nothing is stored except editions, counts and these reasons. No offsets were kept.

## Deferred (optional; STATE.md)
(A) A bounded second pass. Landing URLs come only from Eurocontrol's AIS-online list (https://www.eurocontrol.int/articles/ais-online) and ICAO or national CAA sites. Open GEN 2.1 (and one AD 2 page if GEN 2.1 is silent) for DE, ES, GL, PF and any country whose URL is confirmed. Write predictions only where GEN 2.1/AD 2 actually states a zone or offset, then compare. It re-opens as its own plan only if the operator wants it.

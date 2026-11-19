---
type: doc
status: active
tags: [timezone, sources, citations]
relatedTo: [03-02-PLAN]
---

# Time zone rule sources

Short keys used in `rules.csv` notes. Facts (place → zone) are taken from these; no text is copied beyond short quotes.

## LHHEUM
Ley de los Husos Horarios en los Estados Unidos Mexicanos. DOF 2022-10-28; last reform DOF 2022-11-29.
- URL: https://www.diputados.gob.mx/LeyesBiblio/pdf_mov/Ley_de_los_Husos_Horarios_en_los_Estados_Unidos_Mexicanos.pdf
- Fetched: 2026-11-19, sha256 `2cd9c3c2a3b0e433a4e789bc2f3f0e18142aa55d96689eb870ebfec4db7367f9`
- Art. 3: the four zones by state (fr. II excepts Bahía de Banderas from Nayarit). Art. 5: the northern-border municipalities on seasonal time, by name.

## tzdata northamerica
IANA tzdata 2026f `northamerica` (public domain), vendored beside zone1970.tab from the same release; zone1970.tab is byte-identical to the vendored copy.
- URL: https://data.iana.org/time-zones/releases/tzdata2026f.tar.gz, sha256 `01b4a91cec5167ed48c11e8ab78f2048cead78ce94b0cafcad0ae8c5a3044d3d`
- Used for named time anomalies in Canadian provinces (03-02 O1-O3).

## Ontario Time Act
R.S.O. 1990, c. T.9, s. 2(1)-(2): east of 90°W Eastern, west Central; no named exceptions. https://www.ontario.ca/laws/statute/90t09 (fetched 2026-11-19).

## CGNDB (Ontario)
Canadian Geographical Names Database, Ontario CSV (Natural Resources Canada, Open Government Licence - Canada). Used only as evidence of a place's longitude in notes; no rows are copied.
- URL: https://ftp.cartes.canada.ca/pub/nrcan_rncan/vector/geobase_cgn_toponyme/prov_csv_eng/cgn_on_csv_eng.zip (Last-Modified 2026-11-18), sha256 `bfee1cc93e6caf31db377045bb076bce8809d26cc9793aa08bd8b15d4fa112bc`
- O1 margin: easternmost anomaly named in northamerica is the Big Trout Lake area (lake FAIIZ at 90.007W; "extending east of 90°W"). Others: Pickle Lake FDZLA 90.140W, Mishkeegogamang FOBRY 90.229W, Upsala FCZHV 90.498W, Atikokan FAEBC 91.622W. Margin to 85.5W ≈ 4.5°, so the 85W cut-off holds.

## CGNDB (Nova Scotia)
https://ftp.cartes.canada.ca/pub/nrcan_rncan/vector/geobase_cgn_toponyme/prov_csv_eng/cgn_ns_csv_eng.zip, sha256 `86d8094a9a27ca970d3c7637feb44bdacb60dc1946e9d57dd0b31b13d6231c47`. The county in each record's Location field decides island vs mainland. Port Hawkesbury (on the strait) and Sable Island (no record) stay NULL. America/Glace_Bay and America/Halifax differ only before 1972.

## BC government release 2026AG0013-000209
https://news.gov.bc.ca/releases/2026AG0013-000209 (fetched 2026-11-19): permanent Pacific time from 2026; names the northeastern places on year-round UTC-7 and Fort Ware (Kwadacha) as an exception.

## BC Interpretation Act s.26 and CGNDB (BC)
- RSBC 1996 c 238 s.26: "Pacific Time" is UTC-7; a reference to time in BC is Pacific Time. https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96238_01 (fetched 2026-11-19)
- CGNDB BC: https://ftp.cartes.canada.ca/pub/nrcan_rncan/vector/geobase_cgn_toponyme/prov_csv_eng/cgn_bc_csv_eng.zip, sha256 `08653acac0eec1141cbd996259a1ba1ee55d820b7675e269b55502a9cad20524`. The land district in each record's Location field is used.
- D1 membership lists: RDEK and RDCK sites returned no membership list on their home pages; RDKB and CSRD return 403 to automated fetch (not bypassed). Cranbrook, Castlegar, Trail and Revelstoke stay NULL until an official list is read.

## StatCan SGC 2021 and CGNDB (QC)
- SGC 2021 structure CSV: https://www.statcan.gc.ca/en/statistical-programs/document/sgc-cgt-2021-structure-eng.csv, sha256 `55f6eb915415b4aa911c6fce3cbaced641c4ed9af023bebc414b2929721a62d2`. Gives district (CD) membership for D1; CSD type comes from the CGNDB generic term (sqwkd 2026-11-19: City, Town, Village, District Municipality only).
- CGNDB QC: https://ftp.cartes.canada.ca/pub/nrcan_rncan/vector/geobase_cgn_toponyme/prov_csv_eng/cgn_qc_csv_eng.zip, sha256 `b0314109acbac6abc9b6726a72c78f385aa9a722f4f45b168379e92c8c1d78f3`.
- The Legal Time Act (CQLR c T-5.1) at legisquebec.gouv.qc.ca returns 403 to automated fetch; the operator supplied the text instead (2026-11-19).

## Quebec Legal Time Act
CQLR c T-5.1 (2006, c. 39), English consolidation "Updated to October 15, 2026", © Québec Official Publisher, PDF supplied by the operator 2026-11-19. Not public domain, so only the citation and hash are kept; no text is vendored.
- sha256 `0292d9dada4f05f2fea051be116bc98be0a6f56edac4d12321540d32f89e7205` (T-5.1.pdf, 91.5 KB)
- s.1: west of 63°W is Eastern time (with DST); s.1 also applies to all of MRC Minganie.
- s.2: east of 63°W and the Listuguj reserve are Atlantic time; DST only in the Îles-de-la-Madeleine and Listuguj, so the rest is AST all year (America/Puerto_Rico).
- Rows: rule-cited when every matching CGNDB populated place or administrative area and the airport lie west of 63.5°W (0.5° margin, as O1); name-cited by MRC when the municipality's CGNDB record gives Location MRC Minganie (Natashquan, Baie-Johan-Beetz). SGC 2021 merges Minganie and Le Golfe-du-Saint-Laurent into CD 2498, so it cannot confirm MRC membership; CGNDB's Location field (source: Commission de toponymie) is the only membership source.
- Agrees with tzdata 2026f northamerica (Quebec commentary): Îles-de-la-Madeleine and Listuguj on America/Halifax, east of Natashquan on America/Puerto_Rico.

## Newfoundland and Labrador Standard Time Act
RSNL 1990 c S-23 (am. 2006 c31, 2011 c6), https://assembly.nl.ca/Legislation/sr/statutes/s23.htm (fetched 2026-11-19, sha256 `0511a08873a3a35dba5ce4ccdb4550994738d3717f972e74e4df2fc5945cdd37`). s.2(1): time in the province is UTC-3:30; s.3(1.1): UTC-2:30 from the second Sunday in March to the first Sunday in November; s.4 allows regulations applying another zone to part of the province (none found; tzdata: "Legally Labrador should observe Newfoundland time").
- CGNDB NL: https://ftp.cartes.canada.ca/pub/nrcan_rncan/vector/geobase_cgn_toponyme/prov_csv_eng/cgn_nl_csv_eng.zip, sha256 `6021780e243d0402c3a2333c395e318bfa44b21ba76e509d02ad43cfb71b1da9`. Its Location field is mostly empty, so island membership comes from SGC 2021 (CDs 1001-1009 are the island; 1010-1011 Labrador).

## Saskatchewan Time Act, 2026
Bill 58 (30th Legislature, 2nd session), https://docs.legassembly.sk.ca/legdocs/Bills/30L2S/Bill30-58.pdf (fetched 2026-11-19, sha256 `4c288edf072161e780174abfefff086802dfc75c1d1c77550f7d926f6c488039`); in force 2026-10-30 (government release of that date; tzdata cites OIC 438/2026). s.4: central standard time (UTC-6) in Saskatchewan, which includes Lloydminster (s.2, s.3(2)), subject to s.5 time option areas prescribed by regulation. https://www.saskatchewan.ca/en/government/municipal-administration/tools-guides-and-resources/saskatchewan-time-system (fetched 2026-11-19): "There are currently no time option areas in Saskatchewan."
- CGNDB SK: cgn_sk_csv_eng.zip, sha256 `f1749cf9d8cc547e4cbae054023214a57e9e11402e54adee49621542832b523d`. Swift Current City HAPKT (50.288N 107.794W) is the S2 centre.

## Nunavut: SOR/2001-182
Proclamation establishing three different time zones in Nunavut (Interpretation Act s.35(1)), https://laws.justice.gc.ca/eng/regulations/SOR-2001-182/FullText.html (current to 2026-10-29, fetched 2026-11-19, page sha256 `08c54722dbd7ad1f05e9a7134a2505c7559e5702c87cee65cad05f42cbcaebd0`): (a) east of 85°W and Southampton Island EST; (b) 85°W-102°W except Southampton and Kitikmeot CST; (c) west of 102°W and all of Kitikmeot MST. Territorial Time Zone Regulations R-033-2021 (DST) returned 403 at nunavutlegislation.ca; DST from tzdata (deviation). CGNDB NU sha256 `1bd555b78ae595fe3dc48d9fcd27f89887f4bc4e856cd48e3ecaef688abc22d9`; Kitikmeot = SGC 2021 CD 6208.

## Northwest Territories: R-090-2026
NWT Time Regulations R-090-2026 (UTC-6 year-round, in force 2026-08-21). justice.gov.nt.ca served an HTML landing page instead of the PDF (not worked around); cited via tzdata 2026f northamerica (Eggert 2026-08-21) and the GNWT release (deviation, with AB MB NB PE). CGNDB NT sha256 `544a322e7780058fd4ba3a70fce0d1b947212fe6c218d093927ba2d9e619ce72`.

## Yukon: Interpretation Act and OIC 2020/125
RSY 2002 c125 s.33; OIC 2020/125 (UTC-7 year-round) returned 403 at yukon.ca and laws.yukon.ca; cited via tzdata's quote (deviation). Zone split: Commissioner's Order 1967/59 (138°W) as quoted verbatim in tzdata. CGNDB YT sha256 `ef8cfc441ab5940b840e093e81741bbd13977e0f39c64954a5f8f72a65bcc5c5`.

## tzdata australasia, southamerica, europe, asia, backward
Vendored from the same tzdata2026f.tar.gz (sha256 above) for 03-03: named anomalies and zone histories for AU, BR, RU and ID; `backward` for link names (e.g. Australia/Canberra).

## Brazil: Decreto 2.784/1913, Lei 11.662/2008, Lei 12.876/2013
planalto.gov.br resets connections from the automated client (2026-11-19); not worked around. Cited via tzdata 2026f `southamerica`, which quotes Lei 11.662/2008, gives each zone's state list, names east/west Pará and Amazonas places, and gives the Tabatinga-Porto Acre great-circle line (Lei 12.876/2013) as the Amazonas division. Deviation: no statute text or hash.

## Australia
- ACT Standard Time and Summer Time Act 1972: https://www.legislation.act.gov.au/DownloadFile/a/1972-34/current/RTF/1972-34.RTF, sha256 `832237f15ccdcb2e411e659ee133475b6691c089bc85538771a116a9df0463c0`.
- SA Standard Time Act 2009: https://www.legislation.sa.gov.au/_legislation-documents/lz/c/a/standard-time-act-2009/current/2009.4.un.rtf, sha256 `49c7ab7b35790c96fc92fddfa2f19ec4b974d511fcc62dc14907a2ca28800050`.
- WA Standard Time Act 2005 s.4: https://www.legislation.wa.gov.au/legislation/prod/filestore.nsf/FileURL/mrdoc_5122.htm/$FILE/Standard%20Time%20Act%202005%20-%20%5B00-00-02%5D.html, sha256 `e64efe2d60fd40c52a4fa8ed1bea27507806d08c96be53129e78ee7f2553026f`.
- Qld Standard Time Act 1894: https://www.legislation.qld.gov.au/view/pdf/inforce/current/act-1894-014, sha256 `e29917b4416dc6fd3fc355b7253f7a1d2177e7d28ca09bff99950d3756466534`. Text not extractable with our tools, so it is cited via tzdata.
- Blocked or unavailable, so cited via tzdata `australasia` (deviation):
  - NSW Standard Time Act 1987 (legislation.nsw.gov.au and AustLII return 403);
  - Tas (404);
  - Vic and NT (landing pages only).
- Positions: OurAirports airport coordinates (public domain) are the only position evidence. No Australian gazetteer is used: Geoscience Australia's is CC-BY.

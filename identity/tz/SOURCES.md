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
- The Legal Time Act (CQLR c T-5.1) at legisquebec.gouv.qc.ca returns 403 to automated fetch; the operator has been asked for the text.

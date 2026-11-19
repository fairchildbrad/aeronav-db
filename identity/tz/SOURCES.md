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

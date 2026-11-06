# aeronav-db

A public-domain aeronautical database — **airports, NAVAIDs, named fixes,
airways, and ARTCC/FIR boundaries** —
compiled into a single SQLite file and rebuilt automatically every AIRAC cycle.

One file, no API key, no licence to read, works offline.

```
airports    35,305 codes   IATA + ICAO + FAA identifiers
fixes       70,056         US named fixes / 5-letter name codes
navaids      9,752         worldwide VOR / VORTAC / NDB / DME / TACAN
airways      1,515         US low/high routes, 19,247 ordered points
boundaries      54         ARTCC and FIR rings, 2,687 ordered points
```

> **Not for navigation.** This is a convenience dataset for software that needs
> to put a marker on a map. It is not a certified navigation database, it is not
> quality-assured for flight, and it must not be used as a primary source for
> operational decisions.

## Where the data comes from

| Source | Covers | Cadence | Licence |
|---|---|---|---|
| [FAA NASR 28-Day Subscription](https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/) | United States | 28-day AIRAC | US Government work — public domain |
| [OurAirports](https://ourairports.com/data/) | Worldwide | Nightly | Dedicated to the public domain by the publisher |

**Merge rule: NASR wins inside US airspace; OurAirports is the global fallback.**
A national aeronautical information service is authoritative within its own
jurisdiction, so US airports and navaids carry the FAA's own surveyed
coordinates, and everywhere else falls back to OurAirports — which is also the
only one of the two carrying IATA codes outside the US.

For navaids the rule is applied a little harder: OurAirports rows inside US
jurisdiction are dropped outright rather than merged, because its US layer still
lists aids the FAA has decommissioned under the VOR MON programme and the NDB
drawdown, and a dead navaid that resolves is worse than one that is missing.
Outside that jurisdiction the two layers overlap only where NASR carries a
Canadian, Bahamian or Mexican border aid, so an OurAirports row is dropped when
it names a NASR aid standing in roughly the same place. Everything else is kept.

`airports` and `navaids` are the two worldwide tables. `fixes`, `airways` and
`boundaries` come from NASR alone — OurAirports does not publish them.

**NASR's authority is jurisdictional, not global.** It is the source of truth
about a US airport; it is not the source of truth about which airport owns a
globally-assigned IATA code. Those are different claims, and conflating them
was a real bug: a three-letter FAA local identifier collides with a foreign
IATA code **512 times** in the 2026-08-06 cycle, and NASR was displacing the
IATA row every time. `DUB` resolved to DUBOIS MUNI in Pennsylvania rather than
Dublin, `CPT` to CLEBURNE RGNL in Texas rather than Cape Town, `PUJ` to a field
in Georgia rather than Punta Cana — 76 of the 512 were large international
airports.

So NASR displaces an OurAirports row only when the two sit within
**25 NM** of each other, which is the test for *is this the same field described
twice* rather than *two airports sharing three letters*. All 1,617 genuine
same-airport pairs are unaffected and still take the FAA's surveyed
coordinates. A displaced US field keeps its ICAO identifier (Paulding is
reachable as `KPUJ`), and the five US fields that have no ICAO id are the whole
cost of the fix.

Both sources are public domain, so **the compiled database is too**. There is no
attribution requirement and no copyleft clause to propagate into whatever you
build on it.

The two sources are not equally airtight, and it is worth knowing which is
which. NASR is a work of the US Government and uncopyrightable under 17 USC
§105 — that is about as settled as data provenance gets. OurAirports is a
publisher's **dedication** of its data to the public domain, not a named
instrument like CC0, and OurAirports itself aggregates from further sources: it
credits the discontinued NGA DAFIF alongside community sites and individual
contributors, without stating their copyright status. DAFIF was a US Government
work, but NGA withdrew it from public distribution in 2006 after foreign
aeronautical information services objected to redistribution of their source
data — so US public-domain status does not settle what those bodies may claim in
their own jurisdictions. Separately, the EU database right (Directive 96/9/EC)
protects compilation investment independently of copyright, and coordinates are
facts that copyright would not reach anyway.

None of that is a reason not to use this database, and relying in good faith on
an explicit public-domain dedication is a normal position. But if your exposure
is in the EU or UK, make your own assessment rather than taking this README's
word for it. Every row records its `source`, so a consumer who wants only the
US Government layer can filter to `source = 'nasr'` and stand on §105 alone.

## Using it

Every release publishes four assets at stable "latest" URLs:

```bash
# What is currently published -- cycle, checksum, row counts. ~400 bytes.
curl -sL https://github.com/fairchildbrad/aeronav-db/releases/latest/download/manifest.json

# The database itself. ~10.1 MB.
curl -sLO https://github.com/fairchildbrad/aeronav-db/releases/latest/download/navigation.sqlite3
curl -sLO https://github.com/fairchildbrad/aeronav-db/releases/latest/download/navigation.sqlite3.sha256
sha256sum -c navigation.sqlite3.sha256
```

The intended update loop is: **fetch the manifest, compare `airac_cycle` and
`sha256` with what you already have, and only download the database when they
differ.** The manifest is tiny, so a client can check often and download rarely.

```json
{
  "schema_version": "2",
  "airac_cycle": "2026-08-06",
  "built_at": "2026-08-17T18:48:21+00:00",
  "database": {
    "filename": "navigation.sqlite3",
    "size_bytes": 10113024,
    "sha256": "8a5b1ab2..."
  },
  "counts": {
    "airports": 35305, "fixes": 70056, "navaids": 9752,
    "airways": 1515, "airway_points": 19247,
    "boundaries": 54, "boundary_points": 2687
  },
  "sources": "FAA NASR 28-Day Subscription (US Government work, public domain); OurAirports (publisher dedicates to the public domain)"
}
```

### Querying

```sql
-- Resolve an airport by IATA, ICAO, or FAA identifier.
SELECT lat, lon, name, source FROM airports WHERE code = 'KDFW';

-- Named fixes. Identifiers are indexed; they are unique today but the schema
-- does not assume it, because a future cycle could change that.
SELECT lat, lon, artcc_low FROM fixes WHERE fix_id = 'BOSOX';

-- Navaids. An identifier can name several aids worldwide, so disambiguate by
-- position -- here, the nearest 'BIG' to a point over southern England.
SELECT ident, nav_type, name, lat, lon FROM navaids WHERE ident = 'BIG'
ORDER BY (lat - 51.3) * (lat - 51.3) + (lon - 0.0) * (lon - 0.0) LIMIT 1;

-- One airway, in order, ready to draw. Points that could not be placed come
-- back with NULL coordinates rather than being skipped, so a consumer can
-- break the line there instead of drawing a wrong straight segment.
SELECT seq, point_id, lat, lon FROM airway_points
WHERE awy_id = 'V1' AND location = 'C' ORDER BY seq;

-- One boundary ring, in order.
SELECT lat, lon FROM boundary_points
WHERE boundary_id = 'ZAB' AND kind = 'ARTCC' AND altitude = 'HIGH'
ORDER BY seq;

-- Which cycle is this?
SELECT value FROM metadata WHERE key = 'airac_cycle';
```

### Schema

```sql
airports(code PRIMARY KEY, lat, lon, name, kind, code_type, source)
navaids (ident, nav_type, name, lat, lon, frequency, source)   -- indexed on ident
fixes   (fix_id, lat, lon, use_code, artcc_high, artcc_low, state_code, source)

airways        (awy_id, location, designation, regulatory, point_count, source)
                 -- PRIMARY KEY (awy_id, location)
airway_points  (awy_id, location, seq, point_id, point_type, lat, lon,
                 artcc, state_code)  -- PRIMARY KEY (awy_id, location, seq)

boundaries     (boundary_id, name, kind, altitude, point_count, source)
                 -- PRIMARY KEY (boundary_id, kind, altitude)
boundary_points(boundary_id, kind, altitude, seq, lat, lon, description)

metadata(key PRIMARY KEY, value)
```

`source` is `nasr` or `ourairports` on every row, so a consumer can always tell
which layer answered. `code_type` is `iata`, `icao`, or `faa`.

`metadata` carries `licence` and `disclaimer` alongside the cycle and counts, so
the terms and the not-for-navigation warning travel **inside** the file. A
consumer that fetched only `navigation.sqlite3` still has them:

```sql
SELECT value FROM metadata WHERE key IN ('licence', 'disclaimer', 'sources');
```

The build refuses to publish a database missing either key.

Airports are keyed one row per code, so an airport with both an IATA and an ICAO
code appears twice with the same coordinates. That makes lookup a primary-key hit
regardless of which code system the caller has.

`navaids.ident` is **indexed, not unique** — a 2-3 character navaid identifier is
reused all over the world, and 1,837 of them name more than one aid. `BIG` is a
VORTAC in Alaska, a VOR/DME outside London, and another in Turkey. A worldwide
consumer has to disambiguate by position (or by `source`, for US-only work);
`SELECT ... WHERE ident = ?` returning one row is not something to rely on.
`nav_type` speaks NASR's vocabulary on both layers, so `VOR/DME` — not
OurAirports' `VOR-DME` — matches everywhere, and frequencies are MHz for VHF
aids and kHz for NDBs regardless of which source the row came from.

Airways and boundaries are ordered geometry, so each is two tables: one naming
the feature, one row per point along it. Read them with `ORDER BY seq`.

`location` is part of an airway's identity because NASR scopes airway
identifiers regionally — `C`, `A` for Alaska, `H` for Hawaii — so the same
identifier can name two different airways. `C` is not CONUS-only: it also
carries the Pacific oceanic routes worked by Oakland, Guam and Honolulu.

Boundary `altitude` (`LOW`, `HIGH`, `UNLIMITED`) is part of a boundary's
identity too, because one centre publishes a different ring for each stratum.
`kind` is `ARTCC` for US domestic centres and `FIR`, `CTA/FIR`, `CTA` or `UTA`
for the international ones.

NASR publishes airway points by name with no coordinates. Resolution against the
NASR layer of `navaids` and against `fixes` happens once at build time — the
worldwide navaids are deliberately kept out of that index, because a US airway
naming a 3-letter aid must not resolve to a foreign one sharing the identifier.
It runs at build time because it needs
disambiguation rules and getting it wrong puts an airway across the wrong part
of the country. In the current cycle 169 of 19,247 points (0.9%) do not
resolve; those rows are kept with NULL `lat`/`lon` so the gap is visible rather
than silently closed.

## How the automation works

A weekly job asks the FAA whether a cycle newer than the last release is being
served. If so it builds, verifies, and publishes; if not it does nothing.

```
weekly cron ──▶ newest in-force cycle served by FAA?
                          │
                  same as last release? ──▶ yes ──▶ stop
                          │ no
                          ▼
              build ──▶ verify ──▶ publish release
```

**Verification is a gate, not a report.** Consumers update themselves unattended,
so a broken build must not reach a release. `python -m aeronav_db.verify` refuses
anything that fails an integrity check, is missing a table, has an implausible
row count, has lost an entire source layer from either merged table, or fails a
canary lookup — seven known airports spanning both layers and both code systems,
and three known navaids spanning both layers, each checked to be within half a
degree of where it belongs. A latitude/longitude swap fails it.

Nothing is committed to the repo by the automation. The database lives only in
releases, so cloning stays cheap and history stays free of binaries.

## Building it yourself

```bash
pip install -e ".[dev]"

python -m aeronav_db.build                    # newest in-force cycle
python -m aeronav_db.build --cycle 2026-08-06
python -m aeronav_db.verify dist/navigation.sqlite3
```

Downloading NASR pulls a ~250 MB zip, so local iteration is easier against a
cached copy:

```bash
python -m aeronav_db.build \
  --nasr-zip ./28DaySubscription_Effective_2026-08-06.zip \
  --ourairports-csv ./airports.csv \
  --ourairports-navaids-csv ./navaids.csv
```

The build is **deterministic for a given SQLite version** — rows are sorted and
the database is `VACUUM`ed, so rebuilding from identical inputs on the same
machine produces a byte-identical file.

It is **not** byte-identical across SQLite versions. The file header records the
library version that last wrote it, and page layout differs slightly between
releases: the same data built under SQLite 3.45.1 and 3.53.1 differed in ~17.7 KB
of a 7.6 MB build while every table matched row for row. So a checksum change
means *"this file differs"*, not always *"the data changed"* — if the runner
image bumps SQLite, one cycle will publish a new checksum for unchanged data and
consumers will re-download once. Harmless, but worth knowing before you treat
the checksum as a content fingerprint.

### Tests

```bash
pytest -q
```

Fully offline. The merge rules, verification gate, and cycle arithmetic are all
driven with synthetic rows; nothing in the suite contacts the FAA or OurAirports.

## Notes for anyone parsing NASR directly

Two things cost time when this was first written, both worth knowing:

- **`nfdc.faa.gov` answers every `HEAD` request with HTTP 503.** Probe with a
  ranged `GET` (`Range: bytes=0-0`) instead. It also rejects a default
  `curl`/`urllib` user agent, so send a browser one.
- **The CSVs are inside a nested zip.** The 28-day subscription zip contains
  `CSV_Data/<DD_Mon_YYYY>_CSV.zip`, and the subscriber files
  (`APT_BASE.csv`, `NAV_BASE.csv`, `FIX_BASE.csv`) are inside *that*. The
  top-level archive holds the legacy fixed-width `.txt` files.

Coordinates in `*_BASE.csv` are already signed decimal degrees in
`LAT_DECIMAL`/`LONG_DECIMAL`; the separate hemisphere columns are for the
degrees/minutes/seconds fields and do not need to be applied again.

## Scope

**If a public-domain source publishes it and it belongs on a map, it goes in.**
This database exists to be consumed by other software, so the consumer decides
what it needs — a layer is not left out because some callers will ignore it.
Tables are additive and independent, so an unused layer costs a reader nothing
but the bytes it occupies.

Not in yet, in rough order of intent:

- **SIDs, STARs, and approach procedures.** The FAA publishes these in the CIFP,
  but the coded procedures need ARINC 424 parsing — a substantially larger
  reader than the CSV layers here, and the reason they are not in already. It is
  a matter of effort, not scope.
- **Runways.** Both sources carry them; a straightforward next layer.

The one real boundary is **licensing**, and it is not a consumer's call to make:

- **European en-route fixes.** Eurocontrol's Free Route Airspace points list is
  the obvious next layer geographically, but its terms are
  development/non-operational, unlike the two public-domain sources here.
  Adding it would put a licensing asterisk on an otherwise unencumbered
  database, which would cost every consumer something — including the ones that
  never query a European fix. That trade only goes the other way if the data
  ships as a separate, clearly-labelled artifact.

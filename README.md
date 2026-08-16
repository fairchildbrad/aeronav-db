# aeronav-db

A public-domain aeronautical database — **airports, NAVAIDs, named fixes,
airways, and ARTCC/FIR boundaries** —
compiled into a single SQLite file and rebuilt automatically every AIRAC cycle.

One file, no API key, no licence to read, works offline.

```
airports    35,302 codes   IATA + ICAO + FAA identifiers
fixes       70,056         US named fixes / 5-letter name codes
navaids      1,629         US VOR / VORTAC / NDB / TACAN
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
| [OurAirports](https://ourairports.com/data/) | Worldwide | Nightly | CC0 — public domain |

**Merge rule: NASR wins inside US airspace; OurAirports is the global fallback.**
A national aeronautical information service is authoritative within its own
jurisdiction, so US airports carry the FAA's own surveyed coordinates, and
everywhere else falls back to OurAirports — which is also the only one of the two
carrying IATA codes outside the US.

Both sources are public domain, so **the compiled database is too**. There is no
attribution requirement and no copyleft clause to propagate into whatever you
build on it.

## Using it

Every release publishes three assets at stable "latest" URLs:

```bash
# What is currently published -- cycle, checksum, row counts. ~400 bytes.
curl -sL https://github.com/fairchildbrad/aeronav-db/releases/latest/download/manifest.json

# The database itself. ~7.6 MB.
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
  "built_at": "2026-08-13T22:41:07+00:00",
  "database": {
    "filename": "navigation.sqlite3",
    "size_bytes": 9506816,
    "sha256": "422b3eec..."
  },
  "counts": {
    "airports": 35302, "fixes": 70056, "navaids": 1629,
    "airways": 1515, "airway_points": 19247,
    "boundaries": 54, "boundary_points": 2687
  },
  "sources": "FAA NASR 28-Day Subscription (public domain); OurAirports (CC0 public domain)"
}
```

### Querying

```sql
-- Resolve an airport by IATA, ICAO, or FAA identifier.
SELECT lat, lon, name, source FROM airports WHERE code = 'KDFW';

-- Named fixes. Identifiers are indexed; they are unique today but the schema
-- does not assume it, because a future cycle could change that.
SELECT lat, lon, artcc_low FROM fixes WHERE fix_id = 'BOSOX';

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

Airports are keyed one row per code, so an airport with both an IATA and an ICAO
code appears twice with the same coordinates. That makes lookup a primary-key hit
regardless of which code system the caller has.

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

NASR publishes airway points by name with no coordinates. Resolution against
`navaids` and `fixes` happens once at build time, because it needs
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
row count, has lost an entire source layer, or fails a canary lookup — seven
known airports spanning both layers and both code systems, each checked to be
within half a degree of where it belongs. A latitude/longitude swap fails it.

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
  --nasr-zip ./28DaySubscription_Effective_2026-07-09.zip \
  --ourairports-csv ./airports.csv
```

The build is **deterministic for a given SQLite version** — rows are sorted and
the database is `VACUUM`ed, so rebuilding from identical inputs on the same
machine produces a byte-identical file.

It is **not** byte-identical across SQLite versions. The file header records the
library version that last wrote it, and page layout differs slightly between
releases: the same data built under SQLite 3.45.1 and 3.53.1 differs in ~17.7 KB
of a 7.6 MB file while every table matches row for row. So a checksum change
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

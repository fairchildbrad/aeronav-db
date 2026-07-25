# aeronav-db

A public-domain aeronautical database — **airports, NAVAIDs, and named fixes** —
compiled into a single SQLite file and rebuilt automatically every AIRAC cycle.

One file, no API key, no licence to read, works offline.

```
airports   35,305 codes   IATA + ICAO + FAA identifiers
fixes      70,031         US named fixes / 5-letter name codes
navaids     1,629         US VOR / VORTAC / NDB / TACAN
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
  "schema_version": "1",
  "airac_cycle": "2026-07-09",
  "built_at": "2026-07-25T20:44:50+00:00",
  "database": {
    "filename": "navigation.sqlite3",
    "size_bytes": 7577600,
    "sha256": "97b2e441..."
  },
  "counts": { "airports": 35305, "fixes": 70031, "navaids": 1629 },
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

-- Which cycle is this?
SELECT value FROM metadata WHERE key = 'airac_cycle';
```

### Schema

```sql
airports(code PRIMARY KEY, lat, lon, name, kind, code_type, source)
navaids (ident, nav_type, name, lat, lon, frequency, source)   -- indexed on ident
fixes   (fix_id, lat, lon, use_code, artcc_high, artcc_low, state_code, source)
metadata(key PRIMARY KEY, value)
```

`source` is `nasr` or `ourairports` on every row, so a consumer can always tell
which layer answered. `code_type` is `iata`, `icao`, or `faa`.

Airports are keyed one row per code, so an airport with both an IATA and an ICAO
code appears twice with the same coordinates. That makes lookup a primary-key hit
regardless of which code system the caller has.

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

The build is **deterministic** — rows are sorted and the database is `VACUUM`ed,
so identical inputs produce a byte-identical file. That is what makes the
published checksum meaningful: it changes when the data changes, not when the
build ran.

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

Deliberately **not** included:

- **Airways, SIDs/STARs, and approach procedures.** The FAA publishes these, but
  the coded procedures (CIFP) need ARINC 424 parsing that is its own project.
- **European en-route fixes.** Eurocontrol's Free Route Airspace points list is
  the obvious next layer, but its terms are development/non-operational, unlike
  the two public-domain sources here. Adding it would put a licensing asterisk on
  an otherwise unencumbered database.
- **Airspace boundaries.** Different shape of data; belongs in its own dataset.

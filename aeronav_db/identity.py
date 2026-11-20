"""Permanent airport identity and dated code history.

Neither source offers a key that survives every change. NASR's site number
holds across identifier changes (2Y1 -> 47IA kept 06278.), but it is unique only
together with the site type, it gets corrected (18AL: 03329.19 -> 00329.19),
and the type itself can change. OurAirports' ``id`` holds across code changes
(PBI -> DJT stayed 3766), but duplicates get merged by deleting an id, with
nothing pointing to the survivor. So aeronav-db mints its own id, ``AP`` plus
seven digits, and carries the source keys as attributes.

This module is pure. ``apply_cycle`` takes the previous cycle's state and the
current cycle's observations and returns the next state. The weekly build and
the archive backfill both run through it, so both produce the same history.

Guarantees, which verify also enforces on the published file:

* An id, once issued, is never renamed, reused or removed.
* A closed interval never changes. A cycle can only close intervals that
  are still open, and open new ones.
* Leaving the dataset closes presence and code intervals. It never sets a
  closure status: only a source can say an airport closed.
* Aliases are one hop. When identities converge, the lower id survives, and
  every alias that pointed at the merged id is rewritten to point at the
  survivor.
"""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field

from aeronav_db.build import (
    FAA_LID_RE,
    IATA_RE,
    ICAO_RE,
    NASR_JURISDICTION,
    NASR_SITE_TYPES,
    SAME_AIRPORT_NM,
    _distance_nm,
    _parse_coordinates,
    nasr_source_key,
    ourairports_source_key,
)
from aeronav_db.tz import NASR_LEGACY_COUNTRIES  # retired NASR codes → ISO

ID_RE = re.compile(r"^AP\d{7}$")
# A corrected NASR site number is accepted as the same field only when the FAA
# identifier is unchanged and the reference point has barely moved.
SITE_CORRECTION_NM = 1.0
SCHEMES = ("faa", "icao", "iata")


def format_id(number: int) -> str:
    if not 0 < number <= 9_999_999:
        raise ValueError(f"airport id counter out of range: {number}")
    return f"AP{number:07d}"


def normalize_id(value: str) -> str:
    """Ids compare case-insensitively; this is the canonical spelling."""
    candidate = value.strip().upper()
    if not ID_RE.match(candidate):
        raise ValueError(f"not an airport id: {value!r}")
    return candidate


@dataclass(frozen=True)
class Observation:
    """One source record for one cycle, already reduced to what identity needs.

    ``source_status`` is 'operational', or a closure the source itself states
    ('closed_indefinitely', 'closed_permanently', 'closed').
    """

    source: str
    nasr_site_no: str | None
    nasr_site_type: str | None
    ourairports_id: str | None
    codes: tuple[tuple[str, str], ...]
    lat: float
    lon: float
    name: str | None
    kind: str | None
    source_status: str
    iso_country: str | None


@dataclass(frozen=True)
class Identity:
    airport_id: str
    nasr_site_no: str | None
    nasr_site_type: str | None
    ourairports_id: str | None
    name: str | None
    lat: float
    lon: float
    kind: str | None
    source_status: str
    iso_country: str | None
    first_cycle: str
    last_seen_cycle: str
    match_basis: str


@dataclass(frozen=True, order=True)
class CodeInterval:
    airport_id: str
    scheme: str
    code: str
    effective_date: str
    valid_to: str | None
    source: str = field(compare=True)


@dataclass(frozen=True, order=True)
class Presence:
    airport_id: str
    effective_date: str
    valid_to: str | None


@dataclass(frozen=True, order=True)
class Alias:
    alias_id: str
    airport_id: str
    effective_date: str
    reason: str


@dataclass(frozen=True)
class IdentityState:
    identities: dict[str, Identity]
    codes: tuple[CodeInterval, ...]
    presence: tuple[Presence, ...]
    aliases: tuple[Alias, ...]
    next_id: int
    last_cycle: str | None

    @classmethod
    def empty(cls) -> IdentityState:
        return cls({}, (), (), (), 1, None)


@dataclass
class _Entity:
    """One airport in the current cycle: a NASR record, an OurAirports record,
    or both when they describe the same US field."""

    nasr: Observation | None
    ourairports: Observation | None

    @property
    def primary(self) -> Observation:
        return self.nasr or self.ourairports  # type: ignore[return-value]

    @property
    def sort_key(self) -> tuple:
        if self.nasr is not None:
            return (0, self.nasr.nasr_site_no or "", self.nasr.nasr_site_type or "")
        oa_id = self.ourairports.ourairports_id or ""  # type: ignore[union-attr]
        return (1, oa_id.isdigit(), int(oa_id) if oa_id.isdigit() else 0, oa_id)

    def codes(self) -> list[tuple[str, str, str]]:
        """(scheme, code, source). Inside US jurisdiction NASR is authoritative
        for FAA and ICAO; OurAirports contributes only the IATA code it adds."""
        found: dict[tuple[str, str], str] = {}
        if self.nasr is not None:
            for scheme, code in self.nasr.codes:
                found[(scheme, code.upper())] = "nasr"
            if self.ourairports is not None:
                for scheme, code in self.ourairports.codes:
                    if scheme == "iata":
                        found.setdefault((scheme, code.upper()), "ourairports")
        else:
            for scheme, code in self.ourairports.codes:  # type: ignore[union-attr]
                found[(scheme, code.upper())] = "ourairports"
        return sorted((s, c, src) for (s, c), src in found.items())


def _can_pair(row: Observation, candidate: _Entity) -> bool:
    """Country gate and distance for attaching an OurAirports row to a NASR
    record. Inside US jurisdiction any NASR record may be the partner;
    outside it only one NASR lists in the same country (NASR carries some
    Canadian, Bahamian, Micronesian... fields)."""
    country = row.iso_country or ""
    nasr_country = candidate.nasr.iso_country or ""  # type: ignore[union-attr]
    same_country = country in NASR_JURISDICTION or (
        country != ""
        and (
            country == nasr_country
            or country in NASR_LEGACY_COUNTRIES.get(nasr_country, ())
        )
    )
    return (
        same_country
        and candidate.ourairports is None
        and _distance_nm(
            (row.lat, row.lon), (candidate.primary.lat, candidate.primary.lon)
        )
        <= SAME_AIRPORT_NM
    )


def _identity_country(entity: _Entity, previous: Identity | None) -> str | None:
    """ISO 3166-1 country for the identity row. A retired NASR code (AN) is
    never written: it becomes the successor the attached OurAirports row
    states, else the successor an earlier cycle recorded, else NULL. AN has
    three successors, so anything else would be a guess (01-03)."""
    primary = entity.primary
    successors = NASR_LEGACY_COUNTRIES.get(
        (entity.nasr.iso_country or "") if entity.nasr is not None else ""
    )
    if not successors:
        return primary.iso_country
    if entity.ourairports is not None and entity.ourairports.iso_country in successors:
        return entity.ourairports.iso_country
    if previous is not None and previous.iso_country in successors:
        return previous.iso_country
    return None


def _group(
    observations: list[Observation],
    sticky: dict[str, tuple[str, str]] | None = None,
) -> list[_Entity]:
    """Pair OurAirports rows with the NASR record of the same field.

    ``sticky`` maps an OurAirports id to the NASR site key it was paired with
    before. That pairing holds while the two sources disagree on codes (NASR
    renamed PBI -> DJT a cycle before OurAirports did), as long as the row
    shares no code with any NASR record and still passes the gate.
    """
    nasr = sorted(
        (o for o in observations if o.source == "nasr"),
        key=lambda o: (o.nasr_site_no or "", o.nasr_site_type or ""),
    )
    ourairports = sorted(
        (o for o in observations if o.source == "ourairports"),
        key=lambda o: _Entity(None, o).sort_key,
    )
    entities = [_Entity(o, None) for o in nasr]
    by_code: dict[str, list[_Entity]] = defaultdict(list)
    by_site: dict[tuple[str, str], _Entity] = {}
    for entity in entities:
        for _, code in entity.nasr.codes:  # type: ignore[union-attr]
            by_code[code.upper()].append(entity)
        by_site[(entity.nasr.nasr_site_no or "", entity.nasr.nasr_site_type or "")] = (  # type: ignore[union-attr]
            entity
        )

    for row in ourairports:
        partner = None
        shares = [c for _, code in row.codes for c in by_code.get(code.upper(), [])]
        for candidate in shares:
            if _can_pair(row, candidate):
                partner = candidate
                break
        if partner is None and not shares and sticky:
            site = sticky.get(row.ourairports_id or "")
            candidate = by_site.get(site) if site else None
            if candidate is not None and _can_pair(row, candidate):
                partner = candidate
        if partner is not None:
            partner.ourairports = row
        else:
            entities.append(_Entity(None, row))
    return sorted(entities, key=lambda e: e.sort_key)


def _latest_codes(codes: tuple[CodeInterval, ...], scheme: str) -> dict[str, str]:
    """airport_id -> its most recent code in ``scheme``."""
    latest: dict[str, CodeInterval] = {}
    for interval in codes:
        if interval.scheme != scheme:
            continue
        held = latest.get(interval.airport_id)
        if held is None or interval.effective_date >= held.effective_date:
            latest[interval.airport_id] = interval
    return {airport: interval.code for airport, interval in latest.items()}


def apply_cycle(
    state: IdentityState, effective_date: str, observations: list[Observation]
) -> IdentityState:
    if state.last_cycle is not None and effective_date <= state.last_cycle:
        raise ValueError(
            f"cycle {effective_date} does not follow {state.last_cycle}; "
            "the identity chain only moves forward"
        )

    aliased = {a.alias_id for a in state.aliases}
    live = {k: v for k, v in state.identities.items() if k not in aliased}

    by_site_key: dict[tuple[str, str], str] = {}
    by_site_no: dict[str, list[str]] = defaultdict(list)
    by_oa: dict[str, str] = {}
    for airport_id, identity in sorted(live.items()):
        if identity.nasr_site_no:
            by_site_key[(identity.nasr_site_no, identity.nasr_site_type or "")] = (
                airport_id
            )
            by_site_no[identity.nasr_site_no].append(airport_id)
        if identity.ourairports_id:
            by_oa[identity.ourairports_id] = airport_id
    by_faa: dict[str, list[str]] = defaultdict(list)
    for airport_id, code in sorted(_latest_codes(state.codes, "faa").items()):
        if airport_id in live:
            by_faa[code].append(airport_id)

    claimed: set[str] = set()
    next_id = state.next_id
    identities = dict(state.identities)
    aliases = list(state.aliases)
    matched: dict[str, _Entity] = {}

    def free(airport_id: str | None) -> str | None:
        return airport_id if airport_id and airport_id not in claimed else None

    sticky = {
        identity.ourairports_id: (identity.nasr_site_no, identity.nasr_site_type or "")
        for _, identity in sorted(live.items())
        if identity.ourairports_id and identity.nasr_site_no
    }
    for entity in _group(observations, sticky):
        candidates: list[tuple[str, str]] = []
        if entity.nasr is not None:
            row = entity.nasr
            site_key = (row.nasr_site_no or "", row.nasr_site_type or "")
            site_hit = free(by_site_key.get(site_key))
            if site_hit:
                candidates.append((site_hit, "nasr_site"))
            else:
                same_number = [
                    i for i in by_site_no.get(row.nasr_site_no or "", []) if free(i)
                ]
                if len(same_number) == 1:
                    candidates.append((same_number[0], "nasr_site_number"))
                else:
                    faa = next((c.upper() for s, c in row.codes if s == "faa"), None)
                    near = [
                        i
                        for i in by_faa.get(faa or "", [])
                        if free(i)
                        and _distance_nm(
                            (row.lat, row.lon), (live[i].lat, live[i].lon)
                        )
                        <= SITE_CORRECTION_NM
                    ]
                    if len(near) == 1:
                        candidates.append((near[0], "faa_lid_within_1nm"))
        if entity.ourairports is not None:
            oa_hit = free(by_oa.get(entity.ourairports.ourairports_id or ""))
            if oa_hit and oa_hit not in {c for c, _ in candidates}:
                candidates.append((oa_hit, "ourairports_id"))

        if candidates:
            candidates.sort()
            survivor, basis = candidates[0]
            for merged, _ in candidates[1:]:
                aliases = [
                    Alias(a.alias_id, survivor, a.effective_date, a.reason)
                    if a.airport_id == merged
                    else a
                    for a in aliases
                ]
                aliases.append(Alias(merged, survivor, effective_date, "converged"))
                claimed.add(merged)
        else:
            survivor, basis = format_id(next_id), "minted"
            next_id += 1
        claimed.add(survivor)
        matched[survivor] = entity

        primary = entity.primary
        previous = identities.get(survivor)
        identities[survivor] = Identity(
            airport_id=survivor,
            nasr_site_no=entity.nasr.nasr_site_no if entity.nasr else (
                previous.nasr_site_no if previous else None),
            nasr_site_type=entity.nasr.nasr_site_type if entity.nasr else (
                previous.nasr_site_type if previous else None),
            ourairports_id=entity.ourairports.ourairports_id if entity.ourairports
            else (previous.ourairports_id if previous else None),
            name=primary.name,
            lat=primary.lat,
            lon=primary.lon,
            kind=primary.kind,
            source_status=primary.source_status,
            iso_country=_identity_country(entity, previous),
            first_cycle=previous.first_cycle if previous else effective_date,
            last_seen_cycle=effective_date,
            match_basis=basis,
        )

    # Code intervals: closed ones are carried untouched; open ones close when
    # the airport no longer holds the code (or is absent, or was merged away).
    # NASR is authoritative for the FAA and ICAO codes it assigns: a
    # standalone OurAirports row claiming one of them this cycle (2024-04: a
    # row marked "(Duplicate)" and moved to 0,0 still carried ident KCPF)
    # does not get it.
    nasr_assigned = {
        (scheme, code.upper())
        for entity in matched.values()
        if entity.nasr is not None
        for scheme, code in entity.nasr.codes
    }
    wanted = {
        airport: {
            (s, c): src
            for s, c, src in entity.codes()
            if entity.nasr is not None or (s, c) not in nasr_assigned
        }
        for airport, entity in matched.items()
    }
    codes: list[CodeInterval] = []
    open_now: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for interval in state.codes:
        if interval.valid_to is None:
            if (interval.scheme, interval.code) in wanted.get(interval.airport_id, {}):
                open_now[interval.airport_id].add((interval.scheme, interval.code))
                codes.append(interval)
                continue
            interval = CodeInterval(
                interval.airport_id, interval.scheme, interval.code,
                interval.effective_date, effective_date, interval.source,
            )
        codes.append(interval)
    for airport, held in wanted.items():
        for (scheme, code), source in held.items():
            if (scheme, code) not in open_now[airport]:
                codes.append(
                    CodeInterval(airport, scheme, code, effective_date, None, source)
                )

    presence: list[Presence] = []
    present: set[str] = set()
    for interval in state.presence:
        if interval.valid_to is None:
            if interval.airport_id in matched:
                present.add(interval.airport_id)
            else:
                interval = Presence(
                    interval.airport_id, interval.effective_date, effective_date
                )
        presence.append(interval)
    for airport in matched:
        if airport not in present:
            presence.append(Presence(airport, effective_date, None))

    return IdentityState(
        identities=dict(sorted(identities.items())),
        codes=tuple(sorted(codes)),
        presence=tuple(sorted(presence)),
        aliases=tuple(sorted(aliases)),
        next_id=next_id,
        last_cycle=effective_date,
    )


def lookup(state: IdentityState, scheme: str, code: str, date: str) -> list[str]:
    """Airport ids that held ``code`` under ``scheme`` on ``date`` (ISO).

    More than one id can come back: IATA codes collide worldwide, and a caller
    disambiguates by position. An id may be an alias source; resolve it
    through ``aliases`` (always one hop).
    """
    scheme, code = scheme.lower(), code.upper()
    return sorted(
        {
            interval.airport_id
            for interval in state.codes
            if interval.scheme == scheme
            and interval.code == code
            and interval.effective_date <= date
            and (interval.valid_to is None or date < interval.valid_to)
        }
    )


# --- Observations from the raw source rows ---------------------------------

NASR_STATUS = {
    "O": "operational",
    "CI": "closed_indefinitely",
    "CP": "closed_permanently",
}


def nasr_observations(rows: list[dict[str, str]]) -> list[Observation]:
    """Every APT_BASE row with coordinates, closed ones included: a closure is
    something the source says, and history should record it."""
    observations = []
    for row in rows:
        coords = _parse_coordinates(row.get("LAT_DECIMAL"), row.get("LONG_DECIMAL"))
        if coords is None:
            continue
        status_code = (row.get("ARPT_STATUS") or "").strip().upper()
        if status_code not in NASR_STATUS:
            # Never guess a status; a new FAA code needs a decision.
            raise ValueError(f"unknown NASR ARPT_STATUS {status_code!r}")
        _, site_no, site_type = nasr_source_key(row)
        faa = (row.get("ARPT_ID") or "").strip().upper()
        icao = (row.get("ICAO_ID") or "").strip().upper()
        codes = ([("faa", faa)] if FAA_LID_RE.match(faa) else []) + (
            [("icao", icao)] if ICAO_RE.match(icao) else []
        )
        observations.append(
            Observation(
                source="nasr",
                nasr_site_no=site_no,
                nasr_site_type=site_type,
                ourairports_id=None,
                codes=tuple(codes),
                lat=coords[0],
                lon=coords[1],
                name=(row.get("ARPT_NAME") or "").strip() or None,
                kind=NASR_SITE_TYPES.get(site_type, ("unknown", 6))[0],
                source_status=NASR_STATUS[status_code],
                iso_country=(row.get("COUNTRY_CODE") or "").strip().upper() or None,
            )
        )
    return observations


def ourairports_observations(rows: list[dict[str, str]]) -> list[Observation]:
    """The same OurAirports rows the airports layer uses (an IATA code, or a
    large/medium airport), with the same ICAO derivation, except that an ICAO
    code taken from the ident gives way to a row that states that code in
    icao_code. (2026-07-08: the old Zhaotong field, ident ZPZT, no icao_code;
    the new one, icao_code ZPZT.)"""
    explicit = {
        (row.get("icao_code") or "").strip().upper() for row in rows
    } - {""}
    observations = []
    for row in rows:
        airport_type = (row.get("type") or "").strip()
        iata = (row.get("iata_code") or "").strip().upper()
        has_iata = bool(IATA_RE.match(iata))
        if not has_iata and airport_type not in {"large_airport", "medium_airport"}:
            continue
        coords = _parse_coordinates(row.get("latitude_deg"), row.get("longitude_deg"))
        if coords is None:
            continue
        ident = (row.get("ident") or "").strip().upper()
        stated = (row.get("icao_code") or "").strip().upper()
        if ICAO_RE.match(stated):
            icao = stated
        elif ICAO_RE.match(ident) and ident not in explicit:
            icao = ident
        else:
            icao = None
        codes = ([("iata", iata)] if has_iata else []) + (
            [("icao", icao)] if icao else []
        )
        observations.append(
            Observation(
                source="ourairports",
                nasr_site_no=None,
                nasr_site_type=None,
                ourairports_id=ourairports_source_key(row)[1],
                codes=tuple(codes),
                lat=coords[0],
                lon=coords[1],
                name=(row.get("name") or "").strip() or None,
                kind=airport_type or None,
                source_status="closed" if airport_type == "closed" else "operational",
                iso_country=(row.get("iso_country") or "").strip().upper() or None,
            )
        )
    return observations


def current_key_index(state: IdentityState) -> dict[tuple, str]:
    """Source key -> airport id, over identities seen in the latest cycle.

    A key claimed by two current identities is ambiguous and raises: an
    airports row must map to exactly one id, never to a guess.
    """
    aliased = {a.alias_id for a in state.aliases}
    index: dict[tuple, str] = {}
    ambiguous: set[tuple] = set()
    for airport_id, identity in state.identities.items():
        if identity.last_seen_cycle != state.last_cycle or airport_id in aliased:
            continue
        keys = []
        if identity.nasr_site_no is not None:
            keys.append(("nasr", identity.nasr_site_no, identity.nasr_site_type or ""))
        if identity.ourairports_id is not None:
            keys.append(("ourairports", identity.ourairports_id))
        for key in keys:
            if key in index and index[key] != airport_id:
                ambiguous.add(key)
            index[key] = airport_id
    for key in ambiguous:
        index.pop(key)
    return index


# --- Persistence -------------------------------------------------------------

_IDENTITY_COLUMNS = (
    "airport_id, nasr_site_no, nasr_site_type, ourairports_id, name, lat, lon, "
    "kind, source_status, iso_country, first_cycle, last_seen_cycle, match_basis"
)


def load_state(connection: sqlite3.Connection) -> IdentityState:
    """Read a schema-3 file's identity tables back into an IdentityState."""
    metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    identities = {
        row[0]: Identity(*row)
        for row in connection.execute(
            f"SELECT {_IDENTITY_COLUMNS} FROM airport_identity ORDER BY airport_id"  # noqa: S608
        )
    }
    codes = tuple(
        sorted(
            CodeInterval(*row)
            for row in connection.execute(
                "SELECT airport_id, scheme, code, effective_date, valid_to, source "
                "FROM airport_codes"
            )
        )
    )
    presence = tuple(
        sorted(
            Presence(*row)
            for row in connection.execute(
                "SELECT airport_id, effective_date, valid_to FROM airport_presence"
            )
        )
    )
    aliases = tuple(
        sorted(
            Alias(*row)
            for row in connection.execute(
                "SELECT alias_id, airport_id, effective_date, reason "
                "FROM airport_aliases"
            )
        )
    )
    return IdentityState(
        identities=identities,
        codes=codes,
        presence=presence,
        aliases=aliases,
        next_id=int(metadata["airport_id_next"]),
        last_cycle=metadata["airac_cycle"],
    )


def dump_state(connection: sqlite3.Connection, state: IdentityState) -> None:
    """Write the identity tables. ``in_current_cycle`` is derived: last seen
    in this state's cycle."""
    connection.executemany(
        f"INSERT INTO airport_identity ({_IDENTITY_COLUMNS}, in_current_cycle) "  # noqa: S608
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                i.airport_id, i.nasr_site_no, i.nasr_site_type, i.ourairports_id,
                i.name, i.lat, i.lon, i.kind, i.source_status, i.iso_country,
                i.first_cycle, i.last_seen_cycle, i.match_basis,
                int(i.last_seen_cycle == state.last_cycle),
            )
            for i in sorted(state.identities.values(), key=lambda i: i.airport_id)
        ],
    )
    connection.executemany(
        "INSERT INTO airport_codes "
        "(airport_id, scheme, code, effective_date, valid_to, source) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (c.airport_id, c.scheme, c.code, c.effective_date, c.valid_to, c.source)
            for c in state.codes
        ],
    )
    connection.executemany(
        "INSERT INTO airport_presence (airport_id, effective_date, valid_to) "
        "VALUES (?, ?, ?)",
        [(p.airport_id, p.effective_date, p.valid_to) for p in state.presence],
    )
    connection.executemany(
        "INSERT INTO airport_aliases (alias_id, airport_id, effective_date, reason) "
        "VALUES (?, ?, ?, ?)",
        [(a.alias_id, a.airport_id, a.effective_date, a.reason) for a in state.aliases],
    )

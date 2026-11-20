"""Read airport records out of any archived NASR 28-day subscription.

The FAA archive goes back to 2020-03-26 (earlier cycles return 404; backfill
falls back to the Internet Archive's copies of the same files) and has
changed shape twice:

* format a: fixed-width text only (``APT.txt``), no ``CSV_Data/``;
* format b: one CSV zip per subject (``CSV_Data/DD_Mon_YYYY_APT_CSV.zip``);
* format c: one CSV zip (``CSV_Data/DD_Mon_YYYY_CSV.zip``), what build.py reads.

Every format is reduced to the APT_BASE columns the identity engine reads.
A subscription zip is 140-260 MB but the airport member is a few MB, so the
reader fetches only the bytes it needs with HTTP range requests.
"""

from __future__ import annotations

import csv
import io
import re
import time
import urllib.error
import urllib.request
import zipfile
from decimal import Decimal
from pathlib import Path

from aeronav_db.cycle import BROWSER_USER_AGENT, NASR_URL_TEMPLATE

APT_COLUMNS = (
    "SITE_NO", "SITE_TYPE_CODE", "ARPT_ID", "ICAO_ID", "ARPT_NAME", "ARPT_STATUS",
    "LAT_DECIMAL", "LONG_DECIMAL", "COUNTRY_CODE",
)
RETRIES = 5


def _fetch(url: str, start: int, end: int) -> bytes:
    """Bytes start..end inclusive. Retries 5xx and timeouts; never returns a
    short read."""
    want = end - start + 1
    for attempt in range(RETRIES):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": BROWSER_USER_AGENT, "Range": f"bytes={start}-{end}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                data = response.read()
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == RETRIES - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == RETRIES - 1:
                raise
        else:
            if len(data) != want:
                raise OSError(f"short read from {url}: {len(data)} of {want} bytes")
            return data
        time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


class HttpRangeFile(io.RawIOBase):
    """A seekable read-only view of a remote file, for zipfile."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.position = 0
        request = urllib.request.Request(
            url, headers={"User-Agent": BROWSER_USER_AGENT, "Range": "bytes=0-0"}
        )
        # The FAA host refuses HEAD (503); a 1-byte range reports the size.
        for attempt in range(RETRIES):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                    self.size = int(response.headers["Content-Range"].split("/")[1])
                    break
            except urllib.error.HTTPError as error:
                if error.code < 500 or attempt == RETRIES - 1:
                    raise
                time.sleep(2 ** attempt)

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = 0) -> int:
        self.position = {0: offset, 1: self.position + offset, 2: self.size + offset}[
            whence
        ]
        return self.position

    def readinto(self, buffer) -> int:
        if self.position >= self.size:
            return 0
        end = min(self.size, self.position + len(buffer)) - 1
        data = _fetch(self.url, self.position, end)
        buffer[: len(data)] = data
        self.position += len(data)
        return len(data)


def open_subscription(source: str | Path) -> zipfile.ZipFile:
    """A cycle date (YYYY-MM-DD), a URL, or a local zip path."""
    text = str(source)
    if len(text) == 10 and text[4] == "-":
        text = NASR_URL_TEMPLATE.format(cycle=text)
    if text.startswith("https://"):
        return zipfile.ZipFile(io.BufferedReader(HttpRangeFile(text), 1 << 20))
    return zipfile.ZipFile(text)


def archive_format(archive: zipfile.ZipFile) -> str:
    names = archive.namelist()
    csv_zips = [n for n in names if n.startswith("CSV_Data/") and n.endswith(".zip")]
    if not csv_zips:
        return "a"
    if any(n.endswith("_APT_CSV.zip") for n in csv_zips):
        return "b"
    return "c"


def _member(archive: zipfile.ZipFile, basename: str) -> bytes:
    match = [n for n in archive.namelist() if n.rsplit("/", 1)[-1] == basename]
    if len(match) != 1:
        raise ValueError(f"expected one {basename} in the archive, found {match}")
    return archive.read(match[0])


def _csv_apt_rows(
    archive: zipfile.ZipFile, fmt: str
) -> tuple[list[dict[str, str]], bytes]:
    suffix = "_APT_CSV.zip" if fmt == "b" else "_CSV.zip"
    inner_name = [
        n for n in archive.namelist()
        if n.startswith("CSV_Data/") and n.endswith(suffix)
    ]
    if len(inner_name) != 1:
        raise ValueError(f"expected one CSV_Data/*{suffix}, found {inner_name}")
    inner = zipfile.ZipFile(io.BytesIO(archive.read(inner_name[0])))
    raw = _member(inner, "APT_BASE.csv")
    rows = [
        {column: (row.get(column) or "").strip() for column in APT_COLUMNS}
        for row in csv.DictReader(io.StringIO(raw.decode("latin-1")))
    ]
    return rows, raw


def apt_rows(source: str | Path) -> tuple[str, list[dict[str, str]], bytes]:
    """(format, rows, raw member bytes). The raw bytes are what lineage
    hashes: the exact input the rows came from."""
    archive = open_subscription(source)
    fmt = archive_format(archive)
    if fmt == "a":
        raw = _member(archive, "APT.txt")
        return fmt, legacy_apt_rows(raw, legacy_record_length(archive)), raw
    rows, raw = _csv_apt_rows(archive, fmt)
    return fmt, rows, raw


# Format a, record type APT. (start, length), 1-based, from the apt_rf.txt
# layout shipped inside every format-a archive.
LEGACY_FIELDS = {
    "record": (1, 3),
    "site": (4, 11),           # e.g. '50009.*A'; the '*A' repeats the type
    "type": (15, 13),
    "lid": (28, 4),
    "state": (49, 2),          # associated state post office code
    "county_state": (92, 2),   # for non-US fields an internal FAA code
    "name": (134, 50),
    "lat_seconds": (539, 12),  # SSSSSS.SSSSH
    "lon_seconds": (566, 12),
    "status": (841, 2),
    "icao": (1211, 7),
}
LEGACY_TYPES = {
    "AIRPORT": "A", "BALLOONPORT": "B", "SEAPLANE BASE": "C",
    "GLIDERPORT": "G", "HELIPORT": "H", "ULTRALIGHT": "U",
}
# Format a has no country column. A US row carries a state post office code;
# a non-US row has none, and its county_state is the ISO country code, except
# 'CN' for Canada. Derived from, and validated 100% against, the 2022-12-29
# cycle, which ships both APT.txt and CSV (02-01-SUMMARY).
LEGACY_COUNTRY_RENAMES = {"CN": "CA"}


def _seconds_to_decimal(text: str) -> str:
    """Exact decimal division, so rounding matches the CSV's decimal values."""
    text = text.strip()
    if not text:
        return ""
    value = Decimal(text[:-1]) / 3600
    return str(-value if text[-1] in "SW" else value)


def _field(line: str, name: str) -> str:
    start, length = LEGACY_FIELDS[name]
    return line[start - 1 : start - 1 + length].strip()


# The name apt_rf.txt gives each LEGACY_FIELDS entry. Every format-a archive
# carries its own layout in Layout_Data/apt_rf.txt; the records are checked
# against it, never against a hard-coded length (02-04: 2017-10-12 to
# 2021-04-22 state 1529, 2021-05-20 to 2022-10-06 state 1531, with these
# fields unmoved). Additional_Data/ may hold the NEXT cycle's layout and is
# never read.
LEGACY_FIELD_NAMES = {
    "record": "RECORD TYPE INDICATOR.",
    "site": "LANDING FACILITY SITE NUMBER",
    "type": "LANDING FACILITY TYPE",
    "lid": "LOCATION IDENTIFIER",
    "state": "ASSOCIATED STATE POST OFFICE CODE",
    "county_state": "ASSOCIATED COUNTY'S STATE (POST OFFICE CODE)",
    "name": "OFFICIAL FACILITY NAME",
    "lat_seconds": "AIRPORT REFERENCE POINT LATITUDE (SECONDS)",
    "lon_seconds": "AIRPORT REFERENCE POINT LONGITUDE (SECONDS)",
    "status": "AIRPORT STATUS CODE",
    "icao": "ICAO IDENTIFIER",
}
LEGACY_LAYOUT_MEMBER = "layout_data/apt_rf.txt"
_LAYOUT_LINE = re.compile(r"^\s*L\s+AN\s+(\d{4})\s+(\d{5})\s+\S+\s+(.*?)\s*$")


def legacy_record_length(archive: zipfile.ZipFile) -> int:
    """The APT record length this archive's own Layout_Data/apt_rf.txt
    states, after checking that every field we read sits where it says.
    Anything else is refused: a layout we have not verified is not parsed."""
    members = [n for n in archive.namelist() if n.lower() == LEGACY_LAYOUT_MEMBER]
    if len(members) != 1:
        raise ValueError(
            f"format a without exactly one Layout_Data/apt_rf.txt: {members}; "
            "the layout cannot be checked"
        )
    text = archive.read(members[0]).decode("latin-1")
    stated = re.search(r"RECORD LENGTH:\s*(\d+)", text)
    if stated is None:
        raise ValueError("apt_rf.txt states no RECORD LENGTH; the layout differs")
    positions: dict[tuple[int, int], str] = {}
    for line in text.splitlines():
        match = _LAYOUT_LINE.match(line)
        if match:
            positions.setdefault(
                (int(match.group(2)), int(match.group(1))), match.group(3))
    for field, (start, length) in LEGACY_FIELDS.items():
        found = positions.get((start, length))
        if found != LEGACY_FIELD_NAMES[field]:
            raise ValueError(
                f"apt_rf.txt has {found!r} at {start}/{length}, expected "
                f"{LEGACY_FIELD_NAMES[field]!r}; the layout differs"
            )
    return int(stated.group(1))


def legacy_apt_rows(raw: bytes, record_length: int) -> list[dict[str, str]]:
    """APT records as APT_BASE-shaped rows. A record with a blank status is
    left out, as the FAA's own CSV extract leaves it out (2022-12-29: CZBB,
    the only one); ``legacy_blank_status`` counts them for the report."""
    rows = []
    for number, line in enumerate(raw.decode("latin-1").splitlines(), 1):
        if not line.startswith("APT"):
            continue
        if len(line) != record_length:
            raise ValueError(
                f"APT.txt line {number}: record length {len(line)}, expected "
                f"{record_length} (apt_rf.txt); the layout differs"
            )
        if not _field(line, "status"):
            continue
        state, county_state = _field(line, "state"), _field(line, "county_state")
        if state:
            country = "US"
        else:
            country = LEGACY_COUNTRY_RENAMES.get(county_state, county_state)
        rows.append(
            {
                "SITE_NO": _field(line, "site").split("*")[0],
                "SITE_TYPE_CODE": LEGACY_TYPES.get(_field(line, "type"), ""),
                "ARPT_ID": _field(line, "lid"),
                "ICAO_ID": _field(line, "icao"),
                "ARPT_NAME": _field(line, "name"),
                "ARPT_STATUS": _field(line, "status"),
                "LAT_DECIMAL": _seconds_to_decimal(_field(line, "lat_seconds")),
                "LONG_DECIMAL": _seconds_to_decimal(_field(line, "lon_seconds")),
                "COUNTRY_CODE": country,
                "_LEGACY_STATE": state,
                "_LEGACY_COUNTY_STATE": county_state,
            }
        )
    return rows


def legacy_blank_status(raw: bytes) -> list[str]:
    """Site numbers of APT records left out for a blank status."""
    return [
        _field(line, "site")
        for line in raw.decode("latin-1").splitlines()
        if line.startswith("APT") and not _field(line, "status")
    ]

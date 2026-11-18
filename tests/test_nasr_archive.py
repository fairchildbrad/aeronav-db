"""Archive reader: the three NASR subscription formats reduce to the same rows."""

from __future__ import annotations

import io
import zipfile

import pytest

from aeronav_db import nasr_archive as na
from aeronav_db.identity import nasr_observations

CSV_HEADER = ",".join(na.APT_COLUMNS)


def legacy_line(site="19562.*A", ftype="AIRPORT", lid="PDT", state="OR",
                county_state="OR", name="EASTERN OREGON RGNL", lat="164501.4440N",
                lon="427836.1270W", status="O", icao="KPDT") -> str:
    line = [" "] * 1300
    def put(field, value):
        start, length = na.LEGACY_FIELDS[field]
        line[start - 1 : start - 1 + length] = value.ljust(length)[:length]
    put("record", "APT")
    for field, value in (("site", site), ("type", ftype), ("lid", lid),
                         ("state", state), ("county_state", county_state),
                         ("name", name), ("lat_seconds", lat), ("lon_seconds", lon),
                         ("status", status), ("icao", icao)):
        put(field, value)
    return "".join(line).rstrip()


def subscription(tmp_path, fmt, apt_text):
    path = tmp_path / f"{fmt}.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Layout_Data/apt_rf.txt", "layout")
        if fmt == "a":
            archive.writestr("APT.txt", apt_text)
            return path
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as csvs:
            csvs.writestr("APT_BASE.csv", apt_text)
        name = "29_Dec_2022_APT_CSV.zip" if fmt == "b" else "25_Jan_2024_CSV.zip"
        archive.writestr("CSV_Data/", "")
        archive.writestr(f"CSV_Data/{name}", inner.getvalue())
    return path


CSV_ROW = (
    "19562.,A,PDT,KPDT,EASTERN OREGON RGNL,O,45.6948455555556,-118.843369722222,US"
)
CSV_TEXT = f"{CSV_HEADER}\n{CSV_ROW}\n"


@pytest.mark.parametrize("fmt", ["b", "c"])
def test_csv_formats(tmp_path, fmt):
    found, rows, _ = na.apt_rows(subscription(tmp_path, fmt, CSV_TEXT))
    assert found == fmt
    assert rows[0]["ARPT_ID"] == "PDT" and rows[0]["COUNTRY_CODE"] == "US"


def test_legacy_format_matches_the_csv_row(tmp_path):
    found, rows, raw = na.apt_rows(subscription(tmp_path, "a", legacy_line() + "\n"))
    assert found == "a" and raw
    _, csv_rows, _ = na.apt_rows(subscription(tmp_path, "c", CSV_TEXT))
    legacy, current = nasr_observations(rows)[0], nasr_observations(csv_rows)[0]
    assert legacy.codes == current.codes == (("faa", "PDT"), ("icao", "KPDT"))
    assert (legacy.nasr_site_no, legacy.nasr_site_type) == ("19562.", "A")
    assert abs(legacy.lat - 45.694846) < 1e-5 and abs(legacy.lon + 118.843369) < 1e-5


def test_legacy_country_comes_from_state_or_the_foreign_code(tmp_path):
    text = "\n".join([
        legacy_line(),
        legacy_line(site="90038.5*A", lid="CYDB", state="", county_state="CN",
                    icao="CYDB"),
        legacy_line(site="90870.*A", lid="TNCE", state="", county_state="AN",
                    icao="TNCE"),
    ])
    _, rows, _ = na.apt_rows(subscription(tmp_path, "a", text))
    assert [r["COUNTRY_CODE"] for r in rows] == ["US", "CA", "AN"]


def test_a_blank_legacy_status_is_left_out_and_counted(tmp_path):
    text = legacy_line() + "\n" + legacy_line(site="90038.*A", lid="CZBB", status="")
    _, rows, raw = na.apt_rows(subscription(tmp_path, "a", text))
    assert [r["ARPT_ID"] for r in rows] == ["PDT"]
    assert na.legacy_blank_status(raw) == ["90038.*A"]


def test_an_archive_without_airport_data_is_an_error(tmp_path):
    path = tmp_path / "empty.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("README.txt", "x")
    with pytest.raises(ValueError, match="APT.txt"):
        na.apt_rows(path)

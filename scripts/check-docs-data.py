#!/usr/bin/env python3

from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "doc"
MEMORY_STATUS_VALUES = {
    "NA",
    "NT",
    "OK",
    "OK (JTAG)",
    "RBF",
    "SVF",
    "TBD",
}
FLASH_STATUS_VALUES = {
    "AS",
    "EF",
    "IF",
    "IF/EF",
    "NA",
    "NT",
    "OK",
    "OK (DFU)",
    "OK (primary)",
    "OK (primary and secondary)",
    "OK. BPI parallel NOR flash (MT28GU512AAA1EGC)",
    "POF",
    "SVF",
    "TBD",
}
ALLOWED_DUPLICATE_BOARD_IDS = {
    "arty": "legacy board alias used by multiple Digilent instruments",
    "ice40_generic": "generic FTDI SPI wiring shared by multiple iCE40 boards",
    "runber": "shared FT232 profile used by Runber and MiniSpartan6+ entries",
}


class Reporter:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, location: str, message: str) -> None:
        self.errors.append(f"{location}: error: {message}")

    def warning(self, location: str, message: str) -> None:
        self.warnings.append(f"{location}: warning: {message}")

    def report(self) -> int:
        for message in self.warnings:
            print(message, file=sys.stderr)
        for message in self.errors:
            print(message, file=sys.stderr)
        if self.errors:
            print(f"{len(self.errors)} data validation error(s)", file=sys.stderr)
            return 1
        if self.warnings:
            print(f"{len(self.warnings)} data validation warning(s)", file=sys.stderr)
        else:
            print("Documentation data checks passed.")
        return 0


def load_yaml(path: Path, reporter: Reporter) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fptr:
            return yaml.safe_load(fptr)
    except yaml.YAMLError as err:
        reporter.error(str(path.relative_to(ROOT)), f"invalid YAML: {err}")
    return None


def check_no_trailing_whitespace(path: Path, reporter: Reporter) -> None:
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.rstrip(" \t") != line:
            reporter.error(f"{path.relative_to(ROOT)}:{line_no}", "trailing whitespace")


def describe_value(value: Any) -> str:
    return repr(value) if isinstance(value, str) else type(value).__name__


def require_text(entry: dict[str, Any], key: str, location: str, reporter: Reporter) -> None:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        reporter.error(location, f"missing non-empty {key}")
        return
    if value.strip() != value:
        reporter.error(location, f"{key} has leading or trailing whitespace")


def check_status(
    entry: dict[str, Any],
    key: str,
    allowed_values: set[str],
    location: str,
    reporter: Reporter,
    required: bool = True,
) -> None:
    value = entry.get(key)
    if value is None and not required:
        return
    require_text(entry, key, location, reporter)
    if not isinstance(value, str) or not value.strip():
        return
    if value not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        reporter.error(location, f"unknown {key} status {value!r}; expected one of: {allowed}")


def check_url(url: Any, location: str, reporter: Reporter, required: bool = True) -> None:
    if url is None:
        if required:
            reporter.error(location, "missing URL")
        return
    if not isinstance(url, str) or not url.strip():
        reporter.error(location, f"invalid URL value {describe_value(url)}")
        return
    if url.strip() != url:
        reporter.error(location, "URL has leading or trailing whitespace")
        return
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        reporter.error(location, f"URL is not absolute HTTP(S): {url}")
        return
    if parsed.netloc in {"http:", "https:"} or "://" in parsed.netloc:
        reporter.error(location, f"URL has malformed host: {url}")


def check_model(value: Any, location: str, reporter: Reporter) -> None:
    if isinstance(value, str):
        if not value.strip():
            reporter.error(location, "Model is empty")
        elif value.strip() != value:
            reporter.error(location, "Model has leading or trailing whitespace")
        return
    if isinstance(value, list) and value:
        for idx, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                reporter.error(f"{location}.Model[{idx}]", "missing non-empty model")
            elif item.strip() != item:
                reporter.error(f"{location}.Model[{idx}]", "model has leading or trailing whitespace")
        return
    reporter.error(location, "Model must be a string or a non-empty list of strings")


def check_mapping_lists(
    data: Any,
    path: Path,
    reporter: Reporter,
    entry_checker: Any,
) -> None:
    rel_path = str(path.relative_to(ROOT))
    if not isinstance(data, dict):
        reporter.error(rel_path, "expected a YAML mapping")
        return
    for section, entries in data.items():
        section_location = f"{rel_path}:{section}"
        if not isinstance(section, str) or not section.strip():
            reporter.error(rel_path, f"invalid section name {describe_value(section)}")
            continue
        if not isinstance(entries, list):
            reporter.error(section_location, "expected a list of entries")
            continue
        for idx, entry in enumerate(entries):
            location = f"{section_location}[{idx}]"
            if not isinstance(entry, dict):
                reporter.error(location, "expected an entry mapping")
                continue
            entry_checker(entry, location, reporter)


def check_boards(data: Any, reporter: Reporter) -> None:
    path = DOC / "boards.yml"
    rel_path = str(path.relative_to(ROOT))
    if not isinstance(data, list):
        reporter.error(rel_path, "expected a YAML list")
        return

    ids: list[str] = []
    for idx, entry in enumerate(data):
        location = f"{rel_path}[{idx}]"
        if not isinstance(entry, dict):
            reporter.error(location, "expected an entry mapping")
            continue
        require_text(entry, "ID", location, reporter)
        require_text(entry, "Description", location, reporter)
        require_text(entry, "FPGA", location, reporter)
        check_status(entry, "Memory", MEMORY_STATUS_VALUES, location, reporter)
        check_status(entry, "Flash", FLASH_STATUS_VALUES, location, reporter, required=False)
        check_url(entry.get("URL"), location, reporter)
        board_id = entry.get("ID")
        if isinstance(board_id, str) and board_id.strip():
            ids.append(board_id)

    for board_id, count in sorted(Counter(ids).items()):
        if count > 1:
            reason = ALLOWED_DUPLICATE_BOARD_IDS.get(board_id)
            if reason is None:
                reporter.error(rel_path, f"duplicate board ID {board_id!r} appears {count} times")
            else:
                reporter.warning(rel_path, f"duplicate board ID {board_id!r} appears {count} times ({reason})")


def check_fpga_entry(entry: dict[str, Any], location: str, reporter: Reporter) -> None:
    require_text(entry, "Description", location, reporter)
    check_model(entry.get("Model"), location, reporter)
    check_status(entry, "Memory", MEMORY_STATUS_VALUES, location, reporter)
    check_status(entry, "Flash", FLASH_STATUS_VALUES, location, reporter)
    check_url(entry.get("URL"), location, reporter)


def check_cable_entry(entry: dict[str, Any], location: str, reporter: Reporter) -> None:
    require_text(entry, "Name", location, reporter)
    require_text(entry, "Description", location, reporter)
    check_url(entry.get("URL"), location, reporter, required=False)


def validate_yaml_files(paths: Iterable[Path], reporter: Reporter) -> dict[Path, Any]:
    data: dict[Path, Any] = {}
    for path in paths:
        check_no_trailing_whitespace(path, reporter)
        data[path] = load_yaml(path, reporter)
    return data


def main() -> int:
    reporter = Reporter()
    paths = [DOC / "boards.yml", DOC / "FPGAs.yml", DOC / "cable.yml"]
    data = validate_yaml_files(paths, reporter)

    check_boards(data[DOC / "boards.yml"], reporter)
    check_mapping_lists(data[DOC / "FPGAs.yml"], DOC / "FPGAs.yml", reporter, check_fpga_entry)
    check_mapping_lists(data[DOC / "cable.yml"], DOC / "cable.yml", reporter, check_cable_entry)

    return reporter.report()


if __name__ == "__main__":
    raise SystemExit(main())

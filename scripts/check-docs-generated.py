#!/usr/bin/env python3

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "doc"

sys.path.insert(0, str(DOC))

from data import (  # noqa: E402
    board_data_to_table,
    cable_data_to_table,
    fpga_data_to_table,
    read_board_data_from_yaml,
    read_cable_data_from_yaml,
    read_fpga_data_from_yaml,
)


def main() -> int:
    generated_files = {
        DOC / "compatibility/boards.inc": board_data_to_table(read_board_data_from_yaml()),
        DOC / "compatibility/fpga.inc": fpga_data_to_table(read_fpga_data_from_yaml()),
        DOC / "compatibility/cable.inc": cable_data_to_table(read_cable_data_from_yaml()),
    }

    errors = []
    for path, expected in generated_files.items():
        rel_path = path.relative_to(ROOT)
        if not path.exists():
            errors.append(f"{rel_path}: missing generated file")
            continue
        actual = path.read_text(encoding="utf-8")
        if not actual.strip():
            errors.append(f"{rel_path}: generated file is empty")
        if actual != expected:
            errors.append(f"{rel_path}: generated file is stale")

    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"{len(errors)} generated documentation file error(s)", file=sys.stderr)
        return 1

    print("Generated documentation include files are fresh.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

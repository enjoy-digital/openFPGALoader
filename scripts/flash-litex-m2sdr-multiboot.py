#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

import argparse
import filecmp
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile


DEFAULT_RELEASE_URL = (
    "https://github.com/enjoy-digital/litex_m2sdr/releases/download/"
    "2026_05_15/litex_m2sdr_m2_pcie_x1_2026_05_15.zip"
)
DEFAULT_OPENFPGALOADER = "./build/openFPGALoader"
DEFAULT_BOARD = "litex_m2sdr"
DEFAULT_FREQ = "30e6"
DEFAULT_FALLBACK_OFFSET = "0x800000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fast LiteX M2SDR multiboot flash helper"
    )
    parser.add_argument(
        "release",
        nargs="?",
        default=DEFAULT_RELEASE_URL,
        help="release zip, extracted release directory, or URL "
             f"(default: {DEFAULT_RELEASE_URL})",
    )
    parser.add_argument(
        "--openfpgaloader",
        default=DEFAULT_OPENFPGALOADER,
        help=f"openFPGALoader executable (default: {DEFAULT_OPENFPGALOADER})",
    )
    parser.add_argument(
        "--board",
        default=DEFAULT_BOARD,
        help=f"openFPGALoader board name (default: {DEFAULT_BOARD})",
    )
    parser.add_argument(
        "--freq",
        default=DEFAULT_FREQ,
        help=f"JTAG frequency passed to openFPGALoader (default: {DEFAULT_FREQ})",
    )
    parser.add_argument(
        "--fallback-offset",
        default=DEFAULT_FALLBACK_OFFSET,
        help=f"fallback image flash offset (default: {DEFAULT_FALLBACK_OFFSET})",
    )
    parser.add_argument(
        "--cache-dir",
        default="/tmp/litex_m2sdr_releases",
        help="download cache for URL releases",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="number of boards to flash; prompts between boards when >1",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="flash boards until interrupted; prompts before each board",
    )
    verify_group = parser.add_mutually_exclusive_group()
    verify_group.add_argument(
        "--verify-readback",
        dest="verify_readback",
        action="store_true",
        default=True,
        help="dump both flash slots after writing and compare them to the input files "
             "(default)",
    )
    verify_group.add_argument(
        "--no-verify-readback",
        dest="verify_readback",
        action="store_false",
        help="skip readback verification for maximum throughput",
    )
    parser.add_argument(
        "--no-final-reset",
        action="store_true",
        help="leave the spiOverJtag bridge loaded after the final operation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print commands without running them",
    )
    return parser.parse_args()


def is_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in ("http", "https")


def ensure_release_path(release: str, cache_dir: Path) -> Path:
    if not is_url(release):
        path = Path(release).expanduser()
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    cache_dir.mkdir(parents=True, exist_ok=True)
    name = Path(urllib.parse.urlparse(release).path).name
    if not name:
        raise RuntimeError(f"cannot derive filename from URL: {release}")
    cached = cache_dir / name
    if cached.exists():
        print(f"Using cached release: {cached}", flush=True)
        return cached

    print(f"Downloading {release}", flush=True)
    tmp = cached.with_suffix(cached.suffix + ".tmp")
    urllib.request.urlretrieve(release, tmp)
    tmp.replace(cached)
    print(f"Cached release: {cached}", flush=True)
    return cached


def extract_if_needed(path: Path, work_dir: Path) -> Path:
    if path.is_dir():
        return path
    if path.suffix.lower() != ".zip":
        raise RuntimeError(f"release must be a zip or directory: {path}")

    extract_dir = work_dir / path.stem
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        archive.extractall(extract_dir)
    return extract_dir


def single_match(root: Path, pattern: str) -> Path:
    matches = sorted(root.rglob(pattern))
    if len(matches) != 1:
        paths = "\n".join(str(match) for match in matches)
        raise RuntimeError(
            f"expected one {pattern} in {root}, found {len(matches)}"
            + (f":\n{paths}" if paths else "")
        )
    return matches[0]


def run_command(cmd: list[str], dry_run: bool) -> float:
    print("+ " + " ".join(cmd), flush=True)
    if dry_run:
        return 0.0

    start = time.monotonic()
    subprocess.run(cmd, check=True)
    elapsed = time.monotonic() - start
    print(f"Elapsed: {elapsed:.2f} s", flush=True)
    return elapsed


def require_matching_readback(label: str, expected: Path, readback: Path) -> None:
    if not readback.exists():
        raise RuntimeError(f"{label} readback failed: {readback} was not created")

    expected_size = expected.stat().st_size
    readback_size = readback.stat().st_size
    if readback_size != expected_size:
        raise RuntimeError(
            f"{label} readback failed: expected {expected_size} bytes, "
            f"got {readback_size} bytes"
        )

    if not filecmp.cmp(expected, readback, shallow=False):
        raise RuntimeError(f"{label} readback failed: data differs from input image")


def flash_board(args: argparse.Namespace, operational: Path, fallback: Path) -> None:
    loader = args.openfpgaloader
    common = [loader, "-b", args.board, "--freq", args.freq]

    op_time = run_command(
        common + ["-f", "--skip-reset", str(operational)],
        args.dry_run,
    )

    fallback_cmd = common + [
        "-f",
        "--skip-load-bridge",
        "-o",
        args.fallback_offset,
    ]
    if args.no_final_reset or args.verify_readback:
        fallback_cmd.append("--skip-reset")
    fallback_time = run_command(fallback_cmd + [str(fallback)], args.dry_run)

    print(f"Flash total: {op_time + fallback_time:.2f} s", flush=True)

    if args.verify_readback:
        verify_readback(args, operational, fallback, common)


def verify_readback(
    args: argparse.Namespace,
    operational: Path,
    fallback: Path,
    common: list[str],
) -> None:
    with tempfile.TemporaryDirectory(prefix="litex-m2sdr-readback-") as tmp:
        tmp_dir = Path(tmp)
        op_readback = tmp_dir / "operational.bin"
        fallback_readback = tmp_dir / "fallback.bin"

        run_command(
            common + [
                "--dump-flash",
                "--file-size",
                str(operational.stat().st_size),
                "--skip-load-bridge",
                "--skip-reset",
                "-o",
                "0x0",
                str(op_readback),
            ],
            args.dry_run,
        )
        run_command(
            common + [
                "--dump-flash",
                "--file-size",
                str(fallback.stat().st_size),
                "--skip-load-bridge",
                "--skip-reset",
                "-o",
                args.fallback_offset,
                str(fallback_readback),
            ],
            args.dry_run,
        )

        if not args.dry_run:
            require_matching_readback("operational", operational, op_readback)
            require_matching_readback("fallback", fallback, fallback_readback)
            print("Readback verify: OK", flush=True)

    if not args.no_final_reset:
        run_command(common + ["--reset"], args.dry_run)


def prompt_for_board(index: int) -> None:
    input(f"Connect LiteX M2SDR board #{index}, then press Enter to flash...")


def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise RuntimeError("--count must be >= 1")

    cache_dir = Path(args.cache_dir).expanduser()
    with tempfile.TemporaryDirectory(prefix="litex-m2sdr-release-") as tmp:
        release = ensure_release_path(args.release, cache_dir)
        release_dir = extract_if_needed(release, Path(tmp))
        operational = single_match(release_dir, "*_operational.bin")
        fallback = single_match(release_dir, "*_fallback.bin")

        print(f"Operational: {operational}", flush=True)
        print(f"Fallback:    {fallback}", flush=True)

        board_index = 1
        if args.loop:
            while True:
                prompt_for_board(board_index)
                flash_board(args, operational, fallback)
                board_index += 1

        for board_index in range(1, args.count + 1):
            if args.count > 1:
                prompt_for_board(board_index)
            flash_board(args, operational, fallback)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)

# Contributing

## Local build

Install the same core dependencies used by the Linux CI job. On Debian or
Ubuntu:

```bash
sudo apt update
sudo apt install -y cmake gzip libftdi1-dev libhidapi-dev libudev-dev pkg-config zlib1g-dev
```

Configure and build from a separate build directory:

```bash
cmake --preset default
cmake --build build
```

If your CMake version does not support presets, use `cmake -S . -B build`
instead.

Run a basic executable smoke check:

```bash
./build/openFPGALoader --help
```

## Minimal build check

For changes that should not depend on cable or FPGA vendor backends, also run a
minimal feature build:

```bash
cmake --preset minimal
cmake --build build-minimal
```

Without preset support, configure the same build manually:

```bash
cmake -S . -B build-minimal \
  -DENABLE_CABLE_ALL=OFF \
  -DENABLE_VENDORS_ALL=OFF \
  -DENABLE_USB_SCAN=OFF
```

## Documentation

Install the documentation dependencies and build the HTML docs locally:

```bash
python3 -m pip install -r doc/requirements.txt
scripts/check-docs-python.sh
scripts/check-docs.sh
```

For pull-request style validation, run the strict offline check:

```bash
scripts/check-docs-python.sh
scripts/check-docs.sh --strict
```

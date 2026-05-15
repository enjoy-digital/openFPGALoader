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
cmake -S . -B build
cmake --build build
```

Run a basic executable smoke check:

```bash
./build/openFPGALoader --help
```

## Minimal build check

For changes that should not depend on cable or FPGA vendor backends, also run a
minimal feature build:

```bash
cmake -S . -B build-minimal \
  -DENABLE_CABLE_ALL=OFF \
  -DENABLE_VENDORS_ALL=OFF \
  -DENABLE_USB_SCAN=OFF
cmake --build build-minimal
```

## Documentation

Install the documentation dependencies and build the HTML docs locally:

```bash
python3 -m pip install -r doc/requirements.txt
sphinx-build -b html doc doc/_build/html
```

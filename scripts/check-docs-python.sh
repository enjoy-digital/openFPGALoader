#!/bin/sh

set -eu

cd "$(dirname "$0")/.."

python3 -m py_compile doc/conf.py doc/data.py

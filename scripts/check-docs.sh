#!/bin/sh

set -eu

cd "$(dirname "$0")/.."

sphinx-build -b html doc doc/_build/html

#!/bin/sh

set -eu

cd "$(dirname "$0")/.."

usage() {
	echo "usage: $0 [--strict]" >&2
}

strict=false
if [ "${1:-}" = "--strict" ]; then
	strict=true
	shift
fi

if [ "$#" -ne 0 ]; then
	usage
	exit 2
fi

if [ "$strict" = true ]; then
	OFL_DOCS_OFFLINE=1 sphinx-build -W -b html doc doc/_build/html
	OFL_DOCS_OFFLINE=1 scripts/check-docs-generated.py
else
	sphinx-build -b html doc doc/_build/html
	scripts/check-docs-generated.py
fi

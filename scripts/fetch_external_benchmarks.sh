#!/usr/bin/env bash
set -euo pipefail

mkdir -p external

if [[ ! -d external/FEA-Bench/.git ]]; then
  git clone --depth 1 https://github.com/microsoft/FEA-Bench.git external/FEA-Bench
fi

if [[ ! -d external/SWE-bench/.git ]]; then
  git clone --depth 1 https://github.com/SWE-bench/SWE-bench.git external/SWE-bench
fi

echo "External benchmark repositories are available."

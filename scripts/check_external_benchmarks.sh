#!/usr/bin/env bash
set -euo pipefail

status=0

check_file() {
  local path="$1"
  if [[ -e "$path" ]]; then
    echo "OK  $path"
  else
    echo "ERR $path"
    status=1
  fi
}

check_file external/FEA-Bench/README.md
check_file external/FEA-Bench/instances_lite.json
check_file external/SWE-bench/README.md
check_file external/SWE-bench/docs/guides/evaluation.md

if curl -L --silent 'https://datasets-server.huggingface.co/splits?dataset=princeton-nlp%2FSWE-bench_Lite' >/dev/null; then
  echo "OK  SWE-bench Lite dataset endpoint reachable"
else
  echo "ERR SWE-bench Lite dataset endpoint unreachable"
  status=1
fi

if curl -L --silent 'https://datasets-server.huggingface.co/splits?dataset=microsoft%2FFEA-Bench' >/dev/null; then
  echo "OK  FEA-Bench dataset endpoint reachable"
else
  echo "ERR FEA-Bench dataset endpoint unreachable"
  status=1
fi

if command -v docker >/dev/null 2>&1; then
  echo "OK  docker available"
else
  echo "WARN docker is not available on the login node; official SWE/FEA evaluation must run on a compute node with container support"
fi

exit "$status"

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CONDA_BIN="/storage/ice1/2/9/eliu354/miniconda3/bin/conda"
ENV_NAME="${ENV_NAME:-monitor-ai-system}"

DATASET_NAME="${DATASET_NAME:-SWE-bench/SWE-bench_Lite}"
RUN_ID="${RUN_ID:-SWEBench_Lite_Gold}"
MAX_WORKERS="${MAX_WORKERS:-4}"
TIMEOUT="${TIMEOUT:-1800}"
CACHE_LEVEL="${CACHE_LEVEL:-env}"

bash "$REPO_ROOT/scripts/check_benchmark_runtime.sh" "$ENV_NAME"

PYTHONPATH="$REPO_ROOT/external/SWE-bench" \
"$CONDA_BIN" run -n "$ENV_NAME" python -m swebench.harness.run_evaluation \
  --dataset_name "$DATASET_NAME" \
  --predictions_path gold \
  --max_workers "$MAX_WORKERS" \
  --cache_level "$CACHE_LEVEL" \
  --timeout "$TIMEOUT" \
  --run_id "$RUN_ID"

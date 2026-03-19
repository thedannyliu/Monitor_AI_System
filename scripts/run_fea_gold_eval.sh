#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CONDA_BIN="/storage/ice1/2/9/eliu354/miniconda3/bin/conda"
ENV_NAME="${ENV_NAME:-monitor-ai-system}"

DATASET_PATH="${DATASET_PATH:-$REPO_ROOT/feabench-data/FEA-Bench-v1.0-Lite-Standard}"
SAVE_DIR="${SAVE_DIR:-$REPO_ROOT/results/benchmarks/fea_gold}"
FILE_NAME="${FILE_NAME:-Gold__FEABench_v1.0_Lite__test.jsonl}"
RUN_ID="${RUN_ID:-FEABench_Lite_Gold}"
MAX_WORKERS="${MAX_WORKERS:-4}"
TIMEOUT="${TIMEOUT:-900}"
CACHE_LEVEL="${CACHE_LEVEL:-instance}"

bash "$REPO_ROOT/scripts/check_benchmark_runtime.sh" "$ENV_NAME"
bash "$REPO_ROOT/scripts/prepare_fea_eval_harness.sh" "$ENV_NAME"

PYTHONPATH="$REPO_ROOT/external/FEA-Bench" \
"$CONDA_BIN" run -n "$ENV_NAME" python -m feabench.get_gold_results \
  --dataset_name_or_path "$DATASET_PATH" \
  --save_dir "$SAVE_DIR" \
  --file_name "$FILE_NAME"

PYTHONPATH="$REPO_ROOT/external/FEA-evaluator/SWE-bench" \
"$CONDA_BIN" run -n "$ENV_NAME" python -m swebench.harness.run_evaluation \
  --dataset_name "$DATASET_PATH" \
  --predictions_path "$SAVE_DIR/$FILE_NAME" \
  --max_workers "$MAX_WORKERS" \
  --cache_level "$CACHE_LEVEL" \
  --timeout "$TIMEOUT" \
  --run_id "$RUN_ID"

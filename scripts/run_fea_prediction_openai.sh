#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CONDA_BIN="/storage/ice1/2/9/eliu354/miniconda3/bin/conda"
ENV_NAME="${ENV_NAME:-monitor-ai-system}"

DATASET_PATH="${DATASET_PATH:-$REPO_ROOT/feabench-data/FEA-Bench-v1.0-Lite-Standard}"
INPUT_TEXT="${INPUT_TEXT:-natural-detailed}"
MODEL_NAME="${MODEL_NAME:-Qwen/Qwen2.5-Coder-7B-Instruct}"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/results/benchmarks/fea_predictions/$INPUT_TEXT}"
NUM_PROC="${NUM_PROC:-1}"
MODEL_ARGS="${MODEL_ARGS:-temperature=0.0,top_p=1.0,max_tokens=4096}"

export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8000/v1}"

PYTHONPATH="$REPO_ROOT/external/FEA-Bench" \
"$CONDA_BIN" run -n "$ENV_NAME" python -m feabench.run_prediction \
  --dataset_name_or_path "$DATASET_PATH" \
  --model_type openai \
  --model_name_or_path "$MODEL_NAME" \
  --input_text "$INPUT_TEXT" \
  --output_dir "$OUTPUT_DIR" \
  --model_args "$MODEL_ARGS" \
  --num_proc "$NUM_PROC"

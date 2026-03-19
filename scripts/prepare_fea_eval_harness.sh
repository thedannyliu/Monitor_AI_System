#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
EVAL_ROOT="$REPO_ROOT/external/FEA-evaluator"
HARNESS_ROOT="$EVAL_ROOT/SWE-bench"
TARGET_COMMIT="a0536ee6f9fd5ff88acf17a36a384bf3da3d93d6"
CONDA_BIN="/storage/ice1/2/9/eliu354/miniconda3/bin/conda"
ENV_NAME="${1:-monitor-ai-system}"

mkdir -p "$EVAL_ROOT"

if [[ ! -d "$HARNESS_ROOT/.git" ]]; then
  git clone https://github.com/SWE-bench/SWE-bench.git "$HARNESS_ROOT"
fi

git -C "$HARNESS_ROOT" fetch --all --tags
git -C "$HARNESS_ROOT" checkout "$TARGET_COMMIT"

if ! git -C "$HARNESS_ROOT" apply --check "$REPO_ROOT/external/FEA-Bench/swe-bench.diff" >/dev/null 2>&1; then
  echo "FEA patch already applied or conflicts with the current harness state."
else
  git -C "$HARNESS_ROOT" apply "$REPO_ROOT/external/FEA-Bench/swe-bench.diff"
fi

PYTHONPATH="$HARNESS_ROOT" "$CONDA_BIN" run -n "$ENV_NAME" python -m swebench.harness.run_evaluation --help >/dev/null

echo "Prepared FEA evaluator harness at $HARNESS_ROOT"

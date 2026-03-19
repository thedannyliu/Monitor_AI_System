#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CONDA_BIN="/storage/ice1/2/9/eliu354/miniconda3/bin/conda"
ENV_NAME="${1:-monitor-ai-system}"

"$CONDA_BIN" run -n "$ENV_NAME" pip install -r "$REPO_ROOT/requirements-bench.txt"

echo "Installed benchmark extras into '$ENV_NAME'."

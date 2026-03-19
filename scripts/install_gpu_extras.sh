#!/usr/bin/env bash
set -euo pipefail

CONDA_ROOT="${CONDA_ROOT:-/storage/ice1/2/9/eliu354/miniconda3}"
CONDA_BIN="$CONDA_ROOT/bin/conda"
ENV_NAME="${ENV_NAME:-monitor-ai-system}"

unset CONDA_EXE CONDA_PREFIX CONDA_PROMPT_MODIFIER CONDA_SHLVL CONDA_PYTHON_EXE CONDA_DEFAULT_ENV CONDA_ENVS_PATH CONDA_PKGS_DIRS

"$CONDA_BIN" run -n "$ENV_NAME" python -m pip install -r requirements-gpu.txt

echo "Installed GPU extras into '$ENV_NAME'."

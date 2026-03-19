#!/usr/bin/env bash
set -euo pipefail

CONDA_ROOT="${CONDA_ROOT:-/storage/ice1/2/9/eliu354/miniconda3}"
CONDA_BIN="$CONDA_ROOT/bin/conda"
ENV_NAME="${ENV_NAME:-monitor-ai-system}"

unset CONDA_EXE CONDA_PREFIX CONDA_PROMPT_MODIFIER CONDA_SHLVL CONDA_PYTHON_EXE CONDA_DEFAULT_ENV CONDA_ENVS_PATH CONDA_PKGS_DIRS

"$CONDA_BIN" info --base >/dev/null

if "$CONDA_BIN" env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  "$CONDA_BIN" run -n "$ENV_NAME" python --version
else
  "$CONDA_BIN" create -y -n "$ENV_NAME" python=3.12
fi

"$CONDA_BIN" run -n "$ENV_NAME" python -m pip install --upgrade pip
"$CONDA_BIN" run -n "$ENV_NAME" python -m pip install -r requirements.txt
"$CONDA_BIN" run -n "$ENV_NAME" python -m pip install -e external/SWE-bench
"$CONDA_BIN" run -n "$ENV_NAME" python -m pip install -e external/FEA-Bench --no-deps

echo "Environment '$ENV_NAME' is ready."

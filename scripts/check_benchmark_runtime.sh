#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CONDA_BIN="/storage/ice1/2/9/eliu354/miniconda3/bin/conda"
ENV_NAME="${1:-monitor-ai-system}"

echo "Checking benchmark runtime prerequisites for env '$ENV_NAME'..."

"$CONDA_BIN" run -n "$ENV_NAME" python - <<'PY'
import importlib
required = ["bs4", "dotenv", "docker", "modal", "datasets", "ghapi", "unidiff"]
missing = [name for name in required if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit(f"Missing benchmark Python dependencies: {missing}")
print("Python benchmark dependencies are available.")
PY

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker CLI is not available on this node."
  echo "Use a compute node that exposes Docker before running official SWE/FEA evaluation."
  exit 2
fi

docker --version
echo "Docker CLI is available."

if docker info >/dev/null 2>&1; then
  echo "Docker daemon is reachable."
else
  echo "Docker CLI exists but the daemon is not reachable."
  exit 3
fi

if [[ ! -d "$REPO_ROOT/external/SWE-bench" ]]; then
  echo "Missing external/SWE-bench checkout."
  exit 4
fi

if [[ ! -d "$REPO_ROOT/external/FEA-Bench" ]]; then
  echo "Missing external/FEA-Bench checkout."
  exit 5
fi

echo "Benchmark runtime checks completed successfully."

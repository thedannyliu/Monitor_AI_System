#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CONDA_BIN="/storage/ice1/2/9/eliu354/miniconda3/bin/conda"
ENV_NAME="${1:-monitor-ai-system}"

echo "Checking benchmark runtime prerequisites for env '$ENV_NAME'..."
echo "Host: $(hostname)"

DOCKER_BIN="$(command -v docker || true)"
APPTAINER_BIN="$(command -v apptainer || true)"
SINGULARITY_BIN="$(command -v singularity || true)"

"$CONDA_BIN" run -n "$ENV_NAME" python - <<'PY'
import importlib
required = ["bs4", "dotenv", "docker", "modal", "datasets", "ghapi", "unidiff"]
missing = [name for name in required if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit(f"Missing benchmark Python dependencies: {missing}")
print("Python benchmark dependencies are available.")
PY

echo "Container runtimes:"
echo "  docker: ${DOCKER_BIN:-not found}"
echo "  apptainer: ${APPTAINER_BIN:-not found}"
echo "  singularity: ${SINGULARITY_BIN:-not found}"

if [[ -z "$DOCKER_BIN" ]]; then
  echo
  echo "Conclusion:"
  echo "  - This node can still run inference, vLLM, monitor generation, and prediction generation."
  echo "  - This node cannot run the official SWE/FEA Docker evaluation harness as-is."
  echo "  - If Apptainer/Singularity is available, it may still be useful for other containerized workflows, but not as a drop-in replacement for the official Docker harness."
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

echo
echo "Conclusion:"
echo "  - This node is suitable for official SWE/FEA benchmark evaluation."
echo "  - It can also run inference and prediction generation."

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"

echo "PACE node capability check"
echo "Host: $(hostname)"
echo

for cmd in docker apptainer singularity nvidia-smi; do
  path="$(command -v "$cmd" || true)"
  if [[ -n "$path" ]]; then
    echo "$cmd: $path"
  else
    echo "$cmd: not found"
  fi
done

echo
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "GPU summary:"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true
else
  echo "GPU summary: unavailable on this node"
fi

echo
if [[ -f /etc/os-release ]]; then
  echo "OS:"
  sed -n '1,6p' /etc/os-release
fi

echo
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    docker_state="available"
  else
    docker_state="cli-only"
  fi
else
  docker_state="missing"
fi

apptainer_state="missing"
if command -v apptainer >/dev/null 2>&1; then
  apptainer_state="available"
elif command -v singularity >/dev/null 2>&1; then
  apptainer_state="available-via-singularity"
fi

echo "Capability summary:"
case "$docker_state" in
  available)
    echo "  - Official SWE/FEA Docker evaluation: supported"
    ;;
  cli-only)
    echo "  - Official SWE/FEA Docker evaluation: blocked because Docker daemon is unreachable"
    ;;
  missing)
    echo "  - Official SWE/FEA Docker evaluation: not supported on this node"
    ;;
esac

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "  - GPU inference / vLLM: likely supported"
else
  echo "  - GPU inference / vLLM: not supported on this node"
fi

case "$apptainer_state" in
  available|available-via-singularity)
    echo "  - Apptainer/Singularity workflows: supported"
    ;;
  *)
    echo "  - Apptainer/Singularity workflows: not detected"
    ;;
esac

echo
echo "Recommended interpretation:"
if [[ "$docker_state" == "available" ]]; then
  echo "  - This node can run both prediction generation and official benchmark evaluation."
elif command -v nvidia-smi >/dev/null 2>&1; then
  echo "  - Use this node for model inference and prediction generation."
  echo "  - Move predictions to a Docker-enabled machine for official evaluation."
else
  echo "  - This node is suitable mainly for lightweight preprocessing and orchestration."
fi

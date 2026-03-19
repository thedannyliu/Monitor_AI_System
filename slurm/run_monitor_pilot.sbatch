#!/usr/bin/env bash
#SBATCH --job-name=monitor-pilot
#SBATCH --partition=ice-gpu
#SBATCH --gres=gpu:l40s:1
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=results/pilot/monitor_pilot_%j.out

set -euo pipefail

cd /storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys

BACKEND="${MONITOR_BACKEND:-heuristic}"
BASE_URL="${MONITOR_BASE_URL:-http://127.0.0.1:8000/v1}"
MODEL_NAME="${MONITOR_MODEL_NAME:-Qwen/Qwen2.5-Coder-7B-Instruct}"

echo "Running pilot with backend=$BACKEND"

/storage/ice1/2/9/eliu354/miniconda3/bin/conda run -n monitor-ai-system python scripts/run_pilot.py \
  --self-manifest data/self_bench/pilot/manifest.json \
  --fea-manifest data/fea_bench/curated/pilot_manifest.json \
  --swe-manifest data/swe_bench/curated/pilot_manifest.json \
  --output-dir results/pilot/run_${SLURM_JOB_ID} \
  --backend "$BACKEND" \
  --base-url "$BASE_URL" \
  --model-name "$MODEL_NAME"

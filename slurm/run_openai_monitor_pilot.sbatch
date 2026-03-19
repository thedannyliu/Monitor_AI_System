#!/usr/bin/env bash
#SBATCH --job-name=monitor-openai-pilot
#SBATCH --partition=ice-gpu
#SBATCH --gres=gpu:l40s:1
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=results/pilot/openai_monitor_pilot_%j.out

set -euo pipefail

cd /storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys

CONDA_BIN="/storage/ice1/2/9/eliu354/miniconda3/bin/conda"
BASE_URL="${MONITOR_BASE_URL:-http://127.0.0.1:8000/v1}"
MODEL_NAME="${MONITOR_MODEL_NAME:-Qwen2.5-Coder-7B-Instruct}"

"$CONDA_BIN" run -n monitor-ai-system python scripts/run_pilot.py \
  --self-manifest data/self_bench/pilot/manifest.json \
  --fea-manifest data/fea_bench/curated/pilot_manifest.json \
  --swe-manifest data/swe_bench/curated/pilot_manifest.json \
  --output-dir results/pilot/openai_run_${SLURM_JOB_ID} \
  --backend openai \
  --base-url "$BASE_URL" \
  --model-name "$MODEL_NAME"

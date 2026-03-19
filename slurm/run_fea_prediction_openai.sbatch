#!/usr/bin/env bash
#SBATCH --job-name=fea-openai-pred
#SBATCH --partition=ice-gpu
#SBATCH --gres=gpu:l40s:1
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --output=results/benchmarks/fea_prediction_%j.out

set -euo pipefail

cd /storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys

export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8000/v1}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"
export MODEL_NAME="${MODEL_NAME:-Qwen/Qwen2.5-Coder-7B-Instruct}"
export DATASET_PATH="${DATASET_PATH:-/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/feabench-data/FEA-Bench-v1.0-Lite-Standard}"
export OUTPUT_DIR="${OUTPUT_DIR:-/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/results/benchmarks/fea_predictions/natural-detailed}"

bash scripts/run_fea_prediction_openai.sh

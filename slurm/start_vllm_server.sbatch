#!/usr/bin/env bash
#SBATCH --job-name=vllm-qwen7b
#SBATCH --partition=ice-gpu
#SBATCH --gres=gpu:l40s:1
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=results/pilot/vllm_server_%j.out

set -euo pipefail

cd /storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys

bash scripts/install_gpu_extras.sh
bash scripts/start_vllm_server.sh

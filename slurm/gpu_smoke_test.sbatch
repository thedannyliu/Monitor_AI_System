#!/usr/bin/env bash
#SBATCH --job-name=monitor-gpu-smoke
#SBATCH --partition=ice-gpu
#SBATCH --gres=gpu:l40s:1
#SBATCH --time=00:10:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=results/pilot/gpu_smoke_%j.out

set -euo pipefail

cd /storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys

echo "Host: $(hostname)"
echo "Date: $(date)"
echo "CUDA devices:"
nvidia-smi
echo "Python:"
/usr/bin/python3 --version

/usr/bin/python3 scripts/run_pilot.py \
  --self-manifest data/self_bench/pilot/manifest.json \
  --fea-manifest data/fea_bench/curated/pilot_manifest.json \
  --swe-manifest data/swe_bench/curated/pilot_manifest.json \
  --output-dir results/pilot/gpu_smoke_${SLURM_JOB_ID} \
  --backend heuristic

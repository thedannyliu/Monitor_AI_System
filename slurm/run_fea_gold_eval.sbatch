#!/usr/bin/env bash
#SBATCH --job-name=fea-gold-eval
#SBATCH --partition=ice-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output=results/benchmarks/fea_gold_eval_%j.out

set -euo pipefail

cd /storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys
bash scripts/run_fea_gold_eval.sh

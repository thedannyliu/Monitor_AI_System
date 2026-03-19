#!/usr/bin/env bash
#SBATCH --job-name=swe-lite-gold
#SBATCH --partition=ice-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output=results/benchmarks/swe_lite_gold_eval_%j.out

set -euo pipefail

cd /storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys
bash scripts/run_swe_lite_gold_eval.sh

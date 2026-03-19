# Monitor_AI_System

This repository contains the pilot implementation for monitoring hidden assumptions in coding agents.

## Scope

The project studies whether a monitoring layer can surface hidden assumptions from incomplete task specifications before a coding agent executes a task.

The first milestone covers:

1. A shared taxonomy for hidden assumptions
2. A fixed JSON report schema
3. Pilot task curation for three benchmarks
4. A monitor report generation pipeline
5. Slurm batch jobs for GPU smoke tests and pilot runs on PACE ICE

## Fixed Defaults

- Base coder model: `Qwen2.5-Coder-7B-Instruct`
- Monitor model: `Qwen2.5-Coder-7B-Instruct`
- Preferred inference backend: `vLLM`
- Fallback backend: `transformers`
- Pilot benchmarks:
  - self benchmark: 5 tasks
  - FEA-Bench Lite curated pilot: 5 tasks
  - SWE-bench Lite curated pilot: 5 tasks

## Repository Layout

- `docs/`: experiment design and annotation rules
- `configs/`: model and experiment settings
- `data/`: curated pilot tasks and benchmark manifests
- `src/`: monitor, benchmark, and evaluation code
- `scripts/`: local entrypoints
- `slurm/`: GPU batch jobs for PACE ICE

## Quick Start

The login node Python in the current environment is unstable, so the project defaults to `/usr/bin/python3`.

Local smoke test:

```bash
/usr/bin/python3 scripts/run_pilot.py \
  --self-manifest data/self_bench/pilot/manifest.json \
  --fea-manifest data/fea_bench/curated/pilot_manifest.json \
  --swe-manifest data/swe_bench/curated/pilot_manifest.json \
  --output-dir results/pilot/local_smoke \
  --backend heuristic
```

Check external benchmark repos:

```bash
bash scripts/check_external_benchmarks.sh
```

Submit a GPU smoke test:

```bash
sbatch slurm/gpu_smoke_test.sbatch
```

Submit the pilot runner:

```bash
sbatch slurm/run_monitor_pilot.sbatch
```

## Notes

- `external/FEA-Bench` and `external/SWE-bench` are local clones for environment checks and should not be committed.
- Official FEA-Bench dataset construction still requires a GitHub token.
- Official SWE-bench evaluation still requires the full harness dependencies and container runtime on compute nodes.

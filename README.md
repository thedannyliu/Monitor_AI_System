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

- Base coder model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- Monitor model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- Preferred inference backend: `vLLM`
- Fallback backend: `transformers`
- Core env setup: `bash scripts/create_or_update_env.sh`
- Benchmark extras: `bash scripts/install_benchmark_extras.sh`
- Real benchmark runbook: [docs/real_benchmark_runbook.md](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/docs/real_benchmark_runbook.md)
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

The project now uses a dedicated Conda environment named `monitor-ai-system` with Python 3.12.

Create or update the Conda environment:

```bash
bash scripts/create_or_update_env.sh
```

Check external benchmark repos:

```bash
bash scripts/check_external_benchmarks.sh
```

Check the current PACE node capabilities:

```bash
bash scripts/check_pace_node_capabilities.sh
```

Check whether the current node can run official benchmark evaluation:

```bash
bash scripts/check_benchmark_runtime.sh
```

Submit a GPU smoke test:

```bash
sbatch slurm/gpu_smoke_test.sbatch
```

Install GPU extras and start a vLLM server on a compute node:

```bash
sbatch slurm/start_vllm_server.sbatch
```

Run the monitor pilot against an OpenAI-compatible endpoint:

```bash
sbatch slurm/run_openai_monitor_pilot.sbatch
```

Run the execution pilot against the same endpoint after monitor outputs exist:

```bash
sbatch slurm/run_execution_pilot.sbatch
```

Submit the pilot runner:

```bash
sbatch slurm/run_monitor_pilot.sbatch
```

## Notes

- No project-specific Python packages were previously installed into the broken `miniconda3` base while this repo was being bootstrapped. The earlier work used `/usr/bin/python3`, `git`, and shell tooling.
- The `miniconda3` root was repaired in place to preserve existing Conda prefixes. Existing external envs at `/storage/ice1/2/9/eliu354/conda_envs/*` were not moved or rewritten.
- `external/FEA-Bench` and `external/SWE-bench` are local clones for environment checks and should not be committed.
- Official FEA-Bench dataset construction still requires a GitHub token.
- Official SWE-bench evaluation still requires the full harness dependencies and container runtime on compute nodes.

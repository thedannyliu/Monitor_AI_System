# Real Benchmark Runbook

## Purpose

This document records how to move from the current monitor/execution-artifact pilots to official benchmark-scored runs for:

1. `FEA-Bench`
2. `SWE-bench Lite`

The current project already supports:

1. structured assumption extraction
2. oracle review and revised spec generation
3. execution-artifact generation with an OpenAI-compatible backend

The next stage is official benchmark scoring, which requires the benchmark harness runtime.

## Current Boundary

The current pilot outputs in `results/pilot/` are **not** official benchmark scores.

They are:

1. monitor reports
2. revised specs
3. execution plans / artifact JSON

To obtain official benchmark results, the project must run the benchmark harness with patch predictions.

## Runtime Requirements

Official FEA/SWE evaluation requires:

1. Python benchmark extras installed in `monitor-ai-system`
2. Docker CLI
3. a reachable Docker daemon
4. enough disk space for benchmark images and caches

The login node does not provide the required runtime. Use a compute node or another machine where Docker is available.

## Environment Preparation

Install benchmark extras:

```bash
bash scripts/install_benchmark_extras.sh
```

Check the runtime:

```bash
bash scripts/check_benchmark_runtime.sh
```

## FEA-Bench

### 1. Build or locate the dataset

The recommended target for first official runs is:

- `FEA-Bench-v1.0-Lite-Standard`

If the dataset has not been built yet, follow the official `feabench.get_dataset` flow and provide a read-only `GITHUB_TOKEN`.

### 2. Run prediction

For an OpenAI-compatible backend such as local vLLM:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=dummy
export DATASET_PATH=/path/to/FEA-Bench-v1.0-Lite-Standard
export MODEL_NAME=Qwen/Qwen2.5-Coder-7B-Instruct
bash scripts/run_fea_prediction_openai.sh
```

The official FEA output is a `.jsonl` predictions file under:

- `results/benchmarks/fea_predictions/`

### 3. Verify the evaluator with gold patches

```bash
bash scripts/run_fea_gold_eval.sh
```

This script:

1. checks Docker/runtime prerequisites
2. prepares a patched SWE-bench evaluator for FEA
3. writes gold predictions
4. runs official harness evaluation

### 4. Slurm entry points

Available wrappers:

1. [run_fea_prediction_openai.sbatch](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/slurm/run_fea_prediction_openai.sbatch)
2. [run_fea_gold_eval.sbatch](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/slurm/run_fea_gold_eval.sbatch)

## SWE-bench Lite

### 1. Verify the harness with gold patches

```bash
bash scripts/run_swe_lite_gold_eval.sh
```

This confirms that Docker, the harness, and the benchmark images work on the target node before you attempt model-generated patches.

### 2. Slurm entry point

Available wrapper:

1. [run_swe_lite_gold_eval.sbatch](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/slurm/run_swe_lite_gold_eval.sbatch)

## What Is Still Missing For Full Benchmark Scoring

The project still needs one more layer before official scored model runs:

1. a patch-generation runner that emits benchmark-format `.jsonl` predictions with `model_patch`
2. integration between `monitor_then_act` revised specs and that patch generator
3. experiment bookkeeping for `Direct on Redacted`, `Direct on Full`, and `Monitor-then-Act on Redacted`

The current execution pilot produces plans, not patches. That is intentional for the current stage.

## Recommended Next Sequence

1. confirm the improved monitor F1 on the OpenAI backend
2. verify Docker-enabled compute access with `check_benchmark_runtime.sh`
3. run `run_swe_lite_gold_eval.sh`
4. prepare the FEA evaluator with `prepare_fea_eval_harness.sh`
5. run `run_fea_gold_eval.sh`
6. implement the patch-generation runner that consumes revised specs

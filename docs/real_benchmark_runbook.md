# Real Benchmark Runbook

## Purpose

This document records the recommended workflow for:

1. generating benchmark predictions on PACE ICE / Phoenix
2. running official FEA-Bench / SWE-bench evaluation on an external Docker-enabled machine

This split is necessary because the current PACE nodes used in this project support GPU inference well, but the official benchmark harnesses depend on Docker.

---

## 1. What Runs Where

### PACE ICE / Phoenix

Use PACE for:

1. vLLM serving
2. monitor generation
3. revised spec generation
4. patch / prediction generation

Do **not** assume PACE can run the official benchmark harness unless:

1. `docker` exists on the node
2. `docker info` succeeds

Check this with:

```bash
bash scripts/check_pace_node_capabilities.sh
bash scripts/check_benchmark_runtime.sh
```

### External Docker Machine

Use an external Docker-enabled machine for:

1. `swebench.harness.run_evaluation`
2. FEA-Bench official evaluation
3. gold-run verification
4. final resolved-rate measurement

---

## 2. Why This Split Exists

The official SWE-bench harness is Docker-based. FEA-Bench official evaluation is built on top of the SWE-bench harness.

That means:

1. inference does **not** require Docker
2. official scoring **does** require Docker

So the recommended pattern is:

1. generate predictions on PACE
2. copy predictions to a Docker machine
3. run official evaluation there

---

## 3. External Machine Hardware Requirements

### 3.1 For official evaluation only

If the external machine is used **only** for official evaluation and not for model inference:

- GPU: not required
- CPU: at least 8 cores recommended
- RAM: at least 32 GB recommended
- Disk: at least 150 GB free recommended

Reason:

1. the harness builds / pulls benchmark images
2. repositories and environment caches consume substantial disk
3. multiple parallel workers benefit from CPU and RAM

For safer multi-instance evaluation:

- CPU: 16 cores preferred
- RAM: 64 GB preferred
- Disk: 250 GB or more preferred

### 3.2 If the same external machine also runs inference

If you also want the external machine to run local model inference:

- GPU: at least 1 x 24 GB VRAM recommended for 7B serving
- Preferred GPU class:
  - RTX 4090
  - A5000 / A6000
  - L40S
  - A100
  - H100

Recommended minimum for `Qwen/Qwen2.5-Coder-7B-Instruct`:

- 1 x 24 GB VRAM for practical local serving

Preferred:

- 1 x 40 GB+ VRAM if you want longer contexts, more stable vLLM settings, or concurrent workloads

If the machine is **only** for benchmark scoring, GPU is unnecessary.

### 3.3 OS / runtime requirements

Recommended:

1. Linux
2. Docker CLI
3. reachable Docker daemon
4. enough local disk for image cache and logs

---

## 4. Stage A: Generate Predictions on PACE

### 4.1 Start from a compute node

Check the node:

```bash
bash scripts/check_pace_node_capabilities.sh
```

Expected PACE pattern:

1. `apptainer` or `singularity` may exist
2. GPU tools may exist
3. `docker` may be absent

### 4.2 Start model serving

If using the local OpenAI-compatible setup:

```bash
sbatch slurm/start_vllm_server.sbatch
```

### 4.3 Generate predictions / artifacts

For the current project state, the monitor and execution pilots already run on PACE:

```bash
sbatch slurm/run_openai_monitor_pilot.sbatch
sbatch slurm/run_execution_pilot.sbatch
```

For FEA official-style prediction generation:

```bash
sbatch slurm/run_fea_prediction_openai.sbatch
```

Important:

The current repo already supports monitor reports and execution artifacts.  
Full benchmark scoring still requires a patch-generation runner that emits benchmark-format predictions with `model_patch`.

---

## 5. Stage B: Move Predictions Off PACE

Once predictions are generated, copy them to the external Docker machine.

Typical methods:

```bash
scp /path/to/predictions.jsonl user@external-machine:/path/to/eval/
rsync -av /path/to/predictions_dir user@external-machine:/path/to/eval/
```

Recommended to copy:

1. prediction `.jsonl`
2. manifest / metadata used for the run
3. model name
4. commit hash of this repo

This makes the evaluation reproducible.

---

## 6. Stage C: Run Official Evaluation on External Docker Machine

### 6.1 Prepare environment

Clone this repo or copy the needed scripts.

Install:

```bash
bash scripts/create_or_update_env.sh
bash scripts/install_benchmark_extras.sh
```

Check Docker:

```bash
bash scripts/check_benchmark_runtime.sh
```

### 6.2 SWE-bench Lite gold verification

Before evaluating model predictions, verify the machine using gold:

```bash
bash scripts/run_swe_lite_gold_eval.sh
```

### 6.3 FEA evaluator preparation

Prepare the patched evaluator:

```bash
bash scripts/prepare_fea_eval_harness.sh
```

### 6.4 FEA gold verification

```bash
bash scripts/run_fea_gold_eval.sh
```

### 6.5 Evaluate real predictions

For SWE-bench:

```bash
PYTHONPATH=external/SWE-bench \
conda run -n monitor-ai-system python -m swebench.harness.run_evaluation \
  --dataset_name SWE-bench/SWE-bench_Lite \
  --predictions_path /path/to/predictions.jsonl \
  --max_workers 4 \
  --cache_level env \
  --timeout 1800 \
  --run_id YourRunID
```

For FEA-Bench:

```bash
PYTHONPATH=external/FEA-evaluator/SWE-bench \
conda run -n monitor-ai-system python -m swebench.harness.run_evaluation \
  --dataset_name /path/to/FEA-Bench-v1.0-Lite-Standard \
  --predictions_path /path/to/predictions.jsonl \
  --max_workers 4 \
  --cache_level instance \
  --timeout 900 \
  --run_id YourRunID
```

---

## 7. What The New Local Scripts Give You

This repo now includes:

1. [check_pace_node_capabilities.sh](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/scripts/check_pace_node_capabilities.sh)
2. [check_benchmark_runtime.sh](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/scripts/check_benchmark_runtime.sh)
3. [run_fea_prediction_openai.sh](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/scripts/run_fea_prediction_openai.sh)
4. [prepare_fea_eval_harness.sh](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/scripts/prepare_fea_eval_harness.sh)
5. [run_fea_gold_eval.sh](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/scripts/run_fea_gold_eval.sh)
6. [run_swe_lite_gold_eval.sh](/storage/ice1/2/9/eliu354/Projects/Monitor_AI_Sys/scripts/run_swe_lite_gold_eval.sh)

These scripts separate:

1. prediction generation
2. runtime validation
3. official scoring

---

## 8. Current Project Boundary

The current execution pilot still produces execution artifacts rather than final repository patches.

So the remaining engineering step before official scored model runs is:

1. implement a patch-generation runner that writes benchmark-format `.jsonl` predictions with `model_patch`

After that, the evaluation side is already scaffolded.

---

## 9. Recommended Practical Workflow

If you want the fastest reliable path:

1. use PACE ICE / Phoenix for inference and prediction generation
2. keep official evaluation on an external Linux machine with Docker
3. verify that external machine with gold first
4. then score your real predictions

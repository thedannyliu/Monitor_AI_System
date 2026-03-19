# Environment Setup and Conda Recovery

## Purpose

This document records how the project environment is managed after the original local `miniconda3` installation became inconsistent.

It answers four practical questions:

1. What was broken
2. What was preserved
3. What was changed
4. How to recreate the environment safely

---

## 1. Initial State

The original Conda root at:

- `/storage/ice1/2/9/eliu354/miniconda3`

was not usable at the start of the project bootstrap.

Observed symptoms:

1. `conda` failed during interpreter startup
2. `python` under that root failed to initialize filesystem encoding
3. the active shell still carried `CONDA_*` variables from a different PACE system Anaconda installation

At the same time, there were existing external Conda environments already present at:

- `/storage/ice1/2/9/eliu354/conda_envs/dcllm`
- `/storage/ice1/2/9/eliu354/conda_envs/flow-mbpo`

Those existing environments were not part of this project and had to remain untouched.

---

## 2. What Was Not Done

To avoid damaging unrelated environments:

1. the `miniconda3` directory was not renamed
2. the existing external env prefixes were not moved
3. no existing env prefix was deleted
4. no GPU package was installed into base

Also, before the Conda recovery, the project bootstrap work did **not** install Python packages into the broken local base.

Earlier project setup used:

- `/usr/bin/python3`
- `git`
- `curl`
- shell tooling

So there was no project-specific GPU or benchmark package pollution in the broken base from this repository's initial setup.

---

## 3. Recovery Strategy

The recovery strategy was:

1. repair the existing Conda root **in place**
2. keep the same root path
3. keep base minimal
4. create a dedicated project env for this repository

This was chosen because Conda envs are path-sensitive. Renaming the Conda root could invalidate any envs tied to that prefix.

---

## 4. Recovery Steps Performed

### Step 1: In-place Miniconda repair

The root was repaired in place using an official Python 3.12 Miniconda installer.

Result:

- base Python is now `3.12`
- Conda is functional again

### Step 2: Base cleanup

After the in-place repair, the base root still had stale solver/plugin remnants from the earlier broken state.

The following cleanup was applied:

1. set solver to `classic`
2. disable `auto_activate_base`
3. install only minimal missing base support packages
4. remove the broken `conda-libmamba-solver` plugin and `libmambapy`

This keeps base closer to a maintenance root instead of a project runtime.

### Step 3: Dedicated project env

Created project env:

- `monitor-ai-system`

with:

- `python=3.12`

### Step 4: Install project dependencies

Installed:

1. `requirements.txt`
2. editable install of the local repository
3. editable install of `external/SWE-bench`
4. editable install of `external/FEA-Bench --no-deps`

The `--no-deps` on FEA-Bench is intentional because its package metadata pulls `vllm`, which is a GPU-serving dependency and should not be part of the lightweight core env bootstrap on the login node.

---

## 5. Final Environment Layout

### Conda root

- `/storage/ice1/2/9/eliu354/miniconda3`

### Project env

- `monitor-ai-system`

### Existing preserved envs

- `/storage/ice1/2/9/eliu354/conda_envs/dcllm`
- `/storage/ice1/2/9/eliu354/conda_envs/flow-mbpo`

These preserved envs were discovered after the recovery and remained visible through `conda env list`.

---

## 6. Dependency Split

The project now uses a two-layer dependency model.

### Core environment

Installed by:

- `bash scripts/create_or_update_env.sh`

Includes:

- project Python runtime
- monitor pipeline dependencies
- datasets tooling
- benchmark Python packages
- local editable installs

Does **not** include:

- `vllm`

### GPU extras

Installed by:

- `bash scripts/install_gpu_extras.sh`

Currently includes:

- `vllm==0.8.4`

Reason:

1. GPU serving should be isolated from base
2. login-node setup should stay lighter
3. FEA-Bench's `vllm` dependency should not be pulled accidentally during core bootstrap

---

## 7. Required Commands

### Rebuild or refresh the project env

```bash
bash scripts/create_or_update_env.sh
```

### Install GPU-serving extras

```bash
bash scripts/install_gpu_extras.sh
```

### Start a vLLM server

```bash
bash scripts/start_vllm_server.sh
```

### Run the heuristic pilot in the Conda env

```bash
/storage/ice1/2/9/eliu354/miniconda3/bin/conda run -n monitor-ai-system \
  python scripts/run_pilot.py \
  --self-manifest data/self_bench/pilot/manifest.json \
  --fea-manifest data/fea_bench/curated/pilot_manifest.json \
  --swe-manifest data/swe_bench/curated/pilot_manifest.json \
  --output-dir results/pilot/conda_smoke \
  --backend heuristic
```

---

## 8. Important Safety Rule

All project scripts that interact with Conda should unset inherited `CONDA_*` shell variables first.

Reason:

the PACE login shell may already contain environment variables from a different system Anaconda installation, which can pollute the local project Conda root.

This is why the setup scripts explicitly unset:

- `CONDA_EXE`
- `CONDA_PREFIX`
- `CONDA_PROMPT_MODIFIER`
- `CONDA_SHLVL`
- `CONDA_PYTHON_EXE`
- `CONDA_DEFAULT_ENV`
- `CONDA_ENVS_PATH`
- `CONDA_PKGS_DIRS`

---

## 9. Current Limitations

1. Official SWE-bench and FEA-Bench end-to-end evaluation still require compute-node execution and likely a container runtime.
2. The core env is ready for pilot orchestration, but GPU serving still depends on `requirements-gpu.txt`.
3. FEA-Bench Python package import should be treated as tooling support; its full benchmark runtime still belongs on compute nodes.

---

## 10. Recommendation

Use the project env for all repository work and keep base as a maintenance root only.

Recommended policy:

1. do not install project libraries into base
2. do not install GPU-serving libraries into base
3. use `monitor-ai-system` for all repo scripts
4. install `requirements-gpu.txt` only when running on GPU-capable nodes

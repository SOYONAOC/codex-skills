---
name: dmde-compute
description: Use when estimating resources, auto-selecting local SLURM CPU nodes, submitting or dry-running Python jobs, inspecting GPU metadata, or handling N-body, metal-enrichment, halo-catalog, large-memory, and compute workflows.
---

# DMDE Compute

Use this skill for local SLURM compute-node work: submission, fastest-safe node
choice, GPU checks, large-memory jobs, N-body, halo catalogues, merger
trees, Pop III grids, and metal-enrichment calculations.

## Core Rule

Default to the fastest resource that satisfies the job's hard requirements:

```text
resource requirements first, fastest suitable node second
```

Do not submit memory-uncertain jobs to the highest-scoring node just because it
is fastest. Estimate peak RSS first. If uncertain, run a small profiling job or
require large live available memory before scaling up.

## Resource Estimation

Before choosing a node, classify the job:

```text
CPU vs GPU
estimated peak RSS
process workers vs threaded BLAS/OpenMP
I/O-heavy vs CPU-bound
single run vs parameter/grid sweep
```

For Python jobs with uncertain memory, run a representative small profile first:

```bash
python ~/.codex/skills/dmde-compute/scripts/profile_python_resources.py \
  --project-root /path/to/project \
  path/to/script.py -- --small-sample-arg value
```

Use the reported `recommended --min-available-mem-gib` with the submit script.
If a representative profile is not possible, treat memory as unknown and use a
high `--min-available-mem-gib` or run a manual small SLURM profiling job before
scaling up.

## Cluster Discovery

Node and benchmark data are not stored in the skill directory. The submit script
uses a local cache:

```text
${CODEX_DMDE_COMPUTE_CACHE_DIR:-~/.codex/local/dmde-compute}/node_benchmarks.json
```

When the cache is missing, `submit_python_job.py` automatically runs
`scripts/benchmark_nodes.py` to:

- query `sinfo` for usable nodes with idle CPUs, partition, state, CPU counts,
  and SLURM-reported memory fields;
- skip down, drain, and no-idle nodes;
- benchmark every discovered candidate node with one CPU through `srun`;
- normalize the fastest measured node to benchmark `10.0` by default;
- probe GPUs lightly with `nvidia-smi` and store GPU metadata without using it
  in the default CPU score.

Use `--refresh-benchmarks` to regenerate the cache, `--baseline-node NODE` to
choose a specific normalization node, or `--no-auto-benchmark` to fail fast if
the cache is absent.

## Fastest-Safe Policy

Use this selection order:

1. Filter nodes that do not meet the effective live memory requirement.
2. Use at most `--cpu-fraction` of currently idle CPUs.
3. Rank remaining CPU candidates by `usable_cpus * benchmark`.
4. For GPU jobs, inspect cached GPU metadata and live `nvidia-smi` output before
   manually pinning or selecting a GPU-capable node.

Thresholds:

```text
peak RSS known: require peak RSS * --memory-safety-factor live available memory
peak RSS unknown: run a small profile or set an explicit high --min-available-mem-gib
GPU jobs: require an explicit GPU check before submission
```

Do not fill a node by default. Use at most about 80% of idle CPUs for automatic
Python jobs unless the user requests an aggressive run.

## Required Live Checks

Before submitting:

```bash
sinfo -N -o '%N|%P|%t|%C|%e|%m|%G|%E'
squeue -u "$USER" -o '%.18i %.9P %.28j %.8u %.2t %.10M %.10l %.6D %.4C %R'
```

Check actual node memory:

```bash
python ~/.codex/skills/dmde-compute/scripts/benchmark_nodes.py \
  --project-root /path/to/project \
  --output /tmp/node_benchmarks.json
```

Check physical GPUs:

```bash
cat "${CODEX_DMDE_COMPUTE_CACHE_DIR:-$HOME/.codex/local/dmde-compute}/node_benchmarks.json"
```

## Python Job Submission

For Python jobs, use the unified auto-submit script bundled with this skill:

```bash
python ~/.codex/skills/dmde-compute/scripts/submit_python_job.py \
  --job-name my_job \
  --estimated-peak-rss-gib 80 \
  --time 12:00:00 \
  path/to/script.py -- --arg value
```

The script:

- uses `<project_root>/.venv/bin/python` by default;
- creates or reuses the local benchmark cache;
- queries live idle CPUs and SLURM-reported free memory at submit time;
- converts `--estimated-peak-rss-gib` to an effective memory requirement with
  `--memory-safety-factor` (default 1.5);
- filters out nodes below the effective memory requirement;
- verifies candidate node `MemAvailable` with `srun free -BG` when an effective
  memory requirement is set, unless `--node-memory-check never` is explicit;
- requests scheduler memory with `--mem=<ceil(effective requirement)>G` when an
  effective memory requirement is known;
- scores remaining nodes by `usable_cpus * benchmark`;
- adds common worker/thread flags only when missing by default;
- preserves explicit worker counts unless `--parallelism-mode force` is used;
- writes logs and submission metadata to `outputs/`.

Use `--dry-run` before first submission or when resource estimates are uncertain.
The dry-run output includes the full `sbatch` command. If no memory estimate or
explicit minimum memory is supplied, the script does not invent a `--mem` value.
Use `--parallelism-mode none` when a script manages its own worker counts.
Use `--refresh-benchmarks` after hardware, queue, or load changes.

## Manual SLURM Patterns

CPU-bound low-memory job on an explicitly chosen node:

```bash
sbatch -p <partition> --nodelist=<node> -N1 -n1 -c64 --time=12:00:00 \
  -J job_name -o outputs/%x-%j.out -e outputs/%x-%j.err \
  --wrap='cd /path/to/project && .venv/bin/python script.py --workers 64'
```

Large-memory job on an explicitly chosen high-memory node:

```bash
sbatch -p <partition> --nodelist=<node> -N1 -n1 -c38 --time=12:00:00 \
  -J fat_job -o outputs/%x-%j.out -e outputs/%x-%j.err \
  --wrap='cd /path/to/project && free -h && .venv/bin/python script.py --workers 38'
```

GPU job on a pinned CPU-partition GPU node:

```bash
sbatch -p <partition> --nodelist=<gpu-node> -N1 -n1 -c8 --time=04:00:00 \
  -J gpu_job -o outputs/%x-%j.out -e outputs/%x-%j.err \
  --wrap='cd /path/to/project && nvidia-smi && export CUDA_VISIBLE_DEVICES=0 && .venv/bin/python script.py'
```

## Workflow Rules

- Start with a small profiling run when memory or scaling is unknown.
- Keep checkpointing for long grids and N-body post-processing.
- Prefer chunked HDF5/Zarr/parquet I/O for large halo and metal-history tables.
- Preserve the original stderr/logs when a job fails; diagnose the node,
  environment, data, or resource estimate rather than falling back to login-node
  execution.
- For Pop III / metal-enrichment grids, use automatic ranking only when peak
  memory is known; otherwise profile first or set explicit memory requirements.

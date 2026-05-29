---
name: enforce-no-fallbacks
description: Fail-fast coding and debugging discipline that forbids adding fallback / 兜底 / silent-degradation / catch-and-continue / guessed-path / alternate-backend code to hide failures. Use by default whenever Codex writes, runs, tests, debugs, reviews, or modifies code; handles command, import, dependency, runtime, configuration, path, data, TeX, plotting, local Mac, SSH, remote Linux server, and SLURM failures by finding the root cause instead of adding fallback code.
---

# Enforce No Fallbacks

## Core Rule

Do not add fallback code to make a failure disappear. Preserve the failure, find the reason, and fix the reason.

Treat this as a default engineering constraint for local Mac work, remote server work, SSH sessions, and SLURM jobs.

## Forbidden By Default

Avoid adding or keeping patterns that hide problems:

- Broad `try/except` blocks that continue after an unexpected error.
- `except Exception: pass`, empty outputs, synthetic data, cached plots, or placeholder results after a failed computation.
- Silent import fallbacks, alternate libraries, alternate file paths, alternate interpreters, alternate TeX engines, or alternate plotting backends.
- Default values used only because a config key, data column, environment variable, or dependency is missing.
- Switching from a required server, node, queue, or SLURM workflow to local/login-node execution because submission failed.
- Changing scientific parameters, data cuts, units, or physical models to make a run complete without explaining the underlying failure.

## Failure Workflow

When something fails:

1. Reproduce the exact command or code path that failed.
2. Keep the original traceback, stderr, job log, or compiler log visible.
3. Inspect the real cause: interpreter, package versions, paths, permissions, environment variables, config files, input data schema, scheduler resources, or node-specific state.
4. Fix the root cause directly.
5. Add or update a focused test/check when the failure could recur.
6. Report what failed, why it failed, and what changed.

## Cross-Environment Rules

Apply the same rule on local Mac and on servers.

- On local Mac: verify the active shell, `$PATH`, Python/Conda/uv environment, TeX installation, filesystem path, and permissions before changing code.
- On remote servers: verify SSH host, working directory, project environment, modules, permissions, storage mount, and scheduler context.
- On SLURM clusters: inspect submission output, allocation, node logs, stdout/stderr, exit code, walltime, memory, CPU count, and environment activation. If a job must run on a compute node, do not move it to the login node as a workaround.

## Allowed Exceptions

A fallback is allowed only when the user explicitly asks for graceful degradation, or when an existing product requirement already defines it.

Even then, make it observable and testable:

- Name the failure condition precisely.
- Log or surface the fallback path clearly.
- Keep the original error available.
- Add a test that proves both the normal path and fallback path behave as intended.
- Avoid changing scientific meaning or hiding missing data.

## Review Behavior

When reviewing existing code, flag fallback paths that could hide broken environments, missing data, failed jobs, failed imports, or physically invalid results. Recommend root-cause fixes instead of additional fallback layers.

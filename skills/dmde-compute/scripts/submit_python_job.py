#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_SCRIPT = SKILL_DIR / "scripts" / "benchmark_nodes.py"
DEFAULT_CACHE_DIR = Path.home() / ".codex" / "local" / "dmde-compute"
THREAD_ENV_VARS = [
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
]
PREFERRED_PARALLEL_FLAGS = [
    "--workers",
    "--n-workers",
    "--pipeline-workers",
    "--max-workers",
    "--num-workers",
    "--n-jobs",
    "--jobs",
    "--n-processes",
    "--processes",
    "--n-threads",
    "--threads",
    "--cpus",
    "--n-cpus",
]
PARALLEL_NAME_RE = re.compile(
    r"(?:^|_)(?:workers?|n_workers?|pipeline_workers?|max_workers?|num_workers?|jobs?|n_jobs?|processes?|n_processes?|threads?|n_threads?|cpus?|n_cpus?)(?:$|_)"
)


@dataclass
class NodeCandidate:
    node: str
    partition: str
    cpu_model: str
    total_cpus: int
    benchmark: float
    source: str
    state: str
    idle_cpus: int
    free_mem_gib: float
    usable_cpus: int
    resource_score: float


@dataclass
class ParallelInspection:
    supported_flags: list[str]
    uses_slurm_env_default: bool
    uses_process_parallelism: bool
    uses_thread_parallelism: bool


@dataclass
class ParallelAlignment:
    final_args: list[str]
    adjusted: bool
    chosen_flag: str | None
    reason: str
    exported_env: dict[str, str]


def load_table(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(item["node"]): item for item in payload["nodes"]}


def default_table_path() -> Path:
    cache_dir = Path(os.environ.get("CODEX_DMDE_COMPUTE_CACHE_DIR", str(DEFAULT_CACHE_DIR))).expanduser()
    return cache_dir / "node_benchmarks.json"


def generate_benchmark_table(
    table_path: Path,
    project_root: Path,
    python_path: Path,
    benchmark_timeout_seconds: int,
    baseline_node: str | None,
) -> None:
    table_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(BENCHMARK_SCRIPT),
        "--project-root",
        str(project_root),
        "--python",
        str(python_path),
        "--output",
        str(table_path),
        "--benchmark-timeout-seconds",
        str(benchmark_timeout_seconds),
    ]
    if baseline_node is not None:
        cmd.extend(["--baseline-node", baseline_node])
    subprocess.run(cmd, check=True)


def ensure_benchmark_table(
    table_path: Path,
    project_root: Path,
    python_path: Path,
    refresh: bool,
    no_auto_benchmark: bool,
    benchmark_timeout_seconds: int,
    baseline_node: str | None,
) -> Path:
    table_path = table_path.expanduser().resolve()
    if table_path.exists() and not refresh:
        return table_path
    if no_auto_benchmark:
        raise FileNotFoundError(
            f"Benchmark table not available at {table_path}. "
            "Remove --no-auto-benchmark or provide --table pointing to an existing table."
        )
    generate_benchmark_table(
        table_path=table_path,
        project_root=project_root,
        python_path=python_path,
        benchmark_timeout_seconds=benchmark_timeout_seconds,
        baseline_node=baseline_node,
    )
    return table_path


def query_sinfo() -> dict[str, dict[str, object]]:
    result = subprocess.run(
        ["sinfo", "-N", "-h", "-o", "%N|%t|%C|%P|%e"],
        check=True,
        capture_output=True,
        text=True,
    )
    nodes: dict[str, dict[str, object]] = {}
    for line in result.stdout.splitlines():
        node, state, cpu_field, partition, free_mem_mb = line.strip().split("|")
        alloc_s, idle_s, other_s, total_s = cpu_field.split("/")
        nodes[node] = {
            "state": state,
            "alloc": int(alloc_s),
            "idle": int(idle_s),
            "other": int(other_s),
            "total": int(total_s),
            "partition": partition.rstrip("*"),
            "free_mem_gib": float(free_mem_mb) / 1024.0,
        }
    return nodes


def build_candidates(
    table: dict[str, dict[str, object]],
    cpu_fraction: float,
    min_available_mem_gib: float,
) -> list[NodeCandidate]:
    live = query_sinfo()
    candidates: list[NodeCandidate] = []
    for node, item in table.items():
        if node not in live:
            continue
        state = str(live[node]["state"])
        idle_cpus = int(live[node]["idle"])
        free_mem_gib = float(live[node]["free_mem_gib"])
        usable_cpus = max(0, math.floor(idle_cpus * cpu_fraction))
        state_l = state.lower()
        if free_mem_gib < min_available_mem_gib or "down" in state_l or "drain" in state_l or state_l.startswith("dr"):
            usable_cpus = 0
        candidates.append(
            NodeCandidate(
                node=node,
                partition=str(item["partition"]),
                cpu_model=str(item["cpu_model"]),
                total_cpus=int(item["total_cpus"]),
                benchmark=float(item["benchmark"]),
                source=str(item["source"]),
                state=state,
                idle_cpus=idle_cpus,
                free_mem_gib=free_mem_gib,
                usable_cpus=usable_cpus,
                resource_score=usable_cpus * float(item["benchmark"]),
            )
        )
    return candidates


def ranked_usable_candidates(candidates: list[NodeCandidate]) -> list[NodeCandidate]:
    usable = [item for item in candidates if item.usable_cpus > 0]
    if not usable:
        raise RuntimeError("No node satisfies the CPU and memory constraints.")
    usable.sort(
        key=lambda item: (item.resource_score, item.benchmark, item.usable_cpus, item.total_cpus),
        reverse=True,
    )
    return usable


def choose_best(candidates: list[NodeCandidate]) -> NodeCandidate:
    return ranked_usable_candidates(candidates)[0]


def effective_min_available_mem_gib(
    min_available_mem_gib: float,
    estimated_peak_rss_gib: float | None,
    memory_safety_factor: float,
) -> float:
    if memory_safety_factor < 1.0:
        raise ValueError("--memory-safety-factor must be >= 1.0")
    if estimated_peak_rss_gib is None:
        return min_available_mem_gib
    if estimated_peak_rss_gib < 0:
        raise ValueError("--estimated-peak-rss-gib must be >= 0")
    estimated_requirement = estimated_peak_rss_gib * memory_safety_factor
    return max(min_available_mem_gib, estimated_requirement)


def sbatch_memory_request_gib(effective_min_mem_gib: float) -> int | None:
    if effective_min_mem_gib < 0:
        raise ValueError("effective memory requirement must be >= 0")
    if effective_min_mem_gib == 0:
        return None
    return math.ceil(effective_min_mem_gib)


def parse_free_bg_available_gib(output: str) -> float:
    for line in output.splitlines():
        if not line.startswith("Mem:"):
            continue
        fields = line.split()
        if len(fields) < 7:
            raise RuntimeError(f"Could not parse MemAvailable from free output: {line}")
        value = fields[6]
        if value.endswith("Gi"):
            return float(value[:-2])
        if value.endswith("G"):
            return float(value[:-1])
        if value.endswith("Mi"):
            return float(value[:-2]) / 1024.0
        if value.endswith("M"):
            return float(value[:-1]) / 1024.0
        return float(value)
    raise RuntimeError("Could not find MemAvailable line in free output.")


def query_node_mem_available_gib(node: str, partition: str, timeout_seconds: int) -> float:
    result = subprocess.run(
        [
            "srun",
            "-p",
            partition,
            f"--nodelist={node}",
            "-N1",
            "-n1",
            "-c1",
            "--time=00:01:00",
            "bash",
            "-lc",
            "free -BG | sed -n '1,2p'",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return parse_free_bg_available_gib(result.stdout)


def should_verify_node_memory(mode: str, min_available_mem_gib: float) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    if mode == "auto":
        return min_available_mem_gib > 0
    raise ValueError(f"Unknown node memory check mode: {mode}")


def choose_best_with_live_memory(
    candidates: list[NodeCandidate],
    min_available_mem_gib: float,
    node_memory_check: str,
    node_memory_timeout_seconds: int,
) -> NodeCandidate:
    ranked = ranked_usable_candidates(candidates)
    if not should_verify_node_memory(node_memory_check, min_available_mem_gib):
        return ranked[0]

    checked: list[str] = []
    for candidate in ranked:
        available = query_node_mem_available_gib(
            candidate.node, candidate.partition, node_memory_timeout_seconds
        )
        checked.append(f"{candidate.node}={available:.1f}GiB")
        if available >= min_available_mem_gib:
            candidate.free_mem_gib = available
            return candidate

    raise RuntimeError(
        "No ranked node passed live MemAvailable verification. "
        f"Required {min_available_mem_gib:.1f} GiB; checked {', '.join(checked)}."
    )


def resolve_python(project_root: Path, override: str | None) -> Path:
    if override is not None:
        return Path(override).expanduser().absolute()
    candidate = project_root / ".venv" / "bin" / "python"
    if not candidate.exists():
        raise FileNotFoundError(f"Expected project interpreter at {candidate}")
    return candidate.absolute()


def reserve_outputs_dir(project_root: Path) -> Path:
    outputs = project_root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    return outputs


def extract_argparse_flags(script_text: str) -> list[str]:
    try:
        tree = ast.parse(script_text)
    except SyntaxError:
        return []
    flags: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "add_argument":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("-"):
                flags.append(arg.value)
    return flags


def is_parallel_flag(flag: str) -> bool:
    normalized = flag.lstrip("-").replace("-", "_")
    return bool(PARALLEL_NAME_RE.search(normalized))


def inspect_parallel_interfaces(script_path: Path) -> ParallelInspection:
    script_text = script_path.read_text(encoding="utf-8", errors="ignore")
    discovered_flags = extract_argparse_flags(script_text)
    worker_flags = [flag for flag in discovered_flags if flag.startswith("--") and is_parallel_flag(flag)]
    ordered_flags = [flag for flag in PREFERRED_PARALLEL_FLAGS if flag in worker_flags]
    ordered_flags.extend(flag for flag in worker_flags if flag not in ordered_flags)
    uses_slurm_env_default = "SLURM_CPUS_PER_TASK" in script_text
    uses_process_parallelism = any(
        token in script_text
        for token in ("ProcessPoolExecutor", "multiprocessing", "Pool(", "concurrent.futures.ProcessPoolExecutor")
    )
    uses_thread_parallelism = any(
        token in script_text
        for token in ("ThreadPoolExecutor", "threading", "concurrent.futures.ThreadPoolExecutor")
    )
    return ParallelInspection(
        supported_flags=ordered_flags,
        uses_slurm_env_default=uses_slurm_env_default,
        uses_process_parallelism=uses_process_parallelism,
        uses_thread_parallelism=uses_thread_parallelism,
    )


def find_flag_occurrence(args: list[str], flag: str) -> tuple[int, int] | None:
    for index, arg in enumerate(args):
        if arg == flag:
            return index, 2
        if arg.startswith(flag + "="):
            return index, 1
    return None


def set_flag_value(args: list[str], flag: str, value: int) -> tuple[list[str], bool]:
    updated = list(args)
    occurrence = find_flag_occurrence(updated, flag)
    rendered = str(value)
    if occurrence is None:
        updated.extend([flag, rendered])
        return updated, True
    index, width = occurrence
    if width == 2:
        current = updated[index + 1] if index + 1 < len(updated) else None
        updated[index + 1] = rendered
        return updated, current != rendered
    current = updated[index].split("=", 1)[1]
    updated[index] = f"{flag}={rendered}"
    return updated, current != rendered


def build_runtime_env(allocated_cpus: int, inspection: ParallelInspection) -> dict[str, str]:
    if inspection.uses_process_parallelism and not inspection.uses_thread_parallelism:
        thread_count = 1
    else:
        thread_count = max(1, allocated_cpus)
    env = {"SLURM_CPUS_PER_TASK": str(allocated_cpus)}
    for name in THREAD_ENV_VARS:
        env[name] = str(thread_count)
    return env


def align_parallelism(
    script_path: Path,
    script_args: list[str],
    allocated_cpus: int,
    mode: str = "add-missing",
) -> ParallelAlignment:
    if mode not in {"add-missing", "force", "none"}:
        raise ValueError(f"Unknown parallelism mode: {mode}")

    inspection = inspect_parallel_interfaces(script_path)
    updated_args = list(script_args)
    chosen_flag: str | None = None
    adjusted = False

    explicit_parallel_flags = [flag for flag in inspection.supported_flags if find_flag_occurrence(updated_args, flag)]
    if mode == "none":
        reason = "parallel alignment disabled"
    elif explicit_parallel_flags and mode == "force":
        chosen_flag = explicit_parallel_flags[0]
        updated_args, adjusted = set_flag_value(updated_args, chosen_flag, allocated_cpus)
        reason = f"forced {chosen_flag} to allocated cpus"
    elif explicit_parallel_flags:
        chosen_flag = explicit_parallel_flags[0]
        reason = f"preserved explicit {chosen_flag}"
    elif inspection.supported_flags:
        chosen_flag = inspection.supported_flags[0]
        updated_args, adjusted = set_flag_value(updated_args, chosen_flag, allocated_cpus)
        reason = f"added {chosen_flag} to match allocated cpus"
    elif inspection.uses_slurm_env_default:
        reason = "script already reads SLURM_CPUS_PER_TASK by default"
    else:
        reason = "no explicit script-level parallel flag detected"

    env = build_runtime_env(allocated_cpus, inspection)
    if inspection.uses_process_parallelism and not inspection.uses_thread_parallelism:
        reason += "; pinned BLAS/OpenMP thread env vars to 1 to avoid nested oversubscription"
    else:
        reason += "; exported thread env vars to allocated cpus"

    return ParallelAlignment(
        final_args=updated_args,
        adjusted=adjusted,
        chosen_flag=chosen_flag,
        reason=reason,
        exported_env=env,
    )


def build_sbatch_command(
    job_name: str,
    partition: str,
    node: str,
    cpus: int,
    time_limit: str,
    stdout_path: Path,
    stderr_path: Path,
    project_root: Path,
    env_exports: str,
    command_string: str,
    sbatch_mem_gib: int | None,
) -> list[str]:
    command = [
        "sbatch",
        f"--job-name={job_name}",
        f"--partition={partition}",
        f"--nodelist={node}",
        "--nodes=1",
        "--ntasks=1",
        f"--cpus-per-task={cpus}",
    ]
    if sbatch_mem_gib is not None:
        command.append(f"--mem={sbatch_mem_gib}G")
    command.extend(
        [
            f"--time={time_limit}",
            f"--output={stdout_path}",
            f"--error={stderr_path}",
            f"--wrap=cd {shlex.quote(str(project_root))} && export {env_exports} && {command_string}",
        ]
    )
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description="Choose the best SLURM node and submit a Python job.")
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--python", default=None, help="Override interpreter. Default: <project_root>/.venv/bin/python")
    parser.add_argument("--table", default=None)
    parser.add_argument("--refresh-benchmarks", action="store_true")
    parser.add_argument("--benchmark-timeout-seconds", type=int, default=180)
    parser.add_argument("--baseline-node", default=None)
    parser.add_argument("--no-auto-benchmark", action="store_true")
    parser.add_argument("--cpu-fraction", type=float, default=0.8)
    parser.add_argument("--time", default="12:00:00", help="SLURM wall time. Default: 12:00:00")
    parser.add_argument(
        "--min-available-mem-gib",
        type=float,
        default=0.0,
        help="Require the selected node to report at least this much live available memory from sinfo FREE_MEM.",
    )
    parser.add_argument(
        "--estimated-peak-rss-gib",
        type=float,
        default=None,
        help="Estimated peak resident memory from a profiling run. Combined with --memory-safety-factor.",
    )
    parser.add_argument(
        "--memory-safety-factor",
        type=float,
        default=1.5,
        help="Multiplier applied to --estimated-peak-rss-gib. Default: 1.5",
    )
    parser.add_argument(
        "--node-memory-check",
        choices=("auto", "always", "never"),
        default="auto",
        help="Verify selected candidates with srun free -BG. auto checks when an effective memory limit is set.",
    )
    parser.add_argument("--node-memory-timeout-seconds", type=int, default=120)
    parser.add_argument(
        "--parallelism-mode",
        choices=("add-missing", "force", "none"),
        default="add-missing",
        help="add-missing preserves explicit worker flags; force overwrites them; none only exports env vars.",
    )
    parser.add_argument(
        "--no-align-parallelism",
        action="store_true",
        help="Compatibility alias for --parallelism-mode none.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("script")
    parser.add_argument("script_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    python_path = resolve_python(project_root, args.python)
    table_path = Path(args.table).expanduser().resolve() if args.table is not None else default_table_path().resolve()
    table_path = ensure_benchmark_table(
        table_path,
        project_root=project_root,
        python_path=python_path,
        refresh=args.refresh_benchmarks,
        no_auto_benchmark=args.no_auto_benchmark,
        benchmark_timeout_seconds=args.benchmark_timeout_seconds,
        baseline_node=args.baseline_node,
    )
    table = load_table(table_path)
    effective_min_mem_gib = effective_min_available_mem_gib(
        args.min_available_mem_gib,
        args.estimated_peak_rss_gib,
        args.memory_safety_factor,
    )
    candidates = build_candidates(table, args.cpu_fraction, effective_min_mem_gib)
    best = choose_best_with_live_memory(
        candidates,
        effective_min_mem_gib,
        args.node_memory_check,
        args.node_memory_timeout_seconds,
    )

    script_args = list(args.script_args)
    if script_args and script_args[0] == "--":
        script_args = script_args[1:]
    script_path = Path(args.script)
    if not script_path.is_absolute():
        script_path = (project_root / script_path).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    outputs_dir = reserve_outputs_dir(project_root)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stdout_path = outputs_dir / f"{args.job_name}_%j.out"
    stderr_path = outputs_dir / f"{args.job_name}_%j.err"
    info_path = outputs_dir / f"{args.job_name}_submit_{timestamp}.txt"

    parallelism_mode = "none" if args.no_align_parallelism else args.parallelism_mode
    alignment = align_parallelism(script_path, script_args, best.usable_cpus, parallelism_mode)

    command = [str(python_path), str(script_path), *alignment.final_args]
    command_string = shlex.join(command)
    env_exports = " ".join(f"{name}={shlex.quote(value)}" for name, value in alignment.exported_env.items())
    sbatch_mem_gib = sbatch_memory_request_gib(effective_min_mem_gib)
    sbatch_mem_label = f"{sbatch_mem_gib}G" if sbatch_mem_gib is not None else "none"
    sbatch_cmd = build_sbatch_command(
        job_name=args.job_name,
        partition=best.partition,
        node=best.node,
        cpus=best.usable_cpus,
        time_limit=args.time,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        project_root=project_root,
        env_exports=env_exports,
        command_string=command_string,
        sbatch_mem_gib=sbatch_mem_gib,
    )
    info_text = "\n".join(
        [
            f"job_name: {args.job_name}",
            f"selected_node: {best.node}",
            f"selected_partition: {best.partition}",
            f"cpu_model: {best.cpu_model}",
            f"cpu_model_source: {best.source}",
            f"idle_cpus_now: {best.idle_cpus}",
            f"free_mem_gib_now: {best.free_mem_gib:.3f}",
            f"total_cpus: {best.total_cpus}",
            f"usable_cpu_fraction: {args.cpu_fraction}",
            f"min_available_mem_gib: {args.min_available_mem_gib}",
            f"estimated_peak_rss_gib: {args.estimated_peak_rss_gib}",
            f"memory_safety_factor: {args.memory_safety_factor}",
            f"effective_min_available_mem_gib: {effective_min_mem_gib}",
            f"node_memory_check: {args.node_memory_check}",
            f"sbatch_mem: {sbatch_mem_label}",
            f"slurm_time: {args.time}",
            f"allocated_cpus: {best.usable_cpus}",
            f"benchmark: {best.benchmark}",
            f"resource_score: {best.resource_score}",
            f"project_root: {project_root}",
            f"python: {python_path}",
            f"benchmark_table: {table_path}",
            f"script: {script_path}",
            f"stdout_pattern: {stdout_path}",
            f"stderr_pattern: {stderr_path}",
            f"parallel_flag: {alignment.chosen_flag or 'none'}",
            f"parallel_aligned: {alignment.adjusted}",
            f"parallel_reason: {alignment.reason}",
            "exported_env: " + ", ".join(f"{name}={value}" for name, value in alignment.exported_env.items()),
            f"command: {command_string}",
            f"sbatch_command: {shlex.join(sbatch_cmd)}",
        ]
    )
    info_path.write_text(info_text + "\n", encoding="utf-8")

    print(f"Selected node: {best.node}")
    print(f"Partition: {best.partition}")
    print(f"CPU model: {best.cpu_model}")
    print(f"Idle CPUs now: {best.idle_cpus}")
    print(f"Free memory now: {best.free_mem_gib:.1f} GiB")
    print(f"Effective memory requirement: {effective_min_mem_gib:.1f} GiB")
    print(f"SBATCH memory request: {sbatch_mem_label}")
    print(f"Allocated CPUs: {best.usable_cpus}")
    print(f"Benchmark: {best.benchmark}")
    print(f"Resource score: {best.resource_score}")
    print(f"Parallel alignment: {alignment.reason}")
    print(f"Submission info: {info_path}")

    if args.dry_run:
        print(f"Command: {command_string}")
        print(f"SBATCH command: {shlex.join(sbatch_cmd)}")
        print("Dry run only. No job submitted.")
        return

    sbatch = subprocess.run(sbatch_cmd, check=True, capture_output=True, text=True)
    job_id = sbatch.stdout.strip().split()[-1]
    print(f"Submitted job: {job_id}")
    print(f"Stdout: {str(stdout_path).replace('%j', job_id)}")
    print(f"Stderr: {str(stderr_path).replace('%j', job_id)}")


if __name__ == "__main__":
    main()

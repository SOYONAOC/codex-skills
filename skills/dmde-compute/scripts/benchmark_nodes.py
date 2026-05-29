#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
import json
import shlex
import subprocess
from pathlib import Path


BENCHMARK_CODE = (
    "import math,time; "
    "n=5000000; "
    "t=time.perf_counter(); "
    "s=sum(math.sin(i*1e-6)*math.cos(i*1e-6)/(1.0+i*1e-6) for i in range(1,n+1)); "
    "dt=time.perf_counter()-t; "
    "print(f'elapsed_seconds={dt:.6f}'); "
    "print(f'checksum={s:.12f}')"
)


def is_unusable_state(state: str) -> bool:
    state_l = state.lower()
    return "down" in state_l or "drain" in state_l or state_l.startswith("dr")


def parse_sinfo_output(stdout: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        node, state, cpu_field, partition, free_mem_mb, memory_mb, gres = line.strip().split("|")
        alloc_s, idle_s, other_s, total_s = cpu_field.split("/")
        idle_cpus = int(idle_s)
        if idle_cpus <= 0 or is_unusable_state(state):
            continue
        rows.append(
            {
                "node": node,
                "state": state,
                "allocated_cpus": int(alloc_s),
                "idle_cpus": idle_cpus,
                "other_cpus": int(other_s),
                "total_cpus": int(total_s),
                "partition": partition.rstrip("*"),
                "slurm_free_mem_gib": float(free_mem_mb) / 1024.0,
                "slurm_memory_mib": int(memory_mb),
                "gres": gres,
            }
        )
    return rows


def discover_nodes() -> list[dict[str, object]]:
    cmd = ["sinfo", "-N", "-h", "-o", "%N|%t|%C|%P|%e|%m|%G"]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Node discovery failed.\n"
            f"Command: {shlex.join(cmd)}\n"
            f"Return code: {exc.returncode}\n"
            f"Stdout: {exc.stdout or ''}\n"
            f"Stderr: {exc.stderr or ''}"
        ) from exc
    return parse_sinfo_output(result.stdout)


def run_remote(node: str, partition: str, python_path: Path, timeout_seconds: int) -> tuple[str, float]:
    cmd = [
        "srun",
        "-p",
        partition,
        "-N1",
        "-n1",
        "-c1",
        "-w",
        node,
        "--overlap",
        "--time=00:02:00",
        "bash",
        "-lc",
        f"hostname; lscpu | grep 'Model name'; {shlex.quote(str(python_path))} -c {shlex.quote(BENCHMARK_CODE)}",
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Benchmark timed out for node {node} after {timeout_seconds} seconds.\n"
            f"Command: {shlex.join(cmd)}\n"
            f"Stdout: {exc.stdout or ''}\n"
            f"Stderr: {exc.stderr or ''}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Benchmark failed for node {node}.\n"
            f"Command: {shlex.join(cmd)}\n"
            f"Return code: {exc.returncode}\n"
            f"Stdout: {exc.stdout or ''}\n"
            f"Stderr: {exc.stderr or ''}"
        ) from exc
    cpu_model = ""
    elapsed = None
    for line in result.stdout.splitlines():
        if "Model name" in line:
            cpu_model = line.split(":", 1)[1].strip()
        if line.startswith("elapsed_seconds="):
            elapsed = float(line.split("=", 1)[1])
    if not cpu_model or elapsed is None:
        raise RuntimeError(
            f"Failed to parse benchmark output for node {node}.\n"
            f"Command: {shlex.join(cmd)}\n"
            f"Stdout: {result.stdout}\n"
            f"Stderr: {result.stderr}"
        )
    return cpu_model, elapsed


def probe_gpu(node: str, partition: str, timeout_seconds: int) -> dict[str, object]:
    cmd = [
        "srun",
        "-p",
        partition,
        "-N1",
        "-n1",
        "-c1",
        "-w",
        node,
        "--overlap",
        "--time=00:01:00",
        "bash",
        "-lc",
        "if ! command -v nvidia-smi >/dev/null 2>&1; then exit 0; fi; "
        "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
    if result.returncode != 0:
        return {
            "gpu_status": "probe_failed",
            "gpu_count": 0,
            "gpus": [],
            "gpu_probe_stderr": result.stderr.strip(),
        }
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return {"gpu_status": "no_gpu", "gpu_count": 0, "gpus": []}
    gpus = []
    for line in lines:
        name, memory_mb = [part.strip() for part in line.rsplit(",", 1)]
        gpus.append({"name": name, "memory_total_mb": int(memory_mb)})
    return {"gpu_status": "ok", "gpu_count": len(gpus), "gpus": gpus}


def normalize_benchmarks(entries: list[dict[str, object]], baseline_node: str | None) -> None:
    if not entries:
        raise RuntimeError("No benchmark entries to normalize.")
    if baseline_node is None:
        baseline = min(entries, key=lambda item: float(item["elapsed_seconds"]))
        source = "measured_fastest_baseline"
    else:
        matches = [item for item in entries if str(item["node"]) == baseline_node]
        if not matches:
            raise RuntimeError(f"Baseline node was not benchmarked: {baseline_node}")
        baseline = matches[0]
        source = "measured_explicit_baseline"
    baseline_elapsed = float(baseline["elapsed_seconds"])
    for entry in entries:
        entry["benchmark"] = round(10.0 * baseline_elapsed / float(entry["elapsed_seconds"]), 2)
        entry["benchmark_source"] = source
        entry["source"] = "measured"


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure single-core node benchmarks and write a JSON table.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--python", default=None, help="Override interpreter. Default: <project_root>/.venv/bin/python")
    parser.add_argument("--output", required=True)
    parser.add_argument("--nodes", nargs="*", default=None)
    parser.add_argument("--baseline-node", default=None)
    parser.add_argument("--benchmark-timeout-seconds", type=int, default=180)
    parser.add_argument("--gpu-probe-timeout-seconds", type=int, default=45)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    python_path = Path(args.python).expanduser().resolve() if args.python else (project_root / ".venv" / "bin" / "python").resolve()
    if not python_path.exists():
        raise FileNotFoundError(f"Expected interpreter at {python_path}")

    rows = discover_nodes()
    if args.nodes:
        allowed = set(args.nodes)
        rows = [row for row in rows if str(row["node"]) in allowed]
    if not rows:
        raise RuntimeError("No nodes with idle CPUs are available to benchmark.")

    measured_at = date.today().isoformat()
    node_entries: list[dict[str, object]] = []
    for row in rows:
        cpu_model, elapsed = run_remote(
            str(row["node"]),
            str(row["partition"]),
            python_path,
            args.benchmark_timeout_seconds,
        )
        gpu_info = probe_gpu(str(row["node"]), str(row["partition"]), args.gpu_probe_timeout_seconds)
        node_entries.append(
            {
                "node": str(row["node"]),
                "measured_at": measured_at,
                "partition": str(row["partition"]),
                "state": str(row["state"]),
                "cpu_model": cpu_model,
                "allocated_cpus": int(row["allocated_cpus"]),
                "idle_cpus": int(row["idle_cpus"]),
                "other_cpus": int(row["other_cpus"]),
                "total_cpus": int(row["total_cpus"]),
                "slurm_free_mem_gib": float(row["slurm_free_mem_gib"]),
                "slurm_memory_mib": int(row["slurm_memory_mib"]),
                "gres": str(row["gres"]),
                "elapsed_seconds": elapsed,
                **gpu_info,
            }
        )

    normalize_benchmarks(node_entries, args.baseline_node)

    payload = {
        "measured_at": measured_at,
        "benchmark_definition": {
            "description": "Single-core Python math benchmark normalized so selected baseline = 10.00",
            "python": str(python_path),
            "workload": "sum(sin(i*1e-6)*cos(i*1e-6)/(1+i*1e-6) for i=1..5,000,000)",
            "baseline_node": args.baseline_node or "fastest_measured_node",
        },
        "nodes": node_entries,
    }
    output_path = Path(args.output).resolve()
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()

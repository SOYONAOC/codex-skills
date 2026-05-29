from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_nodes.py"
SPEC = importlib.util.spec_from_file_location("benchmark_nodes", SCRIPT_PATH)
benchmark_nodes = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = benchmark_nodes
SPEC.loader.exec_module(benchmark_nodes)


class BenchmarkNodesTests(unittest.TestCase):
    def test_discover_nodes_parses_sinfo_and_skips_unusable_nodes(self) -> None:
        sinfo = "\n".join(
            [
                "fast-cpu-a|mix|1/191/0/192|fast*|106755|1|(null)",
                "drained-cpu-a|drain|0/0/36/36|cpu|641775|1|(null)",
                "draining-cpu-a|drng|0/8/0/8|cpu|641775|1|(null)",
                "down-cpu-a|down|0/36/0/36|cpu|639338|1|(null)",
                "busy-cpu-a|alloc|36/0/0/36|cpu|635434|1|(null)",
            ]
        )
        completed = subprocess.CompletedProcess(args=["sinfo"], returncode=0, stdout=sinfo, stderr="")

        with mock.patch.object(benchmark_nodes.subprocess, "run", return_value=completed):
            nodes = benchmark_nodes.discover_nodes()

        self.assertEqual([node["node"] for node in nodes], ["fast-cpu-a"])
        self.assertEqual(nodes[0]["partition"], "fast")
        self.assertEqual(nodes[0]["state"], "mix")
        self.assertEqual(nodes[0]["idle_cpus"], 191)
        self.assertEqual(nodes[0]["total_cpus"], 192)
        self.assertAlmostEqual(nodes[0]["slurm_free_mem_gib"], 106755 / 1024.0)
        self.assertEqual(nodes[0]["slurm_memory_mib"], 1)

    def test_discover_nodes_uses_slurm_compatible_sinfo_format(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["sinfo"],
            returncode=0,
            stdout="compute-a|idle|0/8/0/8|cpu*|64000|128000|(null)\n",
            stderr="",
        )

        with mock.patch.object(benchmark_nodes.subprocess, "run", return_value=completed) as run:
            benchmark_nodes.discover_nodes()

        self.assertEqual(
            run.call_args.args[0],
            ["sinfo", "-N", "-h", "-o", "%N|%t|%C|%P|%e|%m|%G"],
        )

    def test_run_remote_uses_slurm_20_srun_options(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["srun"],
            returncode=0,
            stdout=(
                "compute-a\n"
                "Model name: Generic CPU\n"
                "elapsed_seconds=2.000000\n"
                "checksum=1.0\n"
            ),
            stderr="",
        )

        with mock.patch.object(benchmark_nodes.subprocess, "run", return_value=completed) as run:
            cpu_model, elapsed = benchmark_nodes.run_remote(
                "compute-a",
                "cpu",
                Path("/project/.venv/bin/python"),
                timeout_seconds=30,
            )

        command = run.call_args.args[0]
        self.assertEqual(cpu_model, "Generic CPU")
        self.assertEqual(elapsed, 2.0)
        self.assertIn("srun", command)
        self.assertIn("--overlap", command)
        self.assertIn("-w", command)
        self.assertIn("compute-a", command)
        self.assertIn("--time=00:02:00", command)

    def test_normalize_benchmarks_uses_fastest_node_by_default(self) -> None:
        entries = [
            {"node": "fast", "elapsed_seconds": 1.0},
            {"node": "slow", "elapsed_seconds": 2.0},
        ]

        benchmark_nodes.normalize_benchmarks(entries, baseline_node=None)

        self.assertEqual(entries[0]["benchmark"], 10.0)
        self.assertEqual(entries[1]["benchmark"], 5.0)
        self.assertEqual(entries[0]["benchmark_source"], "measured_fastest_baseline")

    def test_normalize_benchmarks_supports_explicit_baseline(self) -> None:
        entries = [
            {"node": "fast", "elapsed_seconds": 1.0},
            {"node": "slow", "elapsed_seconds": 2.0},
        ]

        benchmark_nodes.normalize_benchmarks(entries, baseline_node="slow")

        self.assertEqual(entries[0]["benchmark"], 20.0)
        self.assertEqual(entries[1]["benchmark"], 10.0)
        self.assertEqual(entries[1]["benchmark_source"], "measured_explicit_baseline")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "submit_python_job.py"
SPEC = importlib.util.spec_from_file_location("submit_python_job", SCRIPT_PATH)
submit_python_job = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = submit_python_job
SPEC.loader.exec_module(submit_python_job)


class SubmitPythonJobTests(unittest.TestCase):
    def write_script(self, source: str) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        script = Path(tempdir.name) / "job.py"
        script.write_text(textwrap.dedent(source), encoding="utf-8")
        return script

    def test_explicit_parallel_flag_is_preserved_by_default(self) -> None:
        script = self.write_script(
            """
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("--workers", type=int)
            """
        )

        alignment = submit_python_job.align_parallelism(
            script, ["--workers", "4"], allocated_cpus=28, mode="add-missing"
        )

        self.assertEqual(alignment.final_args, ["--workers", "4"])
        self.assertFalse(alignment.adjusted)
        self.assertEqual(alignment.chosen_flag, "--workers")
        self.assertIn("preserved explicit --workers", alignment.reason)

    def test_force_parallelism_overrides_explicit_flag(self) -> None:
        script = self.write_script(
            """
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("--workers", type=int)
            """
        )

        alignment = submit_python_job.align_parallelism(
            script, ["--workers", "4"], allocated_cpus=28, mode="force"
        )

        self.assertEqual(alignment.final_args, ["--workers", "28"])
        self.assertTrue(alignment.adjusted)
        self.assertIn("forced --workers", alignment.reason)

    def test_missing_parallel_flag_is_added(self) -> None:
        script = self.write_script(
            """
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("--workers", type=int)
            """
        )

        alignment = submit_python_job.align_parallelism(script, [], allocated_cpus=12, mode="add-missing")

        self.assertEqual(alignment.final_args, ["--workers", "12"])
        self.assertTrue(alignment.adjusted)

    def test_estimated_peak_memory_sets_safety_margin(self) -> None:
        effective = submit_python_job.effective_min_available_mem_gib(
            min_available_mem_gib=100.0,
            estimated_peak_rss_gib=120.0,
            memory_safety_factor=1.5,
        )

        self.assertEqual(effective, 180.0)

    def test_sbatch_memory_request_rounds_effective_requirement_up_to_gib(self) -> None:
        self.assertIsNone(submit_python_job.sbatch_memory_request_gib(0.0))
        self.assertEqual(submit_python_job.sbatch_memory_request_gib(180.0), 180)
        self.assertEqual(submit_python_job.sbatch_memory_request_gib(180.1), 181)

    def test_build_sbatch_command_includes_memory_request_when_known(self) -> None:
        command = submit_python_job.build_sbatch_command(
            job_name="test-job",
            partition="cpu",
            node="compute-a",
            cpus=12,
            time_limit="01:00:00",
            stdout_path=Path("/tmp/test_%j.out"),
            stderr_path=Path("/tmp/test_%j.err"),
            project_root=Path("/project"),
            env_exports="OMP_NUM_THREADS=12",
            command_string="/project/.venv/bin/python job.py",
            sbatch_mem_gib=181,
        )

        self.assertIn("--mem=181G", command)

    def test_build_sbatch_command_omits_memory_request_when_unknown(self) -> None:
        command = submit_python_job.build_sbatch_command(
            job_name="test-job",
            partition="cpu",
            node="compute-a",
            cpus=12,
            time_limit="01:00:00",
            stdout_path=Path("/tmp/test_%j.out"),
            stderr_path=Path("/tmp/test_%j.err"),
            project_root=Path("/project"),
            env_exports="OMP_NUM_THREADS=12",
            command_string="/project/.venv/bin/python job.py",
            sbatch_mem_gib=None,
        )

        self.assertFalse(any(part.startswith("--mem=") for part in command))

    def test_parse_free_bg_memavailable(self) -> None:
        output = "              total        used        free      shared  buff/cache   available\nMem:           629G         72G        485G        1.0G         71G        557G\n"

        self.assertEqual(submit_python_job.parse_free_bg_available_gib(output), 557.0)

    def test_query_node_memory_uses_srun_and_parses_output(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["srun"],
            returncode=0,
            stdout="Mem:           629G         72G        485G        1.0G         71G        557G\n",
            stderr="",
        )
        with mock.patch.object(submit_python_job.subprocess, "run", return_value=completed) as run:
            available = submit_python_job.query_node_mem_available_gib("compute-a", "cpu", timeout_seconds=30)

        self.assertEqual(available, 557.0)
        command = run.call_args.args[0]
        self.assertIn("srun", command)
        self.assertIn("--nodelist=compute-a", command)
        self.assertIn("--time=00:01:00", command)
        self.assertIn("free -BG | sed -n '1,2p'", command)

    def test_query_sinfo_uses_slurm_compatible_format_and_strips_default_partition(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["sinfo"],
            returncode=0,
            stdout="compute-a|idle|0/8/0/8|cpu*|64000\n",
            stderr="",
        )

        with mock.patch.object(submit_python_job.subprocess, "run", return_value=completed) as run:
            nodes = submit_python_job.query_sinfo()

        self.assertEqual(
            run.call_args.args[0],
            ["sinfo", "-N", "-h", "-o", "%N|%t|%C|%P|%e"],
        )
        self.assertEqual(nodes["compute-a"]["partition"], "cpu")
        self.assertEqual(nodes["compute-a"]["idle"], 8)

    def test_default_table_path_uses_local_cache_env(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"CODEX_DMDE_COMPUTE_CACHE_DIR": "/tmp/codex-dmde-test-cache"},
            clear=False,
        ):
            path = submit_python_job.default_table_path()

        self.assertEqual(path, Path("/tmp/codex-dmde-test-cache") / "node_benchmarks.json")

    def test_ensure_table_generates_missing_cache(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        table_path = Path(tempdir.name) / "node_benchmarks.json"

        with mock.patch.object(submit_python_job, "generate_benchmark_table") as generate:
            resolved = submit_python_job.ensure_benchmark_table(
                table_path,
                project_root=Path("/project"),
                python_path=Path("/project/.venv/bin/python"),
                refresh=False,
                no_auto_benchmark=False,
                benchmark_timeout_seconds=30,
                baseline_node=None,
            )

        self.assertEqual(resolved, table_path)
        generate.assert_called_once_with(
            table_path=table_path,
            project_root=Path("/project"),
            python_path=Path("/project/.venv/bin/python"),
            benchmark_timeout_seconds=30,
            baseline_node=None,
        )

    def test_ensure_table_reuses_existing_cache(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        table_path = Path(tempdir.name) / "node_benchmarks.json"
        table_path.write_text('{"nodes": []}\n', encoding="utf-8")

        with mock.patch.object(submit_python_job, "generate_benchmark_table") as generate:
            resolved = submit_python_job.ensure_benchmark_table(
                table_path,
                project_root=Path("/project"),
                python_path=Path("/project/.venv/bin/python"),
                refresh=False,
                no_auto_benchmark=False,
                benchmark_timeout_seconds=30,
                baseline_node=None,
            )

        self.assertEqual(resolved, table_path)
        generate.assert_not_called()

    def test_ensure_table_refreshes_existing_cache(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        table_path = Path(tempdir.name) / "node_benchmarks.json"
        table_path.write_text('{"nodes": []}\n', encoding="utf-8")

        with mock.patch.object(submit_python_job, "generate_benchmark_table") as generate:
            submit_python_job.ensure_benchmark_table(
                table_path,
                project_root=Path("/project"),
                python_path=Path("/project/.venv/bin/python"),
                refresh=True,
                no_auto_benchmark=False,
                benchmark_timeout_seconds=30,
                baseline_node="nodeA",
            )

        generate.assert_called_once()

    def test_ensure_table_can_disable_auto_generation(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        table_path = Path(tempdir.name) / "node_benchmarks.json"

        with self.assertRaises(FileNotFoundError):
            submit_python_job.ensure_benchmark_table(
                table_path,
                project_root=Path("/project"),
                python_path=Path("/project/.venv/bin/python"),
                refresh=False,
                no_auto_benchmark=True,
                benchmark_timeout_seconds=30,
                baseline_node=None,
            )

    def test_build_candidates_skips_live_down_drain_and_no_idle_nodes(self) -> None:
        table = {
            name: {
                "partition": "cpu",
                "cpu_model": "Generic CPU",
                "total_cpus": 16,
                "benchmark": 8.0,
                "source": "measured",
            }
            for name in ("usable-a", "drain-a", "down-a", "busy-a")
        }
        live = {
            "usable-a": {"state": "mix", "idle": 8, "free_mem_gib": 256.0},
            "drain-a": {"state": "drng", "idle": 8, "free_mem_gib": 256.0},
            "down-a": {"state": "down", "idle": 8, "free_mem_gib": 256.0},
            "busy-a": {"state": "mix", "idle": 0, "free_mem_gib": 256.0},
        }

        with mock.patch.object(submit_python_job, "query_sinfo", return_value=live):
            candidates = submit_python_job.build_candidates(table, cpu_fraction=0.5, min_available_mem_gib=0.0)

        usable_by_node = {candidate.node: candidate.usable_cpus for candidate in candidates}
        self.assertEqual(usable_by_node["usable-a"], 4)
        self.assertEqual(usable_by_node["drain-a"], 0)
        self.assertEqual(usable_by_node["down-a"], 0)
        self.assertEqual(usable_by_node["busy-a"], 0)


if __name__ == "__main__":
    unittest.main()

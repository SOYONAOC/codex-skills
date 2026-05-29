#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from datetime import datetime
from pathlib import Path


def resolve_python(project_root: Path, override: str | None) -> Path:
    if override is not None:
        return Path(override).expanduser().absolute()
    candidate = project_root / ".venv" / "bin" / "python"
    if not candidate.exists():
        raise FileNotFoundError(f"Expected project interpreter at {candidate}")
    return candidate.absolute()


def parse_max_rss_kib(stderr: str) -> int:
    prefix = "Maximum resident set size (kbytes):"
    for line in stderr.splitlines():
        if line.strip().startswith(prefix):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError("Could not parse maximum resident set size from /usr/bin/time -v output.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile a representative small Python run and report recommended DMDE memory headroom."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--python", default=None, help="Override interpreter. Default: <project_root>/.venv/bin/python")
    parser.add_argument("--memory-safety-factor", type=float, default=1.5)
    parser.add_argument("--output", default=None)
    parser.add_argument("script")
    parser.add_argument("script_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.memory_safety_factor < 1.0:
        raise ValueError("--memory-safety-factor must be >= 1.0")

    project_root = Path(args.project_root).resolve()
    python_path = resolve_python(project_root, args.python)
    script_args = list(args.script_args)
    if script_args and script_args[0] == "--":
        script_args = script_args[1:]
    script_path = Path(args.script)
    if not script_path.is_absolute():
        script_path = (project_root / script_path).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    command = [str(python_path), str(script_path), *script_args]
    timed_command = ["/usr/bin/time", "-v", *command]
    result = subprocess.run(
        timed_command,
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="")
        raise SystemExit(result.returncode)

    max_rss_kib = parse_max_rss_kib(result.stderr)
    max_rss_gib = max_rss_kib / 1024.0 / 1024.0
    recommended_min_available_mem_gib = max_rss_gib * args.memory_safety_factor
    payload = {
        "profiled_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "python": str(python_path),
        "script": str(script_path),
        "script_args": script_args,
        "command": shlex.join(command),
        "max_rss_kib": max_rss_kib,
        "max_rss_gib": max_rss_gib,
        "memory_safety_factor": args.memory_safety_factor,
        "recommended_min_available_mem_gib": recommended_min_available_mem_gib,
    }

    if args.output is None:
        outputs = project_root / "outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        output_path = outputs / f"{script_path.stem}_resource_profile_{datetime.now():%Y%m%d_%H%M%S}.json"
    else:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Max RSS: {max_rss_gib:.3f} GiB")
    print(f"Recommended --min-available-mem-gib: {recommended_min_available_mem_gib:.3f}")
    print(f"Profile: {output_path}")


if __name__ == "__main__":
    main()

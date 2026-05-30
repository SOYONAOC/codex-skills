# Codex Skills

Reusable Codex skills for research coding, Beamer slide workflows, scientific
plotting, SLURM compute submission, and local project conventions.

## Included Skills

- `ads-paper-search`: ADS/SciX and arXiv paper lookup workflow.
- `beamer`: Beamer slide creation, review, compilation, and polish workflow.
- `dmde-compute`: Local SLURM node discovery, profiling, and Python job submission.
- `enforce-no-fallbacks`: Fail-fast coding and debugging discipline.
- `physics-aware-plotting`: Scientific plotting rules with physically meaningful axes and limits.
- `project-venv-python`: Use a project's `.venv` Python consistently.
- `research-project-layout`: Research repository file layout conventions.

System-bundled Codex skills are not vendored here.

## Install

From a clone of this repository:

```bash
./install.sh
```

By default this installs to:

```text
${CODEX_HOME:-$HOME/.codex}/skills
```

Set `CODEX_HOME` to install into another Codex home:

```bash
CODEX_HOME=/path/to/codex-home ./install.sh
```

## Notes

- `dmde-compute` generates machine-specific SLURM benchmark caches under
  `${CODEX_DMDE_COMPUTE_CACHE_DIR:-~/.codex/local/dmde-compute}` at runtime.
- Runtime caches, local benchmark tables, Python bytecode, and virtual
  environments are intentionally not tracked.

## Validate

Run the repository checks before publishing changes:

```bash
python scripts/validate_skills.py
python skills/dmde-compute/tests/test_benchmark_nodes.py
python skills/dmde-compute/tests/test_submit_python_job.py
```

The validation script checks skill frontmatter, trigger descriptions, common
privacy/operational leak patterns, unsupported tool-name references, and the
Beamer main-entrypoint size.

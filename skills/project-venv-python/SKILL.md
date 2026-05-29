---
name: project-venv-python
description: Use when working in a code repository where Python work should run inside the project's uv-managed virtual environment at <project_root>/.venv. Prefer this skill for Python scripts, tests, package installs, one-off calculations, and other Python tooling so commands use <project_root>/.venv/bin/python and install missing packages into the project environment with uv rather than the system interpreter.
---

# Project .venv Python

Use this skill whenever a project keeps its Python environment in `<project_root>/.venv` and the task involves running Python code or Python-adjacent tools.

## Default Rule

- Treat the current working directory as the project root unless the repository context makes a different root obvious.
- Prefer `<project_root>/.venv/bin/python` for Python execution.
- Prefer `uv` for package installation and environment-aware dependency changes.
- If `uv pip` needs an explicit interpreter, target `<project_root>/.venv/bin/python`.
- Prefer `<project_root>/.venv/bin/python -m pytest` for tests.
- Prefer module execution through the interpreter, such as `<project_root>/.venv/bin/python -m package.module`, when that is a natural fit.
- Do not silently fall back to the system `python` when `.venv` is expected but missing. Surface the problem and either create the environment if the user asked for setup help or ask before changing the environment.

## Package Installation

- If a required Python package is missing, install it into the project's `.venv`, not the system environment.
- Prefer `uv add <package>` when the package should become a tracked project dependency.
- Prefer `uv add --dev <package>` when the missing package is a tracked development dependency such as `pytest`, `ruff`, or notebook tooling.
- Prefer `uv pip install --python <project_root>/.venv/bin/python <package>` when the package should be installed only into the current environment without editing project dependency metadata.
- Run `uv` commands from the project root so they bind to the correct project and lockfile context.
- If the right choice between tracked dependency and environment-only install is unclear, prefer the tracked form when the codebase will keep using that package, and prefer `uv pip install` for one-off debugging helpers or explicitly temporary tools.
- If `uv` is unavailable but the task assumes a uv-managed project, surface that as an environment issue instead of switching package managers silently.

## Practical Use

- For one-off calculations or quick scripts, run them with `<project_root>/.venv/bin/python`.
- For project scripts that already assume a Python interpreter, prefer explicitly invoking them with `<project_root>/.venv/bin/python path/to/script.py`.
- For tools that expose console entry points inside the environment, prefer the interpreter form when available so the environment choice stays explicit.
- When another skill launches Python work, keep this same interpreter choice unless that skill gives a stronger project-specific rule.
- After installing a missing package, continue using the same project `.venv` for the rest of the task.

## Checks

- If `.venv/bin/python` exists, use it directly.
- If `.venv` is missing but `pyproject.toml` or other repo signals suggest the project should have one, treat that as a setup gap rather than permission to use the system interpreter.
- If a Python import or command fails because a package is missing, fix it with `uv add`, `uv add --dev`, or `uv pip install --python <project_root>/.venv/bin/python` as appropriate.
- If the task spans multiple commands, keep the same interpreter choice throughout so results are reproducible.

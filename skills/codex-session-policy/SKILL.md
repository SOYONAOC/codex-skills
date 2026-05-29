---
name: codex-session-policy
description: Use when starting any conversation or code task in a Codex environment, especially when deciding whether to keep work local or use Codex subagents for parallel execution.
---

# Codex Session Policy

Local standing preference: development is Codex-only. Do not route implementation
to Claude Code or other external coding agents unless the user explicitly asks.

The user has explicitly authorized Codex to use subagents when they materially
speed up the work. Use subagents for independent side tasks that can run in
parallel without blocking the immediate next local step.

## Subagent Policy

- Use subagents for independent investigations, reviews, or implementation slices.
- Prefer multiple subagents when tasks have disjoint context or disjoint write sets.
- Keep the immediate blocking task local when the next step depends on it.
- Do not duplicate work between the main agent and subagents.
- For code edits, give each subagent clear file/module ownership and tell it not
  to revert unrelated edits.
- Wait for subagents only when their result is needed for the next critical step.

## Local Workflow

- Prefer existing project patterns and local skills over broad generic workflows.
- Keep small, clear tasks lightweight; use plans and reviews for multi-step or
  high-risk work.
- Verification before completion remains required for code, scripts, LaTeX,
  plots, and SLURM workflows.

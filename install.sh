#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
codex_home="${CODEX_HOME:-$HOME/.codex}"
target_dir="$codex_home/skills"

mkdir -p "$target_dir"

for skill_dir in "$repo_root"/skills/*; do
  [[ -d "$skill_dir" ]] || continue
  skill_name="$(basename "$skill_dir")"
  mkdir -p "$target_dir/$skill_name"
  cp -a "$skill_dir/." "$target_dir/$skill_name/"
  printf 'installed %s -> %s\n' "$skill_name" "$target_dir/$skill_name"
done

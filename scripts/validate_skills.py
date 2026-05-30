#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
DESCRIPTION_MAX_CHARS = 500
BEAMER_SKILL_MAX_WORDS = 2500

DISALLOWED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"Zhu\s+Hourui",
        r"zhuhourui",
        r"/home/zhuhourui",
        r"\bNAOC\b",
        r"国家天文台",
        r"\bamd1\b",
        r"\bfat2\b",
        r"\bnode[1-7]\b",
        r"\bRTX\b",
        r"\bEPYC\b",
        r"Gold\s+6130",
        r"mcp__",
        r"AskUserQuestion",
        r"TaskCreate",
        r"TaskUpdate",
        r"TaskList",
        r"TaskGet",
        r"allowed-tools",
    )
]


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"{path}: unterminated YAML frontmatter")
    frontmatter = text[4:end]
    parsed: dict[str, str] = {}
    lines = frontmatter.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if ":" not in line:
            raise ValueError(f"{path}: invalid frontmatter line: {line!r}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value == "|":
            index += 1
            block: list[str] = []
            while index < len(lines) and (lines[index].startswith(" ") or not lines[index].strip()):
                block.append(lines[index].strip())
                index += 1
            parsed[key] = " ".join(part for part in block if part)
            continue
        parsed[key] = raw_value.strip('"')
        index += 1
    return parsed


def word_count(path: Path) -> int:
    return len(re.findall(r"\S+", path.read_text(encoding="utf-8")))


def main() -> int:
    errors: list[str] = []
    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    for path in skill_files:
        skill_name = path.parent.name
        try:
            frontmatter = parse_frontmatter(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        name = frontmatter.get("name", "")
        description = frontmatter.get("description", "")
        if name != skill_name:
            errors.append(f"{path}: frontmatter name {name!r} must match directory {skill_name!r}")
        if not description.startswith("Use when "):
            errors.append(f"{path}: description must start with 'Use when '")
        if len(description) > DESCRIPTION_MAX_CHARS:
            errors.append(
                f"{path}: description is {len(description)} chars; max is {DESCRIPTION_MAX_CHARS}"
            )

    for path in sorted(ROOT.rglob("*")):
        if path == Path(__file__).resolve():
            continue
        if ".git" in path.parts or path.is_dir():
            continue
        if path.suffix in {".pyc", ".pdf", ".png", ".jpg", ".jpeg"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in DISALLOWED_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path}: disallowed pattern {pattern.pattern!r}")

    beamer_skill = SKILLS_DIR / "beamer" / "SKILL.md"
    if beamer_skill.exists():
        count = word_count(beamer_skill)
        if count > BEAMER_SKILL_MAX_WORDS:
            errors.append(
                f"{beamer_skill}: {count} words; keep main skill <= {BEAMER_SKILL_MAX_WORDS} words"
            )
    beamer_agents = SKILLS_DIR / "beamer" / "AGENTS.md"
    if beamer_agents.exists():
        errors.append(f"{beamer_agents}: duplicate Beamer entrypoint; keep one SKILL.md plus references")

    if errors:
        print("Skill validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(skill_files)} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

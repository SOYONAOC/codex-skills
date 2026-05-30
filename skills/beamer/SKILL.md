---
name: beamer
description: Use when working on Beamer or LaTeX .tex slide decks, including creating, compiling, reviewing, auditing, fixing TikZ diagrams, extracting paper figures, or generating academic slides from papers.
argument-hint: "[action] [file] - actions: create, compile, review, audit, pedagogy, tikz, excellence, devils-advocate, visual-check, validate, extract-figures"
---

# Beamer Slide Workflow

Universal skill for academic Beamer presentations:
create -> compile -> review -> polish -> verify.

Use this skill only for Beamer or LaTeX `.tex` slide decks. Do not use it for
PowerPoint/PPTX requests unless the user explicitly asks to convert or recreate
the deck in Beamer.

Detailed action rules live in `references/`:

- `references/create-workflow.md`: create decks from papers/materials, phase gates, slide density, figures, quality loop.
- `references/review-actions.md`: proofreading, audit, pedagogy, excellence, validate, visual-check, extract-figures.
- `references/tikz-standards.md`: TikZ quality standards, sizing rules, computed coordinates, SVG extraction.

## Default Style

Default new decks use the compact research-report style: Boadilla theme,
dark-blue structure, orange/green accents, large figures, concise evidence rows,
and no bundled institutional logos or banners. If the user provides a custom
template, preamble, header, or institutional asset, use that instead.

## Reference Preamble

Use this as the default preamble for new decks unless project context provides a
better template:

```latex
\documentclass[aspectratio=169,10pt]{beamer}

\usepackage{fontspec}
% For Chinese or mixed CJK/English decks, require an installed CJK font such as:
% \setmainfont{Noto Sans CJK SC}
% \setsansfont{Noto Sans CJK SC}
% \renewcommand{\familydefault}{\sfdefault}
\usefonttheme{professionalfonts}
\usetheme{Boadilla}
\setbeamertemplate{navigation symbols}{}
\setbeamertemplate{footline}[frame number]
\setbeamertemplate{itemize item}{\small$\blacktriangleright$}
\setbeamertemplate{itemize subitem}{\small$\circ$}

\usepackage{amsmath,amssymb,amsthm,booktabs,mathtools,array}
\usepackage{stmaryrd}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage[table]{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,calc,decorations.pathreplacing}

\graphicspath{{assets/}{../assets/}}

\definecolor{MainBlue}{HTML}{1F3A5F}
\definecolor{AccentOrange}{HTML}{DE8F05}
\definecolor{AccentGreen}{HTML}{029E73}
\definecolor{SoftBlue}{HTML}{EAF2FB}
\definecolor{SoftOrange}{HTML}{FFF1E6}
\definecolor{SoftGray}{HTML}{F5F7FA}
\definecolor{DarkGray}{HTML}{4A5568}
\colorlet{positive}{MainBlue}
\colorlet{negative}{AccentOrange}
\colorlet{emphasis}{AccentGreen}
\colorlet{neutral}{DarkGray}

\setbeamercolor{title}{fg=MainBlue}
\setbeamercolor{frametitle}{fg=MainBlue}
\setbeamercolor{structure}{fg=MainBlue}
\setbeamercolor{block title}{fg=white,bg=MainBlue}
\setbeamercolor{block body}{fg=black,bg=SoftGray}
\setbeamercolor{alerted text}{fg=AccentOrange}
\setbeamerfont{title}{series=\bfseries,size=\huge}
\setbeamerfont{institute}{series=\bfseries,size=\Large}
\setbeamerfont{frametitle}{series=\bfseries,size=\large}

\newcommand{\pos}[1]{\textcolor{MainBlue}{#1}}
\newcommand{\warn}[1]{\textcolor{AccentOrange}{#1}}
\newcommand{\key}[1]{\textcolor{AccentGreen}{#1}}
\newcommand{\con}[1]{\warn{#1}}
\newcommand{\HL}[1]{\key{#1}}
\newcommand{\reportitem}{\textcolor{AccentOrange}{\scriptsize$\blacktriangleright$}\hspace{0.24em}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
```

## Hard Rules

1. Use `aspectratio=169` and `10pt` unless the user or existing deck requires otherwise.
2. Use XeLaTeX by default; LuaLaTeX only when an existing deck requires it. Never switch engine or fonts silently.
3. For Chinese or mixed CJK/English decks, require an installed CJK font and report missing fonts explicitly.
4. Do not use overlays: no `\pause`, `\onslide`, `\only`, or `\uncover`. Duplicate frames for progressive disclosure.
5. Keep Beamer `.tex` as the source of truth for content, notation, and TikZ.
6. Every slide needs a substantive element: formula, diagram, table, theorem, algorithm, or figure.
7. Use telegraphic slide text; avoid long prose, repetitive negative framing, and bullets over two lines.
8. Use at most two colored boxes per slide. A box should contain one display equation or 2-3 short bullets, not both.
9. Avoid `\tiny` for user-facing text. Use `\small` sparingly and `\footnotesize` only as a last resort.
10. Put key cited works on a References slide before the Thank You slide.
11. Put backup slides after Thank You with `\appendix` when the deck needs anticipated-question material.
12. Verify every edit by compiling, checking logs, and visually inspecting modified slides.

## Actions

`compile [file]`: run XeLaTeX/bibtex passes as needed, inspect logs for overfull boxes,
undefined references/citations, and visually check the PDF.

`create [topic]`: follow `references/create-workflow.md`. Read source material
before asking questions, produce an outline for approval, draft in batches, and
run the quality loop before delivery.

`review [file]` / `proofread [file]`: read-only report for grammar, typos,
overflow risks, consistency, citation use, notation, and academic clarity.

`audit [file]`: visual layout audit for spacing, box fatigue, font hierarchy,
tables, equations, figures, and slide-level balance.

`pedagogy [file]`: check motivation-before-formalism, worked examples,
incremental notation, narrative arc, visual rhythm, and cognitive load.

`tikz [file]`: use `references/tikz-standards.md`; require no label overlaps,
computed plotted points, exact reference lines, and diagrams that fit the slide.

`excellence [file]`: comprehensive review. Use parallel review only when the
current environment and user request explicitly permit it; otherwise do the
review locally and synthesize visual, pedagogy, proofreading, TikZ, and domain
findings.

`devils-advocate [file]`: challenge ordering, prerequisites, gaps, alternative
presentations, notation conflicts, cognitive load, and standalone readability.

`visual-check [file]`: compile if needed, convert/view PDF pages, and inspect
each modified slide for overflow, legibility, contrast, table/equation fit, and
TikZ collisions.

`validate [file] [duration]`: check slide count vs. duration, aspect ratio,
file size, log health, overlays, `\tiny`, and references-slide presence.

`extract-figures [pdf] [pages]`: use available PDF tooling or local scripts to
extract figures, preserve attribution, avoid rasterized tables, and verify
cropping after compilation.

## Verification

Before reporting completion:

```text
[ ] xelatex/lualatex exited successfully
[ ] no undefined control sequences, citations, or references
[ ] no overfull hbox/vbox that affects visible output
[ ] modified slides visually inspected in the PDF
[ ] assets used by the deck are present under the deck's asset path
```

## Troubleshooting

- `\llbracket` undefined: add `\usepackage{stmaryrd}` or define the symbol explicitly.
- `Font "..." not found`: verify with `fc-list`; report the missing font rather than silently switching.
- Block content visually overflows with no compiler warning: split content, shorten text, or remove display math from the block.
- Equations overflow: use `align` with line breaks or introduce intermediate variables before considering `\resizebox`.

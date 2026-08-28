# Detailed audit report template

Use this template when the user asks for a full account of the investigation or when a
claim has multiple provenance or implementation layers. Omit empty sections rather than
filling them with generic prose.

## Scope

- Atomic claim or question
- Selected project model and version
- Species, energy or rigidity range, units, and conventions
- What would count as confirmation

## Short conclusion

State the answer, confidence level, and most important boundary in a compact paragraph.

## Decisive paper evidence

For each central passage, provide an evidence card with:

- a visibly embedded, tight crop from the same-version PDF, with the decisive passage
  marked by a restrained translucent highlight or border;
- paper title, stable identifier, version, page, section, equation, table, or figure;
- a short transcription checked against the active TeX source;
- **supports**: the atomic claim directly established by the passage;
- **does not establish**: nearby interpretations that require other evidence.

Do not use a metadata record, search snippet, abstract, or source-only match as a
substitute for this evidence. A paper URL or clickable crop filename also does not
substitute for an inline image. Keep quotation and image scope no larger than needed.

Use this delivery form when local Markdown images are supported:

```markdown
![PDF evidence: paper ID, page N](/absolute/path/to/crop.png)
```

Verify the rendered image visually before including it. If the host cannot display an
image, mark the visual deliverable incomplete rather than presenting links as if they
satisfied the evidence-card requirement.

Use light purple (`#C4B5FD` at opacity `0.28`) with a medium-violet border (`#8B5CF6`)
by default on black-on-white papers. Preserve an unannotated companion crop and record
the raw and annotated hashes, rectangle coordinates, colors, opacity, and border width.
Avoid red unless the annotation specifically denotes a discrepancy or error, and avoid
green when it could be misread as scientific validation.

## Executed physical definition

Give the formula actually used by the selected implementation. Define every symbol and
unit. List all configuration fields, defaults, switches, and branch conditions that can
change it.

## Provenance chain

Show the adoption path from the active artifact to the paper that adopts the model and
then to the original paper, supplement, dataset, or author configuration that defines
the value. Mark any compatibility port or deliberate deviation.

## Evidence ledger

| Atomic claim | Evidence class | Source and exact locator | Supports | Does not establish |
|---|---|---|---|---|
| | | | | |

Use one row per claim. A source should not appear as independent corroboration if it
merely copies another row's source.

## Discrepancy ledger

For every mismatch, record:

- the two values or statements;
- whether each is active;
- version and model scope;
- unit and normalization differences;
- resolution, or the exact reason it remains unresolved.

## Focused checks

Record validators, small calculations, checksum checks, or source/config comparisons.
State their inputs and outputs and label them as reproduction results.

## Evidence manifest

Record enough provenance to reproduce every evidence card:

- paper title, arXiv identifier or DOI, and exact version;
- PDF and source URLs plus retrieval date;
- SHA-256 hashes of the PDF, source archive, unannotated crop, and annotated crop;
- renderer name and version, resolution, one-based PDF page, and crop coordinates;
- output filename and the source file/line or source-search locator;
- whether a human or visual inspection of the rendered crop was completed.
- highlight rectangle coordinates, fill and border colors, opacity, and border width.

Use `scripts/render_pdf_evidence.py` to render a crop and create the mechanical portion
of this manifest. Add source-archive provenance and inspection status separately.

## Audit trail

Summarize what was searched, which files and paper locations were opened, which citation
links were followed, and which candidate sources were rejected and why. Include failed
commands or missing evidence when they affected the investigation.

## Remaining uncertainty

Name missing artifacts, undocumented version changes, unresolved contradictions, and
the next evidence needed to raise confidence. Do not replace this section with a generic
disclaimer.

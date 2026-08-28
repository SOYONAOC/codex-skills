# Source-first, PDF-confirm workflow

Use this workflow whenever both paper source and a rendered PDF are available. The two
formats have different jobs; neither is a universal fallback for the other.

## 1. Lock identity and version

- Resolve title, authors, DOI, arXiv identifier, and version from authoritative
  metadata.
- Download the source archive and PDF for the exact same arXiv version. Record URLs,
  retrieval date, and SHA-256 hashes before reading.
- Treat publisher supplements, author configurations, code, and datasets as separate
  artifacts. Their absence from the arXiv bundle is not permission to infer them.

## 2. Inspect source safely

- Extract an untrusted source archive only in an isolated temporary directory.
- List archive members first and reject absolute paths, parent traversal, device files,
  and links that escape the extraction root.
- Identify the actual root document and follow active `input`, `include`, bibliography,
  and conditional paths. Ignore comments, discarded drafts, and inactive branches.
- Search for distinctive parameter names, units, equation fragments, table labels, and
  citation keys. Read enough surrounding source to capture definitions and scope.

Source is preferred for exact symbols, superscripts, units, table cells, citations, and
cross-file tracing. A source match alone does not prove that text survived compilation.

## 3. Confirm in the PDF

- Locate the same passage in PDF layout text, then open or render the relevant page.
- Verify the value, signs, exponents, units, table headers, footnotes, and surrounding
  qualifiers against the source.
- Use the PDF's printed page, section, equation, table, or figure identifier in the
  evidence locator. Record the file page separately if it differs from printed paging.
- If source and PDF disagree, stop and investigate version mismatch, compilation paths,
  late edits, macros, or extraction errors. Preserve the discrepancy in the report.

PDF confirmation establishes rendered publication content and visual context. It does
not by itself establish that a value is active in current code or scientifically unique.

## 4. Render evidence on a headless host

No desktop session or X server is required. Poppler renders PDF pages directly:

```bash
python scripts/render_pdf_evidence.py PAPER.pdf \
  --page 4 \
  --crop 120 640 1800 520 \
  --highlight 40 300 1680 55 \
  --output evidence/paper-page4-parameter.png \
  --paper-id arXiv:0000.00000v1 \
  --source-url https://arxiv.org/pdf/0000.00000v1 \
  --retrieved-date 2026-01-01
```

Crop coordinates are pixels at the requested rendering resolution. Start with a full
page when coordinates are unknown, inspect it, then make the final tight crop. Visually
inspect the final image for truncation, wrong columns, missing superscripts, and adjacent
text that changes the meaning. Call the artifact a **PDF page crop**, not a screenshot.

The script requires `pdfinfo` and `pdftoppm`, refuses silent tool substitution, checks
the page range, writes a JSON sidecar containing hashes and render parameters, and
prints a ready-to-use Markdown image block with the absolute PNG path.

Highlight coordinates are relative to the final cropped image, not the full PDF page.
Use repeatable `--highlight X Y WIDTH HEIGHT` arguments for disjoint passages. The
default treatment is a translucent warm-yellow fill (`#FFD54F`, opacity `0.22`) with a
4-pixel amber border (`#D97706`). It is readable over black text, visually distinct from
blue hyperlinks, and does not imply error or approval as strongly as red or green.

Keep 6–12 pixels of padding around the decisive text when space permits. Do not cover a
whole paragraph when one phrase, equation, table row, or footnote is decisive. The
script preserves an unannotated `.raw.png` companion and records both hashes plus the
annotation geometry in the JSON manifest. Pillow is required only when highlights are
requested; a missing Pillow installation must fail visibly rather than producing an
unmarked substitute.

## 5. Assemble the evidence card

Present these parts together, with the crop displayed inline rather than linked:

1. the highlighted PDF crop, with the decisive region clearly marked;
2. a short transcription checked from active source;
3. the exact PDF and source locators;
4. the atomic claim the passage supports;
5. what the passage does not establish;
6. the provenance manifest and visual-inspection status.

Keep the unannotated companion crop available through the evidence manifest. The
highlight is a presentation overlay, not part of the source document.

Keep crops and quotations narrowly scoped. Prefer paraphrase for surrounding context.
If source, PDF, supplement, or implementation evidence is unavailable, name the missing
artifact and lower confidence; do not silently replace it with a weaker channel.

For Codex desktop, use this shape with the actual absolute output path:

```markdown
### Paper evidence — arXiv:0000.00000v1, PDF page 4

![PDF evidence: arXiv:0000.00000v1, page 4](/absolute/path/to/evidence.png)

- Source transcription: “short exact passage”
- Locator: section, equation/table, source file and line
- Supports: the atomic claim directly established here
- Does not establish: the interpretation requiring another source or code check
```

## 6. Pass the delivery gate

Before sending the final response:

- open every final crop with the available image-viewing mechanism;
- confirm that the relevant lines, symbols, units, footnotes, and column headings are
  legible and not clipped;
- confirm that the highlight surrounds the intended passage, does not obscure glyphs,
  and does not hide nearby qualifiers;
- confirm that each final crop appears as an image attachment or Markdown image block,
  not merely as a clickable filename or public URL;
- retain the public paper URL and provenance data alongside the image; and
- if inline image delivery is unsupported, state that the visual deliverable is
  incomplete and identify the generated crop path. Do not silently send links only.

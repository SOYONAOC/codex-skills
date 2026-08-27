---
name: paper-claim-audit
description: Use when verifying a scientific claim or numerical parameter by tracing it through the active project artifact, implementation semantics, primary literature, supplements, and cited predecessors. Applies to paper checking, parameter provenance, model-to-code comparisons, and questions where a plausible but weakly sourced answer would be harmful. Do not use for a routine paper summary that does not ask whether a claim is correct.
---

# Paper Claim Audit

Produce an auditable answer whose conclusion is no stronger than its evidence.
Treat the investigation as read-only unless the user separately authorizes edits,
downloads into a maintained data tree, or external actions.

## Define the claim

Turn the request into one or more atomic claims before searching. Distinguish:

- the general theoretical definition;
- the value stated or inherited by a paper;
- the value active in the current project;
- the implementation that converts configuration fields into a physical quantity;
- the scientific interpretation of that quantity.

Resolve ambiguous scope from the active repository when practical. State the chosen
model, version, configuration, species, units, and epoch. Ask the user only when a
reasonable scope choice would materially change the requested conclusion.

## Build the evidence chain

1. Inspect the current project artifact first when the question is project-specific.
   Identify the production configuration, executable or library version, validation
   contract, and any recorded provenance. Do not assume that a README describes the
   live configuration.
2. Resolve paper identity and version with ADS/SciX, DOI records, arXiv, or the
   publisher. Metadata services establish identity and publication metadata; they do
   not establish scientific content.
3. When arXiv source and PDF are available, use a **source-first, PDF-confirm** route.
   Search the active TeX source for exact equations, units, tables, citation keys, and
   included files, then verify the decisive passage in the same-version rendered PDF.
   Source is the efficient semantic reading channel; PDF establishes that the material
   appeared in the compiled paper and supplies stable page, table, figure, and visual
   context. Read [references/source-pdf-workflow.md](references/source-pdf-workflow.md)
   before acquiring or presenting paper evidence.
4. Read the relevant primary-paper section, equation, table, caption, supplement, or
   author-provided configuration. Trace inherited numbers through citations until the
   source that actually defines them is reached. A later paper can establish adoption
   of an earlier model but cannot by itself establish undocumented parameter values.
5. Inspect the implementation used by the active version. Reconstruct the executed
   formula from source code and configuration, including defaults, feature switches,
   branch conditions, normalization conventions, unit conversions, and spatial or
   species dependence.
6. Cross-check the resulting claim against at least one genuinely independent evidence
   path when available. A README copied from the same configuration is corroboration,
   not an independent source.
7. Run a focused calculation or validator when it can test the interpretation. Label
   the result as a reproduction or configuration check, not as a paper statement.

For a detailed audit report, use [references/report-template.md](references/report-template.md).

## Label evidence explicitly

Classify every central statement as one of:

- **Project artifact fact**: value read from the active configuration, output, or data;
- **Implementation fact**: behavior established by the relevant source-code path;
- **Paper statement**: claim made directly by the authors;
- **Cited input**: value or model inherited from another work;
- **Model assumption**: selected form, boundary, prior, or simplification;
- **Reproduction result**: quantity recomputed from documented inputs;
- **Current inference**: interpretation added during the audit.

Give an exact locator for decisive evidence: file and line, section, equation, table,
figure, appendix, supplement filename, DOI, arXiv version, or source revision.

For each decisive paper passage, prefer a compact evidence card containing a tight PDF
crop, a short source transcription, an exact locator, and two explicit fields:
**supports** and **does not establish**. On a headless host, use
`scripts/render_pdf_evidence.py`; call the result a PDF page crop, not a screenshot.

## Handle discrepancies without smoothing them away

- Preserve conflicting values and determine whether they reflect version drift,
  inactive parameters, differing units, different model variants, rounded values, or
  a genuine inconsistency.
- Check control switches before interpreting any nearby parameter. A populated value
  may be inactive.
- Distinguish an exact historical reproduction from a compatibility port, adaptation,
  or current production choice.
- If the evidence chain ends before the claim is established, report the conclusion as
  unresolved and name the missing artifact. Do not fill the gap from memory, a review,
  a search snippet, or a numerically convenient value.

## Misreport-prevention gates

Before answering, verify all applicable gates:

- The source was opened at the relevant passage; a search hit alone is insufficient.
- The arXiv source and PDF are the same explicit version, and the cited TeX belongs to
  the active compilation rather than a comment, discarded draft, or inactive branch.
- The PDF was checked for every source-derived claim presented as published content.
- The numerical value has units, normalization point, functional form, and validity
  range.
- Every active multiplier, exponent, switch, default, and branch in the implementation
  has been checked.
- Paper identity, version, and citation direction are correct.
- General framework behavior is not conflated with the selected configuration or model.
- A parameter printed in a file is not called fitted, observed, or recommended unless
  the source establishes that status.
- Any calculation uses the project's declared environment and fails visibly on missing
  dependencies or inputs.
- Evidence crops are visually inspected, tightly bounded, and accompanied by hashes
  and retrieval/render metadata. A crop is evidence of wording or layout, not proof of
  scientific truth.
- Confidence is reported as **confirmed**, **supported**, or **unresolved**, with the
  remaining limitation stated next to the conclusion.

## Answer shape

Lead with the scoped conclusion, confidence, and physical formula. Then give the PDF
evidence cards, source transcription and locator, provenance chain, current
configuration and implementation, independent checks, discrepancies, remaining
uncertainty, and evidence manifest. Keep quoted text short and paraphrase the rest.
Cite public sources near the claims they support and include local clickable file links
when working in a repository.

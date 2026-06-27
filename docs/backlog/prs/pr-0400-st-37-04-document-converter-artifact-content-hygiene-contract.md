---
type: pr
id: PR-0400
title: "ST-37-04 Document Converter artifact content hygiene contract"
status: ready
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
stories:
  - "ST-37-04"
tags:
  - backend
  - contracts
  - document-converter
  - sir-convert
dependencies:
  - "PR-0381"
  - "PR-0382"
  - "PR-0384"
  - "PR-0398"
  - "PR-0399"
acceptance_criteria:
  - "Given Document Converter renders or proxies a teacher-facing artifact, when the artifact is previewed, downloaded, or saved, then visible content and document metadata contain only source-derived content or approved product-owned metadata, never internal temporary filenames, checkpoint labels, raw job or artifact ids, private paths, debug comments, or generated missing-resource placeholders."
  - "Given an HTML/CSS project references a local image resource, when the uploaded project contains the matching source bytes, then the preview renderer uses those bytes rather than fabricating fallback visual content."
  - "Given an HTML/CSS project references an image resource with no recoverable uploaded bytes, when Document Converter attempts to render it, then the chosen product policy is applied consistently and never emits `Bild saknas`, `Saknad resurs`, `__missing_asset__`, or equivalent placeholder content into the artifact."
  - "Given Sir Convert emits a terminal artifact for a Document Converter flow, when Skriptoteket consumes it, then terminal artifact bytes and metadata are free of implementation stems such as `pdf_checkpointed_output` and checkpoint comments such as `sir-convert-a-lot:partial`."
  - "Given missing image metadata cannot be tied to real extracted or uploaded bytes, when PDF-to-DOCX or PDF-to-Markdown conversion completes, then the final teacher-facing artifact does not preserve that metadata as an implied recovery promise and the future recovery work is tracked separately."
  - "Given the researcher findings and user decision gate are complete, when implementation begins, then the PR document is updated with the accepted policy choices before code changes are made."
---

# PR-0400: ST-37-04 Document Converter Artifact Content Hygiene Contract

## Problem

Current Document Converter and Sir Convert conversion paths can leak
implementation detail into teacher-facing conversion artifacts. The observed
example is `pdf_checkpointed_output`, which comes from an internal Sir Convert
PDF checkpoint bridge and can become visible through Pandoc title fallback.

The audit also found a Skriptoteket-owned local preview issue: HTML/CSS project
preview fallback code can synthesize a visible "missing image" PNG containing
`Bild saknas` and `Saknad resurs`. That makes an implementation detail look
like source content.

This is not a filename protocol problem and should not be folded into
`PR-0396` or `ST-37-05`. It is an artifact-content boundary problem.

## Goal

Define and implement a maintainable artifact hygiene contract for Document
Converter flows:

- final teacher-facing artifacts must contain source-derived content, not
  implementation stems, checkpoint markers, debug comments, raw ids, private
  paths, or fabricated placeholder resources;
- Skriptoteket owns local HTML/CSS project preview hygiene and narrow boundary
  rejection for forbidden upstream artifact markers;
- Sir Convert owns terminal artifact cleanliness for heavy conversion paths;
- partial/checkpoint artifacts remain diagnostic or operator-facing only unless
  a separate sanitized export contract is approved;
- missing-image metadata is preserved only when it is tied to a concrete source
  or extracted-byte recovery path.

## Non-goals

- No broad converter rewrite.
- No tolerant scrubber that hides upstream contract violations while accepting
  dirty terminal artifacts as normal.
- No PDF-to-DOCX image reconstruction from a rendered PDF in this slice.
- No new Document Converter UI labels, eyebrows, or explanatory clutter.
- No ST-37-05 filename protocol changes.
- No production deploy, commit, or push unless explicitly requested after the
  reviewed implementation is accepted.

## Research Findings

Read-only research identified these initial offenders and boundaries:

1. Skriptoteket local project preview currently synthesizes missing-image
   content in `document_converter_project_previews.py` through
   `_fallback_asset_bytes()` and `_missing_image_placeholder_png()`. The source
   fetcher already resolves uploaded project bytes by declared filename, so
   unresolved image resources should be handled by policy instead of fabricated
   visible content.
2. Skriptoteket Sir Convert v2 consumption stores upstream artifact bytes
   unchanged. That is the right default; broad downstream post-processing would
   blur ownership. Skriptoteket may still add a narrow fail-closed guard for
   known forbidden terminal-artifact markers.
3. Sir Convert's PDF-to-DOCX bridge writes intermediate
   `pdf_checkpointed_output.md` and `.html` files. Pandoc HTML conversion can
   use `markdown_path.stem` as a fallback title, allowing the intermediate stem
   to enter visible artifact content or metadata.
4. Sir Convert partial artifacts intentionally include
   `sir-convert-a-lot:partial` checkpoint comments. That may be useful for
   recovery or operator diagnostics, but it must not be treated as a final
   teacher-facing artifact contract.
5. Programmatic PDF-to-DOCX image salvage is a separate feature. PyMuPDF can
   extract embedded images, but layout-aware DOCX reconstruction plus lifecycle
   policy is not a quick hygiene fix.

## Decision Gate

Implementation must not begin until these questions are answered or explicitly
accepted as assumptions:

1. Missing HTML/CSS project images: should a declared local image with no
   uploaded bytes fail the preview, or should the missing visual be omitted?
   Recommendation: fail closed for declared local images; block external or
   invalid resource references without fabricating a placeholder.
2. Bundle truth: if image bytes exist in the uploaded bundle but are not
   manifest-declared, should Document Converter use them? Recommendation:
   keep the `PR-0382` contract for bare manifest-declared filenames unless a
   separate bundle-discovery extension is approved.
3. Fallback document title: when Sir Convert has no YAML title or H1, should it
   use the source filename stem, blank metadata, or a neutral product title?
   User decision: if the document has no YAML title or H1, the converted
   document has no title. Do not synthesize a title from a source filename stem
   or product label.
4. Partial artifacts: is `/artifact/partial` ever teacher-facing in
   Skriptoteket? Recommendation: no; keep partial artifacts diagnostic or
   operator-facing only unless a separate sanitized export contract is created.
5. PDF image recovery: confirm that PDF-to-DOCX image reconstruction from
   rendered PDF output is out of scope here and belongs to a future linked
   artifact/recovery task.
   User decision: out of scope for this PR, but it must be planned as its own
   governed task.

### Missing Image Scenario

The missing-image case is limited to HTML/CSS project preview inputs. It occurs
when the teacher uploads an HTML/CSS project whose HTML or CSS references a
local image such as `cover.png`, but the uploaded project payload available to
the renderer does not contain recoverable bytes for that exact declared image.

That can happen when:

- the teacher uploads `index.html` and `styles.css` but not `cover.png`;
- CSS references an image path that is outside the governed project manifest;
- the path is malformed, external, or blocked by the preview renderer; or
- the UI/backend file grouping drifts so the renderer cannot match a declared
  filename to uploaded bytes.

The artifact-hygiene risk is that a generated PDF containing a fabricated
"missing image" graphic reads as if the source document itself contained that
graphic. The safe contract is therefore: render real uploaded bytes when they
exist; otherwise apply the accepted missing-image policy without adding visible
placeholder content to the artifact.

## Implementation Plan

1. Update this PR with the accepted decision-gate answers before code changes.
2. Add red-first tests for the current Skriptoteket missing-image placeholder
   behavior and the forbidden upstream marker boundary.
3. Replace local preview placeholder generation with the accepted missing-image
   policy. Real uploaded image bytes must still render.
4. Add a narrow artifact hygiene guard at the Skriptoteket/Sir Convert boundary
   for terminal artifacts consumed by Document Converter. It should reject known
   forbidden markers instead of silently sanitizing broad content.
5. Create or link the Sir Convert upstream task for terminal artifact
   cleanliness: source-derived/blank title policy, no temp stems in final
   HTML/DOCX/PDF metadata, and no partial checkpoint comments in final artifact
   bytes.
6. Ensure any operational checkpoint data lives in sidecar/operator metadata,
   not teacher-facing artifact content.

## Test Plan

- Focused Skriptoteket unit tests proving missing-image placeholders are no
  longer emitted into project-preview output.
- Focused Skriptoteket unit tests proving real uploaded image bytes still
  render in HTML/CSS project previews.
- Focused Skriptoteket boundary tests proving artifacts containing
  `pdf_checkpointed_output`, `sir-convert-a-lot:partial`, `__missing_asset__`,
  raw job/artifact ids, or equivalent forbidden markers fail closed before
  preview, download, or save.
- Focused Sir Convert tests proving Markdown-to-HTML and PDF-to-DOCX terminal
  artifacts do not derive title or metadata from internal temporary paths.
- Focused DOCX zip/core-properties proof that final `.docx` artifacts do not
  contain temp/checkpoint strings in visible text or `docProps/core.xml`.
- Relevant focused backend tests in Skriptoteket and Sir Convert.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Revert the artifact hygiene contract and code changes in Skriptoteket, then
restore the previous local preview fallback and upstream artifact proxying
behavior. Keep any separate Sir Convert upstream task intact unless its owner
also chooses to roll it back.

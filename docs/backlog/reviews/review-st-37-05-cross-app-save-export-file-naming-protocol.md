---
type: review
id: REV-ST-37-05
title: "Review: ST-37-05 cross-app save/export file naming protocol"
status: approved
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
reviewer: "codex"
stories:
  - "ST-37-05"
links:
  - "EPIC-37"
  - "PR-0390"
  - "PR-0391"
  - "PR-0392"
  - "PR-0393"
  - "PR-0394"
  - "PR-0395"
  - "PR-0396"
---

## TL;DR

The package is directionally strong: it correctly separates teacher-facing names
from source references, keeps PR-0385 from absorbing a cross-app concern, and
splits protocol/core/UI/app adoption into workable PR-sized slices. The
remediation passes close the original duplicate/collision, server-owned
filename, Swedish purpose-label, and Document Converter DOCX output-label
findings. No content findings remain, and the package is accepted after the
explicit 2026-06-27 owner instruction to flip the review to accepted.

## Problem Statement

Teachers need exported and saved files that are recognizable, editable, and
consistent across curated apps. The review checks whether ST-37-05 and its
planned PR slices define enough shared authority to prevent duplicate extension
bugs, browser-owned filenames, and app-by-app save/export drift.

## Proposed Solution

Use a reviewed reference protocol, then implement shared backend/domain naming
and validation, shared frontend name-editing primitives, `Mina filer` rename
behavior, and app-specific adoption slices for Audio Transcription, Exam
Converter, and Document Converter.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/stories/story-37-05-cross-app-save-export-file-naming-protocol.md` | Parent story scope and acceptance | 5 min |
| `docs/reference/ref-file-naming-save-export-protocol-v1.md` | Shared naming, save, export, and rename contract | 10 min |
| `docs/backlog/prs/pr-0390-st-37-05-file-naming-save-export-protocol-reference.md` | Reference closeout slice | 3 min |
| `docs/backlog/prs/pr-0391-st-37-05-shared-save-export-naming-backend-contract.md` | Backend/domain authority slice | 5 min |
| `docs/backlog/prs/pr-0392-st-37-05-shared-filename-editing-ui-primitives.md` | Shared UI primitive slice | 3 min |
| `docs/backlog/prs/pr-0393-st-37-05-mina-filer-rename-and-extension-contract.md` | Rename and extension preservation slice | 5 min |
| `docs/backlog/prs/pr-0394-st-37-05-audio-transcription-export-naming-adoption.md` | Transcript app adoption | 3 min |
| `docs/backlog/prs/pr-0395-st-37-05-exam-converter-export-naming-adoption.md` | Exam Converter app adoption | 3 min |
| `docs/backlog/prs/pr-0396-st-37-05-document-converter-save-export-naming-adoption.md` | Document Converter app adoption | 3 min |

**Total estimated time:** ~40 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep ST-37-05 separate from PR-0385 | Filename policy is cross-app and should not widen the Document Converter follow-up | [x] |
| Separate display names from source references | Names help teachers; source references preserve authority | [x] |
| Use shared backend/frontend primitives before app adoption | Prevents unnecessary app-specific drift | [x] |
| Define duplicate-save and rename-collision behavior before app adoption | Prevents route-by-route save/export drift | [x] |
| Require server-owned final filename proof | Preserves download/save parity and producer-replay trust boundaries | [x] |
| Centralize output-purpose vocabulary | Keeps user-facing filenames cohesive across apps | [x] |

## Review Checklist

- [x] Scope is bounded and appropriate
- [x] Acceptance criteria or proof obligations are reviewable
- [x] Risks and structural fault lines are called out explicitly
- [x] Verification plan matches the claimed contract
- [x] Shared contracts fully prevent avoidable app-specific drift
- [x] Owner accepted after all content findings were closed

## Review Feedback

**Reviewer:** codex
**Date:** 2026-06-27
**Verdict:** approved

### Required Changes

#### [High] Duplicate and collision behavior remains under-specified

The story explicitly requires cohesive shared contracts across app-owned and
producer-replay outputs (`story-37-05`, lines 18-19), and the reference warns
that duplicate display names are only acceptable if the product explicitly
accepts distinct duplicate records (`ref-file-naming-save-export-protocol-v1`,
lines 81-92). However, the only concrete duplicate-save behavior is scoped to
"the current Document Converter direction" (`ref-file-naming-save-export-protocol-v1`,
lines 94-104), while PR-0391 and PR-0393 do not require tests or acceptance
criteria for duplicate saves, rename collisions, or update-in-place exceptions
(`pr-0391`, lines 17-20 and 41-47; `pr-0393`, lines 19-22 and 43-49).

This leaves the exact drift ST-37-05 is meant to prevent: one app may silently
create another record, another may update an existing record, and rename may be
allowed or rejected depending on which route is touched first.

Required change: define the canonical default for repeated saves and same-owner
rename collisions in the reference and PR-0391/PR-0393. If update-in-place or
duplicate display names are allowed as app-specific exceptions, require the app
adapter to declare that exception and prove it with tests.

Required proof: PR-0391 backend/domain tests for duplicate-save naming or
disambiguation, plus PR-0393 API tests for rename collision behavior.

#### [High] Download filename authority is not pinned to the server contract

ST-37-05 covers both downloads and `Mina filer` saves (`story-37-05`, lines
15-16), and the reference includes download filenames and editable stems in
scope (`ref-file-naming-save-export-protocol-v1`, lines 23-30). But PR-0391
only asks for generated names and validation in the abstract (`pr-0391`, lines
17-20 and 30-33), and the app adoption slices can still satisfy their frontend
tests by composing final filenames in the browser. That would violate the same
trust boundary the reference states for producer-replay outputs: no
browser-owned file authority (`ref-file-naming-save-export-protocol-v1`, lines
119-124).

Required change: make the shared backend/domain contract the final filename
authority for both save and download actions. The browser may submit/display a
stem intent, but the protected API must return or set the sanitized final
filename and extension, for example through response metadata or
`Content-Disposition`.

Required proof: backend/API tests asserting the final filename for download
responses or metadata on both app-owned and producer-replay paths, and frontend
tests showing app UIs consume the returned filename instead of reconstructing it.

#### [Medium] Teacher-facing output-purpose labels are not canonical enough

The acceptance criteria require teacher-facing output purpose in generated
filenames (`story-37-05`, line 15), but the reference examples are English
technical tokens such as `transcript`, `corrected-exam`, `converted-pdf`, and
`markdown` (`ref-file-naming-save-export-protocol-v1`, lines 57-59). The product
surface is Swedish, and app adoption PRs are likely to choose their own label
language and normalization unless the protocol decides it first.

Required change: define the canonical purpose-label policy before app adoption.
For example, decide whether filenames use Swedish human labels with spaces,
stable localized tokens, or ASCII-normalized slugs, and provide exact labels for
transcription, corrected exam, converted PDF, Markdown, combined outputs, and
separate outputs.

Required proof: app adoption tests in PR-0394 through PR-0396 should assert the
generated default names use the canonical purpose vocabulary.

### Suggestions (Optional)

- The validation contract should eventually name max length, Unicode
  normalization, and reserved-name behavior, not only broad categories such as
  path separators and control characters.
- PR-0390 can remain docs-only, but it should not be marked approved until the
  reference carries the decisions above or explicitly blocks downstream
  implementation until they are made.
- After these changes are made, capture the acceptance decision explicitly.

### Decision Approvals

- [x] Keep ST-37-05 separate from PR-0385.
- [x] Separate display names from source references.
- [x] Use shared backend/frontend primitives before app adoption.
- [x] Approve duplicate-save and rename-collision semantics as currently
  specified.
- [x] Approve download filename authority as currently specified.
- [x] Approve output-purpose vocabulary as currently specified.

### Re-Review 2026-06-27

**Reviewer:** codex
**Date:** 2026-06-27
**Verdict:** content findings resolved

The remediation pass resolved the original high-severity duplicate/collision
and server-owned download filename authority findings. The reference now defines
backend-owned disambiguation for repeated saves, rejects same-owner rename
collisions with `FILE_NAME_CONFLICT`, and requires protected APIs to return or
set the final sanitized filename. PR-0391 and PR-0393 now carry matching
acceptance criteria and proof obligations.

The remediation also substantially resolved the original purpose-label finding
by adding Swedish canonical labels. However, one output family remains missing.

#### [Medium] Document Converter DOCX outputs have no canonical purpose label

The remediated reference defines labels for `Transkribering`, `Rättat prov`,
`Konverterad PDF`, `Markdown`, `Sammanslagen PDF`, and `Separat PDF`, but not
for DOCX outputs (`ref-file-naming-save-export-protocol-v1`, lines 75-88).
PR-0396 mirrors that omission by listing only `Konverterad PDF`, `Markdown`,
`Sammanslagen PDF`, and `Separat PDF` for Document Converter default names
(`pr-0396`, lines 21-25).

That conflicts with the governed Document Converter route plan, which includes
PDF to DOCX, Markdown to DOCX, and HTML to DOCX target routes
(`pr-0375`, lines 121-124 and 146-151). It also recreates a small version of
the original drift risk: later implementation can choose an app-local DOCX
label such as `DOCX`, `Word`, `Konverterad DOCX`, or something else without a
shared protocol decision.

Required change: add a canonical teacher-facing DOCX purpose label to the
reference, then update PR-0396 acceptance criteria, implementation plan, and
test plan so Document Converter DOCX output names are covered alongside PDF and
Markdown. If the product wants a general label such as `Word-dokument` instead
of `Konverterad DOCX`, decide it in the reference rather than inside the app
slice.

Required proof: PR-0396 must require backend/frontend tests for DOCX output
default names, extension preservation, and protected API final filename
authority.

### Final Self-Review Update 2026-06-27

**Reviewer:** codex
**Date:** 2026-06-27
**Verdict:** changes_requested

The remaining DOCX vocabulary issue has been remediated. The reference now
defines `Word-dokument` as the canonical teacher-facing label for DOCX and
Word-compatible output, and PR-0396 now requires Document Converter coverage
for PDF, DOCX, Markdown, separate-output, and combined-output names.

No content findings remain from this review. Acceptance is recorded in the
following owner acceptance update.

### Acceptance Update 2026-06-27

**Accepted by:** Olof, via explicit thread instruction
**Date:** 2026-06-27
**Verdict:** approved

After the final DOCX remediation and green docs validation, the owner explicitly
instructed this review to be flipped to accepted. The retained repo status is
therefore `approved`, matching the repo's review status vocabulary.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-ST-37-05` | Retained a changes-requested review for ST-37-05 and PR-0390 through PR-0396. |
| 2 | `REV-ST-37-05` | Recorded blocking findings for duplicate/collision semantics, server-owned download filename authority, and canonical purpose labels. |
| 3 | `REV-ST-37-05` | Re-reviewed the remediation and narrowed remaining changes to Document Converter DOCX purpose-label coverage plus independent approval. |
| 4 | `REF-file-naming-save-export-protocol-v1`, `PR-0396`, `REV-ST-37-05` | Added the canonical `Word-dokument` DOCX output label and required Document Converter DOCX naming proof. |
| 5 | `REV-ST-37-05` | Flipped retained review status to `approved` after explicit owner acceptance. |

## Verification

- Reviewed the ST-37-05 story, file naming reference, PR-0390 through PR-0396,
  related EPIC-37 context, and the PR-0385 review boundary.
- Re-reviewed the remediation diff against PR-0375's Document Converter route
  plan and current generated/frontend output-format surfaces.
- No production code was changed.
- `pdm run docs-validate` passed.
- `git diff --check` passed.

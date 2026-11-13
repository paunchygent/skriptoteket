---
type: reference
id: REF-SKRIPT-MOCKUP-pr-0370-public-landing-copy-requirements-review
title: PR-0370 public landing copy requirements review
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: mockup
summary: PR-0370 public landing copy requirements review
---

## Intent

### Scope

This package defines what the approved public landing direction must
communicate before HTML/CSS mockups introduce provisional Swedish copy.

It does not propose wording.

The approved wording is recorded separately in
[approved-copy.md](approved-copy.md).

### Minimum Communication

| Surface | Must communicate | Must not imply |
|---|---|---|
| Header | The visitor is on Skriptoteket and can reach Klassrumskartan directly. | That login is required before the public app can be opened. |
| Hero | Klassrumskartan is the public first action and works directly in the browser. | That all Skriptoteket apps are public or anonymous. |
| Hero account line | An account is optional and mainly extends the work over time. | That account creation is a prerequisite for trying Klassrumskartan. |
| Authenticated-app preview | Logging in gives access to additional teacher workflows. | That the previewed workflows are available to signed-out visitors. |
| Speech workflow | Speech or media can become text/transcript work. | That live diarization, speaker review, or every export format exists unless verified in the implementation slice. |
| PDF workflow | HTML/CSS or document material can become polished PDF output if the implementation slice verifies the live route/capability. | That Dokumentkonverteraren has a runnable public or authenticated route before one is proven. |
| Exam workflow | Digital exam work may include creation, editing, sharing, print export, and Exam.net-oriented export only to the extent verified before production copy. | That Exam.net direct import, create/edit/share, QTI, DOCX, or source-neutral exam state is live before verification. |
| Auth actions | Login and account creation must remain direct actions when shown. | That a user is sent to a generic hub, chooser, or duplicate action page first. |

### Copy Budget

- Keep the current public hero as the only strong first action.
- Use one section-level account framing for the authenticated preview.
- Do not repeat account status inside every workflow.
- Use only the words needed to disambiguate the three workflow diagrams.
- Avoid helper paragraphs unless the HTML/CSS mockup proves the section is
  unclear without them.

### Forbidden Copy

- No category or metadata labels such as `Vad du gör`, `Nytta`, `Status`,
  `Funktioner`, `Arbetsflöden`, or similar explanatory chrome.
- No all-caps eyebrow labels, badges, column headings, row headings, Roman
  numerals, numeric markers, or index markers in the authenticated preview.
- No final Swedish production sentences until product-owner approval.
- No broad marketing claims, superlatives, or generic productivity filler.
- No internal terms such as compatibility shell, route, registry, Sir Convert,
  pipeline, artifact, or implementation slice.

### Verification Before Production Copy

Before any implementation slice updates `ref-public-landing-copy-lock.md`, it
must verify:

- which transcript capabilities are live and teacher-facing;
- whether HTML/CSS-to-PDF belongs to a truthful runnable route or only planned
  Document Converter direction;
- which digital exam verbs are live: create, edit, share, print export,
  Exam.net-oriented export, direct import;
- whether any planned capability should be omitted from production copy until a
  reviewed route-visible slice exists.

## Package Manifest

No separate material is recorded in the source snapshot.

## Design Interpretation

### Scope

This package defines what the approved public landing direction must
communicate before HTML/CSS mockups introduce provisional Swedish copy.

It does not propose wording.

The approved wording is recorded separately in
[approved-copy.md](approved-copy.md).

### Minimum Communication

| Surface | Must communicate | Must not imply |
|---|---|---|
| Header | The visitor is on Skriptoteket and can reach Klassrumskartan directly. | That login is required before the public app can be opened. |
| Hero | Klassrumskartan is the public first action and works directly in the browser. | That all Skriptoteket apps are public or anonymous. |
| Hero account line | An account is optional and mainly extends the work over time. | That account creation is a prerequisite for trying Klassrumskartan. |
| Authenticated-app preview | Logging in gives access to additional teacher workflows. | That the previewed workflows are available to signed-out visitors. |
| Speech workflow | Speech or media can become text/transcript work. | That live diarization, speaker review, or every export format exists unless verified in the implementation slice. |
| PDF workflow | HTML/CSS or document material can become polished PDF output if the implementation slice verifies the live route/capability. | That Dokumentkonverteraren has a runnable public or authenticated route before one is proven. |
| Exam workflow | Digital exam work may include creation, editing, sharing, print export, and Exam.net-oriented export only to the extent verified before production copy. | That Exam.net direct import, create/edit/share, QTI, DOCX, or source-neutral exam state is live before verification. |
| Auth actions | Login and account creation must remain direct actions when shown. | That a user is sent to a generic hub, chooser, or duplicate action page first. |

### Copy Budget

- Keep the current public hero as the only strong first action.
- Use one section-level account framing for the authenticated preview.
- Do not repeat account status inside every workflow.
- Use only the words needed to disambiguate the three workflow diagrams.
- Avoid helper paragraphs unless the HTML/CSS mockup proves the section is
  unclear without them.

### Forbidden Copy

- No category or metadata labels such as `Vad du gör`, `Nytta`, `Status`,
  `Funktioner`, `Arbetsflöden`, or similar explanatory chrome.
- No all-caps eyebrow labels, badges, column headings, row headings, Roman
  numerals, numeric markers, or index markers in the authenticated preview.
- No final Swedish production sentences until product-owner approval.
- No broad marketing claims, superlatives, or generic productivity filler.
- No internal terms such as compatibility shell, route, registry, Sir Convert,
  pipeline, artifact, or implementation slice.

### Verification Before Production Copy

Before any implementation slice updates `ref-public-landing-copy-lock.md`, it
must verify:

- which transcript capabilities are live and teacher-facing;
- whether HTML/CSS-to-PDF belongs to a truthful runnable route or only planned
  Document Converter direction;
- which digital exam verbs are live: create, edit, share, print export,
  Exam.net-oriented export, direct import;
- whether any planned capability should be omitted from production copy until a
  reviewed route-visible slice exists.

## Runtime And Proof Boundary

No separate material is recorded in the source snapshot.

## Governing Links And Follow-Up

No separate material is recorded in the source snapshot.

### Source Record

### Scope

This package defines what the approved public landing direction must
communicate before HTML/CSS mockups introduce provisional Swedish copy.

It does not propose wording.

The approved wording is recorded separately in
[approved-copy.md](approved-copy.md).

### Minimum Communication

| Surface | Must communicate | Must not imply |
|---|---|---|
| Header | The visitor is on Skriptoteket and can reach Klassrumskartan directly. | That login is required before the public app can be opened. |
| Hero | Klassrumskartan is the public first action and works directly in the browser. | That all Skriptoteket apps are public or anonymous. |
| Hero account line | An account is optional and mainly extends the work over time. | That account creation is a prerequisite for trying Klassrumskartan. |
| Authenticated-app preview | Logging in gives access to additional teacher workflows. | That the previewed workflows are available to signed-out visitors. |
| Speech workflow | Speech or media can become text/transcript work. | That live diarization, speaker review, or every export format exists unless verified in the implementation slice. |
| PDF workflow | HTML/CSS or document material can become polished PDF output if the implementation slice verifies the live route/capability. | That Dokumentkonverteraren has a runnable public or authenticated route before one is proven. |
| Exam workflow | Digital exam work may include creation, editing, sharing, print export, and Exam.net-oriented export only to the extent verified before production copy. | That Exam.net direct import, create/edit/share, QTI, DOCX, or source-neutral exam state is live before verification. |
| Auth actions | Login and account creation must remain direct actions when shown. | That a user is sent to a generic hub, chooser, or duplicate action page first. |

### Copy Budget

- Keep the current public hero as the only strong first action.
- Use one section-level account framing for the authenticated preview.
- Do not repeat account status inside every workflow.
- Use only the words needed to disambiguate the three workflow diagrams.
- Avoid helper paragraphs unless the HTML/CSS mockup proves the section is
  unclear without them.

### Forbidden Copy

- No category or metadata labels such as `Vad du gör`, `Nytta`, `Status`,
  `Funktioner`, `Arbetsflöden`, or similar explanatory chrome.
- No all-caps eyebrow labels, badges, column headings, row headings, Roman
  numerals, numeric markers, or index markers in the authenticated preview.
- No final Swedish production sentences until product-owner approval.
- No broad marketing claims, superlatives, or generic productivity filler.
- No internal terms such as compatibility shell, route, registry, Sir Convert,
  pipeline, artifact, or implementation slice.

### Verification Before Production Copy

Before any implementation slice updates `ref-public-landing-copy-lock.md`, it
must verify:

- which transcript capabilities are live and teacher-facing;
- whether HTML/CSS-to-PDF belongs to a truthful runnable route or only planned
  Document Converter direction;
- which digital exam verbs are live: create, edit, share, print export,
  Exam.net-oriented export, direct import;
- whether any planned capability should be omitted from production copy until a
  reviewed route-visible slice exists.

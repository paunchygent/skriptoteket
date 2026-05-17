# Session History: PR-0326 Through PR-0331 AI-Facit Review Lane

Date: 2026-05-17

## Retained Context

- `PR-0326` added the authenticated two-pass reviewed-completion consumer flow:
  advisory submit, teacher-visible AI-facit suggestions, reviewed overlay
  construction, and reviewed apply submit.
- `PR-0327` added the dev/test-only internal-browser fixture lane for
  authenticated Exam Converter UI inspection after normal HuleEdu login.
- `PR-0328` fixed stale advisory idempotent replay by adding a bounded
  provider-only retry path that changes only the client idempotency digest.
- `PR-0329` extended the reviewed AI-facit handoff to valid `gap_fill`
  candidates and proved the UI reloads file readiness from the reviewed apply
  job bundle.
- `PR-0330` defined the small-screen strategy: phone below `768px` is a
  separate reduced companion flow; tablet/narrow-laptop and desktop remain
  distinct compositions.

## 2026-05-17 User Evidence For PR-0331

The user supplied screenshots plus downloaded artifacts after this sequence:
approve all, create files, approve/current-state export, then download PDF/QTI.

Observed evidence:

- The AI-facit banner exposes competing actions: `Granska`, `Godkänn alla`, and
  `Skapa filer`.
- The Files tab can show raw producer reason text such as
  `Orsak: unsupported_target_shape`.
- A later Files state can show both PDF and QTI as `Godkänt för export` even
  though artifact inspection does not prove reviewed keys survived.
- The highest-severity failure is that accepted AI-suggested keys appear to be
  removed or omitted after the teacher has explicitly approved them.
- `pdftotext` on the downloaded PDF showed key-bearing items exported as manual
  free-text with internal fallback copy, including:
  `Manuell bedömning. Ursprunglig lucktext utan betrodda accepterade värden.`
- `unzip -l` on the QTI package showed eight item XML files plus one image
  resource. Sampled item XML lacked `correctResponse` declarations.

`PR-0331` was created to treat this as a contract and affordance blocker, not a
small-screen styling issue.

## Key Code Pointers

- `useExamConverterAiFacitReview.ts` builds reviewed-completion overlay items.
- `useExamConverterReviewArtifacts.ts` loads optional `effective_ir_json`.
- `digiexamIrReviewParser.ts` stores `effectiveAnswerKeysByItem`, but projected
  question rows are still source-IR plus advisory candidates.
- `digiexamIrQuestionReviewProjection.ts` computes missing `Facit` from manual
  follow-ups and does not consume effective answer keys.
- `ExamConverterFilesReadinessList.vue` falls back to raw `Orsak: ${reasonCode}`
  for unknown producer reason codes.

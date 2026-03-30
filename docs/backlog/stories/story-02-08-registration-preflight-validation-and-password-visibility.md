---
type: story
id: ST-02-08
title: "Registration preflight validation and password visibility"
status: in_progress
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
epic: "EPIC-02"
acceptance_criteria:
  - "Given a visitor types an email address on `/register`, when the address becomes syntactically valid, then the UI validates it before submit against the current registration rules and shows a clear inline message if the domain is blocked, unknown, or already registered."
  - "Given a visitor types a municipality or enskild-huvudman address on `/register`, when the preflight check succeeds, then the UI no longer blocks submit on email-domain grounds."
  - "Given a visitor types a too-short password or mismatched confirmation, when they are still filling out the form, then the UI shows inline feedback before they click `Skapa konto`."
  - "Given a visitor wants to inspect what they typed in the password fields, when they click the eye affordance, then both password inputs can be toggled between masked and visible text without losing focus or value."
  - "Given the browser-side validation disagrees with the authoritative backend on submit, when the final registration request is sent, then backend validation still remains the source of truth and its error is shown clearly."
dependencies: ["ST-02-03", "ST-02-06"]
ui_impact: "Updates `/register` with inline validation states and password visibility controls; adds a lightweight anonymous registration-validation API contract for frontend preflight checks."
data_impact: "No schema change."
---

## Context

Registration already enforces the Swedish school-domain gate and password policy on the backend, but
the current SPA only reveals most failures after a full submit. That is unnecessarily frustrating
for early alpha users, especially when the product now targets municipality and enskild-huvudman
staff only.

## Implementation notes

### Validation contract

- Add a thin anonymous validation endpoint for registration preflight checks.
- Keep the endpoint authoritative for:
  - email syntax acceptance at the API boundary
  - root-domain allow/block checks through the existing domain validator
  - duplicate-email detection
  - current password-policy result
- Return structured field-level status so the SPA can render inline feedback without reverse-
  engineering `DomainError` envelopes.

### Frontend behavior

- Debounce email preflight requests; do not spam the API on every keystroke.
- Keep local immediate checks for:
  - empty first/last name
  - password confirmation mismatch
- Show a helpful domain message in Swedish that reflects the current launch policy:
  - only municipalities and enskilda huvudmän can self-register in the early release
- Do not hide backend submit errors behind generic copy; surface them when submit still fails.

### Password visibility

- Use a standard eye affordance inside the password and password-confirmation inputs.
- Keep keyboard and screen-reader behavior explicit (`aria-pressed`, clear labels).
- Prefer a reusable auth-field primitive if it prevents duplicated toggle markup.

### Verification

- Backend route tests for the new preflight endpoint.
- Handler/unit tests for domain, duplicate-email, and password-policy outcomes.
- Frontend tests for inline validation states, disabled/blocked submit states, and password toggle
  behavior.
- Manual proof on local dev:
  - type a blocked/personal domain and confirm the inline message appears before submit
  - type an allowed school-sector address and confirm the email error clears
  - type a short password / mismatched confirmation and confirm inline feedback appears
  - toggle both password fields visible/invisible and confirm values remain intact

---
type: pr
id: PR-0239
title: "ST-32-08: featured public-app showcase and authenticated-value preview surfaces"
status: done
owners: "agents"
created: 2026-04-07
updated: 2026-04-08
stories:
  - "ST-32-08"
tags: ["frontend", "ux", "landing-page", "public-access", "showcase"]
dependencies:
  - "ST-32-07"
  - "ST-32-08"
  - "PR-0237"
  - "PR-0238"
acceptance_criteria:
  - "Given the current unauthenticated landing page still relies on generic value cards, when this slice ships, then the below-the-fold content is reset around one featured Klassrumskartan showcase that shows what the public app lets a teacher do in practice."
  - "Given the below-the-fold showcase should follow the locked first-screen direction from `ST-32-07`, when this slice begins, then `PR-0238` is already the accepted baseline so the showcase does not ship under an outdated auth-first header/hero."
  - "Given visitors should understand that more capability exists behind login, when the landing page continues after the featured public-app section, then at least one authenticated-only capability preview is shown with explicit account-required framing instead of a misleading public CTA."
  - "Given this slice is visually important, when implementation begins, then the section ordering, copy density, and visual hierarchy follow the approved mockup from `PR-0237` and remain grounded in the existing HuleEdu/Skriptoteket design language."
  - "Given all Swedish copy in this slice remains draft until explicit user sign-off, when implementation happens, then the copy stays short, conversational, verb-led, non-technical, and free of sales language or internal product terminology."
  - "Given the landing page should avoid generic card-stack aesthetics, when this slice is implemented, then it does not default to cards or nested cards and instead uses stronger structural layout devices first."
---

## Problem

The current landing page tells visitors that Skriptoteket is valuable, but it does not show that
value concretely enough.

That is especially weak now that one public app can already be used directly.

## Goal

Replace the generic below-the-fold messaging with a stronger show-first landing narrative:

- one real public-app showcase
- one explicit preview of authenticated-only value

## Non-goals

- Changing the router or unmatched-route handling in this slice.
- Turning the landing page into a long-form marketing site with many generic sections.
- Opening additional public apps here.

## Implementation plan

1. Use the `PR-0237` mockup as the layout and section-order source of truth.
2. Treat `PR-0238` as the hard prerequisite first-screen baseline before changing the below-the-fold
   narrative.
3. Replace the current public highlight cards in `HomeView.vue` with a featured Klassrumskartan
   showcase section.
4. Add a secondary preview section for authenticated-only value surfaces with explicit labeling.
5. Keep the page compact and product-grounded: show real use, avoid generic boasting, avoid card
   stacks, and avoid too many sections.
6. Add focused tests and a live landing-page proof.

## Test plan

- Focused frontend tests for the unauthenticated landing showcase sections in `HomeView.spec.ts`
  plus any needed shell-level assertions if shared layout behavior changes.
- Live browser proof on `http://127.0.0.1:5173/`
- `pdm run fe-type-check`
- `pdm run docs-validate`

## Rollback plan

- Restore the previous generic highlight section if the new showcase direction proves unclear,
  without undoing the header or hero CTA improvements.

## Implementation note (2026-04-08)

This slice shipped the signed-out landing showcase through dedicated home components rather than
re-expanding `HomeView.vue`, keeping the `PR-0238` hero/header baseline frozen while replacing the
old generic value highlights with:

- one featured `Klassrumskartan` product showcase with a shared three-step framed strip
- one authenticated-only ledger preview with explicit account-required labels

The authenticated preview footer intentionally reused the shipped in-place login modal contract from
`PR-0238` so this slice stayed inside the approved landing-content boundary. A follow-up PR slice
should replace that overloaded signed-out modal entry with a dedicated auth redirect page that keeps
redirect targets explicit and is better suited to launch-readiness and future HuleEdu SSO work.

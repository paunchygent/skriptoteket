---
type: task
id: TASK-SKRIPT-REP-0061
title: Every top bar shows the same Skriptoteket logo and page titles follow the shared title role
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-30'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-30'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Juniors 004883339, 4e09bd1bd, 93a60ed1b merged 26a9f062a, 4e6939a4f, 00fa763fa. Mac staging walks: 26a9f062a stopped at 360 px (bar 372.6 px), repaired by D7-D8; 4e6939a4f passed steps 1, 3, 4, 5 and failed step 2 on the HuleEdu sign-in page, repaired by TASK-HULE-REP-0150 (HuleEdu production 86344a83d); 00fa763fa greeting passed at 1366 and 360 px (Mac records Repos/Skriptoteket/.artifacts/staging-walk-rep-0061-*). Production 00fa763fa, deploy log .artifacts/hemma-deploy-20261030-123856.log, healthz 200, web and worker healthy. The user checked production on phone and desktop on 2026-10-30 and answered ''Ser rätt ut''.'
task_kind: repository
acceptance_criteria:
  - The signed-in and signed-out top bars render one shared logo link at the same 40 px height, linking to /, at least 44 px high
  - The login page shows no logo in its card; its title and the activation and handoff page titles use the page-title class
  - The page-title class uses the shared page-title role tokens (20 px, semibold) and the serif face
  - No page body shows a logo; the activation page keeps its small Skriptoteket label
  - A Mac staging walk at desktop and 360 px, signed out (home, login) and signed in (an app page, an immersive game), shows the same logo in every bar
backlog_document_profile: contract-derived
---

## Implementation Contract

REP-0060 replaced the text wordmark in the signed-in top bar only. The signed-out bar (`LandingLayout.vue`) still
shows serif text at 20/24 px, and the login page shows that text in the bar plus a 34 px logo in its card. A signed
out visitor and a signed-in teacher therefore see different brand marks at different sizes. This task gives every
bar the same logo and brings the page titles onto the shared title role.

- Actors: signed-out visitors (home, login, public apps), signed-in users on every page, the immersive game bar.
- One shared brand-link component (logo at `var(--huleedu-space-10)`, `RouterLink to="/"`, min-height
  `var(--huleedu-action-control-height)`) replaces the brand markup in `AuthTopBar.vue` and `LandingLayout.vue`.
  The app label, the immersive token override and the phone rules in `AuthTopBar` stay as built.
- The login card loses its logo. The H1s in `AuthLoginView.vue`, `AuthProvisioningRequiredView.vue` and
  `AuthLifecycleHandoffView.vue` (serif `text-4xl`, 36 px) use `.page-title`. The activation page keeps its small
  uppercase `Skriptoteket` label.
- `.page-title` in `assets/main.css` uses `--huleedu-type-page-title-size` and `--huleedu-type-page-title-weight`
  (20 px, semibold) with the serif face. Every view using the class follows.
- `BrandLogo` sizes are tokens only; the raw `32px` default and `34px` go.
- Phone (< 768 px), from the first Mac walk at 26a9f062a: the signed-out bar needed 373 px at 360 px. Hjälp in the
  signed-out bar shows its glyph only below 768 px through a new `wordFrom="tablet"` mode on `ShellBarButton`, so
  the row is about 329 px. The home hero heading (`text-5xl`, 48 px) pushed the page to 376 px; its phone size
  becomes `text-4xl` (36 px), with the `md` and `lg` sizes unchanged.
- Non-goals: the logo artwork, game titles, the recovery page, HuleEdu.

## Contract Inputs

- TASK-SKRIPT-REP-0060 (its contract named only the signed-in bar and the login page). The user withdrew the
  2026-10-30 approval after seeing the signed-out bar and the differing sizes.
- Mac staging walk at 26a9f062a stopped at step 1 (360 px: bar 372.6 px, page 376 px). User decisions 2026-10-30:
  Hjälp glyph-only on phone; the hero heading fix joins this task.
- User decisions 2026-10-30 (AskUserQuestion): login shows only the bar logo; the activation label stays; the
  three auth H1s move to the title class in this task; `.page-title` moves to the token role in this task.
- Advisor comparison with HuleEdu CJ admin and rater (`human-cj-desktop-workbench.css`): serif wordmark 22 px with
  a terracotta sans tag, header title 14 px sans; wordmark-to-title ratio about 1.6. Skriptoteket after this task:
  logo ink about 35 px over a 20 px title.
- `huleedu-ui-design` visual system (type roles, tokens only, 44 px targets).

## Core Vertical And Performance

The core vertical is one visitor signing in: the signed-out home bar shows the logo, the login page shows the same
logo in its bar and a page-title heading, and after sign-in the bar shows the same logo at the same height. No
performance concern; the logo is already inlined in the bundle.

Units, each for one junior:

1. The shared brand-link component, used by `AuthTopBar` and `LandingLayout`; the login card logo removed; token
   sizes in `BrandLogo`.
2. `.page-title` on the role tokens; the three auth H1s on `.page-title`.
3. Spec updates for both layouts and the login view.

## Validation

- Vitest: both layouts render the shared brand link to `/`; the login view renders no `BrandLogo`; the three auth
  views render their H1 with `.page-title`.
- A Mac staging walk before the user looks: desktop and 360 px, signed out (home, login) and signed in (an app
  page, an immersive game), with screenshots and the logo's measured height in each bar.

## Stop Conditions

- The signed-out bar or the home page is wider than 360 px at 360 px after these changes: stop and report.
- A view overrides `.page-title` so that the role change breaks its layout.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------------------- |
| D1  | Signed-in and signed-out bars use one shared brand-link component: 40 px logo, link to `/`, at least 44 px high.       |
| D2  | The login page shows only the bar logo; no page body shows a logo; the activation page keeps its small label.          |
| D3  | The login, activation and handoff H1s use `.page-title`.                                                               |
| D4  | `.page-title` uses the shared page-title role tokens (20 px, semibold) with the serif face.                            |
| D5  | Logo sizes are tokens only.                                                                                            |
| D6  | Proof is focused Vitest and a Mac staging walk at desktop and 360 px, signed out and signed in, before the user looks. |
| D7  | Below 768 px the signed-out bar's Hjälp shows its glyph only (`wordFrom="tablet"`); the logo keeps 40 px.              |
| D8  | The home hero heading is 36 px below 768 px, so `/` has no horizontal scroll at 360 px.                                |
| D9  | The signed-in start-page greeting H1 uses `.page-title` (user decision 2026-10-30, after the second walk).             |

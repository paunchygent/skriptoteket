# Documentation

This repo uses a **Docs-as-Code** contract to keep documentation consistent and machine-checkable.

- Contract (source of truth): `docs/_meta/docs-contract.yaml`
- Templates: `docs/templates/`
- Validate locally: `pdm run docs-validate`

## Key documents

- PRD (MVP): `docs/prd/prd-script-hub-v0.1.md`
- PRD (Planned): `docs/prd/prd-script-hub-v0.2.md`
- PRD (Frontend): `docs/prd/prd-spa-frontend-v0.1.md`
- PRD (Editor Sandbox): `docs/prd/prd-editor-sandbox-v0.1.md`
- PRD (Tool Authoring): `docs/prd/prd-tool-authoring-v0.1.md`
- PRD (Klassrumskartan current): `docs/prd/prd-group-seating-studio-v0.3.md`
- Technical overview (Klassrumskartan):
  `src/skriptoteket/application/curated_apps/classroom_planner/README.md`
- Product direction (Klassrumskartan): `docs/reference/ref-group-seating-studio-product-direction-2026-03-21.md`
- Workspace UI doctrine (Klassrumskartan):
  `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`
- Shared tool control language:
  `docs/reference/ref-shared-tool-control-language-v1.md`
- Frontend transition continuity pattern:
  `docs/reference/ref-frontend-transition-continuity-v1.md`
- Frontend design-system codemap:
  `docs/reference/ref-frontend-design-system-codemap-2026-03-28.md`
- Smart assignment V1 decision memo:
  `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md`
- Implementation map (v0.2): `docs/reference/ref-implementation-map-script-hub-v0-2.md`
- Editor sandbox preview plan: `docs/reference/ref-editor-sandbox-preview-plan.md`
- Runner execution flow codemap: `docs/reference/reports/codemaps/runner-execution-flow.md`
- Runner Contract V3 (Structured Results, State & Promotions): `docs/reference/ref-runner-contract-v3.md`
- AI API surfaces codemap: `docs/reference/reports/codemaps/ai-api-surfaces-tool-editor.md`
- Observability correlation trace codemap: `docs/reference/reports/codemaps/observability-correlation-trace.md`
- Tool editor framework codemap: `docs/reference/ref-tool-editor-framework-codemap.md`
- Curated app spec: `docs/reference/ref-curated-app-reagent-prep-chef.md`
- Competitive games + Flunk-Out Frenzy reference:
  `docs/reference/ref-curated-app-flunk-out-frenzy-architecture-and-foundational-code.md`
- Seating continuity follow-up:
  `docs/backlog/prs/pr-0105-klassrumskartan-seating-draft-continuity-and-new-seating-draft-lifecycle.md`
- Seating undo/redo follow-up:
  `docs/backlog/prs/pr-0106-klassrumskartan-seating-undo-redo-and-bounded-draft-history.md`
- Seating `Slumpa` follow-up:
  `docs/backlog/prs/pr-0109-klassrumskartan-seating-slumpa-fundamentals.md`
- Overview-first management follow-up:
  `docs/backlog/stories/story-24-07-group-seating-studio-overview-first-workspace-management.md`
- Overview design simplification follow-up:
  `docs/backlog/prs/pr-0112-klassrumskartan-overview-design-simplification-and-seamless-workspace-transitions.md`
- Planner shell refactor follow-up:
  `docs/backlog/prs/pr-0114-klassrumskartan-planner-shell-decomposition-and-shared-ui-primitives.md`
- Route-shell refactor follow-up:
  `docs/backlog/prs/pr-0115-klassrumskartan-route-shell-orchestration-and-catalog-home-state-extraction.md`
- Room-editor refactor follow-up:
  `docs/backlog/prs/pr-0116-klassrumskartan-room-template-editor-modularization-and-shared-room-scene.md`
- Seating workspace zoom parity follow-up:
  `docs/backlog/prs/pr-0117-klassrumskartan-seating-workspace-viewport-zoom-parity.md`
- Seating export webhook hardening follow-up:
  `docs/backlog/prs/pr-0121-klassrumskartan-shared-seating-export-webhook-dispatcher.md`
- Seating export production/Hemma wiring follow-up:
  `docs/backlog/prs/pr-0122-klassrumskartan-seating-export-production-wiring-and-hemma-deploy-orchestration.md`
- Seating scene remediation follow-up:
  `docs/backlog/prs/pr-0123-klassrumskartan-seating-scene-remediation-wall-markers-localization-and-print-contrast.md`
- Wall-fixture parity + poster header branding follow-up:
  `docs/backlog/prs/pr-0126-klassrumskartan-wall-fixture-parity-resize-anchoring-and-poster-header-branding.md`
- Seat drag-preview + same-tool room-editor removal follow-up:
  `docs/backlog/prs/pr-0136-klassrumskartan-seat-drag-preview-and-room-editor-same-tool-toggle-removal.md`
- Class-list import remediation follow-up:
  `docs/backlog/prs/pr-0137-klassrumskartan-class-list-import-remediation-example-corpus-and-overview-reconciliation.md`
- Class-list import drag/drop affordance follow-up:
  `docs/backlog/prs/pr-0175-klassrumskartan-class-list-import-dropzone-in-create-edit-modal.md`
- Seating export single-key/runtime remediation follow-up:
  `docs/backlog/prs/pr-0138-seating-export-single-canonical-sir-convert-v2-key-and-runtime-wiring.md`
- Local export runtime parity/schema remediation follow-up:
  `docs/backlog/prs/pr-0144-klassrumskartan-local-dev-export-runtime-parity-and-schema-remediation.md`
- Alembic migration integrity/idempotency remediation follow-up:
  `docs/backlog/prs/pr-0145-alembic-migration-integrity-and-full-idempotency-coverage.md`
- Seating PDF local cutover/removal follow-up:
  `docs/backlog/prs/pr-0146-klassrumskartan-seating-pdf-local-cutover-and-sir-convert-path-removal.md`
- Smart seating-only teacher-distance contract reset:
  `docs/backlog/prs/pr-0147-klassrumskartan-seating-only-teacher-distance-contract-reset.md`
- Seating smart-rule toolbar + non-overlapping cluster authoring:
  `docs/backlog/prs/pr-0149-klassrumskartan-seating-smart-rule-toolbar-and-non-overlapping-cluster-authoring-v1.md`
- Roster-global smart-rule ownership boundary reset:
  `docs/backlog/prs/pr-0151-klassrumskartan-roster-global-smart-rules-and-draft-local-arrangement-boundary-reset.md`
- Planner session lanes + transition matrix remediation:
  `docs/backlog/prs/pr-0152-klassrumskartan-planner-session-lanes-and-transition-matrix-remediation.md`
- Shared planner export-flow composable cleanup:
  `docs/backlog/prs/pr-0153-klassrumskartan-shared-export-flow-composable-and-planner-hotspot-reduction.md`
- Smart seating v1 backend run + history gating:
  `docs/backlog/prs/pr-0154-klassrumskartan-smart-seating-v1-backend-run-use-history-and-teacher-edge-placement.md`
- Rules workspace + dual-map smart authoring follow-up:
  `docs/backlog/prs/pr-0155-klassrumskartan-rules-workspace-dual-map-authoring-and-summary-cutover.md`
- Smart grouping v1 implementation slice:
  `docs/backlog/prs/pr-0167-st-27-04-smart-grouping-v1-grouping-history-and-live-seating-influence.md`
- Smart grouping compactness simulation + overlay tuning slice:
  `docs/backlog/prs/pr-0178-st-27-04-smart-grouping-compactness-simulation-and-overlay-tuning.md`
- ST-29-01 docs/codemap foundation:
  `docs/backlog/prs/pr-0156-st-29-01-control-language-freeze-primitive-contract-and-fe-codemap.md`
- ST-29-01 shared primitive implementation:
  `docs/backlog/prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md`
- ST-29-01 seating proving-ground adoption:
  `docs/backlog/prs/pr-0158-st-29-01-seating-workspace-adoption-of-shared-dense-tool-primitives.md`
- ST-29-02 shell compression + sticky shared toolbar cutover:
  `docs/backlog/prs/pr-0161-st-29-02-shared-sticky-workspace-toolbar-and-transient-feedback-cutover.md`
- ST-29-09 rule visibility + tool-feedback continuity:
  `docs/backlog/prs/pr-0177-st-29-09-rule-visibility-and-tool-feedback-continuity.md`
- Dishka/FastAPI public-API cutover foundation:
  `docs/backlog/prs/pr-0162-st-07-07-public-http-dishka-adapter-and-observability-cutover.md`
- Hemma kernel lane recovery + `6.14` freeze / `6.17` cutover task:
  `docs/backlog/prs/pr-0159-hemma-kernel-lane-recovery-6-14-freeze-and-6-17-cutover.md`
- Seating export checkpoint registry + history dedupe:
  `docs/backlog/prs/pr-0150-klassrumskartan-seating-export-checkpoint-registry-and-history-dedupe.md`
- Conversion Hub local job boundary follow-up:
  `docs/backlog/prs/pr-0148-conversion-hub-local-job-ledger-owned-status-download-boundary.md`
- Proposed Klassrumskartan export/import epic:
  `docs/backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md`
- Proposed Klassrumskartan export/import review:
  `docs/backlog/reviews/review-epic-26-klassrumskartan-explicit-exports-and-class-list-import.md`
- Accepted Klassrumskartan smart assignment ADR:
  `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md`
- Proposed Klassrumskartan local-export boundary ADR:
  `docs/adr/adr-0075-klassrumskartan-local-export-artifacts-and-conversion-boundary.md`
- Active Klassrumskartan smart assignment epic:
  `docs/backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md`
- Approved Klassrumskartan smart assignment review:
  `docs/backlog/reviews/review-epic-27-klassrumskartan-smart-assignment-v1.md`
- Proposed auth-cutover ADR:
  `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md`
- Accepted same-shell transition continuity ADR:
  `docs/adr/adr-0077-same-shell-transition-continuity.md`
- Proposed local password reset ADR:
  `docs/adr/adr-0078-local-password-reset-via-emailed-token.md`
- Proposed auth-cutover epic:
  `docs/backlog/epics/epic-28-skriptoteket-auth-authority-cutover-to-huleedu.md`
- Approved local password reset review:
  `docs/backlog/reviews/review-epic-02-local-password-reset-via-emailed-token.md`
- Local password reset planning slice:
  `docs/backlog/prs/pr-0172-local-password-reset-via-emailed-token.md`
- Home messaging + registration feedback + default bookmark slice:
  `docs/backlog/prs/pr-0173-home-messaging-registration-feedback-and-default-klassrumskartan-bookmark.md`
- Recovery email hardening + resend-discoverability slice:
  `docs/backlog/prs/pr-0174-recovery-email-hardening-and-verification-resend-discoverability.md`
- Recovery email review-remediation slice:
  `docs/backlog/prs/pr-0176-review-remediation-for-recovery-email-hardening-and-resend-verification-ux.md`
- Klassrumskartan class-list import drag/drop slice:
  `docs/backlog/prs/pr-0175-klassrumskartan-class-list-import-dropzone-in-create-edit-modal.md`
- Proposed auth-cutover review:
  `docs/backlog/reviews/review-epic-28-skriptoteket-auth-authority-cutover-to-huleedu.md`
- Proposed Klassrumskartan desktop-first workspace-overhaul epic:
  `docs/backlog/epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md`
- Proposed Klassrumskartan desktop-first workspace-overhaul review:
  `docs/backlog/reviews/review-epic-29-klassrumskartan-desktop-first-workspace-overhaul.md`
- Active same-shell transition continuity epic:
  `docs/backlog/epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md`
- Approved same-shell transition continuity review:
  `docs/backlog/reviews/review-epic-30-frontend-transition-continuity-for-same-shell-selectors.md`
- Same-shell transition continuity planning slice:
  `docs/backlog/prs/pr-0165-st-30-01-transition-continuity-decision-inventory-and-adoption-plan.md`
- Same-shell transition continuity implementation slice:
  `docs/backlog/prs/pr-0166-st-30-02-transition-continuity-adoption-and-remaining-transition-audit.md`
- Production curated-app visibility hardening slice:
  `docs/backlog/prs/pr-0169-production-curated-app-visibility-gate.md`
- Public-edge app/runtime hardening slice:
  `docs/backlog/prs/pr-0170-st-09-07-public-edge-app-runtime-hardening.md`
- Hemma edge observability + reserved-host lockdown slice:
  `docs/backlog/prs/pr-0171-st-09-08-hemma-edge-observability-and-host-lockdown.md`
- Competitive games cross-cutting programme:
  `docs/reference/ref-competitive-games-cross-cutting-programme.md`
- Proposed ADR: `docs/adr/adr-0073-competitive-games-and-official-high-scores.md`
- Proposed EPIC: `docs/backlog/epics/epic-25-competitive-games-and-flunk-out-frenzy.md`
- Riskunderlag praxis (Reagent Prep Chef): `docs/reference/ref-reagent-prep-chef-riskunderlag-skolpraxis.md`
- Hazards↔shortcards policy (Reagent Prep Chef): `docs/reference/ref-reagent-prep-chef-hazard-shortcard-alignment-policy.md`
- Llama kodassistent eval v1: `docs/reference/ref-llama-kodassistent-eval-v1.md`
- Llama kodassistent eval v2: `docs/reference/ref-llama-kodassistent-eval-v2.md`
- Migration roadmap (SPA): `docs/reference/reports/ref-vue-spa-migration-roadmap.md`
- Toasts + system messages (SPA): `docs/reference/ref-toast-system-messages.md`
- Hemma critical paths + ops inventory: `docs/reference/ref-hemma-critical-paths-2026-01-06.md`
- Agent browser automation runbook: `docs/runbooks/runbook-agent-browser-automation.md`
- Feedback email CLI runbook: `docs/runbooks/runbook-feedback-email-cli.md`
- Active sprint: `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`
- Release notes: `docs/releases/`
- ADRs: `docs/adr/`
- Backlog: `docs/backlog/`

## Guides

- Klassrumskartan kom igång: `docs/guides/guide-klassrumskartan-kom-igang.md`

## Full index

### ADRs

- `docs/adr/adr-0001-ui-server-driven-htmx.md`
- `docs/adr/adr-0002-backend-fastapi.md`
- `docs/adr/adr-0003-script-taxonomy-professions-and-categories.md`
- `docs/adr/adr-0004-clean-architecture-ddd-di.md`
- `docs/adr/adr-0005-user-roles-and-script-governance.md`
- `docs/adr/adr-0006-identity-and-authorization-mvp.md`
- `docs/adr/adr-0007-defer-kafka-until-needed.md`
- `docs/adr/adr-0008-testing-strategy-and-testcontainers-timing.md`
- `docs/adr/adr-0009-auth-local-sessions-admin-provisioned.md`
- `docs/adr/adr-0010-accepting-suggestions-creates-draft-tool.md`
- `docs/adr/adr-0011-huleedu-identity-federation.md`
- `docs/adr/adr-0012-script-source-storage.md`
- `docs/adr/adr-0013-execution-ephemeral-docker.md`
- `docs/adr/adr-0014-versioning-and-single-active.md`
- `docs/adr/adr-0015-runner-contract-and-compatibility.md`
- `docs/adr/adr-0016-execution-concurrency-and-backpressure.md`
- `docs/adr/adr-0017-huleedu-design-system-adoption.md`
- `docs/adr/adr-0018-observability-structured-logging-and-correlation.md`
- `docs/adr/adr-0019-observability-health-metrics-and-tracing.md`
- `docs/adr/adr-0020-responsive-mobile-adaptation.md`
- `docs/adr/adr-0021-http-security-headers.md`
- `docs/adr/adr-0022-tool-ui-contract-v2.md`
- `docs/adr/adr-0023-curated-apps-registry-and-execution.md`
- `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md`
- `docs/adr/adr-0025-embedded-spa-islands.md`
- `docs/adr/adr-0026-observability-stack-infrastructure.md`
- `docs/adr/adr-0027-full-vue-vite-spa.md`
- `docs/adr/adr-0028-spa-hosting-and-routing-integration.md`
- `docs/adr/adr-0029-frontend-styling-pure-css-design-tokens.md`
- `docs/adr/adr-0030-openapi-as-source-and-openapi-typescript.md`
- `docs/adr/adr-0031-multi-file-input-contract.md`
- `docs/adr/adr-0032-tailwind-4-theme-tokens.md`
- `docs/adr/adr-0033-admin-tool-status-enrichment.md`
- `docs/adr/adr-0034-self-registration-and-user-profiles.md`
- `docs/adr/adr-0035-script-editor-intelligence-architecture.md`
- `docs/adr/adr-0036-tool-usage-instructions.md`
- `docs/adr/adr-0037-toast-and-system-messages-spa.md`
- `docs/adr/adr-0037-tool-slug-lifecycle.md`
- `docs/adr/adr-0038-editor-sandbox-interactive-actions.md`
- `docs/adr/adr-0039-session-file-persistence.md`
- `docs/adr/adr-0040-profile-view-edit-separation.md`
- `docs/adr/adr-0041-user-favorites-and-tool-bookmarking.md`
- `docs/adr/adr-0042-flat-catalog-with-label-filtering.md`
- `docs/adr/adr-0043-ai-completion-integration.md`
- `docs/adr/adr-0044-editor-sandbox-preview-snapshots.md`
- `docs/adr/adr-0045-sandbox-settings-isolation.md`
- `docs/adr/adr-0046-draft-head-locks.md`
- `docs/adr/adr-0047-layout-editor-v1.md`
- `docs/adr/adr-0048-linter-context-and-data-flow.md`
- `docs/adr/adr-0049-login-events-audit-trail.md`
- `docs/adr/adr-0050-self-hosted-llm-infrastructure.md`
- `docs/adr/adr-0051-chat-first-ai-editing.md`
- `docs/adr/adr-0052-llm-prompt-budgets-and-kb-fragments.md`
- `docs/adr/adr-0053-production-security-perimeter-and-vpn-gating.md`
- `docs/adr/adr-0054-editor-chat-virtual-file-context.md`
- `docs/adr/adr-0055-tokenizer-backed-prompt-budgeting.md`
- `docs/adr/adr-0056-script-bank-seed-profiles.md`
- `docs/adr/adr-0057-settings-suggestions-from-tool-runs.md`
- `docs/adr/adr-0058-tool-datasets-library.md`
- `docs/adr/adr-0059-user-file-vault.md`
- `docs/adr/adr-0060-ui-contract-v2x-action-prefill.md`
- `docs/adr/adr-0061-asgi-correlation-middleware.md`
- `docs/adr/adr-0062-execution-queue-and-worker-loop.md`
- `docs/adr/adr-0063-runner-request-envelope-v1.md`
- `docs/adr/adr-0064-file-references-and-resolver.md`
- `docs/adr/adr-0065-runner-contract-v3-state-update-errors-and-session-promotions.md`
- `docs/adr/adr-0066-sir-convert-a-lot-v2-as-canonical-conversion-engine.md`
- `docs/adr/adr-0067-reagent-prep-chef-sds-markdown-first-offline-corpus.md`
- `docs/adr/adr-0068-textbook-corpus-pristine-cleanup-and-rag-ingest-governance.md`
- `docs/adr/adr-0069-group-seating-studio-domain-model.md`
- `docs/adr/adr-0070-group-seating-studio-slice-2-engine-and-snapshots.md`
- `docs/adr/adr-0071-group-seating-studio-fundamentals-workflow-and-saved-artifacts.md`
- `docs/adr/adr-0072-group-seating-studio-class-first-workspace-and-draft-kinds.md`
- `docs/adr/adr-0073-competitive-games-and-official-high-scores.md`
- `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md`
- `docs/adr/adr-0075-klassrumskartan-local-export-artifacts-and-conversion-boundary.md`
- `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md`
- `docs/adr/adr-0077-same-shell-transition-continuity.md`
- `docs/adr/adr-0078-local-password-reset-via-emailed-token.md`
- `docs/reference/ref-runner-contract-v3.md`
- `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`
- `docs/reference/ref-frontend-transition-continuity-v1.md`
- `docs/reference/ref-shared-tool-control-language-v1.md`
- `docs/reference/ref-frontend-design-system-codemap-2026-03-28.md`

### PRDs

- `docs/prd/prd-editor-sandbox-v0.1.md`
- `docs/prd/prd-group-seating-studio-v0.3.md`
- `docs/prd/prd-group-seating-studio-v0.2.md`
- `docs/prd/prd-script-hub-v0.1.md`
- `docs/prd/prd-script-hub-v0.2.md`
- `docs/prd/prd-spa-frontend-v0.1.md`
- `docs/prd/prd-tool-authoring-v0.1.md`
- `docs/prd/prd-group-seating-studio-v0.1.md`

### Releases

- `docs/releases/release-script-hub-v0.1.md`
- `docs/releases/release-script-hub-v0.2.0.md`

### Backlog Epics

- `docs/backlog/epics/epic-01-tool-catalog-and-browsing.md`
- `docs/backlog/epics/epic-02-identity-and-access-control.md`
- `docs/backlog/epics/epic-03-script-governance-workflow.md`
- `docs/backlog/epics/epic-04-dynamic-tool-scripts.md`
- `docs/backlog/epics/epic-05-huleedu-design-harmonization.md`
- `docs/backlog/epics/epic-06-quality-and-test-coverage.md`
- `docs/backlog/epics/epic-07-observability-and-operations.md`
- `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`
- `docs/backlog/epics/epic-09-security-hardening.md`
- `docs/backlog/epics/epic-10-interactive-ui-contract-and-curated-apps.md`
- `docs/backlog/epics/epic-11-full-vue-spa-migration.md`
- `docs/backlog/epics/epic-12-advanced-input-output-handling.md`
- `docs/backlog/epics/epic-13-toast-and-system-messages.md`
- `docs/backlog/epics/epic-14-admin-tool-authoring.md`
- `docs/backlog/epics/epic-15-user-profile-and-settings.md`
- `docs/backlog/epics/epic-16-catalog-discovery-and-personalization.md`
- `docs/backlog/epics/epic-17-observability-visualization-and-operations.md`
- `docs/backlog/epics/epic-18-execution-queue-and-worker-loop.md`
- `docs/backlog/epics/epic-19-runner-io-and-file-references-foundations.md`
- `docs/backlog/epics/epic-20-curated-app-reagent-prep-chef.md`
- `docs/backlog/epics/epic-21-curated-app-conversion-hub.md`
- `docs/backlog/epics/epic-22-textbook-corpus-pristine-cleanup-and-rag-readiness.md`
- `docs/backlog/epics/epic-23-group-seating-studio.md`
- `docs/backlog/epics/epic-24-group-seating-studio-slice-2.md`
- `docs/backlog/epics/epic-25-competitive-games-and-flunk-out-frenzy.md`
- `docs/backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md`
- `docs/backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md`
- `docs/backlog/epics/epic-28-skriptoteket-auth-authority-cutover-to-huleedu.md`
- `docs/backlog/epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md`
- `docs/backlog/epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md`

### Backlog Stories

- `docs/backlog/stories/story-23-01-group-seating-studio-skeleton.md`
- `docs/backlog/stories/story-23-02-group-seating-studio-manual-planner.md`
- `docs/backlog/stories/story-23-03-group-seating-studio-drag-drop-canvas.md`
- `docs/backlog/stories/story-23-04-group-seating-studio-seat-canvas.md`
- `docs/backlog/stories/story-23-05-group-seating-studio-sync-engine.md`
- `docs/backlog/stories/story-23-06-group-seating-studio-draft-persistence.md`
- `docs/backlog/stories/story-23-07-group-seating-studio-management-modals.md`
- `docs/backlog/stories/story-24-01-group-seating-studio-landing-page-fundamentals.md`
- `docs/backlog/stories/story-24-05-group-seating-studio-codebase-realignment-and-superseded-contract-removal.md`
- `docs/backlog/stories/story-24-02-group-seating-studio-class-first-workspace.md`
- `docs/backlog/stories/story-24-03-group-seating-studio-grouping-fundamentals-and-saved-groupings.md`
- `docs/backlog/stories/story-24-04-group-seating-studio-seating-fundamentals-and-saved-arrangements.md`
- `docs/backlog/stories/story-24-06-group-seating-studio-seating-slumpa-fundamentals.md`
- `docs/backlog/stories/story-24-07-group-seating-studio-overview-first-workspace-management.md`
- `docs/backlog/stories/story-24-08-group-seating-studio-landing-cutover-and-exit-to-origin.md`
- `docs/backlog/stories/story-25-01-competitive-games-substrate-and-flunk-out-frenzy-bootstrap-contract.md`
- `docs/backlog/stories/story-25-02-flunk-out-frenzy-local-runtime-vertical-slice.md`
- `docs/backlog/stories/story-25-03-competitive-play-pending-score-submission-and-typed-leaderboards.md`
- `docs/backlog/stories/story-25-04-competitive-play-replay-validation-and-official-score-promotion.md`
- `docs/backlog/stories/story-26-01-klassrumskartan-seating-pdf-poster-export-with-standalone-renderer.md`
- `docs/backlog/stories/story-26-02-klassrumskartan-class-list-import-from-file-with-preview-and-confirmation.md`
- `docs/backlog/stories/story-26-03-klassrumskartan-seating-xlsx-export.md`
- `docs/backlog/stories/story-26-04-klassrumskartan-grouping-pdf-export.md`
- `docs/backlog/stories/story-26-05-klassrumskartan-grouping-xlsx-export.md`
- `docs/backlog/stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md`
- `docs/backlog/stories/story-27-02-klassrumskartan-export-checkpoints-for-smart-history.md`
- `docs/backlog/stories/story-27-03-klassrumskartan-smart-seating-v1.md`
- `docs/backlog/stories/story-27-04-klassrumskartan-smart-grouping-v1.md`
- `docs/backlog/stories/story-27-05-klassrumskartan-smart-explanations-and-alternate-options.md`
- `docs/backlog/stories/story-27-06-klassrumskartan-planner-session-lanes-and-transition-matrix-remediation.md`
- `docs/backlog/stories/story-27-07-klassrumskartan-rules-workspace-and-dual-map-authoring.md`
- `docs/backlog/stories/story-28-01-frontend-auth-store-and-api-client-cutover-to-huleedu-session-contract.md`
- `docs/backlog/stories/story-28-02-auth-interruption-and-protected-route-handoff-on-huleedu-owned-session.md`
- `docs/backlog/stories/story-28-03-remove-local-auth-ownership-and-regenerate-client-contracts.md`
- `docs/backlog/stories/story-28-04-cross-app-auth-cutover-smoke-and-operator-runbook-proof.md`
- `docs/backlog/stories/story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md`
- `docs/backlog/stories/story-29-02-klassrumskartan-workspace-shell-compression-and-low-value-feedback-band-reduction.md`
- `docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md`
- `docs/backlog/stories/story-29-04-klassrumskartan-overview-hierarchy-and-class-first-dashboard-redesign.md`
- `docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md`
- `docs/backlog/stories/story-29-06-klassrumskartan-rules-workspace-rail-map-inspector-rebalance.md`
- `docs/backlog/stories/story-29-07-klassrumskartan-reduced-mobile-companion-layouts-and-breakpoint-cutover.md`
- `docs/backlog/stories/story-29-08-klassrumskartan-shared-custom-tooltip-system-and-global-hover-contract.md`
- `docs/backlog/stories/story-29-09-klassrumskartan-rule-visibility-and-tool-feedback-continuity.md`
- `docs/backlog/stories/story-30-01-frontend-transition-continuity-inventory-and-canonical-adoption-plan.md`
- `docs/backlog/stories/story-30-02-adopt-transition-continuity-across-editor-and-selector-shells.md`

### Backlog Reviews

- `docs/backlog/reviews/review-epic-02-local-password-reset-via-emailed-token.md`
- `docs/backlog/reviews/review-epic-06-linter-architecture-refactor.md`
- `docs/backlog/reviews/review-epic-07-correlation-middleware-asgi.md`
- `docs/backlog/reviews/review-epic-08-ai-completion.md`
- `docs/backlog/reviews/review-epic-08-ai-edit-ops-v2.md`
- `docs/backlog/reviews/review-epic-08-editor-ai-edit-ops-patch-only-alignment.md`
- `docs/backlog/reviews/review-epic-08-edit-ops-patch-workflow.md`
- `docs/backlog/reviews/review-epic-08-editor-chat-virtual-files-context.md`
- `docs/backlog/reviews/review-epic-08-llm-response-capture.md`
- `docs/backlog/reviews/review-epic-09-security-hardening.md`
- `docs/backlog/reviews/review-epic-14-editor-sandbox-preview.md`
- `docs/backlog/reviews/review-epic-14-tool-data-libraries.md`
- `docs/backlog/reviews/review-epic-14-ui-contract-v2x-action-prefill.md`
- `docs/backlog/reviews/review-epic-16-catalog-discovery.md`
- `docs/backlog/reviews/review-epic-17-observability-visualization.md`
- `docs/backlog/reviews/review-epic-18-execution-queue.md`
- `docs/backlog/reviews/review-epic-19-runner-io-and-file-references-foundations.md`
- `docs/backlog/reviews/review-epic-20-curated-app-reagent-prep-chef.md`
- `docs/backlog/reviews/review-epic-21-curated-app-conversion-hub.md`
- `docs/backlog/reviews/review-epic-22-textbook-corpus-pristine-cleanup-and-rag-readiness.md`
- `docs/backlog/reviews/review-epic-23-group-seating-studio.md`
- `docs/backlog/reviews/review-epic-24-group-seating-studio-slice-2-planning.md`
- `docs/backlog/reviews/review-epic-25-competitive-games-and-flunk-out-frenzy.md`
- `docs/backlog/reviews/review-epic-26-klassrumskartan-explicit-exports-and-class-list-import.md`
- `docs/backlog/reviews/review-epic-27-klassrumskartan-smart-assignment-v1.md`
- `docs/backlog/reviews/review-epic-28-skriptoteket-auth-authority-cutover-to-huleedu.md`
- `docs/backlog/reviews/review-epic-29-klassrumskartan-desktop-first-workspace-overhaul.md`
- `docs/backlog/reviews/review-epic-30-frontend-transition-continuity-for-same-shell-selectors.md`

### Backlog Sprints

- `docs/backlog/sprints/sprint-2025-12-21-spa-migration-foundations.md`
- `docs/backlog/sprints/sprint-2025-12-22-ui-contract-and-curated-apps.md`
- `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`
- `docs/backlog/sprints/sprint-2026-01-06-interactive-api-and-curated-apps.md`
- `docs/backlog/sprints/sprint-2026-01-20-ssr-typed-ui-rendering.md`
- `docs/backlog/sprints/sprint-2026-02-03-spa-toolchain-and-editor-island.md`
- `docs/backlog/sprints/sprint-2026-02-17-runtime-spa-island-mvp.md`
- `docs/backlog/sprints/sprint-2026-02-24-tool-data-libraries-v1.md`
- `docs/backlog/sprints/sprint-2026-03-03-tool-editor-dx-quick-wins.md`
- `docs/backlog/sprints/sprint-2026-03-17-tool-editor-sandbox-debug-details.md`
- `docs/backlog/sprints/sprint-2026-03-31-tool-editor-schema-editor-v1.md`
- `docs/backlog/sprints/sprint-2026-04-14-tool-editor-schema-validation-v1.md`
- `docs/backlog/sprints/sprint-2026-04-28-tool-editor-version-diff-v1.md`
- `docs/backlog/sprints/sprint-2026-05-12-tool-editor-runner-toolkit-and-intelligence.md`
- `docs/backlog/sprints/sprint-2026-05-26-tool-interaction-dx-high-yield.md`
- `docs/backlog/sprints/sprint-2026-06-09-tool-ui-contract-v2-action-defaults-and-file-refs.md`
- `docs/backlog/sprints/sprint-2026-06-23-tool-layout-editor-v1-contract-and-renderer.md`
- `docs/backlog/sprints/sprint-2026-07-07-tool-layout-editor-v1-drag-and-drop.md`

### Backlog PRs

- `docs/backlog/prs/pr-0001-editor-working-copy-composable-srp-modularization.md`
- `docs/backlog/prs/pr-0109-klassrumskartan-seating-slumpa-fundamentals.md`
- `docs/backlog/prs/pr-0110-klassrumskartan-overview-compact-class-and-classroom-management.md`
- `docs/backlog/prs/pr-0111-klassrumskartan-overview-resumable-cta-and-workspace-entry-polish.md`
- `docs/backlog/prs/pr-0113-klassrumskartan-borja-om-current-grouping-and-seating-draft-without-new-draft.md`
- `docs/backlog/prs/pr-0114-klassrumskartan-planner-shell-decomposition-and-shared-ui-primitives.md`
- `docs/backlog/prs/pr-0115-klassrumskartan-route-shell-orchestration-and-catalog-home-state-extraction.md`
- `docs/backlog/prs/pr-0116-klassrumskartan-room-template-editor-modularization-and-shared-room-scene.md`
- `docs/backlog/prs/pr-0117-klassrumskartan-seating-workspace-viewport-zoom-parity.md`
- `docs/backlog/prs/pr-0118-klassrumskartan-seating-export-contract-and-standalone-poster-scene-model.md`
- `docs/backlog/prs/pr-0119-klassrumskartan-seating-pdf-poster-renderer-and-artifact-delivery.md`
- `docs/backlog/prs/pr-0120-klassrumskartan-seating-export-action-teacher-flow-and-browser-proof.md`
- `docs/backlog/prs/pr-0121-klassrumskartan-shared-seating-export-webhook-dispatcher.md`
- `docs/backlog/prs/pr-0122-klassrumskartan-seating-export-production-wiring-and-hemma-deploy-orchestration.md`
- `docs/backlog/prs/pr-0123-klassrumskartan-seating-scene-remediation-wall-markers-localization-and-print-contrast.md`
- `docs/backlog/prs/pr-0124-klassrumskartan-seating-export-reload-recovery-and-draft-scoped-rehydration.md`
- `docs/backlog/prs/pr-0125-klassrumskartan-legacy-seating-export-callback-cutover-and-decommission.md`
- `docs/backlog/prs/pr-0126-klassrumskartan-wall-fixture-parity-resize-anchoring-and-poster-header-branding.md`
- `docs/backlog/prs/pr-0127-klassrumskartan-overview-roster-preview-overflow-and-fixed-height-scrolling.md`
- `docs/backlog/prs/pr-0128-klassrumskartan-grouping-and-seating-student-pool-split-pane-scrolling.md`
- `docs/backlog/prs/pr-0129-klassrumskartan-shared-planner-action-bar-zoning-and-grouping-toolbar-stabilization.md`
- `docs/backlog/prs/pr-0130-klassrumskartan-seating-toolbar-stabilization-export-cluster-alignment-and-responsive-proof.md`
- `docs/backlog/prs/pr-0131-klassrumskartan-overview-button-hierarchy-and-destructive-action-de-emphasis.md`
- `docs/backlog/prs/pr-0132-klassrumskartan-resume-history-affordance-normalization-and-planner-control-polish.md`
- `docs/backlog/prs/pr-0136-klassrumskartan-seat-drag-preview-and-room-editor-same-tool-toggle-removal.md`
- `docs/backlog/prs/pr-0137-klassrumskartan-class-list-import-remediation-example-corpus-and-overview-reconciliation.md`
- `docs/backlog/prs/pr-0138-seating-export-single-canonical-sir-convert-v2-key-and-runtime-wiring.md`
- `docs/backlog/prs/pr-0139-klassrumskartan-grouping-export-action-hierarchy-and-shared-presentation-contract.md`
- `docs/backlog/prs/pr-0140-klassrumskartan-grouping-xlsx-workbook-layout-and-artifact-delivery.md`
- `docs/backlog/prs/pr-0141-klassrumskartan-grouping-pdf-a4-portrait-presentation-renderer-and-delivery.md`
- `docs/backlog/prs/pr-0142-klassrumskartan-seating-xlsx-menu-option-local-export-contract-and-flow.md`
- `docs/backlog/prs/pr-0143-klassrumskartan-seating-xlsx-workbook-layout-and-artifact-delivery.md`
- `docs/backlog/prs/pr-0144-klassrumskartan-local-dev-export-runtime-parity-and-schema-remediation.md`
- `docs/backlog/prs/pr-0145-alembic-migration-integrity-and-full-idempotency-coverage.md`
- `docs/backlog/prs/pr-0146-klassrumskartan-seating-pdf-local-cutover-and-sir-convert-path-removal.md`
- `docs/backlog/prs/pr-0147-klassrumskartan-seating-only-teacher-distance-contract-reset.md`
- `docs/backlog/prs/pr-0149-klassrumskartan-seating-smart-rule-toolbar-and-non-overlapping-cluster-authoring-v1.md`
- `docs/backlog/prs/pr-0150-klassrumskartan-seating-export-checkpoint-registry-and-history-dedupe.md`
- `docs/backlog/prs/pr-0151-klassrumskartan-roster-global-smart-rules-and-draft-local-arrangement-boundary-reset.md`
- `docs/backlog/prs/pr-0152-klassrumskartan-planner-session-lanes-and-transition-matrix-remediation.md`
- `docs/backlog/prs/pr-0153-klassrumskartan-shared-export-flow-composable-and-planner-hotspot-reduction.md`
- `docs/backlog/prs/pr-0154-klassrumskartan-smart-seating-v1-backend-run-use-history-and-teacher-edge-placement.md`
- `docs/backlog/prs/pr-0155-klassrumskartan-rules-workspace-dual-map-authoring-and-summary-cutover.md`
- `docs/backlog/prs/pr-0156-st-29-01-control-language-freeze-primitive-contract-and-fe-codemap.md`
- `docs/backlog/prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md`
- `docs/backlog/prs/pr-0158-st-29-01-seating-workspace-adoption-of-shared-dense-tool-primitives.md`
- `docs/backlog/prs/pr-0161-st-29-02-shared-sticky-workspace-toolbar-and-transient-feedback-cutover.md`
- `docs/backlog/prs/pr-0162-st-07-07-public-http-dishka-adapter-and-observability-cutover.md`
- `docs/backlog/prs/pr-0163-st-07-07-http-route-dependency-cutover-off-hybrid-dishka-inject.md`
- `docs/backlog/prs/pr-0164-st-07-07-websocket-cutover-hybrid-compat-retirement-and-production-proof.md`
- `docs/backlog/prs/pr-0160-st-29-08-shared-custom-tooltip-primitive-and-dense-tool-adoption.md`
- `docs/backlog/prs/pr-0159-hemma-kernel-lane-recovery-6-14-freeze-and-6-17-cutover.md`
- `docs/backlog/prs/pr-0165-st-30-01-transition-continuity-decision-inventory-and-adoption-plan.md`
- `docs/backlog/prs/pr-0166-st-30-02-transition-continuity-adoption-and-remaining-transition-audit.md`
- `docs/backlog/prs/pr-0169-production-curated-app-visibility-gate.md`
- `docs/backlog/prs/pr-0170-st-09-07-public-edge-app-runtime-hardening.md`
- `docs/backlog/prs/pr-0171-st-09-08-hemma-edge-observability-and-host-lockdown.md`
- `docs/backlog/prs/pr-0172-local-password-reset-via-emailed-token.md`
- `docs/backlog/prs/pr-0173-home-messaging-registration-feedback-and-default-klassrumskartan-bookmark.md`
- `docs/backlog/prs/pr-0174-recovery-email-hardening-and-verification-resend-discoverability.md`
- `docs/backlog/prs/pr-0175-klassrumskartan-class-list-import-dropzone-in-create-edit-modal.md`
- `docs/backlog/prs/pr-0177-st-29-09-rule-visibility-and-tool-feedback-continuity.md`
- `docs/backlog/prs/pr-0148-conversion-hub-local-job-ledger-owned-status-download-boundary.md`
- `docs/backlog/prs/pr-0002-tool-run-composable-srp-modularization.md`
- `docs/backlog/prs/pr-0003-gate-submit-review-help-surfaces.md`
- `docs/backlog/prs/pr-0004-sandbox-transient-settings-input-multi-enum-clear-settings.md`
- `docs/backlog/prs/pr-0005-contract-v2-help-template-update.md`
- `docs/backlog/prs/pr-0006-hemma-incident-log-findings-2026-01-06.md`
- `docs/backlog/prs/pr-0007-editor-ai-chat-thread-tool-scoped-sse.md`
- `docs/backlog/prs/pr-0008-editor-chat-message-storage-minimal-c.md`
- `docs/backlog/prs/pr-0009-editor-chat-message-id-thread-persistence.md`
- `docs/backlog/prs/pr-0010-editor-save-restore-ux-clarity.md`
- `docs/backlog/prs/pr-0011-editor-mode-toggles-and-metadata-mode.md`
- `docs/backlog/prs/pr-0012-editor-cohesion-pass-input-selectors.md`
- `docs/backlog/prs/pr-0013-editor-ai-edit-ops-protocol-v1.md`
- `docs/backlog/prs/pr-0014-editor-ai-diff-preview-apply-undo.md`
- `docs/backlog/prs/pr-0015-editor-ai-edit-ops-anchor-patch-v2.md`
- `docs/backlog/prs/pr-0016-editor-ai-edit-ops-v2-hardening.md`
- `docs/backlog/prs/pr-0017-ai-provider-gpt5-cleanup.md`
- `docs/backlog/prs/pr-0018-ai-chat-provider-failover.md`
- `docs/backlog/prs/pr-0019-ai-srp-refactor-audit-hotspots.md`
- `docs/backlog/prs/pr-0020-ai-frontend-srp-refactor-audit-hotspots.md`
- `docs/backlog/prs/pr-0021-ai-chat-ops-response-capture-on-error.md`
- `docs/backlog/prs/pr-0022-editor-chat-virtual-file-context-retention.md`
- `docs/backlog/prs/pr-0023-tokenizer-backed-prompt-budgeting.md`
- `docs/backlog/prs/pr-0024-action-payload-skriptoteket-action-docs-prompt-alignment.md`
- `docs/backlog/prs/pr-0025-script-bank-curation-and-group-generator.md`
- `docs/backlog/prs/pr-0026-settings-suggestions-from-tool-runs.md`
- `docs/backlog/prs/pr-0027-ai-chat-ops-system-prompt-budget-followups.md`
- `docs/backlog/prs/pr-0050-openai-responses-structured-output-shape-fix.md`
- `docs/backlog/prs/pr-0051-runner-contract-v3-scaffolding.md`
- `docs/backlog/prs/pr-0052-runner-request-envelope-file-refs-contract-v3.md`
- `docs/backlog/prs/pr-0053-ui-contract-file-ref-picker-and-defaults.md`
- `docs/backlog/prs/pr-0054-user-file-vault-backend-and-resolver.md`
- `docs/backlog/prs/pr-0055-user-file-vault-ui-picker.md`
- `docs/backlog/prs/pr-0056-shared-segmented-toggle-and-file-picker-row.md`
- `docs/backlog/prs/pr-0057-browse-cta-removal-and-toolrunview-density-transition-polish.md`
- `docs/backlog/prs/pr-0058-kodredigerare-verktygsval-och-sok.md`
- `docs/backlog/prs/pr-0059-curated-app-reagent-prep-chef.md`
- `docs/backlog/prs/pr-0060-curated-app-reagent-prep-chef-risk-assessment.md`
- `docs/backlog/prs/pr-0061-story-003c-thin-adapter-parity-and-scientific-pdf-workload-validation.md`
- `docs/backlog/prs/pr-0062-curated-app-reagent-prep-chef-risk-assessment-best-effort-contract.md`
- `docs/backlog/prs/pr-0063-adr-0066-epic-21-conversion-hub-planning.md`
- `docs/backlog/prs/pr-0064-conversion-hub-backend-sir-convert-a-lot-v2-client-and-api.md`
- `docs/backlog/prs/pr-0065-conversion-hub-spa-ui-batch-and-preview.md`
- `docs/backlog/prs/pr-0066-migrate-e2e-tests-disable-html-to-pdf-preview-seeding.md`
- `docs/backlog/prs/pr-0148-conversion-hub-local-job-ledger-owned-status-download-boundary.md`
- `docs/backlog/prs/pr-0079-klassrumskartan-landing-page-ui-and-start-contract.md`
- `docs/backlog/prs/pr-0080-klassrumskartan-draft-resolve-and-explicit-resume-cta.md`
- `docs/backlog/prs/pr-0081-klassrumskartan-safe-asset-delete-and-landing-page-error-hardening.md`
- `docs/backlog/prs/pr-0078-klassrumskartan-fundamentals-contract-split-and-draft-lifecycle.md`
- `docs/backlog/prs/pr-0082-klassrumskartan-frontend-visible-legacy-removal.md`
- `docs/backlog/prs/pr-0083-klassrumskartan-frontend-store-and-types-contract-cleanup.md`
- `docs/backlog/prs/pr-0084-klassrumskartan-backend-contract-and-domain-pruning.md`
- `docs/backlog/prs/pr-0085-klassrumskartan-draft-kind-lifecycle-and-class-scoping.md`
- `docs/backlog/prs/pr-0086-klassrumskartan-class-workspace-summary-contract.md`
- `docs/backlog/prs/pr-0087-klassrumskartan-class-first-landing-and-workspace-state-machine.md`
- `docs/backlog/prs/pr-0088-klassrumskartan-task-entry-and-planner-return-semantics.md`
- `docs/backlog/prs/pr-0089-klassrumskartan-task-history-drawers-and-workspace-polish.md`
- `docs/backlog/prs/pr-0090-klassrumskartan-grouping-draft-history-contract.md`
- `docs/backlog/prs/pr-0091-klassrumskartan-grouping-workspace-fundamentals.md`
- `docs/backlog/prs/pr-0092-klassrumskartan-grouping-undo-redo-and-autosave-ux.md`
- `docs/backlog/prs/pr-0093-klassrumskartan-grouping-class-history-and-draft-continuity.md`
- `docs/backlog/prs/pr-0094-flunk-out-frenzy-curated-app-registration-and-discoverability.md`
- `docs/backlog/prs/pr-0095-flunk-out-frenzy-bespoke-route-and-shell.md`
- `docs/backlog/prs/pr-0096-flunk-out-frenzy-bootstrap-contract.md`
- `docs/backlog/prs/pr-0097-flunk-out-frenzy-playable-shell-host-and-runtime-lifecycle.md`
- `docs/backlog/prs/pr-0098-flunk-out-frenzy-runtime-core-and-hud-boundary.md`
- `docs/backlog/prs/pr-0099-flunk-out-frenzy-prototype-alpha-physics-and-rules.md`
- `docs/backlog/prs/pr-0100-flunk-out-frenzy-renderer-audio-and-playable-local-proof.md`
- `docs/backlog/prs/pr-0104-flunk-out-frenzy-post-review-runtime-and-shell-remediation.md`
- `docs/backlog/prs/pr-0107-flunk-out-frenzy-canvas-warning-cleanup-and-test-renderer-boundaries.md`
- `docs/backlog/prs/pr-0108-flunk-out-frenzy-runtime-lazy-load-and-game-bundle-splitting.md`
- `docs/backlog/prs/pr-0101-klassrumskartan-seating-room-builder-resize-ghost-preview-and-wall-anchoring.md`
- `docs/backlog/prs/pr-0102-klassrumskartan-seating-room-builder-object-visuals-labels-and-bench-coalescing.md`
- `docs/backlog/prs/pr-0103-klassrumskartan-seating-room-builder-viewport-zoom-reset-and-circular-seats.md`
- `docs/backlog/prs/pr-0067-curated-app-reagent-prep-chef-sds-corpus.md`
- `docs/backlog/prs/pr-0068-reagent-prep-chef-sds-pdfs-manual-download.md`
- `docs/backlog/prs/pr-0069-reagent-prep-chef-sds-index-available-in-docker.md`
- `docs/backlog/prs/pr-0073-textbook-corpus-governance-immutable-snapshot-and-job-reconciliation.md`
- `docs/backlog/prs/pr-0074-textbook-corpus-deterministic-mechanical-cleanup-and-issue-ledger.md`
- `docs/backlog/prs/pr-0075-textbook-corpus-multi-agent-manual-restoration-and-verification.md`
- `docs/backlog/prs/pr-0076-textbook-corpus-integrity-gates-and-pristine-build-contract.md`
- `docs/backlog/prs/pr-0077-textbook-corpus-rag-packaging-and-postgresql-vector-ingest-contract.md`
- `docs/backlog/prs/pr-0028-editor-focus-mode-and-ai-drawer-density.md`
- `docs/backlog/prs/pr-0029-editor-ai-ux-copy-and-smooth-typing.md`
- `docs/backlog/prs/pr-0030-editor-chat-streaming-reactivity-and-typing-status.md`
- `docs/backlog/prs/pr-0031-editor-ai-edit-ops-patch-only-alignment.md`
- `docs/backlog/prs/pr-0032-asgi-correlation-middleware.md`
- `docs/backlog/prs/pr-0033-large-file-srp-refactors-help-panel-docker-runner-edit-ops.md`
- `docs/backlog/prs/pr-0034-editor-ai-edit-ops-patch-lines-encoding.md`
- `docs/backlog/prs/pr-0035-editor-ai-edit-ops-gbnf-patch-only-grammar.md`
- `docs/backlog/prs/pr-0036-editor-ai-edit-ops-layered-diff-repair.md`
- `docs/backlog/prs/pr-0037-editor-ai-edit-ops-tolerant-diff-matching.md`
- `docs/backlog/prs/pr-0038-editor-ai-diff-preview-scroll-and-states.md`
- `docs/backlog/prs/pr-0039-execution-queue-worker-loop.md`
- `docs/backlog/prs/pr-0040-execution-queue-test-coverage.md`
- `docs/backlog/prs/pr-0041-ai-completion-failover-and-model-selection.md`
- `docs/backlog/prs/pr-0042-openai-prompt-cache-compat.md`
- `docs/backlog/prs/pr-0044-llm-telemetry-and-stats.md`
- `docs/backlog/prs/pr-0045-openai-responses-api-migration.md`
- `docs/backlog/prs/pr-0046-ai-inline-completion-harness.md`
- `docs/backlog/prs/pr-0047-ai-inline-completion-normalization-and-caps.md`
- `docs/backlog/prs/pr-0048-execution-queue-session-context-and-state-semantics.md`
- `docs/backlog/prs/pr-0049-backend-srp-refactor-god-modules.md`
- `docs/backlog/prs/pr-0043-ai-inline-completions-consent-hardening.md`

### Backlog Stories

- `docs/backlog/stories/story-01-01-profession-category-navigation.md`
- `docs/backlog/stories/story-02-01-user-model-and-identity-service.md`
- `docs/backlog/stories/story-02-02-admin-nomination-and-superuser-approval.md`
- `docs/backlog/stories/story-02-03-self-registration.md`
- `docs/backlog/stories/story-02-04-user-profile-and-password-change.md`
- `docs/backlog/stories/story-02-05-brute-force-lockout.md`
- `docs/backlog/stories/story-02-06-swedish-school-domain-allowlist-registration.md`
- `docs/backlog/stories/story-02-07-local-password-reset-via-emailed-token.md`
- `docs/backlog/stories/story-02-08-registration-preflight-validation-and-password-visibility.md`
- `docs/backlog/stories/story-02-09-distributed-password-reset-hardening-for-scaled-auth.md`
- `docs/backlog/stories/story-03-01-submit-script-suggestion.md`
- `docs/backlog/stories/story-03-02-admin-review-and-decision.md`
- `docs/backlog/stories/story-03-03-publish-and-depublish-tools.md`
- `docs/backlog/stories/story-04-01-versioned-script-model.md`
- `docs/backlog/stories/story-04-02-docker-runner-execution.md`
- `docs/backlog/stories/story-04-03-admin-script-editor-ui.md`
- `docs/backlog/stories/story-04-04-governance-audit-rollback.md`
- `docs/backlog/stories/story-04-05-user-execution.md`
- `docs/backlog/stories/story-04-06-script-bank-seeding.md`
- `docs/backlog/stories/story-05-01-css-foundation.md`
- `docs/backlog/stories/story-05-02-simple-templates.md`
- `docs/backlog/stories/story-05-03-browse-templates.md`
- `docs/backlog/stories/story-05-04-suggestion-templates.md`
- `docs/backlog/stories/story-05-05-admin-templates.md`
- `docs/backlog/stories/story-05-06-htmx-enhancements.md`
- `docs/backlog/stories/story-05-07-frontend-stabilization.md`
- `docs/backlog/stories/story-05-08-responsive-header.md`
- `docs/backlog/stories/story-05-09-codemirror-mobile-floor.md`
- `docs/backlog/stories/story-05-10-editor-layout-mobile.md`
- `docs/backlog/stories/story-05-11-hamburger-htmx-bug.md`
- `docs/backlog/stories/story-05-12-mobile-editor-ux.md`
- `docs/backlog/stories/story-06-01-test-coverage-improvements.md`
- `docs/backlog/stories/story-06-02-repository-test-coverage.md`
- `docs/backlog/stories/story-06-03-error-middleware-test-coverage.md`
- `docs/backlog/stories/story-06-04-script-bank-tool-tests.md`
- `docs/backlog/stories/story-06-05-web-pages-test-coverage.md`
- `docs/backlog/stories/story-06-06-test-warnings-hygiene.md`
- `docs/backlog/stories/story-06-07-toast-integration.md`
- `docs/backlog/stories/story-06-08-editor-ui-fixes.md`
- `docs/backlog/stories/story-06-09-playwright-test-isolation.md`
- `docs/backlog/stories/story-06-10-context-rule-architecture.md`
- `docs/backlog/stories/story-06-11-quick-fix-actions.md`
- `docs/backlog/stories/story-06-12-lint-panel-navigation.md`
- `docs/backlog/stories/story-06-13-gutter-filter-polish.md`
- `docs/backlog/stories/story-06-14-headless-test-harness.md`
- `docs/backlog/stories/story-06-15-frontend-critical-test-gaps.md`
- `docs/backlog/stories/story-06-16-backend-srp-refactor-god-modules.md`
- `docs/backlog/stories/story-07-01-structured-logging-and-correlation.md`
- `docs/backlog/stories/story-07-02-healthz-and-metrics-endpoints.md`
- `docs/backlog/stories/story-07-03-opentelemetry-tracing.md`
- `docs/backlog/stories/story-07-04-logging-redaction-and-policy.md`
- `docs/backlog/stories/story-07-05-observability-stack-deployment.md`
- `docs/backlog/stories/story-07-06-asgi-correlation-middleware.md`
- `docs/backlog/stories/story-07-07-retire-hybrid-dishka-fastapi-compatibility-layer-and-restore-supported-web-di.md`
- `docs/backlog/stories/story-08-01-help-framework.md`
- `docs/backlog/stories/story-08-02-login-help.md`
- `docs/backlog/stories/story-08-02-robust-email-verification.md`
- `docs/backlog/stories/story-08-03-email-verification-frontend-route.md`
- `docs/backlog/stories/story-08-03-home-help-index.md`
- `docs/backlog/stories/story-08-04-catalog-help.md`
- `docs/backlog/stories/story-08-05-results-and-downloads-help.md`
- `docs/backlog/stories/story-08-06-contributor-help.md`
- `docs/backlog/stories/story-08-07-admin-dashboard-help.md`
- `docs/backlog/stories/story-08-08-editor-help-overview.md`
- `docs/backlog/stories/story-08-09-editor-help-test-area.md`
- `docs/backlog/stories/story-08-10-script-editor-intelligence.md`
- `docs/backlog/stories/story-08-11-script-editor-intelligence-phase2.md`
- `docs/backlog/stories/story-08-12-script-editor-intelligence-phase3.md`
- `docs/backlog/stories/story-08-13-tool-usage-instructions.md`
- `docs/backlog/stories/story-08-14-ai-inline-completions.md`
- `docs/backlog/stories/story-08-15-contract-lint-source-ids.md`
- `docs/backlog/stories/story-08-16-ai-edit-suggestions.md`
- `docs/backlog/stories/story-08-17-tabby-edit-suggestions-ab-testing.md`
- `docs/backlog/stories/story-08-18-ai-prompt-system-v1.md`
- `docs/backlog/stories/story-08-19-ai-prompt-eval-harness-live-backend.md`
- `docs/backlog/stories/story-08-20-editor-ai-chat-drawer-mvp.md`
- `docs/backlog/stories/story-08-21-ai-structured-crud-edit-ops-protocol-v1.md`
- `docs/backlog/stories/story-08-22-editor-ai-diff-preview-apply-undo.md`
- `docs/backlog/stories/story-08-23-ai-chat-streaming-proxy-and-config.md`
- `docs/backlog/stories/story-08-24-ai-edit-ops-anchor-patch-v2.md`
- `docs/backlog/stories/story-08-25-ai-provider-gpt5-cleanup.md`
- `docs/backlog/stories/story-08-26-ai-chat-provider-failover.md`
- `docs/backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- `docs/backlog/stories/story-08-28-ai-chat-ops-response-capture-on-error.md`
- `docs/backlog/stories/story-08-29-ai-edit-ops-patch-lines-encoding.md`
- `docs/backlog/stories/story-08-30-ai-completion-failover-and-model-selection.md`
- `docs/backlog/stories/story-08-31-openai-responses-api-migration.md`
- `docs/backlog/stories/story-08-32-ai-inline-completion-harness.md`
- `docs/backlog/stories/story-08-33-ai-inline-completion-normalization-and-caps.md`
- `docs/backlog/stories/story-08-34-klassrumskartan-contextual-help.md`
- `docs/backlog/stories/story-09-01-http-security-headers.md`
- `docs/backlog/stories/story-09-02-content-security-policy.md`
- `docs/backlog/stories/story-09-03-firewall-audit.md`
- `docs/backlog/stories/story-09-04-production-perimeter-hardening-v2.md`
- `docs/backlog/stories/story-09-05-content-security-policy-spa.md`
- `docs/backlog/stories/story-09-06-production-curated-app-visibility-gate.md`
- `docs/backlog/stories/story-09-07-public-edge-app-runtime-hardening.md`
- `docs/backlog/stories/story-09-08-hemma-edge-observability-and-host-lockdown.md`
- `docs/backlog/stories/story-10-01-tool-ui-contract-v2.md`
- `docs/backlog/stories/story-10-02-tool-sessions.md`
- `docs/backlog/stories/story-10-03-ui-payload-normalizer.md`
- `docs/backlog/stories/story-10-04-interactive-tool-api.md`
- `docs/backlog/stories/story-10-05-curated-apps-registry.md`
- `docs/backlog/stories/story-10-06-curated-apps-execution.md`
- `docs/backlog/stories/story-10-07-ssr-renderer-for-typed-ui.md`
- `docs/backlog/stories/story-10-08-spa-island-toolchain.md`
- `docs/backlog/stories/story-10-09-editor-spa-island-mvp.md`
- `docs/backlog/stories/story-10-10-runtime-spa-island-mvp.md`
- `docs/backlog/stories/story-11-01-frontend-workspace-and-spa-scaffold.md`
- `docs/backlog/stories/story-11-02-ui-library-and-design-tokens.md`
- `docs/backlog/stories/story-11-03-spa-hosting-fastapi-integration.md`
- `docs/backlog/stories/story-11-04-api-v1-and-openapi-typescript.md`
- `docs/backlog/stories/story-11-05-auth-flow-and-route-guards.md`
- `docs/backlog/stories/story-11-06-spa-browse-views.md`
- `docs/backlog/stories/story-11-07-tool-run-and-results.md`
- `docs/backlog/stories/story-11-08-my-runs-views.md`
- `docs/backlog/stories/story-11-09-curated-apps-views.md`
- `docs/backlog/stories/story-11-10-suggestions-flows.md`
- `docs/backlog/stories/story-11-11-admin-tools-management.md`
- `docs/backlog/stories/story-11-12-script-editor-migration.md`
- `docs/backlog/stories/story-11-13-cutover-and-e2e.md`
- `docs/backlog/stories/story-11-14-admin-tools-status-enrichment.md`
- `docs/backlog/stories/story-11-15-my-tools-view.md`
- `docs/backlog/stories/story-11-16-editor-workflow-actions.md`
- `docs/backlog/stories/story-11-17-tool-metadata-editor.md`
- `docs/backlog/stories/story-11-18-maintainer-management.md`
- `docs/backlog/stories/story-11-19-help-framework.md`
- `docs/backlog/stories/story-11-20-tool-taxonomy-editor.md`
- `docs/backlog/stories/story-11-21-unified-landing-page.md`
- `docs/backlog/stories/story-11-22-remove-login-route.md`
- `docs/backlog/stories/story-11-23-tool-owner-and-maintainer-permissions.md`
- `docs/backlog/stories/story-11-24-home-view-messaging-reset-for-curated-library.md`
- `docs/backlog/stories/story-12-01-multi-file-upload.md`
- `docs/backlog/stories/story-12-02-native-pdf-output-helper.md`
- `docs/backlog/stories/story-12-03-personalized-tool-settings.md`
- `docs/backlog/stories/story-12-04-interactive-text-dropdown-inputs.md`
- `docs/backlog/stories/story-12-05-session-file-persistence.md`
- `docs/backlog/stories/story-12-06-session-file-cleanup.md`
- `docs/backlog/stories/story-12-07-explicit-session-file-reuse-controls.md`
- `docs/backlog/stories/story-13-01-toast-system-primitives-spa.md`
- `docs/backlog/stories/story-13-02-replace-inline-action-feedback-with-toasts.md`
- `docs/backlog/stories/story-13-03-standardize-inline-system-messages.md`
- `docs/backlog/stories/story-13-04-toastify-profile-actions.md`
- `docs/backlog/stories/story-14-01-admin-quick-create-draft-tools.md`
- `docs/backlog/stories/story-14-02-draft-slug-edit-and-publish-guards.md`
- `docs/backlog/stories/story-14-03-sandbox-next-actions-parity.md`
- `docs/backlog/stories/story-14-04-sandbox-input-schema-form-preview.md`
- `docs/backlog/stories/story-14-05-editor-sandbox-settings-parity.md`
- `docs/backlog/stories/story-14-06-editor-sandbox-preview-snapshots.md`
- `docs/backlog/stories/story-14-07-editor-draft-head-locks.md`
- `docs/backlog/stories/story-14-08-editor-sandbox-settings-isolation.md`
- `docs/backlog/stories/story-14-09-editor-input-schema-modes.md`
- `docs/backlog/stories/story-14-10-editor-schema-json-qol.md`
- `docs/backlog/stories/story-14-11-editor-sandbox-run-debug-details-api.md`
- `docs/backlog/stories/story-14-12-editor-sandbox-debug-panel.md`
- `docs/backlog/stories/story-14-13-editor-schema-editor-json-codemirror.md`
- `docs/backlog/stories/story-14-14-editor-schema-editor-snippets-and-diagnostics.md`
- `docs/backlog/stories/story-14-15-editor-schema-validation-endpoint.md`
- `docs/backlog/stories/story-14-16-editor-schema-validation-errors-ux.md`
- `docs/backlog/stories/story-14-17-editor-version-diff-view.md`
- `docs/backlog/stories/story-14-18-editor-review-navigation-and-compare.md`
- `docs/backlog/stories/story-14-19-runner-toolkit-helper-module.md`
- `docs/backlog/stories/story-14-20-editor-intelligence-toolkit-support.md`
- `docs/backlog/stories/story-14-21-tool-run-actions-sticky-inputs.md`
- `docs/backlog/stories/story-14-22-tool-run-ux-progress-and-file-references.md`
- `docs/backlog/stories/story-14-23-ui-contract-action-defaults-prefill.md`
- `docs/backlog/stories/story-14-24-ui-contract-file-references.md`
- `docs/backlog/stories/story-14-25-ui-contract-layout-editor-v1-output.md`
- `docs/backlog/stories/story-14-26-ui-renderer-layout-editor-v1-click-assign.md`
- `docs/backlog/stories/story-14-27-layout-editor-v1-drag-drop.md`
- `docs/backlog/stories/story-14-28-layout-editor-v1-ux-polish-and-a11y.md`
- `docs/backlog/stories/story-14-29-editor-pro-mode-combined-bundle-view.md`
- `docs/backlog/stories/story-14-30-editor-working-copy-persistence-indexeddb.md`
- `docs/backlog/stories/story-14-31-editor-focus-mode-collapse-sidebar.md`
- `docs/backlog/stories/story-14-32-editor-cohesion-pass-input-selectors.md`
- `docs/backlog/stories/story-14-33-script-bank-curation-and-group-generator.md`
- `docs/backlog/stories/story-14-34-settings-suggestions-from-tool-runs.md`
- `docs/backlog/stories/story-14-35-tool-datasets-crud-and-picker.md`
- `docs/backlog/stories/story-14-36-user-file-vault-and-picker.md`
- `docs/backlog/stories/story-14-37-ui-output-vega-lite.md`
- `docs/backlog/stories/story-14-38-kodredigerare-verktygsval-och-sok.md`
- `docs/backlog/stories/story-15-01-user-profile-redesign.md`
- `docs/backlog/stories/story-15-02-avatar-upload.md`
- `docs/backlog/stories/story-16-01-favorites-domain-and-database.md`
- `docs/backlog/stories/story-16-02-favorites-api-endpoints.md`
- `docs/backlog/stories/story-16-03-flat-catalog-api-with-filtering.md`
- `docs/backlog/stories/story-16-04-recently-used-tools-api.md`
- `docs/backlog/stories/story-16-05-flat-catalog-vue-view.md`
- `docs/backlog/stories/story-16-06-tool-card-favorites-toggle.md`
- `docs/backlog/stories/story-16-07-home-view-favorites-and-recent.md`
- `docs/backlog/stories/story-16-08-catalog-cleanup-and-review.md`
- `docs/backlog/stories/story-16-09-default-klassrumskartan-bookmark.md`
- `docs/backlog/stories/story-17-01-grafana-datasource-verification.md`
- `docs/backlog/stories/story-17-02-http-metrics-dashboard.md`
- `docs/backlog/stories/story-17-03-prometheus-alerting-rules.md`
- `docs/backlog/stories/story-17-04-jaeger-public-access.md`
- `docs/backlog/stories/story-17-05-runbook-verification.md`
- `docs/backlog/stories/story-17-06-user-session-metrics.md`
- `docs/backlog/stories/story-17-07-login-events-audit-trail.md`
- `docs/backlog/stories/story-18-01-execution-queue-worker-loop.md`
- `docs/backlog/stories/story-19-01-runner-request-envelope.md`
- `docs/backlog/stories/story-19-02-file-refs-resolver-and-promotion.md`
- `docs/backlog/stories/story-19-03-runner-contract-v3-structured-errors-state-update-and-promotions.md`
- `docs/backlog/stories/story-19-04-runner-request-factory-seam.md`
- `docs/backlog/stories/story-19-05-runner-result-parser-seam.md`
- `docs/backlog/stories/story-19-06-runner-contract-selection-seam.md`
- `docs/backlog/stories/story-19-07-story-003c-thin-adapter-consumer-adoption-and-scientific-pdf-workload.md`
- `docs/backlog/stories/story-20-01-curated-app-reagent-prep-chef.md`
- `docs/backlog/stories/story-20-02-curated-app-reagent-prep-chef-risk-assessment.md`
- `docs/backlog/stories/story-20-03-curated-app-reagent-prep-chef-sds-corpus.md`
- `docs/backlog/stories/story-21-01-curated-app-conversion-hub-v1.md`
- `docs/backlog/stories/story-21-02-migrate-off-html-to-pdf-preview-and-retire-tool.md`
- `docs/backlog/stories/story-22-01-textbook-corpus-cleanup-pipeline-and-manual-restoration-workflow.md`
- `docs/backlog/stories/story-23-01-group-seating-studio-skeleton.md`
- `docs/backlog/stories/story-23-02-group-seating-studio-manual-planner.md`
- `docs/backlog/stories/story-23-03-group-seating-studio-drag-drop-canvas.md`
- `docs/backlog/stories/story-23-04-group-seating-studio-seat-canvas.md`
- `docs/backlog/stories/story-23-05-group-seating-studio-sync-engine.md`

### Reference

- `docs/reference/ref-competitive-games-cross-cutting-programme.md`
- `docs/reference/ref-curated-app-flunk-out-frenzy-architecture-and-foundational-code.md`
- `docs/reference/ref-ai-completion-architecture.md`
- `docs/reference/ref-ai-inline-completion-harness.md`
- `docs/reference/ref-ai-script-generation-kb-llm.md`
- `docs/reference/ref-ai-script-generation-kb.md`
- `docs/reference/ref-architecture.md`
- `docs/reference/ref-codemirror-integration.md`
- `docs/reference/ref-editor-sandbox-preview-plan.md`
- `docs/reference/ref-frontend-test-gaps-2025-12-29.md`
- `docs/reference/ref-group-seating-studio-product-direction-2026-03-21.md`
- `docs/reference/ref-frontend-design-system-codemap-2026-03-28.md`
- `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`
- `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md`
- `docs/reference/ref-home-server-architecture.md`
- `docs/reference/ref-home-server-cleanup-timers.md`
- `docs/reference/ref-home-server-cli-tools.md`
- `docs/reference/ref-home-server-nginx-proxy.md`
- `docs/reference/ref-home-server-security-hardening.md`
- `docs/reference/ref-hemma-critical-paths-2026-01-06.md`
- `docs/reference/ref-implementation-map-script-hub-v0-2.md`
- `docs/reference/ref-linter-architecture.md`
- `docs/reference/ref-reagent-prep-chef-hazard-shortcard-alignment-policy.md`
- `docs/reference/ref-reagent-prep-chef-riskunderlag-skolpraxis.md`
- `docs/reference/ref-review-workflow.md`
- `docs/reference/ref-scripting-api-contracts.md`
- `docs/reference/ref-scripting-governance-deferred-options.md`
- `docs/reference/ref-sprint-planning-workflow.md`
- `docs/reference/ref-toast-system-messages.md`
- `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
- `docs/reference/ref-tool-editor-framework-codemap.md`

### Reference Reports

- `docs/reference/reports/ref-ai-edit-suggestions-kb-context-budget-blocker.md`
- `docs/reference/reports/ref-architectural-review-epic-04.md`
- `docs/reference/reports/ref-devops-skill-research.md`
- `docs/reference/reports/ref-external-observability-integration.md`
- `docs/reference/reports/ref-frontend-expert-review-epic-05.md`
- `docs/reference/reports/ref-hemma-host-freeze-investigation-2026-01-03.md`
- `docs/reference/reports/ref-hemma-host-freeze-stack-alignment-2026-01-03.md`
- `docs/reference/reports/ref-hemma-gpu-compatibility-notes-2026-01-05.md`
- `docs/reference/reports/ref-hemma-runpm0-before-after-2026-01-05.md`
- `docs/reference/reports/ref-hemma-perflevel-auto-vs-high-2026-01-05.md`
- `docs/reference/ref-llama-kodassistent-eval-v1.md`
- `docs/reference/ref-llama-kodassistent-eval-v2.md`
- `docs/reference/reports/ref-hemma-canonical-chat-v3-run-2026-01-05.md`
- `docs/reference/reports/ref-hemma-incident-log-2026-01-02-083355-083455.md`
- `docs/reference/reports/ref-hemma-incident-log-2026-01-04-153900-154030.md`
- `docs/reference/reports/ref-hemma-kdump-amdgpu-blacklist-dc0-test-2026-01-11.md`
- `docs/reference/reports/ref-hemma-bios-update-guide-2026-01-03.md`
- `docs/reference/reports/ref-htmx-ux-enhancement-plan.md`
- `docs/reference/reports/ref-lead-architect-suggestions-post-mvp.md`
- `docs/reference/reports/ref-lead-developer-assessment-epic-04.md`
- `docs/reference/reports/ref-runner-tool-code-modularization-map.md`
- `docs/reference/reports/ref-security-perimeter-vpn-gating-ssh-and-observability.md`
- `docs/reference/reports/ref-vue-spa-migration-assessment.md`
- `docs/reference/reports/ref-vue-spa-migration-roadmap.md`
- `docs/reference/reports/ref-editor-chat-virtual-file-context-tokenizers-2026-01-11.md`

### Runbooks

- `docs/runbooks/runbook-editor-ai-pipeline.md`
- `docs/runbooks/runbook-agent-browser-automation.md`
- `docs/runbooks/runbook-feedback-email-cli.md`
- `docs/runbooks/runbook-gpu-ai-workloads.md`
- `docs/runbooks/runbook-home-server.md`
- `docs/runbooks/runbook-huleedu-integration.md`
- `docs/runbooks/runbook-openai-responses-api.md`
- `docs/runbooks/runbook-observability-grafana.md`
- `docs/runbooks/runbook-observability-logging.md`
- `docs/runbooks/runbook-observability-metrics.md`
- `docs/runbooks/runbook-observability-tracing.md`
- `docs/runbooks/runbook-observability.md`
- `docs/runbooks/runbook-runner-image.md`
- `docs/runbooks/runbook-script-bank-seeding-home-server.md`
- `docs/runbooks/runbook-script-bank-seeding.md`
- `docs/runbooks/runbook-tabby-codemirror.md`
- `docs/runbooks/runbook-testing.md`
- `docs/runbooks/runbook-user-management.md`

### Tooling

- `scripts/ai_prompt_eval/README.md`

### Templates

- `docs/templates/template-adr.md`
- `docs/templates/template-codemap.md`
- `docs/templates/template-epic.md`
- `docs/templates/template-pr.md`
- `docs/templates/template-prd.md`
- `docs/templates/template-reference.md`
- `docs/templates/template-release-notes.md`
- `docs/templates/template-review.md`
- `docs/templates/template-runbook.md`
- `docs/templates/template-sprint-plan.md`
- `docs/templates/template-story.md`

### Meta

- `docs/_meta/README.md`

## Agent support

- Start-here: `AGENTS.md`
- Session handoff: `.agents/handoff.md`
- Next-session prompt template: `.agents/next-session-instruction-prompt-template.md`

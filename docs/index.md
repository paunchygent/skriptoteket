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
- Implementation map (v0.2): `docs/reference/ref-implementation-map-script-hub-v0-2.md`
- Editor sandbox preview plan: `docs/reference/ref-editor-sandbox-preview-plan.md`
- Tool editor framework codemap: `docs/reference/ref-tool-editor-framework-codemap.md`
- Migration roadmap (SPA): `docs/reference/reports/ref-vue-spa-migration-roadmap.md`
- Toasts + system messages (SPA): `docs/reference/ref-toast-system-messages.md`
- Active sprint: `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`
- Release notes: `docs/releases/`
- ADRs: `docs/adr/`
- Backlog: `docs/backlog/`

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

### PRDs

- `docs/prd/prd-editor-sandbox-v0.1.md`
- `docs/prd/prd-script-hub-v0.1.md`
- `docs/prd/prd-script-hub-v0.2.md`
- `docs/prd/prd-spa-frontend-v0.1.md`
- `docs/prd/prd-tool-authoring-v0.1.md`

### Releases

- `docs/releases/release-script-hub-v0.1.md`

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

### Backlog Reviews

- `docs/backlog/reviews/review-epic-06-linter-architecture-refactor.md`
- `docs/backlog/reviews/review-epic-08-ai-completion.md`
- `docs/backlog/reviews/review-epic-09-security-hardening.md`
- `docs/backlog/reviews/review-epic-14-editor-sandbox-preview.md`
- `docs/backlog/reviews/review-epic-16-catalog-discovery.md`
- `docs/backlog/reviews/review-epic-17-observability-visualization.md`

### Backlog Sprints

- `docs/backlog/sprints/sprint-2025-12-21-spa-migration-foundations.md`
- `docs/backlog/sprints/sprint-2025-12-22-ui-contract-and-curated-apps.md`
- `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`
- `docs/backlog/sprints/sprint-2026-01-06-interactive-api-and-curated-apps.md`
- `docs/backlog/sprints/sprint-2026-01-20-ssr-typed-ui-rendering.md`
- `docs/backlog/sprints/sprint-2026-02-03-spa-toolchain-and-editor-island.md`
- `docs/backlog/sprints/sprint-2026-02-17-runtime-spa-island-mvp.md`
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

### Backlog Stories

- `docs/backlog/stories/story-01-01-profession-category-navigation.md`
- `docs/backlog/stories/story-02-01-user-model-and-identity-service.md`
- `docs/backlog/stories/story-02-02-admin-nomination-and-superuser-approval.md`
- `docs/backlog/stories/story-02-03-self-registration.md`
- `docs/backlog/stories/story-02-04-user-profile-and-password-change.md`
- `docs/backlog/stories/story-02-05-brute-force-lockout.md`
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
- `docs/backlog/stories/story-07-01-structured-logging-and-correlation.md`
- `docs/backlog/stories/story-07-02-healthz-and-metrics-endpoints.md`
- `docs/backlog/stories/story-07-03-opentelemetry-tracing.md`
- `docs/backlog/stories/story-07-04-logging-redaction-and-policy.md`
- `docs/backlog/stories/story-07-05-observability-stack-deployment.md`
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
- `docs/backlog/stories/story-09-01-http-security-headers.md`
- `docs/backlog/stories/story-09-02-content-security-policy.md`
- `docs/backlog/stories/story-09-03-firewall-audit.md`
- `docs/backlog/stories/story-09-04-production-perimeter-hardening-v2.md`
- `docs/backlog/stories/story-09-05-content-security-policy-spa.md`
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
- `docs/backlog/stories/story-17-01-grafana-datasource-verification.md`
- `docs/backlog/stories/story-17-02-http-metrics-dashboard.md`
- `docs/backlog/stories/story-17-03-prometheus-alerting-rules.md`
- `docs/backlog/stories/story-17-04-jaeger-public-access.md`
- `docs/backlog/stories/story-17-05-runbook-verification.md`
- `docs/backlog/stories/story-17-06-user-session-metrics.md`
- `docs/backlog/stories/story-17-07-login-events-audit-trail.md`

### Reference

- `docs/reference/ref-ai-completion-architecture.md`
- `docs/reference/ref-ai-script-generation-kb-llm.md`
- `docs/reference/ref-ai-script-generation-kb.md`
- `docs/reference/ref-architecture.md`
- `docs/reference/ref-codemirror-integration.md`
- `docs/reference/ref-dynamic-tool-scripts.md`
- `docs/reference/ref-editor-sandbox-preview-plan.md`
- `docs/reference/ref-execution-architecture.md`
- `docs/reference/ref-frontend-test-gaps-2025-12-29.md`
- `docs/reference/ref-home-server-architecture.md`
- `docs/reference/ref-home-server-cleanup-timers.md`
- `docs/reference/ref-home-server-cli-tools.md`
- `docs/reference/ref-home-server-nginx-proxy.md`
- `docs/reference/ref-home-server-security-hardening.md`
- `docs/reference/ref-implementation-map-script-hub-v0-2.md`
- `docs/reference/ref-linter-architecture.md`
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
- `docs/reference/reports/ref-hemma-canonical-chat-v3-run-2026-01-05.md`
- `docs/reference/reports/ref-hemma-incident-log-2026-01-02-083355-083455.md`
- `docs/reference/reports/ref-hemma-incident-log-2026-01-04-153900-154030.md`
- `docs/reference/reports/ref-hemma-bios-update-guide-2026-01-03.md`
- `docs/reference/reports/ref-htmx-ux-enhancement-plan.md`
- `docs/reference/reports/ref-lead-architect-suggestions-post-mvp.md`
- `docs/reference/reports/ref-lead-developer-assessment-epic-04.md`
- `docs/reference/reports/ref-security-perimeter-vpn-gating-ssh-and-observability.md`
- `docs/reference/reports/ref-vue-spa-migration-assessment.md`
- `docs/reference/reports/ref-vue-spa-migration-roadmap.md`

### Runbooks

- `docs/runbooks/runbook-gpu-ai-workloads.md`
- `docs/runbooks/runbook-home-server.md`
- `docs/runbooks/runbook-huleedu-integration.md`
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

### Templates

- `docs/templates/template-adr.md`
- `docs/templates/template-epic.md`
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

- Start-here: `.agent/readme-first.md`
- Session handoff: `.agent/handoff.md`
- Next-session prompt template: `.agent/next-session-instruction-prompt-template.md`

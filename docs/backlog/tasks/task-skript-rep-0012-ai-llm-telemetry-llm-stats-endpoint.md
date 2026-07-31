---
type: task
id: TASK-SKRIPT-REP-0012
title: 'AI: LLM telemetry + llm-stats endpoint'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Prometheus exports LLM pipeline metrics (requests, latency, error rate, tokens,
  cached-token ratio) for inline completions, chat, and edit-ops.
- Structured logs include LLM usage fields (`prompt_tokens`, `completion_tokens`,
  `cached_tokens`, `provider`, `model`, `request_type`, `outcome`).
- Grafana dashboard panels visualize LLM tokens, cached-token ratio, p95 latency,
  and error rate by request type.
- An internal `/observability/llm-stats` endpoint returns a JSON summary (last 1h/24h)
  for quick LLM-assisted analysis.
- PromQL queries used by the endpoint are documented in the PR doc or runbook for
  reproducibility.
---

## Context


We lack consistent, queryable telemetry for LLM efficiency (token usage, cached-token ratio,
latency, and error rate). Debugging is currently log-only and does not provide quick summaries
for cost or performance analysis.

## Impact And Escalation

No separate impact and escalation is stated in the source.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Plan


1. Extend `src/skriptoteket/observability/metrics.py` with LLM metrics:
   - Counters: `skriptoteket_llm_requests_total{request_type,provider,model,outcome}`
   - Histograms: `skriptoteket_llm_request_duration_seconds{request_type,provider,model}`
   - Counters: `huleedu_llm_tokens_total{request_type,provider,model,token_type}`
     where `token_type` ∈ `prompt|completion|cached`.
2. Instrument LLM providers (OpenAI + local llama) to:
   - Observe latency, increment outcome counts.
   - Extract usage tokens and increment token counters.
   - Log structured usage fields for Loki aggregation.
3. Add `/observability/llm-stats` endpoint:
   - Query Prometheus for last 1h/24h aggregates (tokens, cached-token ratio, p95 latency, error rate).
   - Return a compact JSON summary optimized for LLM ingestion.
4. Add Grafana dashboard JSON under `observability/grafana/provisioning/dashboards/`:
   - Panels: tokens (prompt/completion/cached), cached-token ratio, p95 latency, error rate by request type.
5. Document the PromQL queries used by the endpoint (PR doc or runbook) for reproducibility.

## Implementation Steps

No separate implementation steps is stated in the source.

## Proof


- Unit tests for metrics registration and logging field presence.
- Manual: generate inline completion/chat/edit-ops requests and verify `/metrics` includes LLM series.
- Manual: validate `/observability/llm-stats` response matches Prometheus query outputs.
- Grafana: confirm dashboard panels populate and match PromQL outputs.

## Validation

No separate validation is stated in the source.

## Stop Conditions


- Revert the metrics/logging instrumentation and disable the dashboard provisioning.

## Lessons Learned

No separate lessons learned is stated in the source.

## Notes

No separate notes is stated in the source.

### Source: Goal


- Add metrics + logs that make LLM pipeline efficiency observable.
- Provide a lightweight JSON summary endpoint for quick analysis (and LLM-assisted reviews).
- Visualize the key LLM pipeline KPIs in Grafana.

### Source: Non-goals


- Payload compatibility changes (handled in PR-0042).
- Prompt rewrites or UX changes.

## Readiness

No separate readiness is stated in the source.

## Closeout

No separate closeout is stated in the source.

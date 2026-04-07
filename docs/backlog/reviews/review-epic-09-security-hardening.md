---
type: review
id: REV-EPIC-09
title: "Review: Security hardening for production deployment (VPN gating)"
status: pending
owners: "agents"
created: 2026-01-01
updated: 2026-04-06
reviewer: "lead-developer"
epic: EPIC-09
adrs:
  - ADR-0053
stories:
  - ST-09-04
---

## TL;DR

We want to reduce exposure of administrative surfaces on `hemma.hule.education` by adopting a VPN-gated perimeter:

- Make SSH reachable only via VPN (stop exposing port 22 publicly).
- Consider moving observability domains (Grafana/Prometheus/Jaeger) behind VPN as well, while keeping remote browser
  access via VPN clients on MacBook + phone.

## Problem Statement

Even with strong authentication and edge hardening, a public internet-facing server receives constant probing:

- SSH brute-force bots (noise + risk)
- HTTP scanners probing sensitive paths and uncommon methods
- Credential probing against observability domains

We want a defense-in-depth posture where only trusted devices can reach admin surfaces at all.

## Proposed Solution

1. Keep existing edge hardening + Fail2ban as baseline.
2. Decide and document the **target perimeter**:
   - SSH behind VPN (yes/no, and which VPN).
   - Observability behind VPN (yes/no).
3. Stage rollout with an explicit break-glass plan to avoid lockout.

Architecture is captured in ADR-0053; decision support is in the research report referenced there.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0053-production-security-perimeter-and-vpn-gating.md` | Requirements, options, open decisions | 5 min |
| `docs/reference/reports/ref-security-perimeter-vpn-gating-ssh-and-observability.md` | Tradeoffs + rollout steps | 10 min |
| `docs/backlog/stories/story-09-04-production-perimeter-hardening-v2.md` | Acceptance criteria + verification | 5 min |

**Total estimated time:** ~20 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| SSH should be VPN-only (close public port 22) | Removes most SSH bot traffic + reduces attack surface | [ ] |
| VPN tech choice (Tailscale vs WireGuard) | Tradeoff between UX/ops and control/self-hosting | [ ] |
| Observability should be VPN-only (Grafana/Prometheus/Jaeger) | Reduces probing while keeping remote browser access | [ ] |
| Break-glass plan required before rollout | Avoids accidental lockout; preserves “no monitor required” ops | [ ] |

## Review Checklist

- [ ] ADR defines clear target state and open decisions
- [ ] Requirements cover MacBook + phone + agent SSH workflows
- [ ] Risks and mitigations are explicit (especially lockout risk)
- [ ] Follow-up stories are testable and appropriately scoped

---

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-06
**Verdict:** pending

### Required Changes

Decide the target perimeter before implementation starts: SSH-only VPN, observability-only VPN, or both.

### Suggestions (Optional)

Keep the break-glass recovery steps in the same document so lockout risk stays visible during review.

### Decision Approvals

- [ ] SSH behind VPN
- [ ] VPN tech choice
- [ ] Observability behind VPN
- [ ] Break-glass plan

---

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | Review record | Replaced template placeholders with an explicit pending-review perimeter decision surface. |
| 2 | ADR-0053 | Kept the VPN gating question, rollout risks, and recovery posture visible for review. |

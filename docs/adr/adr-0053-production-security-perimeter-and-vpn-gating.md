---
type: adr
id: ADR-0053
title: "Production security perimeter and VPN gating (SSH + observability)"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-01
supersedes: []
---

## Context

The home server (`hemma.hule.education`) is continuously probed:

- SSH brute-force attempts against port `22`
- Web probes against common sensitive paths (`/.env`, `/.git/*`, `wp-*`, `cgi-bin`, `*.php`)
- Probing of observability subdomains (Grafana/Prometheus/Jaeger) even when protected by auth

We already have defense-in-depth measures in place:

- Edge hardening in nginx-proxy (drop common probes + scanner methods with `444`)
- Fail2ban on SSH with a `recidive` jail (repeat offenders can be permabanned)
- Loki/Promtail ingestion of nginx-proxy access logs with query-friendly labels (`vhost`, `client_ip`, `method`, `status`)

### Requirements

- Preserve full SSH access (keys, incl. root) from:
  - MacBook (primary)
  - Phone (emergency)
  - Local agent workflow (uses SSH from the developer machine)
- Avoid “keyboard/monitor required” recovery during normal operations.
- Keep observability usable from a browser while remote (Grafana/Prometheus/Jaeger).

## Decision

Adopt a **VPN-gated admin perimeter** as the long-term target state:

- **SSH**: stop exposing port `22` publicly; require VPN membership for SSH access.
- **Observability**: evaluate moving Grafana/Prometheus/Jaeger behind VPN as well (instead of being public + auth).

This ADR is `proposed` because the following implementation decisions remain open:

1. **VPN technology choice**: Tailscale vs WireGuard.
2. **Scope of VPN gating**:
   - SSH only
   - SSH + observability
3. **Break-glass plan** for lockout scenarios (documented before rollout).

### Current implementation status (as of 2026-01-01)

- SSH is VPN-gated in production: router port-forward for `22/tcp` is removed and UFW allows SSH only via `tailscale0`
  and the LAN break-glass subnet.
- Observability subdomains remain publicly reachable (still protected by auth) pending the decision for option B.

### Options considered

#### Option A: Tailscale

- Pros: very low operational overhead; excellent NAT traversal; great Mac/iOS clients; device ACLs; quick rollout.
- Cons: third-party control plane; requires trusting vendor + account security; exit strategy should be documented.

#### Option B: WireGuard

- Pros: fully self-hosted; minimal trusted third parties; very small attack surface.
- Cons: more ops work (key distribution, NAT traversal, peer management); mobile UX more manual; higher “lockout”
  risk if misconfigured.

## Consequences

- Major reduction in SSH bot traffic (and security noise), shifting SSH to “only trusted devices can reach it”.
- Observability exposure can be reduced while preserving remote browser access (by using VPN on client devices).
- Requires careful staged rollout and documented recovery steps to avoid accidental lockout.

## Follow-up work

See:

- Story: `docs/backlog/stories/story-09-04-production-perimeter-hardening-v2.md`
- Research: `docs/reference/reports/ref-security-perimeter-vpn-gating-ssh-and-observability.md`

---
type: reference
id: REF-security-perimeter-vpn-gating-ssh-and-observability
title: "Research: VPN gating SSH and observability on hemma"
status: active
owners: "agents"
created: 2026-01-01
topic: "security"
---

This document supports **ADR-0053** by explaining VPN gating options and what they mean in practice for:

- SSH access from MacBook + phone
- Remote browser access to Grafana/Prometheus/Jaeger
- The local agent workflow (SSH from the dev machine)

## Executive summary

- **A (SSH behind VPN)** is the highest security ROI: it removes almost all SSH bot traffic by eliminating public
  reachability of port `22`.
- **B (observability behind VPN)** is desirable but has a DNS/UX decision: do you accept using VPN-specific hostnames
  (e.g., MagicDNS) or do you want `*.hemma.hule.education` to resolve to VPN IPs when on VPN (split DNS)?
- **Tailscale** is the lowest operational risk for A/B (especially with iOS + NAT traversal). **WireGuard** is fully
  self-hosted but requires more ops effort and has a higher “lockout” risk if misconfigured.

## Current baseline (already implemented)

- nginx-proxy edge hardening drops common probes and scanner methods with `444`.
- Fail2ban: `sshd` + `recidive` (repeat offenders can be permabanned).
- SSH is VPN-gated (Tailscale): public reachability of port `22` is removed; SSH is allowed only via `tailscale0` and
  the LAN break-glass subnet.
- Loki/Promtail: nginx-proxy access logs are queryable by `vhost`, `client_ip`, `method`, `status`.

## Requirements and constraints

- **No-console ops**: normal operations must not require attaching a keyboard/monitor.
- **SSH keys remain the auth mechanism** (root included).
- **Remote access from phone** must work (break-glass).
- **Agent assistance must still work**: if SSH becomes VPN-only, the dev machine running the agent must have the VPN
  client connected when using `ssh hemma ...`.

## Option 1: Tailscale

Tailscale is a managed mesh VPN built on WireGuard:

- Each device gets a stable VPN IP (typically `100.64.0.0/10`).
- It is designed to “just work” through NAT and mobile networks (no port forwarding required).
- Device access control is managed via the Tailscale admin UI (ACLs / device approval).

### What changes for you (practice)

- MacBook: install Tailscale app → connect → `ssh` to the server’s Tailscale IP (or a MagicDNS name).
- Phone: install Tailscale → connect → emergency SSH works over VPN.
- Port 22 can be closed publicly once confirmed working.

### Pros / cons

- Pros: easiest rollout; best mobile experience; very low ops burden; strong NAT traversal.
- Cons: depends on a third-party control plane; must secure the Tailscale account as a critical dependency.

## Option 2: WireGuard (self-hosted)

WireGuard is a lightweight VPN protocol. A self-hosted setup usually means:

- You manage keys and peer configs yourself.
- You manage NAT traversal / port forwarding (unless using a relay).
- You must maintain a simple “VPN user management” workflow over time.

### What changes for you (practice)

- MacBook/phone need WireGuard configs imported/managed.
- Server needs a stable UDP port exposed publicly (often `51820/udp`), unless you have an existing router VPN.
- SSH can still be closed publicly once VPN reachability is verified.

### Pros / cons

- Pros: full control; fewer third-party dependencies; smallest possible stack.
- Cons: more ops work; higher misconfiguration risk; more fragile mobile UX when roaming between networks.

## A) SSH behind VPN: staged rollout (recommended)

This is the safest migration shape regardless of VPN choice:

1. **Install VPN on Hemma** (do not change firewall/sshd yet).
2. **Install VPN on MacBook and phone** and confirm the VPN can reach Hemma.
3. **Verify SSH over VPN**:
   - Use the VPN IP (or VPN DNS name) and your existing SSH keys.
4. **Add a break-glass plan** before closing public SSH:
   - Confirm phone VPN + SSH works.
   - Ensure there is a documented recovery path (router access, alternative VPN, or temporary reopen procedure).
5. **Restrict/close public port 22**:
   - Either firewall-allow SSH only from the VPN interface/IP range, or fully close public `22`.
6. **Observe for 24–48h** and verify you can still do routine ops without exceptions.

Decision points for A:

- Which VPN: Tailscale vs WireGuard
- Whether to keep a temporary “dual access” window during rollout (recommended)

## B) Observability behind VPN: what “remote browser access” means

If you want to access Grafana/Prometheus/Jaeger remotely **from a browser**, you have three practical patterns:

1. **Keep public domains, keep auth, add banning/edge hardening** (least change, still probed)
2. **Use VPN-only hostnames** (MagicDNS / tailnet domain) and keep observability effectively private
3. **Use split DNS** so `grafana.hemma.hule.education` resolves to a VPN IP when you are on VPN

### Key constraint: DNS

If `grafana.hemma.hule.education` resolves to the public IP (`83.252.61.217`), your browser traffic will go over the
public internet and will not be “VPN-gated” unless you implement split DNS or use VPN-specific names.

### Recommended approach for B (low-risk)

- First: keep public access but harden (auth + edge drops + Fail2ban on repeated 401s).
- Then: decide between “VPN-only hostnames” vs “split DNS”.
- Finally: lock down observability vhosts so only VPN-sourced traffic is allowed.

## Recommendation (for decision)

- If you want the fastest, safest reduction of SSH bots with the lowest operational risk: **choose Tailscale for A**.
- For B, decide whether you are comfortable using a VPN-specific name for Grafana/Prometheus/Jaeger; if yes, B becomes
  much simpler. If no, plan split DNS explicitly before committing to VPN-only observability.

## Open questions to answer in review

1. Do you accept a third-party control plane (Tailscale), or do you want fully self-hosted (WireGuard)?
2. For observability remote access, do you require `*.hemma.hule.education` domains specifically, or is a VPN-specific
   hostname acceptable?
3. What is the break-glass plan if VPN access fails while port 22 is closed publicly?

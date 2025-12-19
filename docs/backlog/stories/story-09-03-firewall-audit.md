---
type: story
id: ST-09-03
title: "Firewall audit and cleanup"
epic: EPIC-09
status: done
owners: "agents"
created: 2025-12-17
acceptance_criteria:
  - "Given UFW rules are listed, when audited, then the stale port 5000 allow-rule is removed"
  - "Given UFW rules are listed, when audited, then all remaining rules have a documented purpose"
  - "Given UFW is enabled, when audited, then only required ports are exposed (22, 80, 443)"
  - "Given firewall changes are applied, when verified, then the final UFW status is recorded"
---

## Goal

Audit UFW firewall rules on home server and remove stale/unused rules.

## Acceptance Criteria

- [ ] Stale port 5000 rule removed (nothing listening)
- [ ] All remaining rules have documented purpose
- [ ] Only necessary ports exposed (22, 80, 443)
- [ ] Firewall status documented

## Current State

```
To                         Action      From
--                         ------      ----
5000                       ALLOW       Anywhere    <- STALE (nothing listening)
22/tcp                     ALLOW       Anywhere    <- SSH
80/tcp                     ALLOW       Anywhere    <- HTTP redirect
443/tcp                    ALLOW       Anywhere    <- HTTPS
```

## Implementation

```bash
# Remove stale rules
sudo ufw delete allow 5000
sudo ufw delete allow 5000/tcp

# Verify
sudo ufw status
```

## Expected Final State

```
To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

## Notes

- Port 5000 was likely from a previous Flask app or Docker registry test
- Calico/vxlan rules are for Kubernetes (if applicable)

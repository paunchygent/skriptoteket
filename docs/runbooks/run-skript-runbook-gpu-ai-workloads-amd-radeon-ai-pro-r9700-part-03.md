---
type: runbook
id: RUN-SKRIPT-runbook-gpu-ai-workloads-amd-radeon-ai-pro-r9700-PART-03
title: 'Runbook: GPU AI Workloads (AMD Radeon AI PRO R9700) — part 03'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: RUN-SKRIPT-runbook-gpu-ai-workloads-amd-radeon-ai-pro-r9700
part: 3
---

```bash
### If kernel updates break driver
ssh hemma "sudo dkms status"
ssh hemma "sudo dkms autoinstall"
ssh hemma "sudo reboot"
```

## Rollback

No separate source material was recorded for this section.

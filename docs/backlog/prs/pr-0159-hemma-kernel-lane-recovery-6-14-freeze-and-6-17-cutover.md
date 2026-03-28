---
type: pr
id: PR-0159
title: "Hemma kernel lane recovery, 6.14 freeze, and 6.17 cutover"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-03-28
stories: []
tags: ["devops", "hemma", "kernel", "dkms", "rocm", "ops"]
acceptance_criteria:
  - "The current Hemma wedged-package state is documented with the exact audit commands, gating checks, and recovery commands required to restore apt/dpkg while preserving the working 6.14 kernel lane."
  - "The steady-state 6.14 policy is explicit: which package families are held out of routine apt upgrade runs, which kernel packages are kept manual to avoid autoremove, and which operator habits are forbidden."
  - "The future 6.17 migration path is documented as a controlled maintenance workflow with prerequisite support-matrix checks, dry-run commands, pre-reboot DKMS validation, fallback expectations, and post-reboot verification."
  - "The task ends by asking for explicit approval to execute the plan on Hemma."
---

> Execution update (2026-03-28): completed the immediate Hemma recovery. The broken `6.17.0-14` HWE lane was
> removed, `dpkg`/`apt` were restored to a clean state, the active `6.14.0-37` kernel packages were marked
> manual, and the AMDGPU/ROCm/DKMS lane was put on hold. The future `6.17` cutover remains deferred and should
> be treated as a separate maintenance change.

## Problem

Hemma is currently running on `6.14.0-37-generic`, but the package manager is wedged by a
partially configured HWE transition to `6.17.0-14`. Read-only inspection on 2026-03-28 showed:

- `linux-headers-6.17.0-14-generic` is half-configured.
- `linux-generic-hwe-24.04` and `linux-headers-generic-hwe-24.04` are unpacked but unconfigured.
- `linux-image-6.17.0-14-generic` has pending trigger processing.
- DKMS modules currently present on Hemma include `amdgpu/6.16.13-2278356.24.04` and
  `it87/v1.0-207-ga9eb249.20251226`, both successfully built for `6.14.0-37-generic`.

This blocks normal package maintenance and creates a recurring failure mode where `dpkg --configure -a`
simply replays the broken `6.17` configure hooks.

## Goal

Define and then execute a Hemma-safe operational policy that:

1. recovers from the current wedged `6.17.0-14` package state without disturbing the working `6.14` lane,
2. freezes Hemma on a stable `6.14` kernel/driver/runtime baseline for routine maintenance,
3. and describes the exact future cutover sequence for moving to `6.17` intentionally, rather than via
   opportunistic HWE drift.

## Non-goals

- Shipping `6.17` immediately on Hemma.
- Changing Skriptoteket application code or Docker deployment layout.
- Replacing AMDGPU/ROCm with a different GPU stack.
- Treating this as a general Ubuntu recipe; the commands are Hemma-specific and must preserve the working
  GPU runtime.

## Implementation plan

### 1. Capture a read-only baseline on Hemma

Run these commands first and save the output into the task notes / execution log:

```bash
ssh hemma "/bin/bash -lc 'uname -r'"
ssh hemma "/bin/bash -lc 'sudo dpkg --audit || true'"
ssh hemma "/bin/bash -lc 'sudo dkms status || true'"
ssh hemma "/bin/bash -lc 'apt-cache policy linux-generic-hwe-24.04 linux-image-generic-hwe-24.04 linux-headers-generic-hwe-24.04'"
ssh hemma "/bin/bash -lc \"dpkg -l | egrep 'linux-(image|headers)-(6.14|6.17)|linux-(generic|image-generic|headers-generic)-hwe-24.04|amdgpu|rocm|it87|dkms'\""
```

Gate:

- Confirm the running kernel is still `6.14.0-37-generic`.
- Confirm the broken state is limited to the `6.17.0-14` transition.
- Confirm the working AMDGPU/ROCm lane is still attached to `6.14`, not already partially rebuilt for `6.17`.

### 2. Dry-run the recovery before changing anything

Simulate removal of the broken HWE transition:

```bash
ssh hemma "/bin/bash -lc 'sudo apt-get -s purge \
  linux-generic-hwe-24.04 \
  linux-image-generic-hwe-24.04 \
  linux-headers-generic-hwe-24.04 \
  linux-image-6.17.0-14-generic \
  linux-headers-6.17.0-14-generic'"
```

Gate:

- Do **not** proceed unless the simulation preserves:
  - `linux-image-6.14.0-37-generic`
  - `linux-headers-6.14.0-37-generic`
  - the currently installed AMDGPU/ROCm packages required for the live GPU stack

### 3. Recover the wedged package state

If the dry-run is clean, execute the recovery:

```bash
ssh hemma "/bin/bash -lc 'sudo apt-get purge -y \
  linux-generic-hwe-24.04 \
  linux-image-generic-hwe-24.04 \
  linux-headers-generic-hwe-24.04 \
  linux-image-6.17.0-14-generic \
  linux-headers-6.17.0-14-generic'"

ssh hemma "/bin/bash -lc 'sudo apt-get -f install -y'"
ssh hemma "/bin/bash -lc 'sudo dpkg --configure -a'"
ssh hemma "/bin/bash -lc 'sudo dpkg --audit || true'"
```

Expected result:

- `dpkg --audit` returns clean or only expected non-kernel follow-up items.
- `apt` is usable again.
- Hemma remains booted on `6.14.0-37-generic`.

### 4. Freeze the steady-state `6.14` lane

Prevent accidental kernel drift while keeping normal user-space updates available:

```bash
ssh hemma "/bin/bash -lc 'sudo apt-mark manual linux-image-6.14.0-37-generic linux-headers-6.14.0-37-generic'"
ssh hemma "/bin/bash -lc \"dpkg -l | awk '\$1 == \\\"ii\\\" && (\$2 ~ /^(amdgpu|rocm)/ || \$2 == \\\"dkms\\\" || \$2 ~ /^it87/) { print \$2 }'\""
```

Then hold the exact package set discovered above, for example:

```bash
ssh hemma "/bin/bash -lc 'sudo apt-mark hold dkms <amdgpu-packages-from-audit> <rocm-packages-from-audit> <optional-it87-package-if-retained>'"
```

Steady-state policy:

- Routine `apt upgrade` runs may update general user-space packages.
- Routine `apt upgrade` runs must **not** advance kernel/HWE, DKMS, AMDGPU, or ROCm packages.
- Do **not** reinstall `linux-generic-hwe-24.04` during routine maintenance.
- Do **not** run `apt autoremove` casually on Hemma; verify kernel retention first.

### 5. Validate the frozen `6.14` lane

Run after recovery/pinning:

```bash
ssh hemma "/bin/bash -lc 'uname -r'"
ssh hemma "/bin/bash -lc 'sudo dpkg --audit || true'"
ssh hemma "/bin/bash -lc 'sudo dkms status || true'"
ssh hemma "/bin/bash -lc 'sudo apt upgrade --simulate'"
ssh hemma "/bin/bash -lc 'rocminfo | head -n 20'"
ssh hemma "/bin/bash -lc 'rocm-smi || true'"
```

Gate:

- `uname -r` stays on `6.14.0-37-generic`
- `dpkg --audit` is clean
- `dkms status` shows the expected modules for the running kernel
- `apt upgrade --simulate` no longer tries to re-enter the broken `6.17.0-14` transition
- GPU tooling still responds on the live host

### 6. Planned future `6.17` cutover

Do **not** reuse the old broken `6.17.0-14` lane. Treat the future move as a fresh maintenance change.

Preconditions:

- Re-check AMD support matrix for the target date and release train.
- Upgrade Hemma to the AMD-supported Ubuntu point-release baseline for `6.17`.
- Choose the matching AMDGPU/ROCm release before re-enabling kernel movement.
- Ensure an operator is available for reboot/fallback observation.

Suggested sequence:

```bash
ssh hemma "/bin/bash -lc 'sudo apt-mark unhold dkms <amdgpu-packages> <rocm-packages> <optional-it87-package>'"
ssh hemma "/bin/bash -lc 'sudo apt update'"
ssh hemma "/bin/bash -lc 'sudo apt-get -s install linux-generic-hwe-24.04 linux-image-generic-hwe-24.04 linux-headers-generic-hwe-24.04'"
```

Gate:

- Do **not** proceed unless the dry-run shows the intended target kernel only, with no surprise removals.
- Confirm the selected AMDGPU/ROCm release explicitly supports the target Ubuntu + HWE combination.

Then execute the coordinated upgrade:

```bash
ssh hemma "/bin/bash -lc 'sudo apt-get install -y linux-generic-hwe-24.04 linux-image-generic-hwe-24.04 linux-headers-generic-hwe-24.04 <validated-amdgpu/rocm-updates>'"
ssh hemma "/bin/bash -lc 'sudo dkms status || true'"
ssh hemma "/bin/bash -lc 'sudo dkms autoinstall || true'"
ssh hemma "/bin/bash -lc 'sudo update-grub'"
ssh hemma "/bin/bash -lc 'sudo reboot'"
```

Post-reboot validation:

```bash
ssh hemma "/bin/bash -lc 'uname -r'"
ssh hemma "/bin/bash -lc 'sudo dkms status || true'"
ssh hemma "/bin/bash -lc 'sudo dpkg --audit || true'"
ssh hemma "/bin/bash -lc 'rocminfo | head -n 20'"
ssh hemma "/bin/bash -lc 'rocm-smi || true'"
ssh hemma "/bin/bash -lc 'sudo apt upgrade --simulate'"
```

Success criteria:

- Host boots the intended `6.17` kernel
- DKMS modules are built for the running kernel
- GPU runtime is healthy
- `apt` remains clean after reboot

## Test plan

- Run `pdm run docs-validate` after adding/updating this task doc.
- When executing on Hemma, preserve the console output of each audit, dry-run, recovery, and validation command.
- Treat the recovery and `6.17` migration as separate change windows with separate validation records.

## Rollback plan

If the recovery dry-run shows removal of the working `6.14` lane or current GPU runtime packages, stop and revise the purge set before executing.

If the future `6.17` cutover fails after package install but before reboot:

- stop and inspect `sudo dkms status`
- inspect the failing module logs
- do not reboot into the new kernel until DKMS is clean or the new kernel packages are removed

If the future `6.17` cutover fails after reboot:

- boot the known-good `6.14` entry from GRUB
- re-hold the kernel/driver packages
- remove the failed `6.17` lane and return to the frozen `6.14` policy

## Execution request

When this task is approved, ask explicitly:

> Do you want me to execute the Hemma recovery plan now: clear the wedged `6.17.0-14` state, freeze the host on `6.14`, validate `apt`/DKMS/ROCm health, and leave the `6.17` cutover as a later maintenance change?

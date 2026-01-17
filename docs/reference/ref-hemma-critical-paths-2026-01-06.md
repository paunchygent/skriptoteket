---
type: reference
id: REF-hemma-critical-paths-2026-01-06
title: "Hemma critical paths and operations inventory (2026-01-06)"
status: active
owners: "agents"
created: 2026-01-06
updated: 2026-01-17
topic: "devops"
---

## Overview

This reference lists critical paths, configs, and operational dependencies for
the Hemma host. It is meant to support restores, reimages, and fast audits.

Host snapshot context:
- Hostname: `paunchygent-server`
- OS: Ubuntu 24.04.3 LTS (Noble)
- Backup snapshot: `/mnt/backup/hemma-root-20260106/` (~110G)

## Access & SSH

- SSH server config: `/etc/ssh/sshd_config`, `/etc/ssh/sshd_config.d/`
- Client config: `/etc/ssh/ssh_config`, `/etc/ssh/ssh_config.d/`
- Host keys: `/etc/ssh/ssh_host_*`
- Authorized keys:
  - Root: `/root/.ssh/authorized_keys`
  - Paunchygent: `/home/paunchygent/.ssh/authorized_keys`
- Autoinstall seed for headless reinstall (SSH-from-start):
  - Seed mount: `/mnt/seed` (label `CIDATA` on `/dev/sdd1`)
  - Files: `/mnt/seed/user-data`, `/mnt/seed/meta-data`,
    `/mnt/seed/authorized_keys_all.txt` (deduped union of all keys)

## Firewall & Security

- UFW status: active (default deny incoming)
- UFW config: `/etc/ufw/`, `/etc/default/ufw`
- UFW rules:
  - IPv4: `/etc/ufw/user.rules`
  - IPv6: `/etc/ufw/user6.rules`
- Fail2ban: `/etc/fail2ban/`, service `fail2ban.service`
- SSH watchdog:
  - Service: `ssh-watchdog.service`
  - Timer: `ssh-watchdog.timer`
- Hardware watchdog (hard reset on wedges):
  - Driver: `sp5100_tco` (SP5100/SB800 TCO watchdog)
  - Module options: `/etc/modprobe.d/sp5100_tco.conf` (`nowayout=1 heartbeat=60`)
  - Health-gated petter: `/etc/systemd/system/health-watchdog.service` + `/usr/local/bin/health-watchdog.sh`
  - Keep watchdog running across warm reboots: `watchdog.stop_on_reboot=0`
    - Normal boot cmdline: `/etc/default/grub` (then `update-grub` + reboot)
    - Crash-kernel cmdline: `/etc/default/kdump-tools` (then `kdump-config unload && kdump-config load`)
  - Module loader: `/etc/systemd/system/sp5100-tco-watchdog.service`
  - systemd watchdog config: `/etc/systemd/system.conf.d/99-watchdog.conf`

## Power Rail Monitoring (PSU)

- Sensors package: `lm-sensors`
- Super I/O driver: out-of-tree `it87` DKMS module (IT8665E)
  - Source: `/usr/src/it87` (repo: frankcrawford/it87)
  - Auto-load: `/etc/modules-load.d/it87.conf`
- Logging script: `/usr/local/bin/log-power-rails.sh`
- Systemd: `log-power-rails.service` + `log-power-rails.timer`
- Logs:
  - `/root/logs/power-rails/sensors-*.log` (snapshots, 30-day retention)
  - `/root/logs/power-rails/alerts.log` (threshold breaches only)

### UFW rules (snapshot: 2026-01-06)

```
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
Anywhere on vxlan.calico   ALLOW IN    Anywhere
Anywhere on cali+          ALLOW IN    Anywhere
Anywhere                   DENY IN     206.189.22.108
8082/tcp                   ALLOW IN    172.16.0.0/12   # LLM server for Docker
22/tcp on tailscale0       ALLOW IN    Anywhere
22/tcp                     ALLOW IN    192.168.0.0/24
22/tcp                     ALLOW IN    Anywhere        # SSH WAN access during reimage
80/tcp (v6)                ALLOW IN    Anywhere (v6)
443/tcp (v6)               ALLOW IN    Anywhere (v6)
Anywhere (v6) on vxlan.calico ALLOW IN    Anywhere (v6)
Anywhere (v6) on cali+     ALLOW IN    Anywhere (v6)
22/tcp (v6) on tailscale0  ALLOW IN    Anywhere (v6)
22/tcp (v6)                ALLOW IN    Anywhere (v6)    # SSH WAN access during reimage
```

## Network & Tailscale

- Netplan configs: `/etc/netplan/01-netcfg.yaml`
- Resolved symlink: `/etc/resolv.conf` → `/run/systemd/resolve/stub-resolv.conf`
- Tailscale:
  - Config: `/etc/default/tailscaled`
  - State: `/var/lib/tailscale/`
  - Service: `tailscaled.service`

## Web & Reverse Proxy

- Nginx system config: `/etc/nginx/`
- Nginx sites: `/etc/nginx/sites-available/`, `/etc/nginx/sites-enabled/`
- Nginx proxy stack (compose + certs):
  - `/home/paunchygent/infrastructure/`
  - `/home/paunchygent/infrastructure/nginx/`
  - `/home/paunchygent/infrastructure/nginx/certs/`
  - `/home/paunchygent/infrastructure/htpasswd/`

## Docker & Containers

- Docker data: `/var/lib/docker/`
- Docker (snap) service: `snap.docker.dockerd.service`
- Compose stacks:
  - `/home/paunchygent/infrastructure/docker-compose.yml`
  - `/home/paunchygent/apps/skriptoteket/compose.prod.yaml`
  - `/home/paunchygent/apps/skriptoteket/compose.dev.yaml`

## Shared PostgreSQL (production)

- Container name: `shared-postgres`
- Network: `hule-network`
- Compose/config dir: `/home/paunchygent/infrastructure/postgres/`
- Init scripts: `/home/paunchygent/infrastructure/postgres/init/`
- Data volume (docker): `infrastructure_postgres_data`
  - Host path: `/var/snap/docker/common/var-lib-docker/volumes/infrastructure_postgres_data/_data`
  - Container path: `/var/lib/postgresql/data`
- Backups (host): `/home/paunchygent/backups/` (see runbook)
- Connect (example):
  - `ssh hemma "sudo docker exec -it shared-postgres psql -U skriptoteket -d skriptoteket"`

## Core systemd services (snapshot)

- `snap.docker.dockerd.service`
- `snap.keepalived.daemon.service`
- `tailscaled.service`
- `fail2ban.service`
- `ssh.socket` (with `ssh.service`)
- `kdump-tools.service` (loads crash kernel; enabled)
- `sp5100-tco-watchdog.service` (loads watchdog module)
- `nginx.service` (installed, currently disabled)

## Crash capture (kdump) (current)

- Config:
  - `/etc/default/kdump-tools`
  - `/etc/default/grub.d/kdump-tools.cfg`
  - `/etc/sysctl.d/99-crash-capture.conf`
- Units:
  - `kdump-tools.service` (normal boot; loads crash kernel)
  - `kdump-tools-dump.service` (crash-kernel boot; saves vmcore)
- Post-savecore reboot hardening:
  - Unit override: `/etc/systemd/system/kdump-tools-dump.service.d/10-sysrq-reboot.conf`
  - Wrapper: `/usr/local/sbin/kdump-savecore-and-sysrq-reboot` (forces reboot via SysRq)

## Skriptoteket App

- Repo: `/home/paunchygent/apps/skriptoteket/`
- Env: `/home/paunchygent/apps/skriptoteket/.env`
- Logs (if local runs): `/home/paunchygent/apps/skriptoteket/.artifacts/`

## GPU / ROCm Stack

- ROCm root: `/opt/rocm/`
- Installer package: `/home/paunchygent/amdgpu-install_7.1.1.70101-1_all.deb`
- Kernel module (DKMS): `/lib/modules/$(uname -r)/updates/dkms/amdgpu.ko.zst`

## Storage & Backups

- System LVM PVs: `/dev/sda3` + `/dev/sdb1` (LVM span)
- Backup disk:
  - Seed partition: `/dev/sdd1` (FAT32 label `CIDATA`, mounted `/mnt/seed`)
  - Backup partition: `/dev/sdd2` (ext4 label `BACKUP`, mounted `/mnt/backup`)
- Full snapshot: `/mnt/backup/hemma-root-20260106/`
  - Package inventory: `dpkg-selections.txt`
  - Unit inventory: `unit-files.txt`
  - Authorized keys: `authorized_keys.txt`

## CLI / Ops Tooling (installed)

Core operational tools (non-exhaustive):
- `ripgrep`, `fd-find`, `bat`, `fzf`, `jq`, `yq`
- `curl`, `wget`, `git`, `rsync`, `tmux`, `htop`, `tree`
- `openssh-server`, `tailscale`, `ufw`, `fail2ban`
- Docker snap (`snap.docker.dockerd.service`)

Authoritative package inventory:
- Live system: `dpkg --get-selections`
- Snapshot: `/mnt/backup/hemma-root-20260106/dpkg-selections.txt`

## Restore Checklist (minimum)

1) Restore `/etc` (ssh, netplan, nginx, ufw, fail2ban).
2) Restore `/home/paunchygent` and `/root` (keys, scripts).
3) Restore docker stacks (`/home/paunchygent/infrastructure`, `/home/paunchygent/apps`).
4) Reinstall AMD GPU/ROCm stack and verify GPU health.

## Autoinstall boot (SSH-from-start)

Use the Ubuntu 24.04.2 Server ISO with the CIDATA seed on `/dev/sdd1`:

1) At GRUB, press `e` and append:

```
autoinstall ds=nocloud
```

or (explicit seed device):

```
autoinstall ds=nocloud;s=/dev/disk/by-label/CIDATA/
```

This loads the seed from `/mnt/seed` and enables SSH during the installer.

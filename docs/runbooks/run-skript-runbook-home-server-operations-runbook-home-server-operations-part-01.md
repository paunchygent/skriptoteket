---
type: runbook
id: RUN-SKRIPT-runbook-home-server-operations-PART-01
title: 'Runbook: Home Server Operations — part 01'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: RUN-SKRIPT-runbook-home-server-operations
part: 1
---

## Trigger

Run this procedure only for the system condition described by the source record and its system frontmatter field.

## Preconditions

Source: `docs/runbooks/runbook-home-server.md`. Runbook: Home Server Operations.

Operations guide for the home server hosting Skriptoteket and future HuleEdu services. - `/srv/scratch` = fast SSD work tier - Docker root and BuildKit cache - HF/model caches - active generated artifacts - `/srv/storage` = large HDD bulk-data tier - raw corpora - cold retained datasets - `/` = OS disk - not the long-term home for Docker persistent state or large ML artifact trees ```bash ssh hemma           # paunchygent (non-root default) ssh hemma-root      # root (use only with explicit approval) ssh hemma-local ssh hemma-local-root ``` Notes: - SSH is intentionally **not exposed on the public internet** (no router port-forward for `22/tcp`). - Default user is non-root (`paunchygent`); u

## Steps

### Source procedure

Operations guide for the home server hosting Skriptoteket and future HuleEdu services.

### Storage Tiers

- `/srv/scratch` = fast SSD work tier
  - Docker root and BuildKit cache
  - HF/model caches
  - active generated artifacts
- `/srv/storage` = large HDD bulk-data tier
  - raw corpora
  - cold retained datasets
- `/` = OS disk
  - not the long-term home for Docker persistent state or large ML artifact
    trees

### Setup

### Server Access (SSH)

```bash
### Remote admin access (VPN-gated; Tailscale)
ssh hemma           # paunchygent (non-root default)
ssh hemma-root      # root (use only with explicit approval)

### Local network break-glass (LAN)
ssh hemma-local
ssh hemma-local-root
```

Notes:

- SSH is intentionally **not exposed on the public internet** (no router port-forward for `22/tcp`).
- Default user is non-root (`paunchygent`); use `ssh hemma-root` only with explicit approval.
- UFW allows SSH only:
  - On `tailscale0` (VPN), and
  - From the LAN break-glass subnet `192.168.0.0/24`.
- If `ssh hemma` still points at `hemma.hule.education`, update your `~/.ssh/config` so `ssh hemma` uses MagicDNS:

```text
Host hemma
  HostName hemma.tail730aa2.ts.net
  User paunchygent
  IdentityFile ~/.ssh/hemma-paunchygent_ed25519

Host hemma-root
  HostName hemma.tail730aa2.ts.net
  User root

Host hemma-local
  HostName 192.168.0.9
  User paunchygent
  IdentityFile ~/.ssh/hemma-paunchygent_ed25519

Host hemma-local-root
  HostName 192.168.0.9
  User root
```

### SSH Hardening + Fail2ban

Security hardening (sshd settings, Fail2ban jails, nginx-proxy probe jail) is documented in
[ref-home-server-security-hardening.md](../reference/ref-home-server-security-hardening.md).

### Health-Gated Hardware Watchdog (Primary Recovery Path)

The primary recovery mechanism is a **health-gated hardware watchdog**. The hardware
watchdog is armed and only petted when key health checks pass. If any health check
fails, the petter exits and the hardware watchdog hard-resets the host within the
configured timeout.

- Petter service: `health-watchdog.service`
- Script: `/usr/local/bin/health-watchdog.sh`
- Health gate (all must pass after grace period):
  - `systemctl is-active ssh` and port `22` listening locally
  - default route present
  - `enp7s0` link is `UP`
  - gateway ping (`192.168.0.1`)
- Grace period (seconds): `HEALTH_WATCHDOG_GRACE_SECONDS` (default `300`)
- Interval (seconds): `HEALTH_WATCHDOG_INTERVAL_SECONDS` (default `10`)

Config + ownership:

- Hardware watchdog driver: `sp5100_tco`
  - Module options: `/etc/modprobe.d/sp5100_tco.conf`
    - `options sp5100_tco nowayout=1 heartbeat=60`
- Keep watchdog running across warm reboots (important after crash-kernel SysRq reboot):
  - Normal boot cmdline: add `watchdog.stop_on_reboot=0` in `/etc/default/grub` (`GRUB_CMDLINE_LINUX_DEFAULT`),
    run `sudo update-grub`, then reboot
  - Crash-kernel cmdline: add `watchdog.stop_on_reboot=0` in `/etc/default/kdump-tools` (`KDUMP_CMDLINE_APPEND`),
    run `sudo kdump-config unload && sudo kdump-config load`
- Disable systemd watchdog petting (PID 1 must not own `/dev/watchdog`):
  - `/etc/systemd/system.conf.d/99-watchdog.conf`:
    - `RuntimeWatchdogSec=0`
    - `RebootWatchdogSec=0`
- Petter unit: `/etc/systemd/system/health-watchdog.service`
  - Boot ordering: `/etc/systemd/system/health-watchdog.service.d/10-watchdog-order.conf`
    - `After=sp5100-tco-watchdog.service dev-watchdog0.device`
    - `ExecStartPre` waits for `/dev/watchdog0` (or `/dev/watchdog`) to exist to avoid boot-time races

Verification:

```bash
sudo systemctl status health-watchdog.service --no-pager
sudo journalctl -t health-watchdog --since "1 hour ago"
sudo lsof /dev/watchdog /dev/watchdog0
cat /proc/cmdline | rg watchdog.stop_on_reboot=0
cat /sys/module/watchdog/parameters/stop_on_reboot
cat /sys/class/watchdog/watchdog0/nowayout
cat /sys/class/watchdog/watchdog0/timeout
```

### Heartbeat Log (Hang Correlation)

Logs a simple heartbeat every minute to make hang windows obvious.

```bash
sudo systemctl status heartbeat-log.timer --no-pager
sudo journalctl -t heartbeat --since "2 hours ago"
```

### Current Network + DDNS Settings (as of 2026-01-02)

```text
### Network (ethernet only; Wi‑Fi disabled)
/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
  network: {config: disabled}

/etc/netplan/01-netcfg.yaml
  enp7s0: dhcp4=true, dhcp6=false, optional=true

/etc/netplan/50-cloud-init.yaml.disabled
/etc/netplan/50-cloud-init.yaml.bak

systemctl status wpa_supplicant@wlp5s0.service -> inactive (disabled)
```

```text
### DDNS (Namecheap)
systemctl status ddclient -> active
/etc/ddclient.conf
  protocol=namecheap
  server=dynamicdns.park-your-domain.com
  login=hule.education
  host=hemma
```

### GPU Tunnels (local workstation)

Use the local helper script to tunnel GPU services to localhost:

```bash
~/bin/hemma-gpu-tunnel start        # start llama + tabby tunnels
~/bin/hemma-gpu-tunnel start-llama  # start only llama tunnel (:8082)
~/bin/hemma-gpu-tunnel start-tabby  # start only tabby tunnel (:8083)
~/bin/hemma-gpu-tunnel stop         # stop both tunnels
~/bin/hemma-gpu-tunnel stop-llama   # stop only llama tunnel (:8082)
~/bin/hemma-gpu-tunnel stop-tabby   # stop only tabby tunnel (:8083)
~/bin/hemma-gpu-tunnel status       # show tunnel status
```

### Host GPU AI Services (systemd + Docker)

On `hemma`, llama.cpp runs in Docker (ROCm) but is controlled via a systemd wrapper unit (ROCm + llama.cpp recommended
operations):

- llama.cpp server: `llama-server-rocm.service` (container `llama-server-rocm`, port `8082`, host network)
- `tabby.service` (Tabby completion proxy, port `8083`)

Legacy llama-server units (`llama-server.service`, `llama-server-hip.service`, `llama-server-vulkan.service`) are
retired and must remain disabled/masked to avoid accidental instability.

Canonical runbooks:

- `docs/runbooks/runbook-gpu-ai-workloads.md` (llama.cpp Docker runtime + context/parallel tuning)
- `docs/runbooks/runbook-tabby-codemirror.md` (Tabby ops)

Quick checks:

```bash
ssh hemma "sudo systemctl status --no-pager llama-server-rocm.service tabby.service | head -n 60"
ssh hemma "curl -s http://127.0.0.1:8082/health"
ssh hemma "curl -s http://127.0.0.1:8083/v1/health"
```

### AMDGPU Release Watch (hemma)

Daily check for new AMDGPU releases (alerts when 30.30.x or Radeon Software 25.40 notes appear).

```bash
### Run once
ssh hemma "sudo systemctl start amdgpu-release-watch.service"

### Status + logs
ssh hemma "sudo systemctl status --no-pager amdgpu-release-watch.timer"
ssh hemma "sudo journalctl -t amdgpu-release-watch --since '7 days ago' --no-pager"
```

Files:

- Script: `/usr/local/bin/amdgpu-release-watch.sh`
- Unit: `/etc/systemd/system/amdgpu-release-watch.service`
- Timer: `/etc/systemd/system/amdgpu-release-watch.timer`

### Host Logs + Disk Health (hemma)

Log paths (root):

- `/root/logs/incident-YYYYMMDD-HHMMSS-HHMMSS.log` (incident windows)
- `/root/logs/smart/` (SMART snapshots)
- `/root/logs/power-rails/` (lm-sensors rail snapshots + alerts)
- `/sys/fs/pstore` (kernel crash logs; empty until a crash occurs)
- `/var/lib/systemd/pstore` (archived pstore logs via systemd-pstore)

pstore notes:

- Backend: `efi_pstore` (loaded via `/etc/modules-load.d/pstore.conf`).
- Service: `systemd-pstore.service` (archives pstore files into
  `/var/lib/systemd/pstore`).
- An empty directory is normal before the first crash.

Quick checks:

```bash
ssh hemma "sudo ls -la /sys/fs/pstore"
ssh hemma "sudo ls -la /var/lib/systemd/pstore"
ssh hemma "sudo systemctl status --no-pager systemd-pstore"
```

### Storage Layout (hemma)

Mount points:

- `/` (root SSD): OS + services (snap Docker stores data under `/var/snap/docker/common/var-lib-docker/`)
- `/srv/storage` (HDD, label `HEMMA_DATA`): long-term data
  - `/srv/storage/models` (bind-mounted to `/home/paunchygent/models` for llama.cpp compatibility)
  - `/srv/storage/data`
  - `/srv/storage/archives`
- `/srv/scratch` (SSD, label `HEMMA_SCRATCH`): fast ephemeral work
  - `/srv/scratch/tmp` (sticky like `/tmp`)
  - `/srv/scratch/build`
  - `/srv/scratch/cache`
- `/srv/backup` (label `BACKUP`): long-term backups/snapshots

Scratch defaults (interactive shells, `paunchygent`):

- `/home/paunchygent/.bashrc` sets `TMPDIR=/srv/scratch/tmp` and `XDG_CACHE_HOME=/srv/scratch/cache/$USER` when
  `/srv/scratch` is mounted.
- One-off command pattern:

```bash
ssh hemma "TMPDIR=/srv/scratch/tmp XDG_CACHE_HOME=/srv/scratch/cache/$USER <command>"
```

### Crash Capture Hardening (hemma, 2026-01-07)

Crash capture is hardened with larger kernel buffers, panic-on-oops, kdump, and netconsole.

Kernel/sysctl settings:

- Sysctl config: `/etc/sysctl.d/99-crash-capture.conf`
  - `kernel.panic_on_oops=1`
  - `kernel.panic=10`
  - `kernel.softlockup_panic=1`
  - `kernel.panic_on_warn=1`
- GRUB cmdline: `log_buf_len=4M`
- GRUB cmdline: `watchdog.stop_on_reboot=0` (keeps the hardware watchdog running across warm reboots)
- GPU hang mitigation flags (GRUB cmdline, hemma):
  - `amdgpu.cwsr_enable=0`
  - `amdgpu.mcbp=0`
  - `amdgpu.runpm=0`
- Crash-kernel GPU blacklist (prevents kdump hang if AMDGPU is wedged):
  - `KDUMP_CMDLINE_APPEND="... modprobe.blacklist=amdgpu"` in `/etc/default/kdump-tools`
  - Reload kdump kernel after changes: `sudo kdump-config unload && sudo kdump-config load`
  - Verify: `sudo kdump-config show` (kexec cmdline should include `modprobe.blacklist=amdgpu`)
- Kdump enabled via `linux-crashdump` + `kdump-tools`
  - `crashkernel=1536M` set in `/etc/default/grub.d/kdump-tools.cfg` (requires `update-grub` + reboot)
- Reduced kdump dumps enabled: `MAKEDUMP_ARGS="-c -d 31"` in `/etc/default/kdump-tools`
  - Faster + smaller kernel-only dumps; user-space cores handled by `systemd-coredump`
- Savecore timeout guard: `KDUMP_SAVECORE_TIMEOUT=40s` in `/etc/default/kdump-tools`
  - The kdump savecore wrapper uses `timeout --preserve-status` when set (prevents infinite hang)
- Post-kdump reboot hardening (avoid hanging `systemctl reboot` path):
  - Unit override: `/etc/systemd/system/kdump-tools-dump.service.d/10-sysrq-reboot.conf`
  - Wrapper: `/usr/local/sbin/kdump-savecore-and-sysrq-reboot`
    - Runs `kdump-config savecore` (with `KDUMP_SAVECORE_TIMEOUT`)
    - Forces reboot via SysRq: `echo b > /proc/sysrq-trigger` (falls back to `reboot -f` if needed)
- Hardware watchdog (hard reset if the host wedges, including crash-kernel hang):
  - Driver: `sp5100_tco` (SP5100/SB800 TCO watchdog)
  - Module options: `/etc/modprobe.d/sp5100_tco.conf`
    - `nowayout=1` (cannot be disabled without reboot)
    - `heartbeat=60` (seconds)
  - Keep watchdog running across warm reboots (prevents disarm during post-kdump reboot):
    - Set `watchdog.stop_on_reboot=0` in:
      - `/etc/default/grub` (`GRUB_CMDLINE_LINUX_DEFAULT`) then `sudo update-grub` + reboot
      - `/etc/default/kdump-tools` (`KDUMP_CMDLINE_APPEND`) then `sudo kdump-config unload && sudo kdump-config load`
    - Verify:
      - `cat /proc/cmdline | rg watchdog.stop_on_reboot=0`
      - `cat /sys/module/watchdog/parameters/stop_on_reboot` (should be `0`)
      - `sudo kdump-config show | rg watchdog.stop_on_reboot=0`
  - systemd watchdog is disabled (petting handled by `health-watchdog`):
    - `/etc/systemd/system.conf.d/99-watchdog.conf`: `RuntimeWatchdogSec=0`, `RebootWatchdogSec=0`
  - Health-gated petter owns `/dev/watchdog`:
    - `/etc/systemd/system/health-watchdog.service`
    - `/usr/local/bin/health-watchdog.sh`
    - Boot ordering: `/etc/systemd/system/health-watchdog.service.d/10-watchdog-order.conf` (waits for watchdog device node)
  - Crash-kernel hardening (kdump):
    - Systemd watchdog disabled in crash initrd:
      - `/etc/initramfs-tools/hooks/zz-kdump-disable-watchdog`
      - Verifiable in initrd as `etc/systemd/system.conf.d/zzz-kdump-no-watchdog.conf`
    - Ensure watchdog module + options in crash initrd:
      - `/etc/initramfs-tools/hooks/zz-kdump-watchdog-hardening`
      - Adds `sp5100_tco` module and `/etc/modprobe.d/sp5100_tco.conf` to kdump initrd
    - Ensure watchdog timer is actually started in crash kernel (not just module loaded):
      - `kdump-watchdog-arm.service` + `/usr/local/sbin/kdump-watchdog-arm` (opens `/dev/watchdog0` and holds fd; does not pet)
      - Wired into `kdump-tools-dump.service` via `/etc/systemd/system/kdump-tools-dump.service.d/05-watchdog-arm.conf`
    - Rebuild and reload kdump initrd after changes:
      - `sudo /etc/kernel/postinst.d/kdump-tools $(uname -r)`
      - `sudo kdump-config unload && sudo kdump-config load`
  - Verify watchdog is active + owned:
    - `sudo lsof /dev/watchdog`
    - `cat /sys/class/watchdog/watchdog0/nowayout`
    - `cat /sys/class/watchdog/watchdog0/timeout`
  - Verify crash initrd contents:
    - `sudo lsinitramfs /var/lib/kdump/initrd.img-$(uname -r) | rg 'sp5100_tco|sp5100_tco.conf|zzz-kdump-no-watchdog'`
- Controlled crash testing (maintenance window only):
  - Trigger: `ssh hemma "sudo sh -c 'echo 1 > /proc/sys/kernel/sysrq; echo c > /proc/sysrq-trigger'"`
  - Verify dump + crash boot:
    - `ssh hemma "journalctl --list-boots | tail -n 10"`
    - `ssh hemma "sudo journalctl -b -1 -u kdump-watchdog-arm.service --no-pager"`
    - `ssh hemma "sudo journalctl -b -1 -u kdump-tools-dump.service --no-pager | tail -n 200"`
    - `ssh hemma "ls -lah /var/crash | tail -n 20"`
  - If it was a test, rename the dump directory to `*-test` to avoid confusion.

One-time DC-off test boot (headless):

- Add custom entries in `/etc/grub.d/40_custom` for `Ubuntu (safe)` and `Ubuntu (dc=0 test)`.
- Regenerate GRUB: `sudo update-grub`.
- One-time boot: `sudo grub-reboot "Ubuntu (dc=0 test)" && sudo reboot`.
- Verify after boot: `cat /proc/cmdline | rg amdgpu.dc=0`.
- Expect display corruption/blank after early boot; use SSH. A normal reboot returns to the safe entry.
- Related reference: `docs/reference/reports/ref-hemma-kdump-amdgpu-blacklist-dc0-test-2026-01-11.md`.

Netconsole (UDP kernel logging):

- Module config: `/etc/modprobe.d/netconsole.conf`
- Module load: `/etc/modules-load.d/netconsole.conf`
- Current target: `192.168.0.11:6666` (listener on Mac; update if the receiver changes)
- Verify sender:

```bash
ssh hemma "dmesg -T | rg -i 'netconsole|netpoll' | tail -n 20"
```

Listener (Mac):

```bash
sudo tcpdump -ni en0 udp port 6666
```

Reboot log retrieval (persistent journal):

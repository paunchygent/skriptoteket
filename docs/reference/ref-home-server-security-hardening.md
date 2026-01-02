---
type: reference
id: REF-home-server-security-hardening
title: "Reference: Home Server Security Hardening"
status: active
owners: "olof"
created: 2026-01-02
updated: 2026-01-02
topic: "SSH + Fail2ban hardening for Hemma"
---

Security hardening details for the home server. Use this for audits or when applying changes.

## SSH Hardening (Checklist)

```bash
sudo nano /etc/ssh/sshd_config.d/99-hardening.conf
```

```text
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitRootLogin prohibit-password
AllowUsers root paunchygent
```

```bash
sudo sshd -t
sudo systemctl reload ssh
sudo install -d -m 700 /root/.ssh
sudo tee -a /root/.ssh/authorized_keys
sudo chmod 600 /root/.ssh/authorized_keys
```

## Fail2ban (Checklist)

```bash
sudo apt install fail2ban
sudo nano /etc/fail2ban/jail.d/sshd.local
```

```text
[sshd]
enabled = true
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
```

```bash
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
sudo fail2ban-client get sshd banip
sudo fail2ban-client set sshd unbanip <ip>
```

### Recidive jail (3 strikes → permaban)

This enforces a "repeat offenders get permabanned" policy based on Fail2ban's own log (including rotated logs).

```bash
sudo nano /etc/fail2ban/jail.d/recidive.local
```

```text
[recidive]
enabled = true
logpath = /var/log/fail2ban.log*
banaction = nftables[type=allports]

# 3 strikes within 7 days => permaban
findtime = 7d
maxretry = 3
bantime = -1
```

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status recidive
```

### nginx-proxy probe jail (HTTP scanners)

Ban repeat HTTP scanners hitting `nginx-proxy` (e.g. paths dropped with `444`, repeated `401/403` auth probes).

Files (hemma):

- Filter: `/etc/fail2ban/filter.d/nginx-proxy-probe.conf`
- Jail: `/etc/fail2ban/jail.d/nginx-proxy-probe.local`

Key settings:

- `backend = polling` (avoid `systemd` backend without precise `journalmatch`)
- `logpath = /var/snap/docker/common/var-lib-docker/containers/*/*-json.log` (snap docker)
- `usedns = no` (logs include both vhost and client IP; only ban client IP)
- `banaction = nftables[type=allports]` (cuts off multi-port probing)

Restart and verify:

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status nginx-proxy-probe
sudo fail2ban-client get nginx-proxy-probe logpath
sudo fail2ban-client get nginx-proxy-probe banip
sudo fail2ban-client set nginx-proxy-probe unbanip <ip>
```

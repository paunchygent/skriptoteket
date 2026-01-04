---
type: reference
id: REF-hemma-bios-update-guide-2026-01-03
title: "Guide: hemma BIOS update (PRIME X370-PRO)"
status: active
owners: "agents"
created: 2026-01-03
updated: 2026-01-03
topic: "devops"
links:
  - docs/runbooks/runbook-home-server.md
  - docs/runbooks/runbook-gpu-ai-workloads.md
---

# Guide: hemma BIOS update (PRIME X370-PRO)

This is a step-by-step guide for safely updating the ASUS PRIME X370-PRO BIOS on the hemma host.
It includes pre-checks, exact commands to stage the BIOS file, the EZ Flash steps, and quick FAQ/troubleshooting.

## Preconditions

- Physical access to the server (keyboard + monitor).
- Stable power (preferably on UPS).
- A USB stick formatted as FAT32.
- Confirm CPU compatibility on the ASUS CPU support list for PRIME X370-PRO.

## Step 1: Identify USB stick

Insert the USB stick and confirm it appears (example shown as `/dev/sde1`):

```bash
ssh hemma "lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MODEL,TRAN,MOUNTPOINT"
```

## Step 2: Mount USB stick

```bash
ssh hemma "sudo mkdir -p /mnt/usb && sudo mount /dev/sdX1 /mnt/usb"
```

Replace `/dev/sdX1` with the correct device (e.g., `/dev/sde1`).

## Step 3: Download the latest BIOS

As of 2026-01-03, the latest BIOS for PRIME X370-PRO is **6232 (2024-11-14)**.
Re-check ASUS support before use if the date is older than a few months.

```bash
ssh hemma "cd /tmp && curl -L -o PRIME-X370-PRO-ASUS-6232.zip \
  'https://dlcdnets.asus.com/pub/ASUS/mb/BIOS/PRIME-X370-PRO-ASUS-6232.zip?model=PRIME%20X370-PRO'"
```

## Step 4: Extract and copy .CAP to USB root

```bash
ssh hemma "cd /tmp && rm -rf bios-6232 && mkdir bios-6232 && \
  unzip -q PRIME-X370-PRO-ASUS-6232.zip -d bios-6232 && \
  ls -la bios-6232"

ssh hemma "sudo cp /tmp/bios-6232/*.CAP /mnt/usb/ && sync && ls -la /mnt/usb"
```

You should see a file like:

```
PRIME-X370-PRO-ASUS-6232.CAP
```

## Step 5: Unmount USB stick

```bash
ssh hemma "sudo umount /mnt/usb"
```

## Step 6: Update BIOS via EZ Flash

1. Reboot the server.
2. Press `Del` (or `F2`) to enter BIOS setup.
3. Navigate to **Tool → ASUS EZ Flash 3**.
4. Select the USB drive and the `.CAP` file.
5. Confirm and **do not power off** during the update.
6. System will reboot when finished.

## Step 7: Verify BIOS version

After reboot:

```bash
ssh hemma "sudo dmidecode -s bios-version; sudo dmidecode -s bios-release-date"
```

## FAQ / Troubleshooting

### Can I flash the BIOS purely over SSH (hemma-root)?

Not directly. You can use SSH to **stage** the BIOS file onto a FAT32 USB stick (steps above), but the actual flash on
this board is done inside **UEFI Setup → ASUS EZ Flash**, which is **pre-boot** and not accessible over SSH.

Alternatives exist in general (vendor “capsule updates” via `fwupd`, or “USB BIOS Flashback” on boards that support it),
but PRIME X370‑PRO updates are typically done via **EZ Flash**.

### Remote option: external network KVM (PiKVM / TinyPilot)

If you want to do this without standing next to the server each time, an external remote KVM gives you “BIOS access over
the network”:

- **What it is:** a small device that captures the server’s **video output** (HDMI) and emulates a **USB keyboard/mouse**
  into the server, so you can see and control BIOS/boot screens remotely.
- **How it connects:** HDMI from the server’s GPU (often via DP→HDMI adapter) + a USB cable to the server for HID
  keyboard/mouse emulation.
- **Power control (optional):** some setups add ATX power/reset control (or a smart PDU) so you can reboot remotely even
  if the host wedges.
- **Common choices:** PiKVM (Raspberry Pi-based) or TinyPilot (commercial).

Operational notes:

- Ensure the GPU outputs a pre-boot signal on the port you connect (some DP ports/monitors are finicky).
- Treat remote KVM like “physical access”: keep it on LAN/VPN, use strong auth, and restrict exposure.

### BIOS file not visible in EZ Flash
- Ensure the USB is **FAT32** and the `.CAP` is in the **root** of the drive.
- Try a different USB port (rear ports are more reliable).
- Use a smaller USB stick if the BIOS is picky.

### CPU compatibility warnings
- ASUS removed **7th‑gen A‑series/Athlon X4** support starting at BIOS 6026.
- Ryzen 7 1700 remains supported in the official CPU list.

### System won’t boot after update
- Clear CMOS using the motherboard jumper or battery removal.
- Re-enter BIOS and re‑enable the expected boot mode (Legacy vs UEFI).
- Re-check boot order and SATA/NVMe settings.

### UEFI vs Legacy
- The board supports UEFI, but the host is currently **Legacy BIOS** boot.
- Switching to UEFI requires an EFI System Partition (ESP) on disk.

## Safety checklist

- No active firmware flashing during storms or unstable power.
- Ensure the BIOS file matches the exact motherboard model: **PRIME X370‑PRO**.
- Do not interrupt the flash process.

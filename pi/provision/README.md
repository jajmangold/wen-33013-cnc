# Provisioning the LinuxCNC Pi

How `lcnc` is built from a blank card. Done on Windows; the traps below are
the ones that actually bit, recorded so they only cost time once.

## What it is

| | |
|---|---|
| Host | Raspberry Pi 4 Model B Rev 1.2, 4 GB |
| Image | `image_2026-01-21-raspios-lcnc-2.9.8-trixie-arm64.zip` from `linuxcnc.org/iso/` |
| Kernel | `6.12.34+rpt-rpi-v8-rt` (`SMP PREEMPT_RT`) |
| Card | 32 GB (see "card size" below) |
| Hostname | `lcnc`, user `josh`, SSH key auth |
| Network | eth0 + wlan0, both DHCP; Tailscale `lcnc.python-bull.ts.net` |

SPI is already enabled in the stock image: `dtparam=spi=on` is in
`config.txt` and `/dev/spidev0.0` + `0.1` exist. No boot-config work needed
for the motion node.

## Steps

1. **Fetch the image** - `fetch-image.ps1`.

   `linuxcnc.org` throttles hard **per connection** (~52 KB/s). The script
   pulls 216 ranged chunks over 16 parallel connections, which sustained
   ~430 KB/s - 1.7 GB in about 75 minutes instead of nine hours. There are no
   mirrors; that host is the only source.

2. **Write the card** - `write-card.ps1`, run elevated.

   It waits for the image, validates the target, clears it, writes in 8 MB
   chunks, then **reads the card back and SHA256s it against the image**. The
   hash is the proof, not the absence of errors.

3. **First boot.** The script leaves a `firstrun.sh` on `bootfs` plus a
   `systemd.run=` line in `cmdline.txt`. The Pi configures hostname, user,
   SSH key, wifi and timezone, deletes the script, strips the cmdline entry
   and reboots itself. Allow two boot cycles before expecting SSH.

4. **Install the udev rules** so USB nodes keep stable identity:

   ```bash
   sudo cp 99-cnc-nodes.rules /etc/udev/rules.d/
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```

   That file is generated - edit `machine/wen33013.toml` and `/regen`.

## Traps

**Pin the target disk by SERIAL, never by number.** Disk numbers are recycled.
A card swapped mid-run left the first attempt pointing at "disk 1", which by
then was a different card. The script now re-asserts the serial immediately
before opening the write handle and again before verifying, so a swap aborts
instead of retargeting.

**`Set-Disk -IsOffline` fails on removable media.** A USB stick presents as a
fixed disk and can be taken offline; an SD card in a reader cannot, and throws
*"Removable media cannot be set to offline"*. The equivalent is `mountvol /N`
to disable automount for the duration, restored in both `catch` and `finally`.
Without it Windows mounts `bootfs` the instant the partition table lands and
drops a `System Volume Information` into the FAT, which breaks the read-back
hash.

**Card size.** The image is 5.68 GB. On an 8 GB card that leaves ~1.8 GB after
the rootfs expands - enough to work, not enough for a desktop `apt
full-upgrade`. 32 GB leaves ~22 GB and avoids the whole conversation.

**Two kernels are installed.** `uname -r` must end in `-rt`. The image also
carries a stock `6.12.62+rpt-rpi-v8`, and `update-initramfs` builds both. An
`apt upgrade` that repoints the default boot kernel would silently cost
realtime, and the first symptom would be rough motion rather than an error.
Check after every update.

**Serial console holds the UART.** `cmdline.txt` ships with
`console=serial0,115200`. If the DWIN pendant is ever wired to the Pi's
hardware UART rather than its own RP2040, that has to go first.

**VNC does not come up.** `raspi-config nonint do_vnc 0` runs during first
boot, but both `wayvnc` and `vncserver-x11-serviced` report `inactive` -
Trixie is Wayland/labwc and wayvnc needs a headless output configured.
Unresolved; the machine is driven over SSH and the pendant instead.

## Verification

```bash
ssh josh@lcnc 'uname -r; ls /dev/spidev*; df -h /; nproc; free -h'
```

Expect an `-rt` kernel, both spidev nodes, and the rootfs expanded to the full
card.

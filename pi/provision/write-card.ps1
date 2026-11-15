$ErrorActionPreference = 'Stop'
$sp   = 'C:\Users\Josh\pi-images'
$log  = Join-Path $sp 'write3.log'

# --- target is pinned by SERIAL, not by disk number ---
# Find yours:  Get-Disk | Select Number,SerialNumber,FriendlyName,Size
# NEVER pin by disk number: numbers are recycled when a card is swapped,
# and the script would then happily write to whatever took that slot.
$SERIAL_   = '121220160204'   # <-- CHANGE THIS for a different card
$MINSIZE_  = 25GB
$MAXSIZE_  = 35GB

$HOSTNAME_ = 'lcnc'
$USER_     = 'josh'
$SSID_     = 'Bender'
$COUNTRY_  = 'US'
$KEYMAP_   = 'us'
$TZ_       = 'America/Chicago'
$PUBKEY_F  = 'C:\Users\Josh\.ssh\id_ed25519.pub'

function L($m) { "$((Get-Date).ToString('HH:mm:ss'))  $m" | Add-Content -Path $log -Encoding utf8 }
"=== elevated writer v3 started $(Get-Date) ===" | Set-Content -Path $log -Encoding utf8

$automountOff = $false

# Resolve the pinned disk, or die. Called repeatedly, never cached.
function Get-Target {
  $m = @(Get-Disk | Where-Object {
    $_.SerialNumber -eq $SERIAL_ -and $_.BusType -eq 'USB' -and
    $_.Size -gt $MINSIZE_ -and $_.Size -lt $MAXSIZE_ -and
    -not $_.IsBoot -and -not $_.IsSystem
  })
  if ($m.Count -ne 1) { throw "guard: expected exactly 1 disk with serial $SERIAL_ in $([int]($MINSIZE_/1GB))-$([int]($MAXSIZE_/1GB))GB, found $($m.Count)" }
  if ($m[0].Number -eq 0) { throw 'guard: refusing to touch disk 0' }
  return $m[0]
}

try {
  # ---------- 1. image must already be extracted ----------
  $img = Get-ChildItem $sp -Filter *.img -ErrorAction SilentlyContinue |
           Sort-Object Length -Descending | Select-Object -First 1
  if (-not $img) { L 'FATAL: no .img in scratchpad'; exit 1 }
  if ($img.Length -ne 6098518016) { L "FATAL: img is $($img.Length) bytes, expected 6098518016"; exit 1 }
  L ("img = {0} ({1:N2} GB)" -f $img.Name, ($img.Length / 1GB))
  L 'hashing image'
  $imgHash = (Get-FileHash -Path $img.FullName -Algorithm SHA256).Hash
  L "img sha256 = $imgHash"

  # ---------- 2. resolve target by serial ----------
  $disk = Get-Target
  L ("target = disk {0} serial {1} '{2}' {3:N2} GB" -f $disk.Number, $disk.SerialNumber, $disk.FriendlyName, ($disk.Size / 1GB))
  if ($img.Length -gt $disk.Size) { L 'FATAL: image larger than card'; exit 1 }

  # ---------- 3. clear + offline ----------
  L 'clearing partition table'
  Clear-Disk -Number $disk.Number -RemoveData -RemoveOEM -Confirm:$false -ErrorAction SilentlyContinue
  $disk = Get-Target                                   # re-assert after clear
  try { Set-Disk -Number $disk.Number -IsReadOnly $false }
  catch { L 'note: clearing read-only flag not supported here' }

  # An SD card in a reader is REMOVABLE MEDIA, so Set-Disk -IsOffline is unsupported.
  # mountvol /N is the equivalent: it stops Windows auto-mounting bootfs the instant the
  # write lays down a partition table, which would otherwise scribble a
  # System Volume Information into the FAT and break the read-back hash.
  & mountvol /N 2>&1 | ForEach-Object { L "mountvol /N: $_" }
  $automountOff = $true
  L 'automount disabled for the duration of the write'
  try { Set-Disk -Number $disk.Number -IsOffline $true; L 'disk also set offline' }
  catch { L 'note: cannot offline removable media (expected) - relying on cleared table + automount off' }
  Start-Sleep -Seconds 2

  # ---------- 4. re-assert identity IMMEDIATELY before writing ----------
  $disk = Get-Target
  $devNum = $disk.Number
  L ("confirmed pre-write: disk {0} serial {1} {2:N2} GB" -f $devNum, $disk.SerialNumber, ($disk.Size / 1GB))
  $dev = "\\.\PhysicalDrive$devNum"

  L "writing $($img.Length) bytes to $dev"
  $sw  = [Diagnostics.Stopwatch]::StartNew()
  $src = [IO.File]::OpenRead($img.FullName)
  $dst = [IO.File]::Open($dev, 'Open', 'Write', 'ReadWrite')
  $buf = New-Object byte[] (8MB)
  $done = 0L
  $nextMark = 512MB
  while (($r = $src.Read($buf, 0, $buf.Length)) -gt 0) {
    if ($r % 512 -ne 0) { $r = [int]([math]::Ceiling($r / 512) * 512) }
    $dst.Write($buf, 0, $r)
    $done += $r
    if ($done -ge $nextMark) {
      L ("  {0:N0} MB written ({1:N1} MB/s)" -f ($done / 1MB), ($done / 1MB / $sw.Elapsed.TotalSeconds))
      $nextMark += 512MB
    }
  }
  $dst.Flush()
  $dst.Close()
  $src.Close()
  $sw.Stop()
  L ("write finished: {0:N0} MB in {1:N1} min" -f ($done / 1MB), $sw.Elapsed.TotalMinutes)

  # ---------- 5. read back and compare ----------
  $chk = Get-Target                                    # re-assert before verify
  if ($chk.Number -ne $devNum) { L 'FATAL: disk number moved between write and verify'; exit 1 }
  L 'verifying (reading the card back)'
  $sha = [Security.Cryptography.SHA256]::Create()
  $rd  = [IO.File]::Open($dev, 'Open', 'Read', 'ReadWrite')
  $left = $img.Length
  $vb = New-Object byte[] (8MB)
  while ($left -gt 0) {
    $want = [math]::Min([int64]$vb.Length, $left)
    $wantAligned = [int]([math]::Ceiling($want / 512) * 512)
    $got = $rd.Read($vb, 0, $wantAligned)
    if ($got -le 0) { break }
    $use = [int][math]::Min([int64]$got, $left)
    $sha.TransformBlock($vb, 0, $use, $null, 0) | Out-Null
    $left -= $use
  }
  $sha.TransformFinalBlock((New-Object byte[] 0), 0, 0) | Out-Null
  $rd.Close()
  $devHash = (($sha.Hash | ForEach-Object { $_.ToString('x2') }) -join '').ToUpper()
  L "dev sha256 = $devHash"
  if ($devHash -ne $imgHash.ToUpper()) { L 'FATAL: VERIFY MISMATCH'; exit 1 }
  L 'VERIFY OK'

  # ---------- 6. re-enable automount, find bootfs ----------
  & mountvol /E 2>&1 | ForEach-Object { L "mountvol /E: $_" }
  $automountOff = $false
  L 'automount re-enabled'
  try { Set-Disk -Number $devNum -IsOffline $false } catch { }
  Update-Disk -Number $devNum -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 5
  $boot = $null
  for ($i = 0; $i -lt 24; $i++) {
    $boot = Get-Partition -DiskNumber $devNum -ErrorAction SilentlyContinue |
              Where-Object { $_.DriveLetter } |
              ForEach-Object { Get-Volume -Partition $_ -ErrorAction SilentlyContinue } |
              Where-Object { $_.FileSystem -eq 'FAT32' } | Select-Object -First 1
    if ($boot) { break }
    Start-Sleep -Seconds 5
  }
  if (-not $boot) {
    L 'bootfs got no drive letter; assigning one'
    $p = Get-Partition -DiskNumber $devNum | Where-Object { $_.Size -lt 2GB } | Select-Object -First 1
    $free = (68..90 | ForEach-Object { [char]$_ } | Where-Object { -not (Test-Path ($_ + ':')) })[0]
    Set-Partition -InputObject $p -NewDriveLetter $free
    Start-Sleep -Seconds 3
    $boot = Get-Volume -DriveLetter $free
  }
  $B = "$($boot.DriveLetter):"
  L "bootfs mounted at $B (label '$($boot.FileSystemLabel)')"
  L "cmdline.txt before: $((Get-Content "$B\cmdline.txt" -Raw).Trim())"

  # ---------- 7. credentials ----------
  $openssl = 'C:\Program Files\Git\mingw64\bin\openssl.exe'
  $alphabet = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789-_.'.ToCharArray()
  $pw = -join (1..20 | ForEach-Object { $alphabet[(Get-Random -Maximum $alphabet.Length)] })
  $pwHash = (& $openssl passwd -6 $pw).Trim()
  L "generated login password (shown once): $pw"

  $sshKey = (Get-Content $PUBKEY_F -Raw).Trim()
  L "ssh key: $($sshKey.Substring(0,28))... $($sshKey.Split(' ')[-1])"

  $prof = netsh wlan show profile name="$SSID_" key=clear 2>&1
  $kc = "$(($prof | Select-String 'Key Content') -replace '.*:\s*', '')".Trim()
  if (-not $kc) { L "FATAL: could not read PSK for '$SSID_'"; exit 1 }
  $kdf = [Security.Cryptography.Rfc2898DeriveBytes]::new(
            [Text.Encoding]::UTF8.GetBytes($kc),
            [Text.Encoding]::UTF8.GetBytes($SSID_),
            4096,
            [Security.Cryptography.HashAlgorithmName]::SHA1)
  $psk = ($kdf.GetBytes(32) | ForEach-Object { $_.ToString('x2') }) -join ''
  $kdf.Dispose()
  $kc = $null
  L "psk hashed for '$SSID_' ($($psk.Length) hex chars); plaintext not stored"

  # ---------- 8. firstrun.sh, LF endings ----------
  $tpl = @'
#!/bin/bash
set +e

CURRENT_HOSTNAME=`cat /etc/hostname | tr -d " \t\n\r"`
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
   /usr/lib/raspberrypi-sys-mods/imager_custom set_hostname @@HOST@@
else
   echo @@HOST@@ >/etc/hostname
   sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\t@@HOST@@/g" /etc/hosts
fi

FIRSTUSER=`getent passwd 1000 | cut -d: -f1`
FIRSTUSERHOME=`getent passwd 1000 | cut -d: -f6`
if [ -f /usr/lib/userconf-pi/userconf ]; then
   /usr/lib/userconf-pi/userconf '@@USER@@' '@@PWHASH@@'
else
   echo "$FIRSTUSER:"'@@PWHASH@@' | chpasswd -e
   if [ "$FIRSTUSER" != "@@USER@@" ]; then
      usermod -l "@@USER@@" "$FIRSTUSER"
      usermod -m -d "/home/@@USER@@" "@@USER@@"
      groupmod -n "@@USER@@" "$FIRSTUSER"
      if grep -q "^autologin-user=" /etc/lightdm/lightdm.conf 2>/dev/null ; then
         sed -i "s/^autologin-user=.*/autologin-user=@@USER@@/" /etc/lightdm/lightdm.conf
      fi
      if [ -f /etc/systemd/system/getty@tty1.service.d/autologin.conf ]; then
         sed -i "s/$FIRSTUSER/@@USER@@/g" /etc/systemd/system/getty@tty1.service.d/autologin.conf
      fi
      if [ -f /etc/sudoers.d/010_pi-nopasswd ]; then
         sed -i "s/^$FIRSTUSER /@@USER@@ /" /etc/sudoers.d/010_pi-nopasswd
      fi
   fi
fi

if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
   /usr/lib/raspberrypi-sys-mods/imager_custom enable_ssh -p '@@SSHKEY@@'
else
   install -o "@@USER@@" -m 700 -d "/home/@@USER@@/.ssh"
   echo '@@SSHKEY@@' > "/home/@@USER@@/.ssh/authorized_keys"
   chown @@USER@@:@@USER@@ "/home/@@USER@@/.ssh/authorized_keys"
   chmod 600 "/home/@@USER@@/.ssh/authorized_keys"
   systemctl enable ssh
fi

if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
   /usr/lib/raspberrypi-sys-mods/imager_custom set_wlan '@@SSID@@' '@@PSK@@' '@@COUNTRY@@'
   /usr/lib/raspberrypi-sys-mods/imager_custom set_keymap '@@KEYMAP@@'
   /usr/lib/raspberrypi-sys-mods/imager_custom set_timezone '@@TZ@@'
fi

# a first-boot wizard would hang a box with no monitor
systemctl disable userconfig.service >/dev/null 2>&1
rm -f /etc/xdg/autostart/piwiz.desktop

# VNC, so AXIS is reachable without a screen
if [ -x /usr/bin/raspi-config ]; then
   raspi-config nonint do_vnc 0 >/dev/null 2>&1
fi

rm -f /boot/firmware/firstrun.sh
sed -i 's| systemd\.[^ ]*||g' /boot/firmware/cmdline.txt
exit 0
'@

  $firstrun = $tpl.Replace('@@HOST@@', $HOSTNAME_).
                   Replace('@@USER@@', $USER_).
                   Replace('@@PWHASH@@', $pwHash).
                   Replace('@@SSHKEY@@', $sshKey).
                   Replace('@@SSID@@', $SSID_).
                   Replace('@@PSK@@', $psk).
                   Replace('@@COUNTRY@@', $COUNTRY_).
                   Replace('@@KEYMAP@@', $KEYMAP_).
                   Replace('@@TZ@@', $TZ_)
  $firstrun = $firstrun -replace "`r`n", "`n"
  [IO.File]::WriteAllText("$B\firstrun.sh", $firstrun, (New-Object Text.UTF8Encoding $false))
  L "wrote $B\firstrun.sh ($($firstrun.Length) bytes, LF endings)"

  # ---------- 9. cmdline.txt ----------
  $cl = (Get-Content "$B\cmdline.txt" -Raw).Trim()
  $cl = $cl -replace '\s*systemd\.[^\s]*', ''
  $cl = "$cl systemd.run=/boot/firmware/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target"
  [IO.File]::WriteAllText("$B\cmdline.txt", "$cl`n", (New-Object Text.UTF8Encoding $false))
  L "cmdline.txt after: $cl"

  [IO.File]::WriteAllText("$B\ssh", '', (New-Object Text.UTF8Encoding $false))
  L 'wrote bare ssh flag file'

  L 'DONE'
}
catch {
  L "EXCEPTION: $($_.Exception.Message)"
  L $_.ScriptStackTrace
  if ($automountOff) {
    & mountvol /E 2>&1 | Out-Null
    L 'automount re-enabled after failure'
  }
  exit 1
}
finally {
  if ($automountOff) {
    & mountvol /E 2>&1 | Out-Null
    L 'automount re-enabled in finally'
  }
}

$ErrorActionPreference = 'Stop'
$sp  = 'C:\Users\Josh\pi-images'
$u   = 'https://www.linuxcnc.org/iso/image_2026-01-21-raspios-lcnc-2.9.8-trixie-arm64.zip'
$out = Join-Path $sp 'lcnc-2.9.8.zip'
$pd  = Join-Path $sp 'parts'
$log = Join-Path $sp 'dl.log'
$total = 1805209192
$cs = 8MB
New-Item -ItemType Directory -Force -Path $pd | Out-Null
$n = [int][math]::Ceiling($total / $cs)
"start $(Get-Date -f HH:mm:ss) chunks=$n" | Set-Content $log

0..($n-1) | ForEach-Object -Parallel {
    $i = $_
    $cs = $using:cs; $total = $using:total; $pd = $using:pd; $u = $using:u
    $s = [int64]$i * $cs
    $e = [math]::Min($s + $cs - 1, $total - 1)
    $exp = $e - $s + 1
    $f = Join-Path $pd ("chunk_{0:D5}.bin" -f $i)
    for ($a = 0; $a -lt 6; $a++) {
        if ((Test-Path $f) -and (Get-Item $f).Length -eq $exp) { break }
        & curl.exe -s --max-time 900 -r "$s-$e" -o $f $u
    }
} -ThrottleLimit 16

$missing = @()
for ($i = 0; $i -lt $n; $i++) {
    $s = [int64]$i * $cs
    $e = [math]::Min($s + $cs - 1, $total - 1)
    $exp = $e - $s + 1
    $f = Join-Path $pd ("chunk_{0:D5}.bin" -f $i)
    if (-not (Test-Path $f) -or (Get-Item $f).Length -ne $exp) { $missing += $i }
}
if ($missing.Count -gt 0) { "MISSING: $($missing -join ',')" | Add-Content $log; exit 1 }

$fs = [IO.File]::Create($out)
for ($i = 0; $i -lt $n; $i++) {
    $f = Join-Path $pd ("chunk_{0:D5}.bin" -f $i)
    $in = [IO.File]::OpenRead($f); $in.CopyTo($fs); $in.Close()
}
$fs.Close()
$len = (Get-Item $out).Length
"assembled $len bytes (expected $total)" | Add-Content $log
if ($len -ne $total) { "SIZE MISMATCH" | Add-Content $log; exit 1 }
Remove-Item (Join-Path $pd 'chunk_*.bin') -Force
"DONE $(Get-Date -f HH:mm:ss)" | Add-Content $log

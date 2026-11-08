<#
  Mac Test — TESTING ONLY. Windows counterpart of macdrive's first-frame probe, so the Mac and Windows numbers
  measure the same thing: from Start-Process to (a) the main window existing and (b) the first captured frame of
  that window's CLIENT AREA (below the native WPF title bar and frame, i.e. the WebView2 content only) with painted
  app content (>= 40 distinct colours, the same rule as on the Mac, where the window has no native title bar).
  D-127: test side only, no app change.

    pwsh tests/mac/win_firstframe.ps1 -Exe <path to ChuvadiReader.Windows.exe> -Runs 10
#>
param([Parameter(Mandatory)][string]$Exe, [int]$Runs = 10, [string]$Out = 'win-firstframe.csv')

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class ChvdWin {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
}
"@
[ChvdWin]::SetProcessDPIAware() | Out-Null

function Count-Colours([System.Drawing.Bitmap]$bmp) {
    $set = New-Object 'System.Collections.Generic.HashSet[int]'
    $rect = New-Object System.Drawing.Rectangle 0, 0, $bmp.Width, $bmp.Height
    $data = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        $bytes = New-Object byte[] ($data.Stride * $bmp.Height)
        [System.Runtime.InteropServices.Marshal]::Copy($data.Scan0, $bytes, 0, $bytes.Length)
        for ($y = 0; $y -lt $bmp.Height; $y += 2) {
            $row = $y * $data.Stride
            for ($x = 0; $x -lt $bmp.Width; $x += 2) {
                $i = $row + $x * 4
                [void]$set.Add((($bytes[$i + 2] -shr 3) -shl 10) -bor (($bytes[$i + 1] -shr 3) -shl 5) -bor ($bytes[$i] -shr 3))
            }
        }
    } finally { $bmp.UnlockBits($data) }
    return $set.Count
}

"run,window_ms,first_render_ms,frames" | Set-Content $Out
for ($run = 1; $run -le $Runs; $run++) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $Exe -PassThru
    $win = $null; $first = $null; $frames = 0
    while ($sw.Elapsed.TotalSeconds -lt 30) {
        $p.Refresh()
        if ($p.MainWindowHandle -eq [IntPtr]::Zero) { Start-Sleep -Milliseconds 2; continue }
        if (-not $win) { $win = $sw.Elapsed.TotalMilliseconds }
        $r = New-Object ChvdWin+RECT
        [void][ChvdWin]::GetClientRect($p.MainWindowHandle, [ref]$r)
        $o = New-Object ChvdWin+POINT
        [void][ChvdWin]::ClientToScreen($p.MainWindowHandle, [ref]$o)
        $w = $r.R - $r.L; $h = $r.B - $r.T
        if ($w -lt 200 -or $h -lt 150) { continue }
        $t = $sw.Elapsed.TotalMilliseconds
        $bmp = New-Object System.Drawing.Bitmap $w, $h
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.CopyFromScreen($o.X, $o.Y, 0, 0, $bmp.Size)
        $g.Dispose()
        $frames++
        $c = Count-Colours $bmp
        if ($c -ge 40) { $first = $t; if ($run -le 2) { $bmp.Save("win-first-render-$run.png") }; $bmp.Dispose(); break }
        $bmp.Dispose()
    }
    "{0},{1:F0},{2:F0},{3}" -f $run, $win, $first, $frames | Add-Content $Out
    Write-Host ("run {0,2}: window {1:F0} ms, first render {2:F0} ms ({3} frames)" -f $run, $win, $first, $frames)
    Start-Sleep -Milliseconds 1500
    $null = $p.CloseMainWindow()
    if (-not $p.WaitForExit(5000)) { $p.Kill() }
    Start-Sleep -Milliseconds 800
}
$rows = Import-Csv $Out
foreach ($col in 'window_ms', 'first_render_ms') {
    $v = $rows | Where-Object { $_.$col -ne '' } | ForEach-Object { [double]$_.$col } | Sort-Object
    if ($v.Count) { Write-Host ("{0}: median {1} · worst {2} · best {3} (n={4})" -f $col, $v[[int][math]::Floor($v.Count / 2)], $v[-1], $v[0], $v.Count) }
}

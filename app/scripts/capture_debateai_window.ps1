param(
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$Title = "Debate AI"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class DebateAiWindowCapture {
    [StructLayout(LayoutKind.Sequential)] public struct RECT {
        public int Left, Top, Right, Bottom;
    }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}
"@

$process = Get-Process -Name DebateAI -ErrorAction Stop |
    Where-Object { $_.MainWindowTitle -eq $Title -and $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1
if ($null -eq $process) { throw "Visible DebateAI window not found." }

$rect = New-Object DebateAiWindowCapture+RECT
if (-not [DebateAiWindowCapture]::GetWindowRect($process.MainWindowHandle, [ref]$rect)) {
    throw "Could not read the DebateAI window bounds."
}
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) { throw "Invalid DebateAI window bounds." }

$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
    $parent = Split-Path -Parent $OutputPath
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
Write-Output $OutputPath

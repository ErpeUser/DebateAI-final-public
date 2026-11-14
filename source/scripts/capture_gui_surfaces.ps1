param(
    [string]$OutputRoot = (Join-Path (Get-Location) "evidence\gui-all-screenshots"),
    [int]$Width = 1280,
    [int]$Height = 820,
    [switch]$BothThemes
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System;
using System.Drawing;
using System.Runtime.InteropServices;
public static class DebateAiCaptureNative {
    [StructLayout(LayoutKind.Sequential)] public struct RECT {
        public int Left, Top, Right, Bottom;
    }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint flags);
    public static readonly IntPtr HWND_TOP = IntPtr.Zero;
    public const uint SWP_NOZORDER = 0x0004;
    public const uint SWP_SHOWWINDOW = 0x0040;
}
"@

function Get-DebateWindow {
    $process = Get-Process -Name DebateAI -ErrorAction Stop |
        Where-Object { $_.MainWindowTitle -eq "Debate AI" -and $_.MainWindowHandle -ne 0 } |
        Select-Object -First 1
    if ($null -eq $process) { throw "Visible DebateAI window not found. Start DebateAI first." }
    return [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
}

function Find-Button([System.Windows.Automation.AutomationElement]$Window, [string]$Name) {
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Button
    )
    $wanted = (($Name -replace "\s", "").ToLowerInvariant())
    foreach ($button in $Window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)) {
        $actual = [string]$button.Current.Name
        $normalized = (($actual -replace "\s", "").ToLowerInvariant())
        if ($actual -eq $Name -or $normalized -eq $wanted -or $normalized.StartsWith($wanted)) { return $button }
    }
    return $null
}

function Invoke-Button([System.Windows.Automation.AutomationElement]$Window, [string]$Name) {
    $button = Find-Button $Window $Name
    if ($null -eq $button) { throw "Button not found: $Name" }
    try {
        $pattern = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        $pattern.Invoke()
    } catch {
        try {
            $pattern = $button.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
            $pattern.Select()
        } catch {
            $button.SetFocus()
            (New-Object -ComObject WScript.Shell).SendKeys("{ENTER}")
        }
    }
    Start-Sleep -Milliseconds 500
}

function Capture([System.Windows.Automation.AutomationElement]$Window, [string]$Path) {
    $handle = [IntPtr]$Window.Current.NativeWindowHandle
    [DebateAiCaptureNative]::SetForegroundWindow($handle) | Out-Null
    Start-Sleep -Milliseconds 150
    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
    $rect = New-Object DebateAiCaptureNative+RECT
    if (-not [DebateAiCaptureNative]::GetWindowRect($handle, [ref]$rect)) {
        throw "Window bounds unavailable."
    }
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

function Set-WindowSize([System.Windows.Automation.AutomationElement]$Window, [int]$Width, [int]$Height) {
    $handle = [IntPtr]$Window.Current.NativeWindowHandle
    [DebateAiCaptureNative]::SetWindowPos($handle, [DebateAiCaptureNative]::HWND_TOP, 20, 20, $Width, $Height,
        [DebateAiCaptureNative]::SWP_NOZORDER -bor [DebateAiCaptureNative]::SWP_SHOWWINDOW) | Out-Null
    Start-Sleep -Milliseconds 300
}

function Capture-Current([System.Windows.Automation.AutomationElement]$Window, [string]$Folder, [string]$Name) {
    Capture $Window (Join-Path $Folder ("{0}.png" -f $Name))
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runFolder = Join-Path $OutputRoot $stamp
New-Item -ItemType Directory -Path $runFolder -Force | Out-Null
$window = Get-DebateWindow
Set-WindowSize $window $Width $Height

$states = @(
    @{ Name = "main"; Button = "Zurück" },
    @{ Name = "assistant"; Button = "Assistenten9/10" },
    @{ Name = "transcription-audio"; Button = "Transkription & Audio" },
    @{ Name = "privacy"; Button = "Datenschutz" },
    @{ Name = "connections"; Button = "Verbindungen" },
    @{ Name = "info"; Button = "Info" }
)

try {
    # Main surface.
    $back = Find-Button $window "Zurück"
    if ($null -ne $back) { Invoke-Button $window "Zurück" }
    Capture-Current $window $runFolder "main-top"

    # Test laboratory is a separate graphical surface.
    $lab = Find-Button $window "Testlabor"
    if ($null -ne $lab) {
        Invoke-Button $window "Testlabor"
        Capture-Current $window $runFolder "testlabor-top"
        $window = Get-DebateWindow
        $close = Find-Button $window "Zur Debatte"
        if ($null -ne $close) { Invoke-Button $window "Zur Debatte" }
    }

    # Return to settings and capture every settings tab.
    $window = Get-DebateWindow
    $settings = Find-Button $window "Einstellungen"
    if ($null -ne $settings) { Invoke-Button $window "Einstellungen" }
    foreach ($state in $states | Where-Object { $_.Name -ne "main" }) {
        $window = Get-DebateWindow
        Invoke-Button $window $state.Button
        Capture-Current $window $runFolder ("{0}-top" -f $state.Name)
    }

    if ($BothThemes) {
        $window = Get-DebateWindow
        $themeButton = $window.FindFirst(
            [System.Windows.Automation.TreeScope]::Descendants,
            (New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
                [System.Windows.Automation.ControlType]::Button
            ))
        )
        $buttons = $window.FindAll(
            [System.Windows.Automation.TreeScope]::Descendants,
            (New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
                [System.Windows.Automation.ControlType]::Button
            ))
        )
        foreach ($button in $buttons) {
            if ($button.Current.Name -like "Zum *Design wechseln") {
                $pattern = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
                $pattern.Invoke()
                Start-Sleep -Milliseconds 500
                break
            }
        }
        foreach ($state in $states | Where-Object { $_.Name -ne "main" }) {
            $window = Get-DebateWindow
            Invoke-Button $window $state.Button
            Capture-Current $window $runFolder ("{0}-theme-2-top" -f $state.Name)
        }
    }
} finally {
    $manifest = [ordered]@{
        captured_at = (Get-Date).ToString("o")
        window = "Debate AI"
        size = "${Width}x${Height}"
        both_themes = [bool]$BothThemes
        files = @(Get-ChildItem -LiteralPath $runFolder -Filter "*.png" | Sort-Object Name | ForEach-Object { $_.Name })
    }
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $runFolder "manifest.json") -Encoding UTF8
}

Write-Output $runFolder

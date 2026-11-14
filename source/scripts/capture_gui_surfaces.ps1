param(
    [string]$OutputRoot = (Join-Path (Get-Location) "evidence\gui-all-screenshots"),
    [int]$Width = 1280,
    [int]$Height = 820,
    [int]$MaxScrolls = 20,
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

function Try-Invoke-Button([System.Windows.Automation.AutomationElement]$Window, [string]$Name) {
    $button = Find-Button $Window $Name
    if ($null -eq $button) { return $false }
    Invoke-Button $Window $Name
    return $true
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

function Get-ScrollableElements([System.Windows.Automation.AutomationElement]$Window) {
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::IsScrollPatternAvailableProperty,
        $true
    )
    $elements = @()
    foreach ($element in $Window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)) {
        try {
            $pattern = $element.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
            if ($pattern.Current.VerticallyScrollable -or $pattern.Current.HorizontallyScrollable) {
                $elements += $element
            }
        } catch {
            # A control may advertise the pattern while its provider is still loading.
        }
    }
    return $elements
}

function Capture-FullSurface(
    [System.Windows.Automation.AutomationElement]$Window,
    [string]$Folder,
    [string]$Name
) {
    Capture-Current $Window $Folder ("{0}-top" -f $Name)
    $scrollables = @(Get-ScrollableElements $Window)
    $scrollIndex = 0
    $capturedScroll = 0
    foreach ($scrollable in $scrollables) {
        try {
            $pattern = $scrollable.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
            if (-not $pattern.Current.VerticallyScrollable) { continue }
            $scrollIndex++
            $step = 0
            $lastPercent = -2.0
            while ($step -lt $MaxScrolls) {
                $before = [double]$pattern.Current.VerticalScrollPercent
                if ($before -ge 100 -or $before -eq -1) { break }
                $pattern.ScrollVertical([System.Windows.Automation.ScrollAmount]::LargeIncrement)
                Start-Sleep -Milliseconds 250
                $after = [double]$pattern.Current.VerticalScrollPercent
                if ($after -eq $before -or $after -eq $lastPercent -or $after -lt 0) { break }
                $step++
                $lastPercent = $after
                Capture-Current $Window $Folder ("{0}-scroll{1:00}-{2:00}" -f $Name, $scrollIndex, $step)
                $capturedScroll++
                if ($after -ge 100) { break }
            }
        } catch {
            # Continue with the remaining scrollable surfaces; one provider must
            # not prevent the complete GUI evidence set from being written.
        }
    }

    # WebView2 can expose the document without a UIA ScrollPattern. In that
    # case use real PageDown input against the focused window and stop when
    # two consecutive captures are byte-identical.
    if ($capturedScroll -eq 0) {
        $shell = New-Object -ComObject WScript.Shell
        $previousHash = (Get-FileHash (Join-Path $Folder ("{0}-top.png" -f $Name)) -Algorithm SHA256).Hash
        for ($step = 1; $step -le $MaxScrolls; $step++) {
            $shell.AppActivate("Debate AI") | Out-Null
            $shell.SendKeys("{PGDN}")
            Start-Sleep -Milliseconds 350
            $path = Join-Path $Folder ("{0}-pagedown-{1:00}.png" -f $Name, $step)
            Capture $Window $path
            $hash = (Get-FileHash $path -Algorithm SHA256).Hash
            if ($hash -eq $previousHash) {
                Remove-Item -LiteralPath $path -Force
                break
            }
            $previousHash = $hash
        }
    }
}

function Capture-DebateWorkflows([System.Windows.Automation.AutomationElement]$Window, [string]$Folder) {
    # The laboratory is a modal surface. Close it first so the underlying
    # debate navigation can be captured deterministically.
    $window = Get-DebateWindow
    [void](Try-Invoke-Button $window "Testlabor schliessen und zur Debatte")
    $window = Get-DebateWindow

    # If the app is currently inside settings, return to the main debate view.
    [void](Try-Invoke-Button $window "Zurück")
    $window = Get-DebateWindow
    Capture-FullSurface $window $Folder "main"

    # Creation form: do not start audio or a model run.
    if (Try-Invoke-Button $window "Neue Debatte") {
        $window = Get-DebateWindow
        Capture-FullSurface $window $Folder "debate-create"
        $created = $false
        foreach ($name in @("Debatte anlegen", "Debatte erstellen", "Erstellen")) {
            if (Try-Invoke-Button $window $name) {
                $created = $true
                break
            }
        }
        if ($created) {
            $window = Get-DebateWindow
            Capture-FullSurface $window $Folder "debate-created"
            # The created-session surface is the safe live-debate handoff:
            # controls are visible, but no microphone/system-audio capture is
            # started by the documentation script.
            Capture-FullSurface $window $Folder "debate-live-ready"
        }
    }

    # Capture a live-debate-ready surface when it is exposed, but never press
    # the microphone/start controls during documentation capture.
    $window = Get-DebateWindow
    foreach ($name in @("Gespräch starten", "Debatte starten", "Live-Debatte", "Aufnahme starten")) {
        if ($null -ne (Find-Button $window $name)) {
            Capture-FullSurface $window $Folder "debate-live-ready"
            break
        }
    }
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
    Capture-DebateWorkflows $window $runFolder

    # Test laboratory is a separate graphical surface.
    $window = Get-DebateWindow
    $lab = Find-Button $window "Testlabor"
    if ($null -ne $lab) {
        Invoke-Button $window "Testlabor"
        Capture-FullSurface $window $runFolder "testlabor"
        $window = Get-DebateWindow
        $close = Find-Button $window "Testlabor schliessen und zur Debatte"
        if ($null -eq $close) { $close = Find-Button $window "Zur Debatte" }
        if ($null -ne $close) {
            if (Find-Button $window "Testlabor schliessen und zur Debatte") {
                Invoke-Button $window "Testlabor schliessen und zur Debatte"
            } else {
                Invoke-Button $window "Zur Debatte"
            }
        }
    }

    # Return to settings and capture every settings tab.
    $window = Get-DebateWindow
    $settings = Find-Button $window "Einstellungen"
    if ($null -ne $settings) { Invoke-Button $window "Einstellungen" }
    foreach ($state in $states | Where-Object { $_.Name -ne "main" }) {
        $window = Get-DebateWindow
        if (Try-Invoke-Button $window $state.Button) {
            $window = Get-DebateWindow
            Capture-FullSurface $window $runFolder $state.Name
        }
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
            if (Try-Invoke-Button $window $state.Button) {
                $window = Get-DebateWindow
                Capture-FullSurface $window $runFolder ("{0}-theme-2" -f $state.Name)
            }
        }
    }
} finally {
    $manifest = [ordered]@{
        captured_at = (Get-Date).ToString("o")
        window = "Debate AI"
        size = "${Width}x${Height}"
        max_scrolls = $MaxScrolls
        both_themes = [bool]$BothThemes
        files = @(Get-ChildItem -LiteralPath $runFolder -Filter "*.png" | Sort-Object Name | ForEach-Object { $_.Name })
    }
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $runFolder "manifest.json") -Encoding UTF8
}

$zipPath = "$runFolder.zip"
try {
    Compress-Archive -Path (Join-Path $runFolder "*") -DestinationPath $zipPath -Force
} catch {
    Write-Warning "Screenshot ZIP could not be created: $($_.Exception.Message)"
}

Write-Output $runFolder

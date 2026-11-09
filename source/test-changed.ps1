[CmdletBinding()]
param(
    [string[]]$Path,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$repoRoot = $PSScriptRoot

function Resolve-BackendPython {
    foreach ($candidate in @(
        (Join-Path $repoRoot ".venv\Scripts\python.exe"),
        (Join-Path $repoRoot ".release-venv\Scripts\python.exe")
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    return (Get-Command python.exe -ErrorAction Stop).Source
}

function Invoke-Checked {
    param([string]$Label, [string]$File, [string[]]$Arguments, [string]$WorkingDirectory)
    Write-Host "[test-changed] $Label"
    if ($WhatIf) {
        Write-Host "  $File $($Arguments -join ' ')"
        return
    }
    Push-Location $WorkingDirectory
    try {
        & $File @Arguments
        if ($LASTEXITCODE -ne 0) { throw "$Label fehlgeschlagen (Code $LASTEXITCODE)." }
    } finally {
        Pop-Location
    }
}

if (-not $Path) {
    $tracked = @(& git -C $repoRoot diff --name-only --diff-filter=ACMRTUXB HEAD)
    $untracked = @(& git -C $repoRoot ls-files --others --exclude-standard)
    $Path = @($tracked + $untracked | Where-Object { $_ } | Sort-Object -Unique)
}

if (-not $Path) {
    Write-Host "[test-changed] Keine geänderten Dateien gefunden."
    exit 0
}

$python = Resolve-BackendPython
$backendModules = [Collections.Generic.HashSet[string]]::new()
$desktopModules = [Collections.Generic.HashSet[string]]::new()
$frontendChanged = $false

foreach ($file in $Path) {
    $normalized = $file.Replace("\", "/")
    if ($normalized -like "backend/tests/test_*.py") {
        [void]$backendModules.Add(($normalized.Substring(8, $normalized.Length - 11)).Replace("/", "."))
    } elseif ($normalized -like "backend/app/*.py" -or $normalized -like "backend/app/**/*.py") {
        $base = [IO.Path]::GetFileNameWithoutExtension($normalized)
        $candidate = Join-Path $repoRoot "backend\tests\test_$base.py"
        if (Test-Path -LiteralPath $candidate) { [void]$backendModules.Add("tests.test_$base") }
        if ($normalized -match "agents/(orchestrator|objection_handler|prompts|prompt_resources)\.py$") {
            [void]$backendModules.Add("tests.test_debate_copilot")
            [void]$backendModules.Add("tests.test_objection_handler")
            [void]$backendModules.Add("tests.test_prompt_system_instruction")
            if (Test-Path (Join-Path $repoRoot "backend\tests\test_prompt_resources.py")) {
                [void]$backendModules.Add("tests.test_prompt_resources")
            }
        }
    }

    if ($normalized -like "desktop/tests/test_*.py") {
        [void]$desktopModules.Add(($normalized.Substring(8, $normalized.Length - 11)).Replace("/", "."))
    } elseif ($normalized -like "desktop/*.py" -or $normalized -like "desktop/**/*.py") {
        $base = [IO.Path]::GetFileNameWithoutExtension($normalized)
        $candidate = Join-Path $repoRoot "desktop\tests\test_$base.py"
        if (Test-Path -LiteralPath $candidate) { [void]$desktopModules.Add("tests.test_$base") }
        if ($normalized -eq "desktop/launcher.py") { [void]$desktopModules.Add("tests.test_launcher") }
    }

    if ($normalized -like "frontend/src/*" -or $normalized -like "frontend/src/**/*" -or $normalized -eq "frontend/package.json") {
        $frontendChanged = $true
    }
}

if ($backendModules.Count -gt 0) {
    Invoke-Checked "Backend: $($backendModules.Count) betroffene Module" $python `
        (@("-m", "unittest") + @($backendModules | Sort-Object)) (Join-Path $repoRoot "backend")
}
if ($desktopModules.Count -gt 0) {
    Invoke-Checked "Desktop: $($desktopModules.Count) betroffene Module" $python `
        (@("-m", "unittest") + @($desktopModules | Sort-Object)) (Join-Path $repoRoot "desktop")
}
if ($frontendChanged) {
    Invoke-Checked "Frontend-Smoke" "npm.cmd" @("test") (Join-Path $repoRoot "frontend")
}
if ($backendModules.Count -eq 0 -and $desktopModules.Count -eq 0 -and -not $frontendChanged) {
    Write-Host "[test-changed] Nur Dateien ohne zugeordneten Laufzeit-Test wurden geändert."
}

$ErrorActionPreference = "Stop"
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../../.."))
$scriptFile = Join-Path $root "Start-DebateAI.ps1"
$source = Get-Content -LiteralPath $scriptFile -Raw

function Assert([bool]$Value, [string]$Message) {
    if (-not $Value) { throw $Message }
}

Assert ($source.Contains("recover_release.py")) "Starter does not use the signed release fetcher"
Assert ($source.Contains("DEBATEAI_UPDATE_DESCRIPTOR_URL")) "Descriptor endpoint is not explicitly configured"
Assert ($source.Contains("DEBATEAI_UPDATE_ASSET_URL")) "Asset endpoint is not explicitly configured"
Assert ($source.Contains("Install-VerifiedBuild")) "Installer must keep smoke and rollback path"
Assert ($source.Contains("RestoreArchived")) "Archived release restore path is missing"
Assert ($source.Contains("installed-release-2026-11-19/DebateAI")) "Archived bundle path is not explicit"
Assert ($source.Contains("app/desktop/release_signing_keys.json")) "Trust keys must be anchored in versioned source"
Assert ($source.Contains('--keys $keyPath')) "Recovery must pass the pinned key path explicitly"
Assert ($source.Contains("Signed release")) "Signed recovery status must be visible"
Assert (-not $source.Contains("Invoke-WebRequest")) "No unsigned web-download shortcut permitted"

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("debateai-launcher-test-" + [Guid]::NewGuid().ToString("N"))
try {
    New-Item -Path $tmp -ItemType Directory -Force | Out-Null
    Copy-Item -LiteralPath $scriptFile -Destination (Join-Path $tmp "Start-DebateAI.ps1")
    $install = Join-Path $tmp "runtime/DebateAI"
    $files = @(
        "DebateAI.exe", "DebateAIUpdater.exe",
        "_internal/pgsql/bin/postgres.exe", "_internal/pgsql/bin/initdb.exe",
        "_internal/frontend/index.html", "_internal/ffmpeg/ffmpeg.exe",
        "_internal/models/silero_vad.onnx", "_internal/models/voxceleb_resnet152_LM.onnx"
    )
    foreach($relative in $files) {
        $file = Join-Path $install $relative
        New-Item -Path (Split-Path -Parent $file) -ItemType Directory -Force | Out-Null
        Set-Content -LiteralPath $file -Value "test-fixture" -Encoding ascii
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $tmp "Start-DebateAI.ps1") -Check
    Assert ($LASTEXITCODE -eq 0) "An existing complete release was not accepted"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $tmp "Start-DebateAI.ps1") -Offline -NoLaunch
    Assert ($LASTEXITCODE -eq 0) "Offline startup with a complete bundle must work"
    Assert (-not (Test-Path (Join-Path $tmp "DebateAI_Generated"))) "Starter created Generated for existing bundle"
    Remove-Item -LiteralPath (Join-Path $install "DebateAI.exe") -Force
    $oldPreference = $ErrorActionPreference
    try {
        # An expected child-process failure must not become a test-runner exception.
        $ErrorActionPreference = "Continue"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $tmp "Start-DebateAI.ps1") -Offline -NoLaunch 2>$null
        $failedExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldPreference
    }
    Assert ($failedExit -ne 0) "Missing release unexpectedly passed offline startup"
    Assert (-not (Test-Path (Join-Path $tmp "DebateAI_Generated"))) "Failed offline bootstrap created cache"

    # Exercise the real installer with fixture bundles and an isolated fake
    # health probe; NEVER replace or launch the user's production executable.
    $index = $source.LastIndexOf("if (`$Check) {")
    Assert ($index -gt 0) "Cannot locate the script's function definitions"
    $lib = Join-Path $tmp "installer-functions.ps1"
    [IO.File]::WriteAllText($lib, $source.Substring(0, $index), [Text.Encoding]::UTF8)
    . $lib
    $Runtime = Join-Path $tmp "fixture-runtime"
    $Installed = Join-Path $Runtime "DebateAI"
    $Smoke = Join-Path $tmp "fixture_smoke.py"
    [IO.File]::WriteAllText($Smoke, @'
import sys
from pathlib import Path
bundle = Path(sys.argv[sys.argv.index("--bundle")+1])
sys.exit(5 if (bundle / "DebateAI.exe").read_text().strip() == "unhealthy" else 0)
'@)
    $script:SelectedPython = (& py.exe -3.12 -c "import sys; print(sys.executable)" | Select-Object -Last 1).Trim()
    Assert (Test-Path -LiteralPath $script:SelectedPython) "Python fixture interpreter missing"
    $oldCandidate = Join-Path $tmp "fixture-old"
    $goodCandidate = Join-Path $tmp "fixture-good"
    $badCandidate = Join-Path $tmp "fixture-bad"
    foreach ($set in @(
        [pscustomobject]@{Path=$oldCandidate;Version="old"},
        [pscustomobject]@{Path=$goodCandidate;Version="healthy"},
        [pscustomobject]@{Path=$badCandidate;Version="unhealthy"}
    )) {
        foreach ($fileName in $files) {
            $fixture = Join-Path $set.Path $fileName
            New-Item -Path (Split-Path -Parent $fixture) -ItemType Directory -Force | Out-Null
            Set-Content -LiteralPath $fixture -Value $set.Version -Encoding ascii
        }
    }
    New-Item -Path $Runtime -ItemType Directory -Force | Out-Null
    Move-Item -LiteralPath $oldCandidate -Destination $Installed
    Install-VerifiedBuild -Source $goodCandidate
    Assert ((Get-Content (Join-Path $Installed "DebateAI.exe") -Raw).Trim() -eq "healthy") "Healthy staged bundle was not promoted"
    $rollbackWasRequested = $false
    try {
        Install-VerifiedBuild -Source $badCandidate
    } catch {
        $rollbackWasRequested = $_.Exception.Message -match "smoke test failed"
    }
    Assert $rollbackWasRequested "Unhealthy installed candidate was not rejected"
    Assert ((Get-Content (Join-Path $Installed "DebateAI.exe") -Raw).Trim() -eq "healthy") "Rollback lost the last healthy runtime"
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Output "DebateAI startup/recovery contracts: OK"

[CmdletBinding()]
param(
    [switch]$Check,
    [switch]$NoLaunch,
    [switch]$Rebuild,
    [switch]$Offline,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = Join-Path $Repo "runtime"
$Installed = Join-Path $Runtime "DebateAI"
$Exe = Join-Path $Installed "DebateAI.exe"
$Builder = Join-Path $Repo "app/scripts/build_debate_assistant.ps1"
$Smoke = Join-Path $Repo "app/desktop/scripts/smoke_test.py"

function Test-ReleaseBundle {
    param([string]$Path)
    foreach ($relative in @(
        "DebateAI.exe", "DebateAIUpdater.exe",
        "_internal/pgsql/bin/postgres.exe", "_internal/pgsql/bin/initdb.exe",
        "_internal/frontend/index.html", "_internal/ffmpeg/ffmpeg.exe",
        "_internal/models/silero_vad.onnx",
        "_internal/models/voxceleb_resnet152_LM.onnx"
    )) {
        if (-not (Test-Path -LiteralPath (Join-Path $Path $relative) -PathType Leaf)) {
            return $false
        }
    }
    return $true
}

function Find-Python312 {
    if ($Python) {
        $candidates = @($Python)
    } else {
        $candidates = @()
        if ($env:LOCALAPPDATA) {
            $candidates += (Join-Path $env:LOCALAPPDATA "Programs/Python/Python312/python.exe")
        }
        if (Get-Command "py.exe" -ErrorAction SilentlyContinue) {
            try {
                $detected = (& py.exe -3.12 -c "import sys; print(sys.executable)" 2>$null | Select-Object -Last 1)
                if ($LASTEXITCODE -eq 0 -and $detected) {
                    $candidates += $detected.Trim()
                }
            } catch {}
        }
        foreach ($name in @("python3.12.exe", "python.exe")) {
            $command = Get-Command $name -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($null -ne $command) {
                $candidates += $command.Source
            }
        }
    }
    foreach ($candidate in $candidates) {
        try {
            $version = (& $candidate --version 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -eq 0 -and $version -match '^Python 3\.12(?:\.|$)') {
                return $candidate
            }
        } catch {}
    }
    throw "Python 3.12 not found. Install it, or pass -Python <full-path-to-python-3.12.exe>."
}

function Install-VerifiedBuild {
    param([string]$Source)
    if (-not (Test-ReleaseBundle $Source)) {
        throw "Build did not produce a complete Windows bundle at $Source"
    }
    New-Item -Path $Runtime -ItemType Directory -Force | Out-Null
    $token = [Guid]::NewGuid().ToString("N")
    $stage = Join-Path $Runtime ".DebateAI.stage-$token"
    $backup = Join-Path $Runtime ".DebateAI.previous-$token"
    $hadInstall = Test-Path -LiteralPath $Installed
    $backedUp = $false
    $published = $false
    try {
        Copy-Item -LiteralPath $Source -Destination $stage -Recurse -ErrorAction Stop
        if (-not (Test-ReleaseBundle $stage)) {
            throw "Staged bundle is incomplete; existing install unchanged."
        }
        if ($hadInstall) {
            Move-Item -LiteralPath $Installed -Destination $backup -ErrorAction Stop
            $backedUp = $true
        }
        Move-Item -LiteralPath $stage -Destination $Installed -ErrorAction Stop
        $published = $true
        # Verify at its final path too, before retiring the previous release.
        & $script:SelectedPython $Smoke --bundle $Installed
        if ($LASTEXITCODE -ne 0) {
            throw "Installed bundle smoke test failed; rolling back."
        }
    } catch {
        if ($published -and (Test-Path -LiteralPath $Installed)) {
            $failed = Join-Path $Runtime ".DebateAI.failed-$token"
            Move-Item -LiteralPath $Installed -Destination $failed -ErrorAction SilentlyContinue
        }
        if ($backedUp -and (Test-Path -LiteralPath $backup)) {
            Move-Item -LiteralPath $backup -Destination $Installed -ErrorAction Stop
        }
        throw
    } finally {
        if (Test-Path -LiteralPath $stage) {
            Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    if ($backedUp -and (Test-Path -LiteralPath $backup)) {
        try {
            Remove-Item -LiteralPath $backup -Recurse -Force
        } catch {
            Write-Warning "Validated release is installed; old backup remains at $backup"
        }
    }
}

if ($Check) {
    if (Test-ReleaseBundle $Installed) {
        Write-Output "OK: Windows release independent of DebateAI_Generated: $Exe"
        exit 0
    }
    Write-Error "MISSING: complete release at $Installed"
    exit 1
}

if ($Rebuild -or -not (Test-ReleaseBundle $Installed)) {
    if ($Offline) {
        throw "No complete release (or -Rebuild requested); -Offline forbids network recovery."
    }

    $descriptorUrl = [string]$env:DEBATEAI_UPDATE_DESCRIPTOR_URL
    $assetUrl = [string]$env:DEBATEAI_UPDATE_ASSET_URL
    $hasDescriptor = -not [string]::IsNullOrWhiteSpace($descriptorUrl)
    $hasAsset = -not [string]::IsNullOrWhiteSpace($assetUrl)
    if ($hasDescriptor -xor $hasAsset) {
        throw "Configure BOTH DEBATEAI_UPDATE_DESCRIPTOR_URL and DEBATEAI_UPDATE_ASSET_URL."
    }

    $script:SelectedPython = Find-Python312
    if (-not $Rebuild -and $hasDescriptor) {
        $fetcher = Join-Path $Repo "app/scripts/recover_release.py"
        if (-not (Test-Path -LiteralPath $fetcher -PathType Leaf)) {
            throw "Signed release verifier missing: $fetcher"
        }
        $recoverRoot = Join-Path $Repo "DebateAI_Generated/build/recovery"
        $keyPath = Join-Path $Repo "app/desktop/release_signing_keys.json"
        if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) {
            throw "The versioned release trust key file is missing: $keyPath"
        }
        Write-Output "Signed release: downloading and checking the configured update channel."
        $lines = @(& $script:SelectedPython $fetcher --output-dir $recoverRoot --keys $keyPath)
        if ($LASTEXITCODE -ne 0 -or $lines.Count -ne 1) {
            throw "Signed release recovery failed; the current installation was preserved."
        }
        $verifiedBundle = [string]($lines | Select-Object -Last 1)
        $resolvedBundle = [IO.Path]::GetFullPath($verifiedBundle)
        $allowedRoot = [IO.Path]::GetFullPath($recoverRoot)
        if (-not $resolvedBundle.StartsWith(
            ($allowedRoot.TrimEnd([char]92, [char]47) + [IO.Path]::DirectorySeparatorChar),
            [StringComparison]::OrdinalIgnoreCase
        )) {
            throw "Signed recovery returned an unexpected staging path."
        }
        try {
            Install-VerifiedBuild -Source $resolvedBundle
        } finally {
            $stageParent = Split-Path -Parent (Split-Path -Parent $resolvedBundle)
            if ($stageParent -and
                (Split-Path -Leaf $stageParent) -like ".signed-release-*") {
                Remove-Item -LiteralPath $stageParent -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    } else {
        if (-not (Test-Path -LiteralPath $Builder -PathType Leaf)) {
            throw "Versioned build script missing: $Builder"
        }
        $nodeDirectories = @()
        $nodeCommand = Get-Command "node.exe" -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($nodeCommand) {
            $nodeDirectories += Split-Path -Parent $nodeCommand.Source
        }
        foreach ($programFiles in @(
            [Environment]::GetEnvironmentVariable("ProgramFiles"),
            [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
        )) {
            if ($programFiles) {
                $nodeDirectories += Join-Path $programFiles "nodejs"
            }
        }
        $nodeDirectory = $nodeDirectories |
            Where-Object { Test-Path -LiteralPath (Join-Path $_ "node.exe") } |
            Select-Object -First 1
        if ($nodeDirectory -and ($env:PATH -notlike "*$nodeDirectory*")) {
            $env:PATH = "$nodeDirectory;$env:PATH"
        }
        if (-not (Get-Command "npm.cmd" -ErrorAction SilentlyContinue) -or
            -not (Get-Command "node.exe" -ErrorAction SilentlyContinue)) {
            throw "Node.js 24 and npm are needed for a source rebuild."
        }
        $nodeVersion = (& node.exe --version 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or $nodeVersion -notmatch "^v24\.") {
            throw "Node.js 24 is required to rebuild; found $nodeVersion"
        }
        Write-Output "No signed release channel selected; building from versioned source."
        & $Builder -Python $script:SelectedPython -IncludeOracle
        if ($LASTEXITCODE -ne 0) {
            throw "Source build failed; installed runtime was not replaced."
        }
        Install-VerifiedBuild -Source (Join-Path $Repo "DebateAI_Generated/build/releases/DebateAI")
    }
}

if (-not (Test-ReleaseBundle $Installed)) {
    throw "Required bundle files are missing at $Installed"
}
if ($NoLaunch) {
    Write-Output "READY: $Exe"
    exit 0
}
Write-Output "Starting DebateAI: $Exe"
Start-Process -FilePath $Exe -WorkingDirectory $Repo

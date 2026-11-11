[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$SkipDownloads,
    [switch]$IncludeOracle
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Test-Python312Version {
    param([string]$VersionText)
    return $VersionText.Trim() -match '^Python 3\.12(?:\.|$)'
}

function Get-RepositoryRoot {
    param([string]$ScriptDirectory)
    return [IO.Path]::GetFullPath((Join-Path $ScriptDirectory ".."))
}

function Get-DesktopBuildContract {
    param([string]$RepositoryRoot)
    return [pscustomobject]@{
        Frontend = Join-Path $RepositoryRoot "frontend"
        ModelDownloader = Join-Path $RepositoryRoot "backend\scripts\download_models.py"
        PostgresDownloader = Join-Path $RepositoryRoot "desktop\scripts\download_pg.py"
        FfmpegDownloader = Join-Path $RepositoryRoot "desktop\scripts\download_ffmpeg.py"
        CLIProxyDownloader = Join-Path $RepositoryRoot "desktop\scripts\download_cliproxyapi.py"
        Spec = Join-Path $RepositoryRoot "desktop\backchannel.spec"
        SmokeTest = Join-Path $RepositoryRoot "desktop\scripts\smoke_test.py"
        ArchiveSmokeTest = Join-Path $RepositoryRoot "desktop\scripts\smoke_update_archive.py"
        Bundle = Join-Path $RepositoryRoot "dist\DebateAI"
        Artifact = Join-Path $RepositoryRoot "dist\DebateAI-windows-x64.zip"
        StageRoot = Join-Path $RepositoryRoot "build\release-stage"
        StagedBundle = Join-Path $RepositoryRoot "build\release-stage\DebateAI"
        StagedArtifact = Join-Path $RepositoryRoot "build\release-stage\DebateAI-windows-x64.zip"
        PyInstallerWork = Join-Path $RepositoryRoot "build\pyinstaller-release"
        CanonicalSmokeArtifact = Join-Path $RepositoryRoot "dist\.debate-smoke\DebateAI-windows-x64.zip"
        Venv = Join-Path $RepositoryRoot ".release-venv"
        PythonConstraints = Join-Path $RepositoryRoot "desktop\constraints-windows-py312.txt"
    }
}

function Assert-CommandSucceeded {
    param([int]$ExitCode, [string]$Label)
    if ($ExitCode -ne 0) {
        throw "$Label failed with exit code $ExitCode."
    }
}

function Invoke-Checked {
    param([string]$Label, [scriptblock]$Action)
    Write-Host "[build] $Label"
    & $Action
    Assert-CommandSucceeded -ExitCode $LASTEXITCODE -Label $Label
}

function Assert-Python312 {
    param([string]$PythonPath)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $version = (& $PythonPath --version 2>&1 | Out-String).Trim()
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    Assert-CommandSucceeded -ExitCode $exitCode -Label "Reading Python version"
    if (-not (Test-Python312Version $version)) {
        throw "Python 3.12 is required for the Windows bundle; found '$version'. Use -Python <path-to-python-3.12>."
    }
}

function Assert-DownloadAssets {
    param([pscustomobject]$Contract)
    $required = @(
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Contract.ModelDownloader)) "models\silero_vad.onnx"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Contract.ModelDownloader)) "models\voxceleb_resnet152_LM.onnx"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Contract.PostgresDownloader)) "pgsql\bin\postgres.exe"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Contract.PostgresDownloader)) "pgsql\bin\initdb.exe"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Contract.PostgresDownloader)) "pgsql\bin\pg_ctl.exe"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Contract.FfmpegDownloader)) "ffmpeg\ffmpeg.exe"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Contract.CLIProxyDownloader)) "cliproxyapi\cli-proxy-api.exe"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Contract.CLIProxyDownloader)) "cliproxyapi\plugins\windows\amd64\gemini-cli-v1.0.5.dll")
    )
    foreach ($path in $required) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "-SkipDownloads was used, but required build asset is missing: $path"
        }
    }
}

function Publish-ReleaseCandidate {
    param(
        [pscustomobject]$Contract,
        [scriptblock]$MoveAction = {
            param([string]$Source, [string]$Destination)
            Move-Item -LiteralPath $Source -Destination $Destination
        }
    )
    $distRoot = Split-Path -Parent $Contract.Bundle
    New-Item -ItemType Directory -Path $distRoot -Force | Out-Null
    $suffix = [Guid]::NewGuid().ToString("N")
    $bundleBackup = Join-Path $distRoot ".DebateAI.previous-$suffix"
    $artifactBackup = Join-Path $distRoot ".DebateAI-windows-x64.previous-$suffix.zip"
    $bundleWasPresent = Test-Path -LiteralPath $Contract.Bundle
    $artifactWasPresent = Test-Path -LiteralPath $Contract.Artifact
    $bundleBackedUp = $false
    $artifactBackedUp = $false
    $bundlePublished = $false
    $artifactPublished = $false
    try {
        if ($bundleWasPresent) {
            & $MoveAction $Contract.Bundle $bundleBackup
            $bundleBackedUp = $true
        }
        if ($artifactWasPresent) {
            & $MoveAction $Contract.Artifact $artifactBackup
            $artifactBackedUp = $true
        }
        & $MoveAction $Contract.StagedBundle $Contract.Bundle
        $bundlePublished = $true
        & $MoveAction $Contract.StagedArtifact $Contract.Artifact
        $artifactPublished = $true
    } catch {
        if ($bundlePublished -and (Test-Path -LiteralPath $Contract.Bundle)) {
            Remove-Item -LiteralPath $Contract.Bundle -Recurse -Force
        }
        if ($artifactPublished -and (Test-Path -LiteralPath $Contract.Artifact)) {
            Remove-Item -LiteralPath $Contract.Artifact -Force
        }
        if ($bundleBackedUp -and (Test-Path -LiteralPath $bundleBackup)) {
            Move-Item -LiteralPath $bundleBackup -Destination $Contract.Bundle
        }
        if ($artifactBackedUp -and (Test-Path -LiteralPath $artifactBackup)) {
            Move-Item -LiteralPath $artifactBackup -Destination $Contract.Artifact
        }
        throw
    }
    # Publication is already complete here.  Antivirus, Explorer, or a just
    # terminated WebView can briefly retain a DLL handle in the rollback copy;
    # cleanup must not turn a verified and published release into a false build
    # failure.  The dot-prefixed backup remains recoverable and is retried on a
    # later build.
    try {
        if (Test-Path -LiteralPath $bundleBackup) {
            Remove-Item -LiteralPath $bundleBackup -Recurse -Force
        }
        if (Test-Path -LiteralPath $artifactBackup) {
            Remove-Item -LiteralPath $artifactBackup -Force
        }
    } catch {
        Write-Warning "Release published; previous backup cleanup was deferred: $($_.Exception.Message)"
    }
}

function Invoke-DebateDesktopBuild {
    $repoRoot = Get-RepositoryRoot -ScriptDirectory $PSScriptRoot
    $contract = Get-DesktopBuildContract -RepositoryRoot $repoRoot
    Assert-Python312 -PythonPath $Python

    Push-Location $repoRoot
    try {
        Invoke-Checked "Install frontend dependencies" {
            & npm ci --prefix $contract.Frontend
        }
        Invoke-Checked "Build frontend" {
            & npm run build --prefix $contract.Frontend
        }

        if (-not (Test-Path -LiteralPath $contract.Venv -PathType Container)) {
            Invoke-Checked "Create Python 3.12 release environment" {
                & $Python -m venv $contract.Venv
            }
        }
        $venvPython = Join-Path $contract.Venv "Scripts\python.exe"
        Assert-Python312 -PythonPath $venvPython
        Invoke-Checked "Install desktop build dependencies" {
            & $venvPython -m pip install `
                -c $contract.PythonConstraints `
                -r (Join-Path $repoRoot "backend\requirements.txt") `
                -r (Join-Path $repoRoot "desktop\requirements.txt")
        }

        if ($SkipDownloads) {
            Assert-DownloadAssets -Contract $contract
        } else {
            Invoke-Checked "Download ONNX models" { & $venvPython $contract.ModelDownloader }
            Invoke-Checked "Download embedded PostgreSQL" { & $venvPython $contract.PostgresDownloader }
            Invoke-Checked "Download ffmpeg" { & $venvPython $contract.FfmpegDownloader }
            Invoke-Checked "Download CLIProxyAPI" { & $venvPython $contract.CLIProxyDownloader }
        }

        Invoke-Checked "Build pinned Gemini Web bridge" {
            & (Join-Path $repoRoot "desktop\gemini_web_to_api\build.ps1") -RepositoryRoot $repoRoot
        }

        if ($IncludeOracle) {
            $oracleRoot = Join-Path $repoRoot "desktop\chatgpt_oracle"
            $oracleNodeRoot = Join-Path $oracleRoot "node"
            New-Item -ItemType Directory -Path $oracleNodeRoot -Force | Out-Null
            $nodeCommand = Get-Command "node.exe" -CommandType Application -ErrorAction SilentlyContinue
            if ($null -eq $nodeCommand) {
                throw "Node.js 24 is required to bundle the ChatGPT web runtime."
            }
            $nodeVersion = (& $nodeCommand.Source --version 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -ne 0 -or $nodeVersion -notmatch "^v24\.") {
                throw "Node.js 24 is required to bundle the ChatGPT web runtime; found '$nodeVersion'."
            }
            Invoke-Checked "Bundle portable Node runtime for ChatGPT Web" {
                Copy-Item -LiteralPath $nodeCommand.Source -Destination (Join-Path $oracleNodeRoot "node.exe") -Force
            }
            Invoke-Checked "Install pinned ChatGPT Oracle package" {
                & npm ci --prefix $oracleRoot --ignore-scripts --no-audit --no-fund
            }
            $oracleCli = Join-Path $oracleRoot "node_modules\@steipete\oracle\dist\bin\oracle-cli.js"
            if (-not (Test-Path -LiteralPath $oracleCli -PathType Leaf)) {
                throw "ChatGPT Oracle CLI is missing after npm ci: $oracleCli"
            }
        }

        if (Test-Path -LiteralPath $contract.StageRoot) {
            Remove-Item -LiteralPath $contract.StageRoot -Recurse -Force
        }
        New-Item -ItemType Directory -Path $contract.StageRoot | Out-Null

        $previousOracleFlag = $env:DEBATEAI_INCLUDE_ORACLE
        if ($IncludeOracle) {
            $env:DEBATEAI_INCLUDE_ORACLE = "1"
        } else {
            Remove-Item Env:DEBATEAI_INCLUDE_ORACLE -ErrorAction SilentlyContinue
        }
        try {
            Invoke-Checked "Build Windows desktop bundle" {
                & $venvPython -m PyInstaller $contract.Spec `
                    --distpath $contract.StageRoot `
                    --workpath $contract.PyInstallerWork `
                    --noconfirm
            }
        } finally {
            if ($null -eq $previousOracleFlag) {
                Remove-Item Env:DEBATEAI_INCLUDE_ORACLE -ErrorAction SilentlyContinue
            } else {
                $env:DEBATEAI_INCLUDE_ORACLE = $previousOracleFlag
            }
        }

        if (-not (Test-Path -LiteralPath $contract.StagedBundle -PathType Container)) {
            throw "Staged Windows bundle directory is missing: $($contract.StagedBundle)"
        }
        Invoke-Checked "Smoke test staged desktop bundle" {
            & $venvPython $contract.SmokeTest --bundle $contract.StagedBundle
        }

        Write-Host "[build] Package staged candidate $($contract.StagedArtifact)"
        Compress-Archive -LiteralPath $contract.StagedBundle -DestinationPath $contract.StagedArtifact -Force
        $artifact = Get-Item -LiteralPath $contract.StagedArtifact
        if ($artifact.Length -le 0) { throw "Windows debate assistant zip is empty." }

        $smokeDirectory = Split-Path -Parent $contract.CanonicalSmokeArtifact
        if (Test-Path -LiteralPath $smokeDirectory) {
            Remove-Item -LiteralPath $smokeDirectory -Recurse -Force
        }
        New-Item -ItemType Directory -Path $smokeDirectory | Out-Null
        try {
            Copy-Item -LiteralPath $contract.StagedArtifact -Destination $contract.CanonicalSmokeArtifact
            Invoke-Checked "Smoke test packaged update archive" {
                & $venvPython $contract.ArchiveSmokeTest `
                    --platform windows-x64 --archive $contract.CanonicalSmokeArtifact
            }
        } finally {
            Remove-Item -LiteralPath $smokeDirectory -Recurse -Force -ErrorAction SilentlyContinue
        }
        Write-Host "[build] Publish verified release candidate"
        Publish-ReleaseCandidate -Contract $contract
        $artifact = Get-Item -LiteralPath $contract.Artifact
        Write-Host "[build] Ready: $($artifact.FullName) ($([math]::Round($artifact.Length / 1MB, 1)) MB)"
    } finally {
        Pop-Location
    }
}

if ($MyInvocation.InvocationName -ne ".") {
    Invoke-DebateDesktopBuild
}

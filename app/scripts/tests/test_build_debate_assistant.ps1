$ErrorActionPreference = "Stop"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$scriptPath = Join-Path $PSScriptRoot "..\build_debate_assistant.ps1"
Assert-True (Test-Path -LiteralPath $scriptPath -PathType Leaf) `
    "Debate assistant build script is missing"

$buildSource = Get-Content -LiteralPath $scriptPath -Raw
Assert-True ($buildSource.Contains("Remove-OracleDevelopmentFiles")) `
    "Oracle development files are not pruned before packaging"

. $scriptPath

Assert-True (Test-Python312Version "Python 3.12.10") "Python 3.12 was rejected"
Assert-True (-not (Test-Python312Version "Python 3.11.9")) "Python 3.11 was accepted"
Assert-True (-not (Test-Python312Version "Python 3.13.0")) "Python 3.13 was accepted"

$resolvedRoot = Get-RepositoryRoot -ScriptDirectory (Join-Path $PSScriptRoot "..")
$expectedRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
Assert-True ($resolvedRoot -eq $expectedRoot) "Repository root resolution drifted"

$contract = Get-DesktopBuildContract -RepositoryRoot $expectedRoot
Assert-True ($contract.Spec -eq (Join-Path $expectedRoot "desktop\debateai.spec")) `
    "Build does not use desktop/debateai.spec"
Assert-True ($contract.PythonConstraints -eq (Join-Path $expectedRoot "desktop\constraints-windows-py312.txt")) `
    "Windows release dependencies are not constrained"
Assert-True (Test-Path -LiteralPath $contract.PythonConstraints -PathType Leaf) `
    "Windows release dependency constraints are missing"
Assert-True ($contract.Venv -eq (Join-Path ([IO.Path]::GetFullPath((Join-Path $expectedRoot ".."))) "DebateAI_Generated\dependencies\python\release-venv")) `
    "Release venv must be regenerated under disposable Generated"
Assert-True ($contract.ModelDownloader -eq (Join-Path $expectedRoot "backend\scripts\download_models.py")) `
    "Build duplicated or bypassed the model downloader"
Assert-True ($contract.PostgresDownloader -eq (Join-Path $expectedRoot "desktop\scripts\download_pg.py")) `
    "Build duplicated or bypassed the Postgres downloader"
Assert-True ($contract.FfmpegDownloader -eq (Join-Path $expectedRoot "desktop\scripts\download_ffmpeg.py")) `
    "Build duplicated or bypassed the ffmpeg downloader"
Assert-True ($contract.SmokeTest -eq (Join-Path $expectedRoot "desktop\scripts\smoke_test.py")) `
    "Build does not use the existing desktop smoke test"
$generatedRoot = [IO.Path]::GetFullPath((Join-Path $expectedRoot "../DebateAI_Generated"))
Assert-True ($contract.Artifact -eq (Join-Path $generatedRoot "build\releases\DebateAI-windows-x64.zip")) `
    "Bundle archive must stay inside disposable Generated"
Assert-True ($contract.Bundle -eq (Join-Path $generatedRoot "build\releases\DebateAI")) `
    "Built bundle must stay inside disposable Generated"
Assert-True ($contract.CanonicalSmokeArtifact -eq (Join-Path $generatedRoot "build\.debate-smoke\DebateAI-windows-x64.zip")) `
    "Archive smoke test must be disposable"
Assert-True ($contract.StageRoot -eq (Join-Path $generatedRoot "build\release-stage")) `
    "Release candidate is not isolated in disposable staging"
Assert-True ($contract.NpmCache -eq (Join-Path $generatedRoot "cache\npm")) `
    "Npm download cache must be disposable"
Assert-True ($contract.PipCache -eq (Join-Path $generatedRoot "cache\pip")) `
    "Python package cache must be disposable"
Assert-True ($contract.StagedBundle -eq (Join-Path $contract.StageRoot "DebateAI")) `
    "Staged bundle contract drifted"
Assert-True ($contract.StagedArtifact -eq (Join-Path $contract.StageRoot "DebateAI-windows-x64.zip")) `
    "Staged archive contract drifted"
Assert-True ($contract.StagedBundle -ne $contract.Bundle) `
    "Build would overwrite the final bundle before smoke verification"

$failedFast = $false
try {
    Assert-CommandSucceeded -ExitCode 7 -Label "fixture"
} catch {
    $failedFast = $_.Exception.Message -match "fixture.*7"
}
Assert-True $failedFast "Native command failures do not stop the build"
Assert-CommandSucceeded -ExitCode 0 -Label "fixture"

$fixtureRoot = Join-Path $expectedRoot ("build\test-publish-contract-" + [Guid]::NewGuid().ToString("N"))
try {
    $fixture = [pscustomobject]@{
        Bundle = Join-Path $fixtureRoot "dist\DebateAI"
        Artifact = Join-Path $fixtureRoot "dist\DebateAI.zip"
        StagedBundle = Join-Path $fixtureRoot "stage\DebateAI"
        StagedArtifact = Join-Path $fixtureRoot "stage\DebateAI.zip"
    }
    New-Item -ItemType Directory -Path $fixture.Bundle -Force | Out-Null
    New-Item -ItemType Directory -Path $fixture.StagedBundle -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $fixture.Bundle "version.txt") -Value "old"
    Set-Content -LiteralPath $fixture.Artifact -Value "old archive"
    Set-Content -LiteralPath (Join-Path $fixture.StagedBundle "version.txt") -Value "new"
    Set-Content -LiteralPath $fixture.StagedArtifact -Value "new archive"

    Publish-ReleaseCandidate -Contract $fixture

    Assert-True ((Get-Content -Raw (Join-Path $fixture.Bundle "version.txt")).Trim() -eq "new") `
        "Verified staged bundle was not published"
    Assert-True ((Get-Content -Raw $fixture.Artifact).Trim() -eq "new archive") `
        "Verified staged archive was not published"

    $rollback = [pscustomobject]@{
        Bundle = Join-Path $fixtureRoot "rollback-dist\DebateAI"
        Artifact = Join-Path $fixtureRoot "rollback-dist\DebateAI.zip"
        StagedBundle = Join-Path $fixtureRoot "rollback-stage\DebateAI"
        StagedArtifact = Join-Path $fixtureRoot "rollback-stage\missing.zip"
    }
    New-Item -ItemType Directory -Path $rollback.Bundle -Force | Out-Null
    New-Item -ItemType Directory -Path $rollback.StagedBundle -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $rollback.Bundle "version.txt") -Value "old"
    Set-Content -LiteralPath $rollback.Artifact -Value "old archive"
    Set-Content -LiteralPath (Join-Path $rollback.StagedBundle "version.txt") -Value "bad candidate"
    $rolledBack = $false
    try {
        Publish-ReleaseCandidate -Contract $rollback
    } catch {
        $rolledBack = $true
    }
    Assert-True $rolledBack "A partial publish unexpectedly succeeded"
    Assert-True ((Get-Content -Raw (Join-Path $rollback.Bundle "version.txt")).Trim() -eq "old") `
        "Failed publish did not restore the previous bundle"
    Assert-True ((Get-Content -Raw $rollback.Artifact).Trim() -eq "old archive") `
        "Failed publish did not restore the previous archive"

    foreach ($failureMove in @(1, 2)) {
        $earlyFailure = [pscustomobject]@{
            Bundle = Join-Path $fixtureRoot "early-$failureMove-dist\DebateAI"
            Artifact = Join-Path $fixtureRoot "early-$failureMove-dist\DebateAI.zip"
            StagedBundle = Join-Path $fixtureRoot "early-$failureMove-stage\DebateAI"
            StagedArtifact = Join-Path $fixtureRoot "early-$failureMove-stage\DebateAI.zip"
        }
        New-Item -ItemType Directory -Path $earlyFailure.Bundle -Force | Out-Null
        New-Item -ItemType Directory -Path $earlyFailure.StagedBundle -Force | Out-Null
        Set-Content -LiteralPath (Join-Path $earlyFailure.Bundle "version.txt") -Value "old"
        Set-Content -LiteralPath $earlyFailure.Artifact -Value "old archive"
        Set-Content -LiteralPath (Join-Path $earlyFailure.StagedBundle "version.txt") -Value "new"
        Set-Content -LiteralPath $earlyFailure.StagedArtifact -Value "new archive"
        $moveState = @{ Count = 0; FailureMove = $failureMove }
        $moveAction = {
            param([string]$Source, [string]$Destination)
            $moveState.Count++
            if ($moveState.Count -eq $moveState.FailureMove) {
                throw "Injected move failure $($moveState.FailureMove)"
            }
            Move-Item -LiteralPath $Source -Destination $Destination
        }.GetNewClosure()
        $failed = $false
        try {
            Publish-ReleaseCandidate -Contract $earlyFailure -MoveAction $moveAction
        } catch {
            $failed = $true
        }
        Assert-True $failed "Injected backup failure $failureMove unexpectedly succeeded"
        Assert-True ((Get-Content -Raw (Join-Path $earlyFailure.Bundle "version.txt")).Trim() -eq "old") `
            "Backup failure $failureMove removed the previous bundle"
        Assert-True ((Get-Content -Raw $earlyFailure.Artifact).Trim() -eq "old archive") `
            "Backup failure $failureMove removed the previous archive"
    }
} finally {
    if (Test-Path -LiteralPath $fixtureRoot) {
        Remove-Item -LiteralPath $fixtureRoot -Recurse -Force
    }
}

Write-Output "Debate assistant desktop build contract: OK"
exit 0

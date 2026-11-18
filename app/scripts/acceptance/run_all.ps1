[CmdletBinding()]
param(
    [ValidateSet('Fast','Full','Audio','ASR','Prompts','Security','Desktop','Release','Report')]
    [string]$Profile = 'Full',
    [string]$Python,
    [string]$OutputDirectory,
    [string]$ResumeState,
    [switch]$AllowNetwork
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if (-not $Python) {
    $localPython = Join-Path $repo 'DebateAI_Generated/dependencies/python/release-venv/Scripts/python.exe'
    if (Test-Path -LiteralPath $localPython -PathType Leaf) { $Python = $localPython }
}
if (-not $Python) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        $candidate = & $launcher.Source -3.12 -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0) { $Python = [string]($candidate | Select-Object -Last 1) }
    }
}
if (-not $Python) {
    $fallback = Get-Command python -ErrorAction SilentlyContinue
    if ($fallback) { $Python = $fallback.Source }
}
if (-not $Python) { throw 'Project Python unavailable; no automatic installation attempted.' }
$arguments = @((Join-Path $PSScriptRoot 'run.py'), '--repo', $repo, '--profile', $Profile)
if ($OutputDirectory) { $arguments += @('--output', $OutputDirectory) }
if ($ResumeState) { $arguments += @('--resume', $ResumeState) }
if ($AllowNetwork) { $arguments += '--allow-network' }
& $Python @arguments
if ($null -eq $LASTEXITCODE) { throw 'Acceptance process returned no exit code.' }
exit $LASTEXITCODE

[CmdletBinding()]
param(
    [string]$Version = "",
    [string]$Python = "python",
    [switch]$SkipDownloads
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Version) {
    & (Join-Path $PSScriptRoot "scripts\release_desktop.ps1") -Version $Version
    exit $LASTEXITCODE
}

& (Join-Path $PSScriptRoot "scripts\build_debate_assistant.ps1") `
    -Python $Python -SkipDownloads:$SkipDownloads
exit $LASTEXITCODE

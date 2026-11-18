param(
    [string]$Url = 'http://127.0.0.1:8474/?desktop=1',
    [string]$OutputRoot = (Join-Path $PSScriptRoot '../../DebateAI_Generated/reports/gui-capture'),
    [int]$Width = 1440,
    [int]$Height = 900,
    [switch]$BothThemes
)
$ErrorActionPreference = 'Stop'
if ((node --version) -notmatch '^v24\.') { throw 'Node 24 is required.' }
$runFolder = Join-Path ([IO.Path]::GetFullPath($OutputRoot)) (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
New-Item -ItemType Directory -Path $runFolder -Force | Out-Null
$failed = $false
try {
    $themes = @('dark')
    if ($BothThemes) { $themes += 'light' }
    foreach ($theme in $themes) {
        & node (Join-Path $PSScriptRoot 'gui-capture/run.mjs') --url $Url --output (Join-Path $runFolder $theme) --theme $theme --width $Width --height $Height
        if ($LASTEXITCODE -ne 0) { $failed = $true }
    }
} finally {
    Compress-Archive -Path (Join-Path $runFolder '*') -DestinationPath "$runFolder.zip"
    Write-Output "Screenshots and report: $runFolder"
    Write-Output "Archive: $runFolder.zip"
}
if ($failed) { throw 'Capture incomplete. See manifest.json for missing surfaces; screenshots and ZIP were retained.' }

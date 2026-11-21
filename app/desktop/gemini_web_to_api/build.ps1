param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
)

$ErrorActionPreference = "Stop"

# Codex can inject GIT_CONFIG_COUNT without the matching key variables into a
# child process. Clear that malformed session-only override before git apply so
# the verified upstream patch is evaluated against the downloaded source.
Get-ChildItem Env:GIT_CONFIG_* -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -LiteralPath ("Env:" + $_.Name) -ErrorAction SilentlyContinue
}

if ($env:OS -ne "Windows_NT") {
    throw "This pinned dependency build currently targets Windows amd64 only."
}

$sourceUrl = "https://github.com/ntthanh2603/gemini-web-to-api/archive/refs/tags/v1.3.4.zip"
$sourceHash = "a2533adcb6ce3c5715598077ebc6460140d2af1274394a77040bdf6bbbdc0f81"
$goUrl = "https://go.dev/dl/go1.27.3.windows-amd64.zip"
$goHash = "f26081f438319757f8a1b46d7d0b2c5ec7583d4038e485e0aa725cfde7885fff"
$target = Join-Path $RepositoryRoot "desktop\gemini_web_to_api\gemini-web-to-api.exe"
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("debateai-gemini-build-" + [guid]::NewGuid().ToString("N"))

function Assert-Hash([string]$Path, [string]$Expected) {
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    if ($actual -ne $Expected) {
        throw "Checksum mismatch for $Path. Expected $Expected, got $actual."
    }
}

try {
    New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
    $sourceArchive = Join-Path $temporaryRoot "source.zip"
    $goArchive = Join-Path $temporaryRoot "go.zip"
    Invoke-WebRequest -UseBasicParsing -Uri $sourceUrl -OutFile $sourceArchive
    Invoke-WebRequest -UseBasicParsing -Uri $goUrl -OutFile $goArchive
    Assert-Hash $sourceArchive $sourceHash
    Assert-Hash $goArchive $goHash

    $sourceRoot = Join-Path $temporaryRoot "source"
    $goRoot = Join-Path $temporaryRoot "go-sdk"
    New-Item -ItemType Directory -Path $sourceRoot, $goRoot | Out-Null
    & tar.exe -xf $sourceArchive -C $sourceRoot
    & tar.exe -xf $goArchive -C $goRoot
    if ($LASTEXITCODE -ne 0) { throw "Archive extraction failed." }

    $source = Join-Path $sourceRoot "gemini-web-to-api-1.3.4"
    & git -C $source apply (Join-Path $PSScriptRoot "debateai-loopback.patch")
    if ($LASTEXITCODE -ne 0) { throw "The loopback patch no longer applies." }

    $go = Join-Path $goRoot "go\bin\go.exe"
    $env:GOMODCACHE = Join-Path $temporaryRoot "gomodcache"
    $env:GOCACHE = Join-Path $temporaryRoot "gocache"
    Push-Location $source
    try {
        & $go fmt "./internal/commons/configs" "./internal/server"
        if ($LASTEXITCODE -ne 0) { throw "go fmt failed." }
    } finally {
        Pop-Location
    }
    $built = Join-Path $temporaryRoot "gemini-web-to-api.exe"
    Push-Location $source
    try {
        & $go build -trimpath -ldflags "-s -w" -o $built ".\cmd\server"
        if ($LASTEXITCODE -ne 0) { throw "go build failed." }
    } finally {
        Pop-Location
    }
    Copy-Item -LiteralPath $built -Destination $target -Force
    Get-FileHash -Algorithm SHA256 -LiteralPath $target
} finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}

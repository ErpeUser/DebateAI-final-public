[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [switch]$SkipDatabase,
    [ValidateRange(0, 300)]
    [int]$SmokeSeconds = 0
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
$frontendRoot = Join-Path $repoRoot "frontend"
$promptRoot = Join-Path $backendRoot "prompts"

function Test-TcpPort {
    param([int]$Port)
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Port)
        return $task.Wait(250) -and $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Resolve-BackendPython {
    $candidates = @(
        (Join-Path $repoRoot "../DebateAI_Generated/dependencies/python/release-venv/Scripts/python.exe"),
        (Join-Path $repoRoot ".venv\Scripts\python.exe"),
        (Join-Path $repoRoot ".release-venv\Scripts\python.exe")
    )
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        & $candidate -c "import fastapi, uvicorn, watchfiles" 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    throw "Keine Python-Umgebung mit FastAPI, Uvicorn und Watchfiles gefunden. Installiere backend\requirements.txt in .venv."
}

function Stop-OwnedProcess {
    param([Diagnostics.Process]$Process)
    if ($null -eq $Process -or $Process.HasExited) { return }
    if ($env:OS -eq "Windows_NT") {
        & taskkill.exe /PID $Process.Id /T /F 2>$null | Out-Null
    } else {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
}

function Start-BundledPostgres {
    $pgBin = Join-Path $repoRoot "desktop\pgsql\bin"
    $pgCtl = Join-Path $pgBin "pg_ctl.exe"
    $initDb = Join-Path $pgBin "initdb.exe"
    if (-not (Test-Path -LiteralPath $pgCtl -PathType Leaf) -or
        -not (Test-Path -LiteralPath $initDb -PathType Leaf)) {
        throw "Docker läuft nicht und die gebündelten PostgreSQL-Binärdateien fehlen."
    }

    $dataRoot = if ($env:DEBATEAI_DATA_DIR) {
        $env:DEBATEAI_DATA_DIR
    } else {
        Join-Path $env:LOCALAPPDATA "DebateAI"
    }
    $pgData = Join-Path $dataRoot "pgdata"
    $passwordFile = Join-Path $dataRoot "pgpassword"
    $logFile = Join-Path $dataRoot "postgres-dev.log"
    New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null

    $pidFile = Join-Path $pgData "postmaster.pid"
    if (Test-Path -LiteralPath $pidFile -PathType Leaf) {
        $pidLines = @(Get-Content -LiteralPath $pidFile)
        $recordedPort = if ($pidLines.Count -ge 4) { $pidLines[3] -as [int] } else { 0 }
        if ($recordedPort -gt 0 -and (Test-TcpPort -Port $recordedPort)) {
            if (-not (Test-Path -LiteralPath $passwordFile -PathType Leaf)) {
                throw "Das Passwort der laufenden lokalen PostgreSQL-Datenbank fehlt."
            }
            return [pscustomobject]@{
                PgCtl = $pgCtl
                PgData = $pgData
                Password = (Get-Content -Raw -LiteralPath $passwordFile).Trim()
                Port = $recordedPort
                Owned = $false
            }
        }
        $savedErrorPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & $pgCtl -D $pgData status 2>$null | Out-Null
            $pgStatus = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $savedErrorPreference
        }
        if ($pgStatus -ne 0) {
            Remove-Item -LiteralPath $pidFile -Force
        } else {
            throw "Die vorhandene PostgreSQL-Instanz antwortet nicht auf ihrem aufgezeichneten Port."
        }
    }

    if (-not (Test-Path -LiteralPath (Join-Path $pgData "PG_VERSION") -PathType Leaf)) {
        if (-not (Test-Path -LiteralPath $passwordFile -PathType Leaf)) {
            ([Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N")) |
                Set-Content -LiteralPath $passwordFile -Encoding ascii -NoNewline
        }
        & $initDb -D $pgData -U debateai -A scram-sha-256 `
            --pwfile $passwordFile --no-locale -E UTF8
        if ($LASTEXITCODE -ne 0) { throw "Die lokale PostgreSQL-Datenbank konnte nicht initialisiert werden." }
    }
    if (-not (Test-Path -LiteralPath $passwordFile -PathType Leaf)) {
        throw "Das Passwort der vorhandenen lokalen PostgreSQL-Datenbank fehlt."
    }

    & $pgCtl -D $pgData -o "-p 5432 -c listen_addresses=127.0.0.1" `
        -l $logFile -w start
    if ($LASTEXITCODE -ne 0) { throw "Die gebündelte PostgreSQL-Datenbank konnte nicht gestartet werden." }
    return [pscustomobject]@{
        PgCtl = $pgCtl
        PgData = $pgData
        Password = (Get-Content -Raw -LiteralPath $passwordFile).Trim()
        Port = 5432
        Owned = $true
    }
}

if (Test-TcpPort -Port $BackendPort) {
    throw "Port $BackendPort wird bereits verwendet. Nutze -BackendPort mit einem freien Port."
}
if (Test-TcpPort -Port $FrontendPort) {
    throw "Port $FrontendPort wird bereits verwendet. Nutze -FrontendPort mit einem freien Port."
}

$python = Resolve-BackendPython
$node = (Get-Command node.exe -ErrorAction Stop).Source
$vite = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"
if (-not (Test-Path -LiteralPath $vite -PathType Leaf)) {
    throw "Frontend-Abhängigkeiten fehlen. Führe einmal 'npm install' im Ordner frontend aus."
}

$databaseStarted = ""
$embeddedDatabase = $null
$databasePort = 5432
$backend = $null
$frontend = $null
$oldDatabaseUrl = $env:DATABASE_URL
$oldPromptDir = $env:DEBATEAI_PROMPT_DIR
$oldApiTarget = $env:DEBATEAI_API_TARGET

try {
    if (-not $SkipDatabase -and -not $env:DATABASE_URL -and -not (Test-TcpPort -Port 5432)) {
        $docker = Get-Command docker.exe -ErrorAction SilentlyContinue
        $dockerReady = $false
        if ($docker) {
            $savedErrorPreference = $ErrorActionPreference
            try {
                $ErrorActionPreference = "Continue"
                & $docker.Source info 2>$null | Out-Null
                $dockerReady = $LASTEXITCODE -eq 0
            } finally {
                $ErrorActionPreference = $savedErrorPreference
            }
        }
        $desktopCluster = Join-Path $env:LOCALAPPDATA "DebateAI\pgdata\PG_VERSION"
        if (Test-Path -LiteralPath $desktopCluster -PathType Leaf) {
            Write-Host "[dev] Verwende die vorhandene eingebettete PostgreSQL-Datenbank ..."
            $embeddedDatabase = Start-BundledPostgres
            $databasePort = $embeddedDatabase.Port
            $databaseStarted = if ($embeddedDatabase.Owned) { "embedded" } else { "existing" }
        } elseif ($dockerReady) {
            Write-Host "[dev] Starte PostgreSQL über Docker ..."
            & $docker.Source compose -f (Join-Path $repoRoot "docker-compose.yml") up -d db
            if ($LASTEXITCODE -ne 0) { throw "PostgreSQL konnte nicht gestartet werden." }
            $databaseStarted = "docker"
        } else {
            Write-Host "[dev] Starte die vorhandene eingebettete PostgreSQL-Datenbank ..."
            $embeddedDatabase = Start-BundledPostgres
            $databasePort = $embeddedDatabase.Port
            $databaseStarted = "embedded"
        }
        $deadline = [DateTime]::UtcNow.AddSeconds(45)
        while (-not (Test-TcpPort -Port $databasePort)) {
            if ([DateTime]::UtcNow -ge $deadline) { throw "PostgreSQL wurde nicht rechtzeitig bereit." }
            Start-Sleep -Milliseconds 500
        }
    }

    if (-not $env:DATABASE_URL) {
        if ($databaseStarted -in @("embedded", "existing")) {
            $env:DATABASE_URL = "postgresql+asyncpg://debateai:$($embeddedDatabase.Password)@127.0.0.1:$databasePort/postgres"
        } else {
            $composeUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "debateai" }
            $composePassword = $env:POSTGRES_PASSWORD
            $composeDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "debateai" }
            if ([string]::IsNullOrWhiteSpace($composePassword)) {
                throw "POSTGRES_PASSWORD muss gesetzt sein, bevor die Docker-Datenbank verwendet wird."
            }
            $env:DATABASE_URL = "postgresql+asyncpg://" + $composeUser + ":" + $composePassword + "@127.0.0.1:5432/" + $composeDb
        }
    }
    $env:DEBATEAI_PROMPT_DIR = $promptRoot

    Write-Host "[dev] Backend mit Python-Reload und externen Prompts ..."
    $backend = Start-Process -FilePath $python -ArgumentList @(
        "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", "$BackendPort",
        "--reload", "--reload-dir", "app"
    ) -WorkingDirectory $backendRoot -PassThru -NoNewWindow

    $backendDeadline = [DateTime]::UtcNow.AddSeconds(45)
    while (-not (Test-TcpPort -Port $BackendPort)) {
        if ($backend.HasExited) { throw "Das Backend wurde mit Code $($backend.ExitCode) beendet." }
        if ([DateTime]::UtcNow -ge $backendDeadline) { throw "Das Backend wurde nicht rechtzeitig bereit." }
        Start-Sleep -Milliseconds 300
    }

    Write-Host "[dev] Frontend mit Vite Fast Refresh ..."
    $env:DEBATEAI_API_TARGET = "http://127.0.0.1:$BackendPort"
    $frontend = Start-Process -FilePath $node -ArgumentList @(
        $vite, "--host", "127.0.0.1", "--port", "$FrontendPort", "--strictPort"
    ) -WorkingDirectory $frontendRoot -PassThru -NoNewWindow

    Write-Host "[dev] Bereit: http://127.0.0.1:$FrontendPort"
    Write-Host "[dev] React aktualisiert sofort; Python lädt gezielt neu; backend\prompts\debate_live_v2.txt wirkt beim nächsten Modellaufruf."
    Write-Host "[dev] Beenden mit Strg+C."
    $smokeDeadline = if ($SmokeSeconds -gt 0) {
        [DateTime]::UtcNow.AddSeconds($SmokeSeconds)
    } else {
        [DateTime]::MaxValue
    }
    while (-not $backend.HasExited -and -not $frontend.HasExited) {
        if ([DateTime]::UtcNow -ge $smokeDeadline) {
            Write-Host "[dev] Smoke-Lauf beendet."
            return
        }
        Start-Sleep -Milliseconds 500
    }
    if ($backend.HasExited) { throw "Das Backend wurde mit Code $($backend.ExitCode) beendet." }
    throw "Das Frontend wurde mit Code $($frontend.ExitCode) beendet."
} finally {
    Stop-OwnedProcess -Process $frontend
    Stop-OwnedProcess -Process $backend
    if ($databaseStarted -eq "docker") {
        Write-Host "[dev] Stoppe die von diesem Lauf gestartete Datenbank ..."
        & docker.exe compose -f (Join-Path $repoRoot "docker-compose.yml") stop db 2>$null | Out-Null
    } elseif ($databaseStarted -eq "embedded" -and $null -ne $embeddedDatabase) {
        Write-Host "[dev] Stoppe die von diesem Lauf gestartete Datenbank ..."
        & $embeddedDatabase.PgCtl -D $embeddedDatabase.PgData -m fast -w stop 2>$null | Out-Null
    }
    $env:DATABASE_URL = $oldDatabaseUrl
    $env:DEBATEAI_PROMPT_DIR = $oldPromptDir
    $env:DEBATEAI_API_TARGET = $oldApiTarget
}

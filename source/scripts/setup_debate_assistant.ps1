[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [switch]$SkipModelPull,
    [switch]$Research,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$script:EndpointName = "German Debate Ollama"
$script:WireModel = "qwen3:4b"
$script:ApiBase = "http://127.0.0.1:8001"
$script:RepoRoot = Split-Path -Parent $PSScriptRoot

function Get-SetupCommandPlan {
    param(
        [bool]$OllamaInstalled,
        [bool]$DockerReady,
        [bool]$SkipInstall,
        [bool]$SkipModelPull
    )
    $commands = @()
    if (-not $OllamaInstalled -and -not $SkipInstall) {
        $commands += "winget install Ollama.Ollama"
    }
    if (-not $SkipModelPull) {
        $commands += "ollama pull qwen3:4b"
    }
    if (-not $DockerReady) {
        $commands += "start Docker Desktop"
    }
    $commands += "docker compose up"
    return $commands
}

function Resolve-EndpointUpsert {
    param([object[]]$Endpoints, [string]$EndpointName)
    $existing = @($Endpoints) | Where-Object {
        $null -ne $_ -and
        $null -ne $_.PSObject.Properties["name"] -and
        $_.name -eq $EndpointName
    } | Select-Object -First 1
    if ($null -ne $existing) {
        return [pscustomobject]@{ Method = "PUT"; Path = "/api/endpoints/$($existing.id)"; Id = $existing.id }
    }
    return [pscustomobject]@{ Method = "POST"; Path = "/api/endpoints"; Id = $null }
}

function Get-EndpointModelId {
    param([string]$EndpointId, [string]$WireModel)
    return "endpoint:${EndpointId}:${WireModel}"
}

function Get-TranscriptionPayload {
    return [ordered]@{
        batch_model_id = "local-parakeet-tdt-0.6b-v3"
        live_preview_model_id = "local-parakeet-v3-live"
        language = "de"
    }
}

function Get-AgentPatches {
    param([string]$ModelId)
    $slugs = @(
        "consolidated_analyst",
        "objection_handler",
        "synthesizer",
        "opportunity_specialist",
        "strategic_signals",
        "transcript_refiner",
        "brief_meeting_lens",
        "brief_discovery_lens",
        "brief_arbiter"
    )
    foreach ($slug in $slugs) {
        [pscustomobject]@{ slug = $slug; model_id = $ModelId }
    }
}

function Get-PrivacyPayload {
    param([bool]$Research)
    return [ordered]@{ local_only = -not $Research }
}

function Get-ResearchEgressMessage {
    param([bool]$Research)
    if ($Research) {
        return "Recherche aktiv: Nur kurze Faktenfragen koennen an die konfigurierten ChatGPT-Web/Gemini-Recherchekanaele gesendet werden. Audio und Transkripte bleiben lokal."
    }
    return "Privacy First aktiv: keine externe Recherche; Audio, Transkription und Textanalyse bleiben lokal."
}

function Test-Program {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments, [string]$Label)
    Write-Host "[setup] $Label"
    if ($DryRun) {
        Write-Host "  DRY RUN: $Program $($Arguments -join ' ')"
        return
    }
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

function Get-OllamaProgram {
    $command = Get-Command "ollama" -ErrorAction SilentlyContinue
    if ($null -ne $command) { return $command.Source }
    $installed = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path -LiteralPath $installed -PathType Leaf) { return $installed }
    return $null
}

function Wait-HttpReady {
    param([string]$Uri, [int]$TimeoutSeconds = 180)
    if ($DryRun) {
        Write-Host "  DRY RUN: wait for $Uri"
        return
    }
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec 5 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $Uri."
}

function Ensure-Ollama {
    $ollama = Get-OllamaProgram
    if ($null -eq $ollama) {
        if ($SkipInstall) {
            if ($DryRun) {
                Write-Host "  DRY RUN: Ollama is absent and installation is intentionally skipped"
                return "ollama"
            }
            throw "Ollama is not installed. Re-run without -SkipInstall."
        }
        Invoke-Checked "winget" @(
            "install", "--id", "Ollama.Ollama", "--exact",
            "--accept-package-agreements", "--accept-source-agreements",
            "--silent", "--disable-interactivity"
        ) "Install Ollama"
        if ($DryRun) { return "ollama" }
        $ollama = Get-OllamaProgram
        if ($null -eq $ollama) { throw "Ollama installed, but ollama.exe was not found." }
    }

    if (-not $DryRun) {
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null
        } catch {
            Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
            Wait-HttpReady -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSeconds 60
        }
    }
    if (-not $SkipModelPull) {
        Invoke-Checked $ollama @("pull", $script:WireModel) "Pull $($script:WireModel)"
    }
    return $ollama
}

function Ensure-DockerReady {
    if (-not (Test-Program "docker")) {
        throw "Docker Desktop with Docker Compose is required. Install it, then re-run this script."
    }
    if ($DryRun) {
        Write-Host "  DRY RUN: verify Docker Desktop"
        return
    }
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & docker info *> $null
    $dockerExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    if ($dockerExitCode -eq 0) { return }

    $desktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path -LiteralPath $desktop -PathType Leaf)) {
        throw "Docker is installed but its engine is not running, and Docker Desktop could not be found."
    }
    Write-Host "[setup] Start Docker Desktop"
    Start-Process -FilePath $desktop -WindowStyle Hidden
    $deadline = (Get-Date).AddMinutes(3)
    do {
        Start-Sleep -Seconds 3
        $ErrorActionPreference = "Continue"
        & docker info *> $null
        $dockerExitCode = $LASTEXITCODE
        $ErrorActionPreference = $previousPreference
        if ($dockerExitCode -eq 0) { return }
    } while ((Get-Date) -lt $deadline)
    throw "Docker Desktop did not become ready within three minutes."
}

function Set-EnvSetting {
    param([string]$Path, [string]$Name, [string]$Value)
    if ($DryRun) {
        Write-Host "  DRY RUN: set $Name=$Value in $Path"
        return
    }
    $lines = if (Test-Path -LiteralPath $Path) { @(Get-Content -LiteralPath $Path) } else { @() }
    $pattern = "^\s*#?\s*" + [regex]::Escape($Name) + "="
    $replacement = "$Name=$Value"
    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match $pattern) {
            if (-not $found) { $replacement }
            $found = $true
        } else {
            $line
        }
    }
    if (-not $found) { $updated += $replacement }
    Set-Content -LiteralPath $Path -Value $updated -Encoding utf8
}

function Invoke-ApiJson {
    param([string]$Method, [string]$Path, [object]$Body = $null)
    $uri = "$($script:ApiBase)$Path"
    if ($DryRun) {
        $json = if ($null -eq $Body) { "" } else { $Body | ConvertTo-Json -Depth 8 -Compress }
        Write-Host "  DRY RUN: $Method $uri $json"
        return $null
    }
    $params = @{ Uri = $uri; Method = $Method; TimeoutSec = 30 }
    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = $Body | ConvertTo-Json -Depth 8
    }
    return Invoke-RestMethod @params
}

function Configure-DebateAI {
    Write-Host "[setup] Configure local endpoint and German debate agents"
    if ($DryRun) {
        $endpointId = "german-debate-ollama"
        Invoke-ApiJson -Method "POST" -Path "/api/endpoints" -Body @{
            name = $script:EndpointName
            base_url = "http://host.docker.internal:11434/v1"
            api_key = ""
            models = @(@{ id = $script:WireModel; label = "Qwen3 4B - German Debate" })
            enabled = $true
        } | Out-Null
    } else {
        $endpoints = @(Invoke-ApiJson -Method "GET" -Path "/api/endpoints")
        $upsert = Resolve-EndpointUpsert -Endpoints $endpoints -EndpointName $script:EndpointName
        $endpointBody = @{
            name = $script:EndpointName
            base_url = "http://host.docker.internal:11434/v1"
            api_key = ""
            models = @(@{ id = $script:WireModel; label = "Qwen3 4B - German Debate" })
            enabled = $true
        }
        $endpoint = Invoke-ApiJson -Method $upsert.Method -Path $upsert.Path -Body $endpointBody
        $endpointId = $endpoint.id
        Invoke-ApiJson -Method "POST" -Path "/api/endpoints/$endpointId/test" | Out-Null
    }

    $modelId = Get-EndpointModelId -EndpointId $endpointId -WireModel $script:WireModel
    foreach ($patch in @(Get-AgentPatches -ModelId $modelId)) {
        $body = @{ model_id = $patch.model_id }
        if ($patch.slug -eq "objection_handler") { $body.enabled = $true }
        Invoke-ApiJson -Method "PATCH" -Path "/api/agents/$($patch.slug)" -Body $body | Out-Null
    }
    Invoke-ApiJson -Method "PATCH" -Path "/api/diagnostics/transcription/config" `
        -Body (Get-TranscriptionPayload) | Out-Null
    Invoke-ApiJson -Method "PUT" -Path "/api/privacy" `
        -Body (Get-PrivacyPayload -Research:$Research) | Out-Null
}

function Invoke-DebateAssistantSetup {
    Push-Location $script:RepoRoot
    try {
        Write-Host "DebateAI German Debate Copilot setup"
        $hasNvidia = Test-Program "nvidia-smi"
        if ($hasNvidia) {
            if (-not $DryRun) { & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader }
        } else {
            Write-Warning "nvidia-smi was not found. Ollama can still run, but response latency may be higher."
        }

        Ensure-Ollama | Out-Null
        Ensure-DockerReady

        $envPath = Join-Path $script:RepoRoot ".env"
        if (-not (Test-Path -LiteralPath $envPath)) {
            if ($DryRun) {
                Write-Host "  DRY RUN: copy .env.example to .env"
            } else {
                Copy-Item -LiteralPath (Join-Path $script:RepoRoot ".env.example") -Destination $envPath
            }
        }
        Set-EnvSetting -Path $envPath -Name "DEBATE_RESEARCH_ENABLED" `
            -Value $(if ($Research) { "true" } else { "false" })

        $composeArguments = @(
            "compose", "-f", "docker-compose.yml", "-f", "docker-compose.debate.yml"
        )
        if ($hasNvidia) {
            $composeArguments += @("-f", "docker-compose.gpu.yml")
        }
        $composeArguments += @("up", "-d", "--build")
        Invoke-Checked "docker" $composeArguments "Start DebateAI"
        Wait-HttpReady -Uri "$($script:ApiBase)/api/privacy" -TimeoutSeconds 300
        Configure-DebateAI

        Write-Host ""
        Write-Host (Get-ResearchEgressMessage -Research:$Research)
        Write-Host "DebateAI: http://localhost:3000"
        Write-Host "Local model: $($script:WireModel) via Ollama"
        Write-Host "Transcription: Parakeet v3 (German, local)"
    } finally {
        Pop-Location
    }
}

if ($MyInvocation.InvocationName -ne ".") {
    Invoke-DebateAssistantSetup
}

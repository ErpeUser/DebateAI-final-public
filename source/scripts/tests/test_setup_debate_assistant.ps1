$ErrorActionPreference = "Stop"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$scriptPath = Join-Path $PSScriptRoot "..\setup_debate_assistant.ps1"
Assert-True (Test-Path -LiteralPath $scriptPath -PathType Leaf) `
    "Debate assistant setup script is missing"

. $scriptPath

$installPlan = Get-SetupCommandPlan -OllamaInstalled:$false -DockerReady:$false `
    -SkipInstall:$false -SkipModelPull:$false
Assert-True ($installPlan -contains "winget install Ollama.Ollama") `
    "Missing Ollama installation decision"
Assert-True ($installPlan -contains "ollama pull qwen3:4b") `
    "Missing model pull decision"
Assert-True ($installPlan -contains "docker compose up") `
    "Missing Compose startup decision"

$skipPlan = Get-SetupCommandPlan -OllamaInstalled:$false -DockerReady:$true `
    -SkipInstall:$true -SkipModelPull:$true
Assert-True (-not ($skipPlan -match "winget install")) "SkipInstall was ignored"
Assert-True (-not ($skipPlan -match "ollama pull")) "SkipModelPull was ignored"

$existing = @(
    [pscustomobject]@{ id = "team-gpu"; name = "Team GPU" },
    [pscustomobject]@{ id = "local-ollama"; name = "German Debate Ollama" }
)
$update = Resolve-EndpointUpsert -Endpoints $existing -EndpointName "German Debate Ollama"
Assert-True ($update.Method -eq "PUT") "Existing endpoint was not updated"
Assert-True ($update.Path -eq "/api/endpoints/local-ollama") "Wrong endpoint update path"

$create = Resolve-EndpointUpsert -Endpoints @() -EndpointName "German Debate Ollama"
Assert-True ($create.Method -eq "POST") "Missing endpoint was not created"
Assert-True ($create.Path -eq "/api/endpoints") "Wrong endpoint create path"

$emptyApiCreate = Resolve-EndpointUpsert -Endpoints @($null) -EndpointName "German Debate Ollama"
Assert-True ($emptyApiCreate.Method -eq "POST") `
    "An empty Invoke-RestMethod result was not treated as an empty endpoint list"

$modelId = Get-EndpointModelId -EndpointId "local-ollama" -WireModel "qwen3:4b"
Assert-True ($modelId -eq "endpoint:local-ollama:qwen3:4b") "Endpoint model id is not canonical"
Assert-True (([uri]::EscapeDataString($modelId)) -eq "endpoint%3Alocal-ollama%3Aqwen3%3A4b") `
    "Endpoint model id does not URL-encode safely"

$transcription = Get-TranscriptionPayload
Assert-True ($transcription.batch_model_id -eq "local-parakeet-tdt-0.6b-v3") `
    "German Parakeet v3 batch model is missing"
Assert-True ($transcription.live_preview_model_id -eq "local-parakeet-v3-live") `
    "German Parakeet v3 live model is missing"
Assert-True ($transcription.language -eq "de") "German transcription language is missing"

$patches = @(Get-AgentPatches -ModelId $modelId)
$expectedSlugs = @(
    "consolidated_analyst", "objection_handler", "synthesizer",
    "opportunity_specialist", "strategic_signals", "transcript_refiner",
    "brief_meeting_lens", "brief_discovery_lens", "brief_arbiter"
)
Assert-True ($patches.Count -eq $expectedSlugs.Count) "Unexpected live text agent patch count"
foreach ($slug in $expectedSlugs) {
    $patch = $patches | Where-Object slug -eq $slug
    Assert-True ($null -ne $patch) "Missing agent patch: $slug"
    Assert-True ($patch.model_id -eq $modelId) "Agent does not use the local model: $slug"
}

Assert-True ((Get-PrivacyPayload -Research:$false).local_only -eq $true) `
    "Privacy First should be enabled when research is off"
Assert-True ((Get-PrivacyPayload -Research:$true).local_only -eq $false) `
    "Research mode should explicitly disable Privacy First"
Assert-True ((Get-ResearchEgressMessage -Research:$false) -match "keine externe") `
    "Private mode does not clearly state that external research is off"
Assert-True ((Get-ResearchEgressMessage -Research:$true) -match "Wikimedia.*DuckDuckGo") `
    "Research mode does not name its external destinations"

Write-Output "Debate assistant setup contract: OK"

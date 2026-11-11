# German debate copilot

DebateAI can run as a local-first German debate assistant on Windows. It
transcribes the meeting, reacts to new final transcript turns, and keeps one
current recommendation with three speaking moves:

- **Jetzt antworten** -- the shortest direct reply;
- **Gegenargument** -- the strongest challenge to the preceding claim;
- **Rueckfrage** -- a useful question that returns the burden of proof.

## Start

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_debate_assistant.ps1
```

The script is idempotent. It detects Docker, Ollama, and the NVIDIA GPU, pulls
`qwen3:4b` when required, starts the Compose services, registers the local
OpenAI-compatible endpoint, selects German Parakeet v3 transcription, assigns
the debate agents, and enables Privacy First. Open
<http://localhost:3000> after it finishes.

For Discord, WhatsApp, or another desktop call, select the browser's option to
share system audio as well as the microphone. Use `-DryRun` to inspect the
planned changes or `-SkipInstall -SkipModelPull` when the local dependencies
are already present.

## Privacy and research

The default command keeps analysis and transcription local. It does not send a
research query to the internet. The live recommendation therefore labels
source refinement as disabled and does not pretend that unsourced claims are
verified.

The benchmark endpoint is separate from research: every custom fixture turn is
sent to the endpoint named by `--endpoint`. Keep the default loopback URL for a
local-only replay. Supplying a remote URL deliberately sends the fixture text
there, even though `research_egress` remains `disabled`; use `--api-key` only
when that endpoint requires a bearer credential.

`-Research` is a deliberate opt-in. In that mode, only the short factual search
query generated for source refinement may leave the machine; the full audio and
transcript stay out of that request. The interface shows research state and
links every returned source to the claim it supports.

## Local model choices

The verified target machine uses:

| Role | Selection |
| --- | --- |
| Debate reasoning | Ollama `qwen3:4b`, 4.0B parameters, Q4_K_M |
| Batch and live transcription | Parakeet v3, language `de` |
| GPU | NVIDIA GeForce RTX 4070 Laptop GPU, 8,188 MiB |

The endpoint is registered as `german-debate-ollama`; its model identifier in
DebateAI is `endpoint:german-debate-ollama:qwen3:4b`. Structured requests
disable Qwen's visible reasoning channel so the application receives the JSON
recommendation instead of an empty answer.

## Measured local replay

On 2026-11-03, the deterministic five-turn German replay completed 5/5 turns
without a generation failure. The values below are wall-clock measurements
against `http://127.0.0.1:11434/v1`, not estimates.

| Measurement | Result |
| --- | ---: |
| Median first/current app update | 3,440.794 ms |
| p95 first/current app update | 4,266.817 ms |
| Superseded requests cancelled | 2 of 2 |
| Research/source refinement | disabled by Privacy First |
| Observed loaded GPU memory after replay | 4,732 MiB |

The cold first turn is responsible for the p95. Timing starts immediately
before final transcript ingestion and stops when the production orchestrator
publishes the matching `debate_update`; it therefore includes prompt/schema
handling, local inference scheduling, revision checks, and WebSocket
publication. With research disabled, the first event is also the current
recommendation. The evidence is kept locally at
`build/debate-copilot-benchmark.json`; generated benchmark and build artifacts
are intentionally ignored by Git.

One pre-fix repeat exposed a formally valid but semantically empty Qwen
recommendation. The production agent now retries that exact condition once
with the required speaking fields made explicit; the final replay above had no
turn or probe failure, and permanently empty output still fails the benchmark.

### Deterministic technical preflight

Every accepted model recommendation in the application-path replay also carries
`quality_preflight`. This is a deliberately narrow, reproducible contract
check, not an automated rhetoric verdict. It records:

- schema validity and a speakable primary move;
- the answer/question word limits;
- presence of the current target claim;
- the existing evidence guards against unsupported numbers or attributions.

The aggregate report exposes `technical_quality_pass_count`,
`technical_quality_failure_count`, and `human_review_required_count`. The last
counter remains non-zero by design: a deterministic preflight cannot replace a
blind human assessment of German rhetoric, naturalness, or strategic quality.

For the remaining V3 acceptance work, validate an evidence package before a
manual run with:

```powershell
.\.release-venv\Scripts\python.exe `
  .\backend\scripts\validate_v3_acceptance_evidence.py `
  .\path\to\evidence-package.json
```

The validator reports either `incomplete` or `ready_for_manual_review`. It
checks reference hashes, hardware/load identity, required metrics, fixed
denominators, and anonymized human ratings. It never reports `passed`; real
hardware and human sign-off remain mandatory for A06, A18, A21, and A22.

Run the replay again with:

```powershell
.\.venv\Scripts\python.exe .\backend\scripts\benchmark_debate_copilot.py `
  --endpoint http://127.0.0.1:11434/v1 `
  --model qwen3:4b `
  --output .\build\debate-copilot-benchmark.json
```

## Windows bundle

Build the self-contained desktop archive with:

```powershell
.\scripts\build_debate_assistant.ps1 -Python .\.venv\Scripts\python.exe
```

The verified artifact is
`dist\DebateAI-DebateAI-windows-x64.zip` (280.8 MiB), SHA-256
`F25F5CC98E6BF3516242AF9FF24441B6E33260D7EC3BEF7C9F22ECB9DE100845`.
Its launcher smoke test reached the health endpoint, found the bundled local
speech model usable, and shut down cleanly.

## Verification record

- Debate benchmark, application-path, limit, and agent tests: 44 passed.
- Frontend: 232 passed; production build completed.
- Backend: 1,384 executed; 1,382 passed, 1 skipped, and the inherited
  Windows-only POSIX mode assertion failed because Windows reports a created
  `0600` key as `0666` through `stat()`.
- Desktop: 126 executed; 124 passed, 1 skipped, and the inherited symlink test
  could not create a Windows symlink without Developer Mode or administrator
  privilege. The real bundle smoke test passed.
- Sentrux was not installed on this machine or at the legacy path recorded in
  `AGENTS.md`, so no structural baseline was changed.

Vite reports the existing large-main-chunk warning; it does not fail the build.

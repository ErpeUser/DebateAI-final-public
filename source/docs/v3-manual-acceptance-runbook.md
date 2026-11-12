# V3 manual acceptance runbook

This is the shortest safe path for the remaining external gates. It does not
turn a complete evidence file into an automatic pass. The validator only
answers whether the package is complete enough for a human review.

## 1. Prepare one reproducible candidate

Run this on the Windows machine that has the real microphone, Discord/system
audio and the display scaling that must be accepted:

```powershell
git rev-parse HEAD
Get-FileHash .\dist\DebateAI\DebateAI.exe -Algorithm SHA256
Get-ComputerInfo | Select-Object WindowsProductName,WindowsVersion,OsBuildNumber,OsArchitecture
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfLogicalProcessors
Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion
```

If a managed machine denies the hardware commands, record that fact instead of
guessing. Do not overwrite an existing user installation or database. Use a
copy of the candidate and keep the previous release available for rollback.

## 2. A06: one real audio run

Use one unchanged, at least 120-second German recording with microphone and
Discord/system audio. During that same session perform all five scenarios:

1. ordinary two-person speech;
2. intentional short overlap/interruption;
3. system-audio/Discord speech while the microphone is active;
4. an input-device switch;
5. a deliberately bounded backlog, followed by a normal stop.

Keep the raw per-track WAV files, the exported transcript, the session log and
the exact hardware/software identifiers. Do not cut, denoise, manually repair,
or concatenate the recording. Compare every spoken passage with the exported
transcript. A06 is accepted only when the comparison is complete, unexplained
loss is absent, and the session ends cleanly. An intentional overflow must be
visible as `diarization_overflow`; an unexplained loss is a failure.

## 3. A21: same-reference ASR A/B

Use the exact same untouched German reference WAV twice on the same machine,
with the same microphone/system load and no manual transcript correction. Run
the two approved ASR paths as `asr_a` and `asr_b`. Record, for both runs:

- WER and number errors;
- negation errors;
- latency in milliseconds;
- dropouts;
- peak CPU/RAM measurement.

Choose the preferred path only after the run, using the threshold agreed before
the run. If no threshold is written down before measurement, record the result
as comparison data and leave A21 blocked rather than selecting by impression.

## 4. A18: ten blinded German cases

Run at least ten multi-turn German cases through both `persuasive` and
`forceful`. A second person (or a separately anonymised review process) rates
the cases blindly. Use anonymised IDs such as `rater-a01`; never put names or
credentials in the evidence file. Rate whether the response:

- acknowledges, narrows, asks, corrects, or correctly declines;
- stays tied to the truth and available evidence;
- is naturally speakable German;
- has one clear primary move rather than a pile of competing cards.

Record each case exactly once per review set. A deterministic schema check is
useful, but it is not a rhetoric verdict.

## 5. A22: independent causal benchmark

Freeze the dataset hash and the positive denominator before running. Exclude
future data. Run the production and reference paths under the same load and
record latency/error-rate metrics plus the blinded human ratings. Keep raw
inputs, outputs, model IDs, commit, hardware and load profile together.

## 6. Build the evidence file and run the gate

Use the JSON shape from `backend/tests/test_v3_acceptance_evidence.py`. Every
artifact and reference gets a SHA-256:

```powershell
$referenceHash = (Get-FileHash .\evidence\reference.wav -Algorithm SHA256).Hash.ToLower()
ffprobe -v error -show_entries format=duration:stream=sample_rate,channels,bits_per_sample `
  -of default=noprint_wrappers=1 .\evidence\reference.wav

.\.release-venv\Scripts\python.exe `
  .\backend\scripts\validate_v3_acceptance_evidence.py `
  .\evidence\A06.json
```

The only acceptable pre-review result is `ready_for_manual_review`. The
validator must never be changed to emit `passed`. After the human comparison,
update the V3 matrix with the reviewer, date, artifact hashes and explicit
pass/fail decision.

## 7. Simple decision rule

| Result | Matrix action |
| --- | --- |
| missing/contradictory metadata | `BLOCKED` or `FEHLGESCHLAGEN`; fix evidence, do not infer success |
| `ready_for_manual_review`, human check not done | `BLOCKED` |
| complete evidence and all required human/hardware checks pass | `BESTANDEN` with hashes and reviewer record |
| any unexplained audio loss, non-identical A/B input/load, or failed human case | `FEHLGESCHLAGEN`; keep raw evidence and open a defect |

Existing short clips in `artifacts/real-smoke/` and `backend/.tmp/asr-real/`
are preserved as evidence candidates. Their durations and metadata do not
meet the A06/A21 contract by themselves.

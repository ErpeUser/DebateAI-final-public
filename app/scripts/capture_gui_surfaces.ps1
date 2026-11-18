# Compatibility entry point. Native window capture remains available separately
# in capture_debateai_window.ps1; UIA window stacking is not full-content capture.
param(
    [string]$Url = 'http://127.0.0.1:8474/?desktop=1',
    [string]$OutputRoot = (Join-Path $PSScriptRoot '../../DebateAI_Generated/reports/gui-capture'),
    [int]$Width = 1440,
    [int]$Height = 900,
    [int]$MaxScrolls = 200,
    [switch]$BothThemes
)
if ($MaxScrolls -ne 200) { Write-Warning 'MaxScrolls is deprecated. Coverage uses actual scroll heights (safety limit: 200 per surface).' }
& (Join-Path $PSScriptRoot 'capture_gui_dom.ps1') -Url $Url -OutputRoot $OutputRoot -Width $Width -Height $Height -BothThemes:$BothThemes

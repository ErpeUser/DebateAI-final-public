[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$State, [string]$Python)
$ErrorActionPreference = 'Stop'
$arguments = @{ ResumeState = $State }
if ($Python) { $arguments.Python = $Python }
# Only a fixed verification profile is resumed; JSON never supplies shell code.
& (Join-Path $PSScriptRoot '../acceptance/run_all.ps1') @arguments
exit $LASTEXITCODE

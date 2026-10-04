param([int]$Port = 18080)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if (Test-Path "$Root\.env") {
  Get-Content "$Root\.env" | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$' -and $_ -notmatch '^\s*#') {
      $name = $Matches[1]
      $value = $Matches[2].Trim().Trim('"').Trim("'")
      [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
  }
}
if (-not $env:CLAWBOT_DECISION_MODE) { $env:CLAWBOT_DECISION_MODE = "deepseek" }
if (-not $env:CLAWBOT_HOST) { $env:CLAWBOT_HOST = "127.0.0.1" }
if (-not $env:CLAWBOT_PORT) { $env:CLAWBOT_PORT = "$Port" }
if (-not $env:PYTHONPATH) { $env:PYTHONPATH = "$Root\src;$Root\workers" }
Write-Host "Starting kefu Decision API on $($env:CLAWBOT_HOST):$($env:CLAWBOT_PORT) in $($env:CLAWBOT_DECISION_MODE) mode"
python -m uvicorn kefu_clawbot.main:app --host $env:CLAWBOT_HOST --port ([int]$env:CLAWBOT_PORT)

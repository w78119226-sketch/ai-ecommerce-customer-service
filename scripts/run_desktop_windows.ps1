param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

# Load the local development environment without echoing its values.
if (Test-Path "$Root\.env") {
  Get-Content "$Root\.env" | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$' -and $_ -notmatch '^\s*#') {
      $name = $Matches[1]
      $value = $Matches[2].Trim().Trim('"').Trim("'")
      [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
  }
}

if (-not $env:PYTHONPATH) { $env:PYTHONPATH = "$Root\src;$Root\workers" }
$Python = "python"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) { $Python = $VenvPython }
& $Python -m kefu_desktop @Arguments
exit $LASTEXITCODE

param(
    [int]$Port = 8765,
    [switch]$Private,
    [switch]$PublicSchedule
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'First run uv sync --locked from the repository root.'
}
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'frontend/dist/index.html'))) {
    throw 'First run npm ci and npm run build from the frontend directory.'
}
$taskArguments = @('-B', '-m', 'fantasy_gm.web', '--port', "$Port")
if ($Private) { $taskArguments += '--private' }
if ($PublicSchedule) { $taskArguments += '--public-schedule' }
if ($Private -or $PublicSchedule) { $taskArguments += '--interactive' }
Push-Location -LiteralPath $taskRoot
try { & $taskPython @taskArguments; exit $LASTEXITCODE }
finally { Pop-Location }

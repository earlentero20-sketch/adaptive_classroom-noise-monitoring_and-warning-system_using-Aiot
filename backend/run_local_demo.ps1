$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repositoryRoot "ml\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
	throw "Project Python environment not found: $python"
}

# Local demo settings use the backend's existing configuration keys and units.
$env:WARNING_THRESHOLD_DB_SPL = "75"
$env:MAX_INPUT_AGE_SECONDS = "30"

Set-Location -LiteralPath $repositoryRoot
& $python -m backend.app

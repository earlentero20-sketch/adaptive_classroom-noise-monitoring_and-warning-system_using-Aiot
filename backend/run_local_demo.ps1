param([switch]$PreflightOnly)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repositoryRoot "ml\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
	throw "Project Python environment not found: $python"
}

# Check configuration without printing the connection URL or contacting PostgreSQL.
$databaseConfigured = -not [string]::IsNullOrWhiteSpace($env:SONIQ_DATABASE_URL)
if (-not $databaseConfigured) {
	Write-Host "SONIQ_DATABASE_URL is not configured in this PowerShell session." -ForegroundColor Yellow
	Write-Host "Ask the database owner to confirm the local SONIQ database, then set the approved URL in this session."
	Write-Host "The backend needs PostgreSQL and will verify the connection when it starts."
	if (-not $PreflightOnly) {
		exit 1
	}
} elseif ($PreflightOnly) {
	Write-Host "SONIQ_DATABASE_URL is present (value hidden); URL validity and database connectivity will not be tested."
}

# Fail early when this project's backend or inference dependencies are unavailable.
& $python -c "import psycopg, psycopg_pool; import ml.audio_inference"
if ($LASTEXITCODE -ne 0) {
	throw "Backend or ML dependencies are unavailable. Follow docs/POSTGRES_LOCAL.md to install the project requirements."
}

# Use the repository's known local artifact only when no model path was supplied.
if ([string]::IsNullOrWhiteSpace($env:SONIQ_AUDIO_MODEL_PATH)) {
	$env:SONIQ_AUDIO_MODEL_PATH = Join-Path $repositoryRoot "ml\artifacts\expanded-local-demo-20261020\experimental_model.joblib"
}
if (-not (Test-Path -LiteralPath $env:SONIQ_AUDIO_MODEL_PATH -PathType Leaf)) {
	throw "The configured SONIQ_AUDIO_MODEL_PATH does not point to a model file. Set it to a compatible local artifact."
}
$modelTrainingMode = & $python -c "import os; from ml.audio_inference import load_audio_model; model = load_audio_model(os.environ['SONIQ_AUDIO_MODEL_PATH']); print(model.training_mode)"
if ($LASTEXITCODE -ne 0) {
	throw "The configured model artifact is incompatible with the current two-class inference pipeline."
}
Write-Host "Model artifact is compatible with the two-class inference pipeline (training mode: $modelTrainingMode)."
if ($modelTrainingMode -eq "experimental_full_fit_no_held_out_evaluation") {
	Write-Host "This experimental model has no held-out evaluation; its presentation prediction is not an accuracy claim." -ForegroundColor Yellow
}

if ($PreflightOnly) {
	if (-not $databaseConfigured) {
		Write-Host "Preflight blocked: set SONIQ_DATABASE_URL after the database owner approves the target." -ForegroundColor Yellow
		exit 1
	}
	Write-Host "Preflight passed for local dependencies, model, and SONIQ_DATABASE_URL presence."
	Write-Host "PostgreSQL connectivity was not tested; the backend was not started."
	exit 0
}

# Local demo settings use the backend's existing configuration keys and units.
$env:WARNING_THRESHOLD_DB_SPL = "75"
$env:MAX_INPUT_AGE_SECONDS = "30"

Set-Location -LiteralPath $repositoryRoot
Write-Host "Launching SONIQ backend. Startup is successful only after PostgreSQL connects and the server reports its listening address."
& $python -m backend.app

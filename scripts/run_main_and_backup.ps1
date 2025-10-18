param(
  [switch]$SkipLLM,
  [string]$BackupDir = "backup",
  [string]$LogDir = "logs",
  [int]$LogKeepDays = 14,
  [int]$BackupKeepDays = 30
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $here "..")

# Ensure UTF-8 output to avoid garbled Chinese
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Activate venv if available
$venvPy = Resolve-Path "..\..\.venv\Scripts\python.exe" -ErrorAction SilentlyContinue
if (-not $venvPy) {
  Write-Host "[WARN] No venv python found, will use system python." -ForegroundColor Yellow
  $python = "python"
} else {
  $python = $venvPy.Path
}

# Run aggregation
Write-Host "--- Run main.py (aggregation + LLM) ---" -ForegroundColor Cyan
if ($SkipLLM) {
  # Use smoke mode if provided, else fallback to main
  if (Test-Path ".\scripts\smoke_agg.py") {
    & $python ".\scripts\smoke_agg.py"
  } else {
    & $python ".\main.py"
  }
} else {
  & $python ".\main.py"
}

# Backup artifact
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
if (Test-Path ".\final_knowledge_base.json") {
  Copy-Item ".\final_knowledge_base.json" (Join-Path $BackupDir "final_knowledge_base.$ts.json") -Force
  Write-Host "[OK] Backup saved to $BackupDir/final_knowledge_base.$ts.json" -ForegroundColor Green
} else {
  Write-Host "[WARN] final_knowledge_base.json not found, skip backup." -ForegroundColor Yellow
}

# Rotate logs (optional cleanup)
try {
  $rotate = ".\scripts\rotate_logs.ps1"
  if (Test-Path $rotate) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $rotate -LogDir $LogDir -KeepDays $LogKeepDays
    Write-Host "[OK] Logs rotated (Dir=$LogDir, KeepDays=$LogKeepDays)." -ForegroundColor Green
  } else {
    Write-Host "[WARN] rotate_logs.ps1 not found, skip log rotation." -ForegroundColor Yellow
  }
} catch {
  Write-Host "[WARN] Log rotation failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Prune old backups by days (optional)
try {
  $prune = ".\\scripts\\prune_backups.ps1"
  if (Test-Path $prune) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $prune -BackupDir $BackupDir -KeepDays $BackupKeepDays
    Write-Host "[OK] Backups pruned (Dir=$BackupDir, KeepDays=$BackupKeepDays)." -ForegroundColor Green
  } else {
    Write-Host "[WARN] prune_backups.ps1 not found, skip backup pruning." -ForegroundColor Yellow
  }
} catch {
  Write-Host "[WARN] Backup pruning failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

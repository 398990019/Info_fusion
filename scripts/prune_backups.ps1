param(
  [string]$BackupDir = "backup",
  [int]$KeepDays = 30,
  [string]$Pattern = "final_knowledge_base.*.json"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $BackupDir)) {
  Write-Host "[INFO] BackupDir '$BackupDir' not found, nothing to prune." -ForegroundColor Yellow
  return
}

$cutoff = (Get-Date).AddDays(-[math]::Abs($KeepDays))
$files = Get-ChildItem -Path $BackupDir -Filter $Pattern -ErrorAction SilentlyContinue
if (-not $files) {
  Write-Host "[INFO] No backup files matched pattern '$Pattern'." -ForegroundColor Yellow
  return
}

$toDelete = $files | Where-Object { $_.LastWriteTime -lt $cutoff }
if ($toDelete) {
  $count = 0
  foreach ($f in $toDelete) {
    try {
      Remove-Item $f.FullName -Force -ErrorAction Stop
      $count++
    } catch {
      Write-Host "[WARN] Failed to remove: $($f.FullName) -> $($_.Exception.Message)" -ForegroundColor Yellow
    }
  }
  Write-Host "[OK] Pruned $count old backup file(s) older than $KeepDays day(s)." -ForegroundColor Green
} else {
  Write-Host "[OK] No backups older than $KeepDays day(s) to prune." -ForegroundColor Green
}

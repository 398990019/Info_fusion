param(
  [string]$LogDir = "logs",
  [int]$KeepDays = 14
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $LogDir)) { return }

$cutoff = (Get-Date).AddDays(-$KeepDays)
Get-ChildItem -Path $LogDir -Filter "*.log" | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
  Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
}

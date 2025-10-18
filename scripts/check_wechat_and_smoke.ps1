Param(
    [string]$WeMPRSSBaseUrl = "http://localhost:8001",
    [switch]$StartApi = $false,
    [string]$ApiHost = "0.0.0.0",
    [int]$ApiPort = 5000
)

Write-Host "=== Info_fusion 一键连通性检查与自检 ===" -ForegroundColor Cyan

$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv/\Scripts/\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

function Test-WeMPRSS {
    param([string]$BaseUrl)
    $feedUrl = "$BaseUrl/feed/all.rss"
    try {
        $res = Invoke-WebRequest -Uri $feedUrl -Method GET -UseBasicParsing -TimeoutSec 5
        return @{ ok = $true; status = $res.StatusCode; url = $feedUrl }
    } catch {
        return @{ ok = $false; error = $_.Exception.Message; url = $feedUrl }
    }
}

Write-Host "[1/3] 检查 We-MP-RSS 连通性: $WeMPRSSBaseUrl" -ForegroundColor Yellow
$probe = Test-WeMPRSS -BaseUrl $WeMPRSSBaseUrl
if ($probe.ok) {
    Write-Host "  ✓ RSS 可访问 ($($probe.status)) -> $($probe.url)" -ForegroundColor Green
} else {
    Write-Host "  ! RSS 不可访问：$($probe.error)" -ForegroundColor Red
    $WeRoot = Join-Path (Split-Path $Root -Parent) "we-mp-rss-1.4.6"
    $StartBat = Join-Path $WeRoot "start.bat"
    Write-Host "  提示：请先启动 We-MP-RSS 服务（例如：$StartBat），并确认浏览器可打开 $($probe.url)" -ForegroundColor DarkYellow
}

Write-Host "[2/3] 运行轻量自检（不触发 LLM）" -ForegroundColor Yellow
$Smoke = Join-Path $Root "scripts/smoke_agg.py"
& $Py $Smoke
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ! 自检脚本返回非零退出码：$LASTEXITCODE" -ForegroundColor Red
}

if ($StartApi) {
    Write-Host "[3/3] 启动后端 API (FastAPI)" -ForegroundColor Yellow
    $ApiSrv = Join-Path $Root "api_server.py"
    Write-Host "  提示：当前终端将被占用。如需在新窗口运行，请手动执行：`n  Start-Process -FilePath `"$Py`" -ArgumentList `"$ApiSrv`"" -ForegroundColor DarkYellow
    & $Py $ApiSrv
}

Write-Host "=== 完成 ===" -ForegroundColor Cyan

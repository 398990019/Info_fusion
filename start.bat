@echo off
setlocal enabledelayedexpansion

REM 基础环境变量确保 We-MP-RSS 任务与本地 RSS 可用
set "ENABLE_JOB=True"
set "RSS_LOCAL=True"
set "WECHAT_FORCE_REFRESH=true"
chcp 65001 > nul
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"

if not exist "logs" mkdir logs

echo === 信息融合知识库启动脚本 ===
echo.

REM 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo Python虚拟环境不存在或损坏，正在创建...
    py -3.13 -m venv .venv 2>nul
    if errorlevel 1 (
        python -m venv .venv
    )
)

REM 激活虚拟环境
call .venv\Scripts\activate.bat

REM 安装Python依赖
echo 正在升级pip...
python -m pip install --upgrade pip >nul
echo 正在安装Python依赖...
python -m pip install -r requirements.txt

REM 定位 We-MP-RSS 项目目录
set "WE_RSS_DIR="
for %%D in (
    "%SCRIPT_DIR%..\we-mp-rss"
    "%SCRIPT_DIR%..\we-mp-rss-1.4.6"
    "%SCRIPT_DIR%..\we-mp-rss\we-mp-rss"
    "%SCRIPT_DIR%..\we-mp-rss-1.4.6\we-mp-rss-1.4.6"
    "%SCRIPT_DIR%..\..\we-mp-rss"
    "%SCRIPT_DIR%..\..\we-mp-rss-1.4.6"
    "%SCRIPT_DIR%..\..\we-mp-rss\we-mp-rss"
    "%SCRIPT_DIR%..\..\we-mp-rss-1.4.6\we-mp-rss-1.4.6"
) do (
    if exist "%%~fD\main.py" (
        set "WE_RSS_DIR=%%~fD"
        goto :FOUND_WE_RSS
    )
)
:FOUND_WE_RSS

if defined WE_RSS_DIR (
    echo 已检测到 We-MP-RSS 目录: %WE_RSS_DIR%
    set "WE_RSS_REQ=%WE_RSS_DIR%\requirements.txt"
) else (
    set "WE_RSS_REQ="
)

REM 安装 We-MP-RSS 依赖
if defined WE_RSS_REQ if exist "%WE_RSS_REQ%" (
    echo 正在安装 We-MP-RSS 服务依赖...
    python -m pip install -r "%WE_RSS_REQ%"
) else (
    echo 警告: 未找到 We-MP-RSS requirements.txt，跳过依赖安装。
)

echo 强制锁定 httpx 兼容版本...
python -m pip install httpx==0.27.0

REM 启动 We-MP-RSS 服务
if defined WE_RSS_DIR if exist "%WE_RSS_DIR%\main.py" (
    if not exist "%WE_RSS_DIR%\config.yaml" (
        if exist "%WE_RSS_DIR%\config.example.yaml" (
            echo 检测到缺少 config.yaml，正在创建默认配置...
            copy /Y "%WE_RSS_DIR%\config.example.yaml" "%WE_RSS_DIR%\config.yaml" >nul
        )
    )
    set "WE_RSS_INIT=-init False"
    if not exist "%WE_RSS_DIR%\data\db.db" (
        echo 检测到首次运行 We-MP-RSS，正在执行初始化...
        set "WE_RSS_INIT=-init True"
    )
    echo 启动 We-MP-RSS 服务（日志输出至 logs\we_mp_rss.log）...
    start "" /B cmd /c "cd /d \"%WE_RSS_DIR%\" && \"%SCRIPT_DIR%\.venv\Scripts\python.exe\" main.py -job True %WE_RSS_INIT% >> \"%SCRIPT_DIR%\logs\we_mp_rss.log\" 2>&1"
    echo 正在等待 We-MP-RSS 服务就绪...
    set "WE_RSS_READY=0"
    set "WE_RSS_HEALTH_URL=http://127.0.0.1:8001/feed/all.rss"
    for /L %%I in (1,1,15) do (
        powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%WE_RSS_HEALTH_URL%' -UseBasicParsing -TimeoutSec 2 ^| Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
        if not errorlevel 1 (
            set "WE_RSS_READY=1"
            goto :WE_RSS_STARTED
        )
        timeout /t 2 > nul
    )
:WE_RSS_STARTED
    if "!WE_RSS_READY!"=="1" (
        echo We-MP-RSS 服务已启动。
    ) else (
        echo 警告: 未检测到 We-MP-RSS 服务，请查看 logs\we_mp_rss.log。
    )
) else (
    echo 警告: 未找到 We-MP-RSS 项目，跳过服务启动。
)

REM 执行数据聚合与 AI 处理管道
echo 正在执行数据聚合与AI分析流程 (main.py)...
python main.py
if errorlevel 1 (
    echo main.py 执行失败，请检查日志后重试。
    pause
    exit /b 1
)

REM 启动API服务器（后台运行）
echo 启动API服务器...
start /B python api_server.py

REM 等待API服务器启动
timeout /t 3 > nul

REM 切换到web目录
cd web

REM 安装前端依赖
if not exist "node_modules" (
    echo 正在安装前端依赖...
    npm install
 ) else (
    echo 已检测到 node_modules，跳过依赖检查。如需强制同步请运行 scripts\ensure_env.ps1 -Frontend -Force
)

echo.
echo === 系统启动完成 ===
echo API服务器: http://localhost:5000
echo 前端界面: http://localhost:3000
echo.
echo 按任意键停止服务...

REM 启动前端开发服务器
npm run dev
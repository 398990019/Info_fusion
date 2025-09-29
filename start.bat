@echo off
chcp 65001 > nul
echo === 信息融合知识库启动脚本 ===
echo.

REM 检查虚拟环境
if not exist ".venv" (
    echo Python虚拟环境不存在，正在创建...
    python -m venv .venv
)

REM 激活虚拟环境
call .venv\Scripts\activate.bat

REM 安装Python依赖
echo 正在检查Python依赖...
pip install -q flask flask-cors requests python-dotenv feedparser simhash lxml

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
)

echo.
echo === 系统启动完成 ===
echo API服务器: http://localhost:5000
echo 前端界面: http://localhost:3000
echo.
echo 按任意键停止服务...

REM 启动前端开发服务器
npm run dev
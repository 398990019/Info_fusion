#!/bin/bash
# start.sh - 启动信息融合知识库系统

echo "=== 信息融合知识库启动脚本 ==="
echo ""

# 检查Python虚拟环境
if [ ! -d ".venv" ]; then
    echo "Python虚拟环境不存在，正在创建..."
    python -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate 2>/dev/null || .venv\\Scripts\\activate

# 安装Python依赖
echo "正在检查Python依赖..."
pip install -q flask flask-cors requests python-dotenv feedparser simhash lxml

# 启动API服务器
echo "启动API服务器..."
python api_server.py &
API_PID=$!
echo "API服务器已启动 (PID: $API_PID)"

# 切换到web目录
cd web

# 安装前端依赖
if [ ! -d "node_modules" ]; then
    echo "正在安装前端依赖..."
    npm install
fi

# 启动前端开发服务器
echo "启动前端开发服务器..."
npm run dev &
WEB_PID=$!

echo ""
echo "=== 系统启动完成 ==="
echo "API服务器: http://localhost:5000"
echo "前端界面: http://localhost:3000"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待中断信号
trap "echo '正在停止服务...'; kill $API_PID $WEB_PID; exit" INT
wait
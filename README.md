# 信息融合知识库 (Info Fusion)

一个智能化的信息聚合与分析系统，能够从微信公众号（通过 We-MP-RSS）和语雀知识库中获取内容，并使用 AI 进行深度分析与洞察。系统目前重点投入在“高质量信息提取与知识沉淀”，前端保持演示形态即可支撑内部使用。

## 功能特性

- 🔗 **多源信息聚合**: 支持从微信公众号 (We-MP-RSS RSS/API) 和语雀知识库获取内容
- 🤖 **AI 智能分析**: 使用大语言模型进行深度总结、要点提取与问题生成
- 🔍 **统一搜索**: 支持全文搜索与 AI 分析结果检索
- 📊 **统计与来源树**: 展示文章总量、最近处理时间，并按「平台→来源」分组
- �️ **运维友好**: `/healthz` 深度健康检查、`/ops/wechat/reload` 一键清缓存+强制刷新、日志按模块落盘
- � **增量更新**: SimHash 去重+时间戳游标，避免重复处理
- 🧪 **研发基座**: 可直接在现有管线上实验新的抽取/归一化逻辑，前端仅作结果展示

## 系统架构

```
Info_fusion/
├── 后端 (Python)
│   ├── main.py                        # 主程序入口，编排聚合+AI分析
│   ├── api_server.py                 # FastAPI 服务器，提供 v1 API / 运维接口
│   ├── wechat_pubaccount_fetcher.py  # 微信公众号数据获取与归一化
│   ├── we_mp_rss_sync.py             # 调度外部 We-MP-RSS 刷新
│   ├── yuque_fetcher.py              # 语雀数据获取
│   ├── ai_processer.py               # AI 分析处理
│   ├── simhash_utils.py              # 文本相似度检测
│   └── config.py                     # 配置管理
├── 脚本与自动化
│   ├── start.bat / start.sh          # 一键启动（含 We-MP-RSS、main.py、API、前端）
│   ├── scripts/run_main_and_backup.ps1  # 生产巡航脚本
│   ├── scripts/check_wechat_and_smoke.ps1 # 连通性与聚合自检
│   └── scripts/trigger_we_mp_rss_refresh.py # 独立刷新入口
├── 前端 (Next.js + TypeScript)
│   ├── src/app/v1/page.tsx           # v1 演示页
│   ├── src/components/ArticleCard.tsx
│   └── package.json
└── 数据文件
    ├── final_knowledge_base.json     # 处理后的知识库
    ├── filtered_articles.json        # 聚合后的文章清单
    ├── yuque_data.json               # 语雀原始数据缓存
    └── .env                          # 环境变量配置
```

## 快速开始

### 1. 环境准备

确保系统已安装：
- Python 3.13（建议与项目一致）
- Node.js 18+
- npm 或 yarn
- Mozilla Firefox + geckodriver（使用本地 We-MP-RSS 主动刷新所需；若仅使用 Docker 版可忽略）

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的配置：

```env
# AI Configuration
AI_API_KEY=your_qwen_api_key
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL_NAME=qwen3-max

# Yuque Configuration  
YUQUE_TOKEN=your_yuque_token
YUQUE_GROUP=your_group_id
YUQUE_BOOK=your_book_id

# WeChat Configuration
WECHAT_RSS_URL=http://127.0.0.1:8001/feed/all.rss
WECHAT_API_BASE_URL=http://127.0.0.1:8001
WECHAT_API_USERNAME=your_wemprss_username   # 若无需调用 API，可留空
WECHAT_API_PASSWORD=your_wemprss_password
# 抓取器实现与限速（当前默认 We-MP-RSS 适配器）
WECHAT_FETCHER_IMPL=wmr
WECHAT_FETCH_CONCURRENCY=8
WECHAT_FETCH_QPS=5
WECHAT_FETCH_TIMEOUT=30

# API 鉴权（可选，配置后需携带 Authorization: Bearer <token>）
API_TOKEN=your_api_token
```

### 3. 一键启动

#### Windows用户
```bash
start.bat
```

> 说明：脚本会自动检查虚拟环境、安装依赖、定位本地或 Docker 版 We-MP-RSS（端口默认 8001，日志落在 `logs/we_mp_rss.log`），执行 `main.py` 聚合最新数据，然后启动后端与前端。首次运行需初始化 We-MP-RSS 数据库并完成扫码登录，整体耗时较长，请根据终端提示耐心等待。

> **提示：若使用本地 We-MP-RSS 进程，请提前安装 [Mozilla Firefox](https://www.mozilla.org/firefox/new/) 与 [geckodriver](https://github.com/mozilla/geckodriver/releases)，并将 geckodriver 加入 PATH 或放入 `we-mp-rss-*/driver/driver/`。初次启动需访问 http://127.0.0.1:8001 扫码登录公众号账号；若改用 Docker 版，只需确保容器映射端口 8001 并挂载数据目录。**

或执行 PowerShell 脚本，自动校验后端与前端环境：

```powershell
pwsh -File .\scripts\ensure_env.ps1 -Frontend
```

#### Linux/Mac用户  
```bash
chmod +x start.sh
./start.sh
```

### 4. We-MP-RSS 登录与账号切换

1. 打开 http://127.0.0.1:8001（Docker 场景请根据映射端口访问）。
2. 在“系统状态”页确认版本、队列运行状态与 Token 是否有效。
3. 点击「登录」获取二维码，使用目标公众号管理员微信扫码。
4. 在「订阅管理」中调整要跟踪的公众号列表，并执行一次「立即刷新」。
5. 若需切换账号或重置数据，可停止服务后清理 `data/db.db`、`data/cache/` 与 `static/wx_qrcode.png`，再按以上步骤重新登录。

完成登录后，`start.bat` / `main.py` 的自动刷新即可使用最新账号数据。

### 5. 手动启动 (可选)

如果自动启动脚本有问题，可以手动启动：

1. **启动后端API服务器**:
```bash
# 激活Python虚拟环境
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖（推荐使用 python -m pip，避免 pip 缓存路径错乱）
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 启动API服务器
python -m uvicorn api_server:app --host 0.0.0.0 --port 5000
```

2. **启动前端开发服务器** (新开命令行窗口):
```bash
cd web
npm install
npm run dev
```

### 6. 访问应用

- 🌐 **前端界面**: http://localhost:3000
- 🔌 **API接口**: http://localhost:5000
- 📄 **API文档**: 
  
  > 说明：以下接口文档仅供内部参考，不对外公开。
  > 如已在环境中设置 `API_TOKEN`，请在请求头中携带 `Authorization: Bearer <token>` 访问。
  
  - `GET /api/articles` - 获取所有文章
  - `GET /api/stats` - 获取统计信息，包含 `source_tree` 层级结构  
  - `GET /api/search?q=关键词` - 搜索文章
  - `GET /api/source-tree` - 独立返回来源树
  - `POST /api/refresh` - 触发一次即时刷新任务

### 标准化 API（v1）

为便于前后端/服务间协作，提供一组遵循统一约定的只读接口。它们与现有接口并存且不破坏兼容。

- 基础路径: `/api/v1`
- 鉴权: 可选。若设置了 `API_TOKEN`，需在请求头携带 `Authorization: Bearer <token>`
- 响应包裹: 统一使用
  - 成功: `{ "code": 200, "msg": "success", "data": <payload>, "meta"?: <object> }`
  - 失败: `{ "code": <4xx/5xx>, "msg": "<error>", "data": null }`
- 命名与时间: 字段为 `snake_case`；时间为 UTC ISO-8601，形如 `2025-10-15T08:00:00Z`

1) GET `/api/v1/docs`
- 作用: 分页获取文档列表
- 查询参数:
  - `page` 整数, 默认 1, 最小 1
  - `size` 整数, 默认 50, 范围 1–200
- 返回 data: DocListItemDTO 数组
  - `id` string: 文档唯一标识（优先使用 link/url）
  - `title` string
  - `author` string|null
  - `source` enum: `yuque|wechat|qq|web`
  - `created_at` string|null: 创建/发布时间（ISO-8601）
  - `updated_at` string|null: 处理或回退为创建时间（ISO-8601）
- 返回 meta: `{ page, size, total, has_more }`

示例响应（节选）:

```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "id": "https://mp.weixin.qq.com/s/xxxx",
      "title": "AIGC 行业周报",
      "author": "某作者",
      "source": "wechat",
      "created_at": "2025-10-10T02:12:34Z",
      "updated_at": "2025-10-10T03:00:00Z"
    }
  ],
  "meta": { "page": 1, "size": 50, "total": 102, "has_more": true }
}
```

2) GET `/api/v1/docs/{id}`
- 作用: 获取单篇文档详情
- 路径参数: `id`（与列表中的 `id` 一致）
- 返回 data: DocDetailDTO
  - `id` string
  - `title` string
  - `content` string|null
  - `tags` string[]
  - `source` enum: `yuque|wechat|qq|web`
  - `created_at` string|null

示例 404 响应:

```json
{ "code": 404, "msg": "not found", "data": null }
```

### 运维速查

- `GET /healthz?deep=1`：检测 We-MP-RSS RSS / 语雀 / （如配置）We-MP-RSS API，返回 `status`、`rss`、`api`。
- `POST /ops/wechat/reload?refresh=1&deep=1`：清理缓存、可选强制刷新，并返回深度健康结果；账号切换或刷新卡住时使用。
- 日志：
  - `logs/we_mp_rss.log`、`logs/we_mp_rss_refresh.log`（公众号抓取）
  - `logs/main.log`（聚合与 AI 流程）
  - `web` 目录下的 Next.js 控制台输出（前端）
- 自检脚本：
  ```powershell
  D:/Apps/Python/NOVA/Info_fusion/.venv/Scripts/python.exe d:\Apps\Python\NOVA\Info_fusion\scripts\smoke_agg.py
  ```
  仅执行聚合与统计，不调用 LLM，可快速验证链路是否畅通。

### 连通性与快速自检

- 确认 We-MP-RSS 服务运行在 `http://127.0.0.1:8001`（未运行时，微信侧文章计数为 0，聚合仍会执行语雀部分）。
- 运行轻量自检脚本，只执行聚合阶段（不触发 LLM），输出汇总数量与示例标题：

```powershell
D:/Apps/Python/NOVA/Info_fusion/.venv/Scripts/python.exe d:\Apps\Python\NOVA\Info_fusion\scripts\smoke_agg.py
```

- 一键连通性检查（含可选 API 启动）：

```powershell
cd d:\Apps\Python\NOVA\Info_fusion
.\scripts\check_wechat_and_smoke.ps1 -WeMPRSSBaseUrl http://127.0.0.1:8001 -StartApi
```

## 使用方法

### 1. 数据收集与处理

首次运行需要收集和处理数据：

```bash
python main.py
```

这会：
- 从配置的RSS源获取微信公众号文章
- 从语雀知识库获取文档
- 使用AI进行深度分析
- 生成 `final_knowledge_base.json` 文件

### 2. 浏览和搜索

启动Web界面后，你可以：
- 📖 浏览所有经过AI分析的文章
- 🔍 使用搜索功能查找特定内容
- 📊 查看数据统计、来源树分布和最新处理情况
- 🔁 在界面顶部点击“刷新数据”按钮触发新的采集批次
- 🔗 点击原文链接查看完整内容

### 信息提取研发建议

- 在 `wechat_pubaccount_fetcher.py` / `ai_processer.py` 中迭代抽取规则，丰富作者、主题、事件时间等结构化字段。
- 利用 `final_knowledge_base.json` 构建实体/关系层，必要时在 `models.py` 引入 Pydantic 校验确保产物格式稳定。
- 编写 Notebook 或 `scripts` 下的实验脚本，评估抽取质量（覆盖率、准确率、重复率）。
- 结合 `/ops/wechat/reload` 与 smoke 脚本，保持数据链路稳定，再按需扩充算法实验。

## 主要特性详解

### AI分析功能
每篇文章都会经过AI分析，包括：
- **深度总结**: 提炼核心观点和要点
- **关键要点**: 以精简条目列出重要信息
- **开放性问题**: 引发进一步思考的问题

### 去重机制
使用SimHash算法进行智能去重：
- 自动检测相似内容
- 可配置相似度阈值
- 支持增量更新

### 响应式设计
前端界面适配各种设备：
- 📱 移动设备友好
- 💻 桌面端优化
- 🎨 现代化UI设计

## 开发指南

### 项目结构说明

- `config.py`: 统一配置管理，支持环境变量 / .env
- `main.py`: 聚合编排入口，负责抓取、去重、AI 分析与落盘
- `api_server.py`: FastAPI 服务；提供 `/api/v1/**`、`/healthz`、`/ops/wechat/*`
- `wechat_pubaccount_fetcher.py`: 微信公众号 RSS + API 适配与归一化
- `we_mp_rss_sync.py`: 驱动外部 We-MP-RSS 刷新
- `ai_processer.py`: AI 分析核心逻辑
- `simhash_utils.py`: 文本去重算法实现

### 自定义开发

1. **添加新的数据源**: 在相应的fetcher文件中实现获取逻辑
2. **修改AI分析**: 调整 `ai_processer.py` 中的提示词和处理逻辑
3. **自定义前端**: 修改 `web/src` 目录下的React组件

## 故障排除

### 常见问题

1. **无法连接RSS服务**: 确保 we-mp-rss 服务正在运行
2. **AI API调用失败**: 检查API密钥和网络连接
3. **前端启动失败**: 确保Node.js版本兼容，尝试删除node_modules后重新安装

### 日志查看

系统日志保存在 `logs/` 目录下，按日期分文件存储。

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 特别鸣谢
We-mp-rss项目:https://github.com/rachelos/we-mp-rss.

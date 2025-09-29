# 信息融合知识库 (Info Fusion)

一个智能化的信息聚合与分析系统，能够从微信公众号和语雀知识库中获取内容，并使用AI进行深度分析和跨学科洞察。

*本项目是南京大学NOVA工作室的学习实践产物。主要目标是创造出一个能够整合来自语雀、微信、QQ以及南京大学官方网站的信息，并通过AI进行总结与拓展，从而提高碎片化信息的收集效率。*

## 功能特性

- 🔗 **多源信息聚合**: 支持从微信公众号(RSS)和语雀知识库获取内容
- 🤖 **AI智能分析**: 使用大语言模型进行深度总结和跨学科分析  
- 🔍 **智能搜索**: 支持全文搜索和AI分析结果搜索
- 📊 **数据统计**: 提供文章来源、学科分布等统计信息
- 🌐 **现代化Web界面**: 响应式设计，美观易用
- 🔄 **增量更新**: 支持SimHash去重和增量更新机制

## 系统架构

```
Info_fusion/
├── 后端 (Python)
│   ├── main.py                    # 主程序入口
│   ├── api_server.py             # Flask API服务器
│   ├── wechat_pubaccount_fetcher.py  # 微信公众号数据获取
│   ├── yuque_fetcher.py          # 语雀数据获取
│   ├── ai_processer.py           # AI分析处理
│   ├── simhash_utils.py          # 文本相似度检测
│   └── config.py                 # 配置管理
├── 前端 (Next.js + TypeScript)
│   ├── src/app/page.tsx          # 主页面
│   ├── src/components/ArticleCard.tsx  # 文章卡片组件
│   └── package.json              # 前端依赖配置
└── 数据文件
    ├── final_knowledge_base.json # 处理后的知识库
    ├── yuque_data.json          # 语雀原始数据
    └── .env                      # 环境变量配置
```

## 快速开始

### 1. 环境准备

确保系统已安装：
- Python 3.8+
- Node.js 16+
- npm 或 yarn

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
WECHAT_RSS_URL=http://localhost:8001/feed/all.rss
```

### 3. 一键启动

#### Windows用户
```bash
start.bat
```

#### Linux/Mac用户  
```bash
chmod +x start.sh
./start.sh
```

### 4. 手动启动 (可选)

如果自动启动脚本有问题，可以手动启动：

1. **启动后端API服务器**:
```bash
# 激活Python虚拟环境
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install flask flask-cors requests python-dotenv feedparser simhash lxml

# 启动API服务器
python api_server.py
```

2. **启动前端开发服务器** (新开命令行窗口):
```bash
cd web
npm install
npm run dev
```

### 5. 访问应用

- 🌐 **前端界面**: http://localhost:3000
- 🔌 **API接口**: http://localhost:5000
- 📄 **API文档**: 
  - `GET /api/articles` - 获取所有文章
  - `GET /api/stats` - 获取统计信息  
  - `GET /api/search?q=关键词` - 搜索文章

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
- 📊 查看数据统计和学科分布
- 🔗 点击原文链接查看完整内容

## 主要特性详解

### AI分析功能
每篇文章都会经过AI分析，包括：
- **深度总结**: 提炼核心观点和要点
- **跨学科洞察**: 从不同学科角度分析内容
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

- `config.py`: 统一配置管理，支持环境变量
- `main.py`: 主要的数据处理流程
- `api_server.py`: Flask API服务，提供前端数据接口
- `ai_processer.py`: AI分析核心逻辑
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

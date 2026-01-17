# 项目结构说明

本文档说明 PDF 目录生成器的项目结构和文件组织。

## 📁 目录结构

```
PDF_TOC_Generater/
├── 📄 README.md                  # 项目主说明文档
├── 📄 CHANGELOG.md               # 更新日志
├── 📄 TODO.md                    # 开发计划
├── 📄 LICENSE                    # 许可证
├── 📄 requirements.txt           # Python 依赖
├── 📄 .env.example              # 环境变量示例
│
├── 🐍 核心文件
│   ├── app.py                   # FastAPI 后端服务
│   ├── main.py                  # 命令行入口
│   ├── config.py                # 配置管理
│   ├── models.py                # 数据模型
│   ├── database.py              # 数据库管理
│   └── test_extract.py          # 测试脚本
│
├── 📚 文档目录 (docs/)
│   ├── README.md                # 文档导航
│   ├── installation.md          # 安装指南
│   ├── usage.md                 # 使用教程
│   ├── configuration.md         # 配置说明
│   ├── api.md                   # API 文档
│   ├── architecture.md          # 架构设计
│   └── development/             # 开发文档
│       ├── IMPLEMENTATION_GUIDE.md
│       ├── IMPLEMENTATION_PLAN.md
│       └── IMPLEMENTATION_SUMMARY.md
│
├── 🤖 AI Agent (agent/)
│   ├── __init__.py
│   ├── ocr_agent.py             # OCR 识别 Agent
│   ├── graph.py                 # LangGraph 工作流
│   └── README.md                # Agent 说明
│
├── 🛠 工具函数 (utils/)
│   ├── __init__.py
│   ├── pdf_extractor.py         # PDF 提取
│   ├── pdf_writer.py            # PDF 写入
│   └── toc_merger.py            # 目录合并
│
├── 🎨 前端项目 (frontend/)
│   ├── index.html               # HTML 入口
│   ├── package.json             # NPM 配置
│   ├── vite.config.js           # Vite 配置
│   └── src/
│       ├── main.js              # Vue 入口
│       ├── App.vue              # 主组件
│       ├── components/          # UI 组件
│       │   ├── BaseButton.vue
│       │   ├── BaseCard.vue
│       │   ├── ProgressBar.vue
│       │   ├── Pagination.vue
│       │   ├── TaskCard.vue
│       │   └── TOCEditor.vue
│       ├── views/               # 页面视图
│       │   ├── UploadView.vue
│       │   ├── ProcessView.vue
│       │   ├── EditView.vue
│       │   ├── HistoryView.vue
│       │   └── CompleteView.vue
│       ├── services/            # API 服务
│       │   └── api.js
│       └── styles/              # 样式文件
│           └── global.css
│
├── 💾 数据目录
│   ├── data/                    # 数据库文件
│   │   └── tasks.db
│   ├── uploads/                 # 上传的PDF
│   ├── temp/                    # 临时文件
│   └── logs/                    # 日志文件
│
├── 📋 提示词 (prompt/)
│   ├── README.md
│   ├── system_prompt.txt
│   ├── analyze_image.txt
│   ├── extract_text.txt
│   ├── parse_structure.txt
│   └── validate_data.txt
│
├── 📐 JSON Schema (schemas/)
│   ├── README.md
│   ├── toc_entry.schema.json
│   ├── toc_page.schema.json
│   └── toc_merged.schema.json
│
├── 📝 示例文件 (examples/)
│   ├── page_1.json
│   ├── page_2.json
│   └── toc_merged.json
│
└── 🧪 测试目录 (tests/)
    ├── __init__.py
    └── test_database.py
```

## 🔑 关键文件说明

### 后端核心

| 文件 | 说明 |
|------|------|
| `app.py` | FastAPI 后端服务，提供 REST API |
| `main.py` | 命令行工具入口 |
| `config.py` | 配置管理，环境变量加载 |
| `models.py` | 数据模型定义（TOCEntry, TOCMetadata 等） |
| `database.py` | SQLite 数据库管理，任务持久化 |

### AI Agent

| 文件 | 说明 |
|------|------|
| `agent/ocr_agent.py` | OCR 识别 Agent，使用 Claude API |
| `agent/graph.py` | LangGraph 工作流定义 |

### 工具函数

| 文件 | 说明 |
|------|------|
| `utils/pdf_extractor.py` | PDF 页面提取和图像处理 |
| `utils/pdf_writer.py` | PDF 书签写入 |
| `utils/toc_merger.py` | 目录数据合并和页码转换 |

### 前端组件

| 组件 | 说明 |
|------|------|
| `TOCEditor.vue` | 结构化目录编辑器（表格形式） |
| `HistoryView.vue` | 任务历史列表 |
| `EditView.vue` | 目录编辑页面（双模式） |
| `ProcessView.vue` | 处理进度页面 |
| `TaskCard.vue` | 任务卡片组件 |
| `Pagination.vue` | 分页组件 |

## 📦 数据流

```
上传 PDF
  ↓
提取目录页图片 (pdf_extractor.py)
  ↓
OCR 识别 (ocr_agent.py)
  ↓
合并目录数据 (toc_merger.py)
  ↓
页码转换 (书籍页码 → PDF页码)
  ↓
保存到数据库 (database.py)
  ↓
用户编辑 (TOCEditor.vue)
  ↓
写入 PDF 书签 (pdf_writer.py)
  ↓
下载结果
```

## 🗄️ 数据库结构

### tasks 表
- task_id (主键)
- pdf_path
- pdf_filename
- page_offset
- page_range
- status
- progress
- created_at
- completed_at
- error_message

### toc_entries 表
- id (主键)
- task_id (外键)
- title
- page (PDF页码)
- level
- order_index

### task_outputs 表
- id (主键)
- task_id (外键)
- output_path
- created_at

## 📚 文档组织

| 文档 | 用途 |
|------|------|
| `README.md` | 项目概览和快速开始 |
| `docs/README.md` | 文档导航中心 |
| `docs/installation.md` | 详细安装步骤 |
| `docs/usage.md` | 完整使用教程 |
| `docs/api.md` | REST API 接口文档 |
| `docs/architecture.md` | 技术架构说明 |
| `docs/development/` | 开发相关文档 |
| `CHANGELOG.md` | 版本更新记录 |
| `TODO.md` | 开发计划 |

## 🔧 配置文件

| 文件 | 说明 |
|------|------|
| `.env` | 环境变量（API Key等，不提交） |
| `.env.example` | 环境变量示例 |
| `frontend/vite.config.js` | Vite 构建配置 |
| `frontend/package.json` | NPM 依赖配置 |
| `requirements.txt` | Python 依赖 |

## 🚀 快速导航

- 开始使用：查看 [README.md](../README.md)
- 安装配置：查看 [docs/installation.md](installation.md)
- 使用说明：查看 [docs/usage.md](usage.md)
- API 文档：查看 [docs/api.md](api.md)
- 开发文档：查看 [docs/development/](development/)

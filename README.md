# PDF 目录生成器

> 基于 AI 的 PDF 目录自动识别与添加工具，支持 Web 界面和命令行两种使用方式

## ✨ 特性

- 🤖 **AI 智能识别** - 使用 Claude AI 自动识别目录内容
- 📊 **结构化编辑** - 可视化目录编辑器，支持拖拽排序和实时预览
- 📚 **任务历史** - 保存处理记录，支持重新编辑和导出
- 🎯 **精确页码** - 智能页码偏置，支持负数书籍页码（摘要、前言等）
- ⚡ **并行处理** - 多页并行 OCR，提升处理速度
- 🎨 **优雅界面** - 简约设计，流畅交互体验

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+（仅 Web 版本需要）
- OpenRouter API Key

### 安装

```bash
# 克隆项目
git clone https://github.com/Gonghysin/PDF_TOC_Generater.git
cd PDF_TOC_Generater

# 安装 Python 依赖
conda create -n pdf-toc python=3.11
conda activate pdf-toc
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 OpenRouter API Key
```

### Web 界面（推荐）

```bash
# 1. 启动后端服务
python app.py

# 2. 安装并启动前端（新终端）
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000 开始使用

### 命令行

```bash
# 交互式模式
python main.py

# OCR 识别
python main.py --pdf book.pdf --range 5-12 --offset 10

# 从文本文件导入
python main.py --from-txt toc.txt --pdf book.pdf --output output.pdf
```

## 📖 使用流程

### Web 界面

1. **上传 PDF** - 拖拽或选择 PDF 文件
2. **配置参数** - 设置目录页范围和页码偏置
3. **AI 识别** - 自动提取和识别目录内容
4. **编辑确认** - 使用结构化编辑器或文本编辑器调整
5. **生成下载** - 生成带书签的 PDF 文件

### 页码偏置说明

**页码偏置** = 书籍第1页对应的PDF页码

例如：如果PDF第10页是书籍正文第1页，则页码偏置为 10

**书籍页码**可以是负数（摘要、前言等在正文之前），但**PDF页码**必须 ≥ 1

## 🏗️ 技术栈

### 后端
- **FastAPI** - 高性能 Web 框架
- **LangGraph** - AI Agent 工作流
- **Claude AI** - 目录识别引擎
- **PyMuPDF** - PDF 处理
- **SQLite** - 任务历史存储

### 前端
- **Vue 3** - 渐进式框架
- **Vite** - 构建工具
- **思源宋体** - 优雅的中文字体

## 📚 文档

- [使用教程](docs/usage.md) - 详细使用说明
- [安装指南](docs/installation.md) - 完整安装步骤
- [配置说明](docs/configuration.md) - 环境变量和配置
- [API 文档](docs/api.md) - REST API 接口
- [架构设计](docs/architecture.md) - 技术架构
- [开发文档](docs/development/) - 开发相关文档

## 🎯 功能特性

### 结构化编辑器

- ✅ 表格形式编辑目录
- ✅ 书籍页码和 PDF 页码双向编辑
- ✅ 自动按 PDF 页码排序
- ✅ 撤销/重做 (Ctrl+Z/Y)
- ✅ 层级可视化（缩进显示）

### 任务历史管理

- ✅ 保存所有处理任务
- ✅ 查看历史记录
- ✅ 重新编辑和导出
- ✅ 任务删除和过滤

### 智能识别

- ✅ 多列目录布局
- ✅ 复杂层级结构
- ✅ 页码自动对齐
- ✅ 并行处理加速

## 🔧 开发

### 项目结构

```
.
├── app.py                  # FastAPI 后端
├── database.py             # 数据库管理
├── models.py               # 数据模型
├── config.py               # 配置管理
├── main.py                 # 命令行入口
├── agent/                  # AI Agent
├── utils/                  # 工具函数
│   ├── pdf_extractor.py   # PDF 提取
│   ├── pdf_writer.py      # PDF 写入
│   └── toc_merger.py      # 目录合并
├── frontend/              # Vue 前端
│   ├── src/
│   │   ├── components/   # UI 组件
│   │   ├── views/        # 页面视图
│   │   └── services/     # API 服务
└── docs/                  # 文档
```

### 运行测试

```bash
pytest tests/
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

Apache-2.0 License

## 🙏 致谢

- [Anthropic Claude](https://www.anthropic.com/) - AI 识别引擎
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent 框架
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF 处理库

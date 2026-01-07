# PDF TOC Generator

基于 AI 的 PDF 目录自动识别与添加工具。

## 简介

自动识别 PDF 书籍的目录页并将其写入 PDF 元数据，支持 OCR 识别和文本导入两种模式。

## 核心功能

- AI 驱动的 OCR 目录识别
- 智能页码对齐（页码偏置）
- 层级结构识别（章、节、小节）
- 文本格式导入导出
- 命令行与交互式操作
- 并行处理加速

## 技术栈

- **Agent 框架**: LangGraph
- **LLM**: OpenRouter API
- **PDF 处理**: PyMuPDF
- **图像处理**: Pillow
- **数据验证**: JSON Schema

## 快速开始

### 安装

```bash
git clone git@github.com:Gonghysin/PDF_TOC_Generater.git
cd PDF_TOC_Generater
conda create -n pdf-toc python=3.11
conda activate pdf-toc
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 OpenRouter API Key
```

### 使用

```bash
# 交互式模式
python main.py

# OCR 识别
python main.py --pdf book.pdf --range 8-10 --offset 11

# 文本导入
python main.py --from-txt toc.txt --pdf book.pdf --output output.pdf
```

## 文档

- [安装指南](docs/installation.md)
- [使用教程](docs/usage.md)
- [配置说明](docs/configuration.md)
- [API 文档](docs/api.md)
- [架构设计](ARCHITECTURE.md)

## 许可证

MIT License

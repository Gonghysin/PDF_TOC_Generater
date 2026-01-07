# PDF 目录自动添加工具

一个基于 AI Agent 的智能工具，用于自动识别 PDF 书籍的目录并将其写入 PDF 元数据，方便阅读器展示和跳转。

## 功能特点

- 🤖 **AI 驱动的 OCR 识别**：使用 LangGraph Agent 框架，结合大语言模型自动识别目录页内容
- 📄 **智能页码对齐**：支持页码偏置设置，准确处理封面、前言等非正文页面
- 🔍 **结构化数据提取**：自动识别目录的层级结构（章、节、小节等）
- 💾 **安全的中间文件**：每页目录单独保存为 JSON，支持手动修正和断点续传
- ✅ **标准化输出**：基于 JSON Schema 验证，确保数据格式规范

## 技术栈

- **Agent 框架**: [LangGraph](https://github.com/langchain-ai/langgraph)
- **LLM API**: OpenRouter（支持多种模型）
- **PDF 处理**: PyMuPDF (fitz)
- **图像处理**: Pillow
- **数据验证**: JSON Schema

## 工作流程

```
┌─────────────────┐
│  1. 用户输入    │
│  - PDF 路径     │
│  - 目录页范围   │
│  - 页码偏置     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. PDF 转图片  │
│  将目录页导出   │
│  为图片文件     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. OCR Agent   │
│  逐页识别目录   │
│  生成 JSON 文件 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. 数据合并    │
│  读取所有 JSON  │
│  合并为完整目录 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. 写入 PDF    │
│  应用页码偏置   │
│  写入 TOC 元数据│
└─────────────────┘
```

## 使用方法

### 1. 环境配置

创建 `.env` 文件并配置以下参数：

```env
API_BASE_URL=https://openrouter.ai/api/v1
API_KEY=your_openrouter_api_key
MODEL_NAME=anthropic/claude-3.5-sonnet
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行程序

```bash
python main.py
```

### 4. 交互式输入

程序运行后会提示输入以下信息：

1. **PDF 文件路径**：待处理的 PDF 文件完整路径
2. **目录页码范围**：例如 `5-12` 表示 PDF 的第 5 页到第 12 页是目录
3. **页码偏置**：书籍正文第 1 页对应 PDF 的第几页（例如封面、版权页后正文从 PDF 第 10 页开始，则输入 `10`）

### 示例

```
请输入 PDF 文件路径: /path/to/book.pdf
请输入目录页码范围 (例如 5-12): 7-10
请输入页码偏置 (书籍第1页是PDF的第几页): 15

开始处理...
✓ 已导出 4 张目录图片到 temp/toc_images/
✓ 正在识别第 1/4 页...
✓ 正在识别第 2/4 页...
✓ 正在识别第 3/4 页...
✓ 正在识别第 4/4 页...
✓ 数据合并完成，共识别 45 个目录项
✓ TOC 已成功写入 PDF！
```

## 目录数据格式

### 单页目录文件（page_N.json）

每页目录识别后保存为独立的 JSON 文件：

```json
[
  {
    "title": "第一章 绪论",
    "page": 1,
    "level": 1
  },
  {
    "title": "1.1 研究背景",
    "page": 3,
    "level": 2
  },
  {
    "title": "1.1.1 国内现状",
    "page": 5,
    "level": 3
  }
]
```

### 合并后的完整目录（toc_merged.json）

```json
{
  "metadata": {
    "pdf_path": "/path/to/book.pdf",
    "page_offset": 15,
    "total_entries": 45,
    "generated_at": "2026-01-04T10:30:00"
  },
  "toc": [
    {
      "title": "第一章 绪论",
      "page": 1,
      "level": 1
    },
    {
      "title": "1.1 研究背景",
      "page": 3,
      "level": 2
    }
  ]
}
```

## 页码计算公式

$$
P_{pdf} = P_{book} + (offset - 1)
$$

其中：
- $P_{book}$：书籍中标注的页码（OCR 识别出的）
- $offset$：用户输入的页码偏置
- $P_{pdf}$：PDF 文件的实际页码（从 1 开始）

## 项目结构

```
.
├── README.md                 # 项目文档
├── requirements.txt          # 依赖列表
├── .env                      # 环境变量配置
├── .env.example             # 环境变量模板
├── schemas/                  # JSON Schema 定义
│   ├── toc_entry.schema.json    # 单条目录项 Schema
│   ├── toc_page.schema.json     # 单页目录 Schema
│   └── toc_merged.schema.json   # 合并目录 Schema
├── examples/                 # 示例数据
│   ├── page_1.json          # 单页目录示例
│   └── toc_merged.json      # 合并目录示例
├── main.py                   # 主程序入口
├── agent/                    # Agent 模块
│   ├── __init__.py
│   ├── ocr_agent.py         # OCR 识别 Agent
│   └── graph.py             # LangGraph 流程定义
├── utils/                    # 工具模块
│   ├── __init__.py
│   ├── pdf_extractor.py     # PDF 转图片
│   ├── toc_merger.py        # 目录数据合并
│   └── pdf_writer.py        # TOC 写入 PDF
└── temp/                     # 临时文件目录（自动生成）
    ├── toc_images/          # 导出的目录页图片
    └── toc_json/            # OCR 识别的 JSON 文件
```

## 注意事项

### 1. 目录识别准确度

- **清晰的扫描质量**：确保 PDF 目录页清晰可读
- **标准的排版格式**：复杂的多栏排版或图文混排可能影响识别
- **手动修正**：识别完成后可手动编辑 `temp/toc_json/` 下的 JSON 文件进行修正

### 2. 页码偏置设置

正确的偏置值计算方法：
- 打开 PDF，找到书籍正文第 1 页
- 查看该页在 PDF 中的实际页码（通常 PDF 阅读器底部会显示）
- 该页码即为偏置值

### 3. Level 层级说明

- `level: 1` - 一级标题（章）
- `level: 2` - 二级标题（节）
- `level: 3` - 三级标题（小节）
- 以此类推，最多支持 4-5 级

### 4. 中间文件管理

- 中间文件保存在 `temp/` 目录
- 如需重新识别某页，删除对应的 `page_N.json` 后重新运行
- 如需完全重新处理，删除整个 `temp/` 目录

## 常见问题

### Q1: OCR 识别出的页码不准确怎么办？

A: 手动编辑 `temp/toc_json/page_N.json` 文件，修改对应条目的 `page` 字段。

### Q2: 目录层级识别错误？

A: 同样手动编辑 JSON 文件，调整 `level` 值（1=章，2=节，3=小节）。

### Q3: 为什么有些目录项没有被识别？

A: 可能原因：
- 图片质量不佳
- 排版过于复杂
- 目录项过于简短或特殊

解决方法：手动在对应的 JSON 文件中添加缺失的条目。

### Q4: 支持哪些 PDF 格式？

A: 支持所有标准 PDF 格式，但扫描版 PDF 效果更好（因为本工具就是为扫描版设计的）。

## 开发计划

- [ ] 支持批量处理多个 PDF
- [ ] 添加 Web UI 界面
- [ ] 支持更多 OCR 引擎（Tesseract、PaddleOCR 等）
- [ ] 自动检测页码偏置
- [ ] 目录预览和可视化编辑

## 许可证

MIT License

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 致谢

- LangGraph 团队
- PyMuPDF 开发者
- OpenRouter 社区

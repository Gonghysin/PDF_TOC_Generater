# PDF TOC Builder - Schema 说明文档

本文档详细说明了 PDF 目录自动添加工具使用的 JSON Schema 结构。

## Schema 文件列表

1. **toc_entry.schema.json** - 单个目录项定义
2. **toc_page.schema.json** - 单页目录定义（OCR 识别单页后的输出）
3. **toc_merged.schema.json** - 合并后的完整目录定义

---

## 1. toc_entry.schema.json

定义单个目录项的数据结构。

### 字段说明

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| `title` | string | ✓ | 目录项标题 | "第一章 绪论" |
| `page` | integer | ✓ | 书籍中标注的页码（未加偏置） | 1 |
| `level` | integer | ✓ | 目录层级（1-5） | 1 |

### 层级说明

- **level: 1** - 一级标题（章）
  - 示例：`第一章 绪论`、`Chapter 1 Introduction`
- **level: 2** - 二级标题（节）
  - 示例：`1.1 研究背景`、`1.1 Background`
- **level: 3** - 三级标题（小节）
  - 示例：`1.1.1 国内现状`、`1.1.1 Domestic Status`
- **level: 4** - 四级标题
- **level: 5** - 五级标题

### 示例数据

```json
{
  "title": "第一章 绪论",
  "page": 1,
  "level": 1
}
```

---

## 2. toc_page.schema.json

定义单页目录的数据结构（OCR 识别单页后的输出）。

### 结构说明

这是一个 **数组**，包含从单页目录中识别出的所有目录项。

### 约束条件

- 最少：0 个条目（空白页或识别失败）
- 最多：100 个条目（理论上限）
- 典型值：5-20 个条目/页

### 文件命名规范

- `page_1.json` - 第 1 页目录
- `page_2.json` - 第 2 页目录
- `page_N.json` - 第 N 页目录

### 示例数据

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
    "title": "1.1.1 国内研究现状",
    "page": 5,
    "level": 3
  }
]
```

---

## 3. toc_merged.schema.json

定义合并后的完整目录数据结构。

### 顶层结构

```json
{
  "metadata": { ... },
  "toc": [ ... ]
}
```

### metadata 字段说明

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| `pdf_path` | string | ✓ | 原始 PDF 文件路径 | "/path/to/book.pdf" |
| `page_offset` | integer | ✓ | 页码偏置值 | 15 |
| `toc_page_range` | string | ✗ | 目录页码范围 | "5-12" |
| `total_entries` | integer | ✓ | 目录项总数 | 45 |
| `generated_at` | string | ✓ | 生成时间（ISO 8601） | "2026-01-04T10:30:00Z" |
| `model_name` | string | ✗ | 使用的 AI 模型 | "anthropic/claude-3.5-sonnet" |

### toc 字段说明

一个 **数组**，包含所有目录项，按书籍顺序排列。

### 示例数据

```json
{
  "metadata": {
    "pdf_path": "/Users/john/Documents/book.pdf",
    "page_offset": 15,
    "toc_page_range": "7-10",
    "total_entries": 45,
    "generated_at": "2026-01-04T10:30:00Z",
    "model_name": "anthropic/claude-3.5-sonnet"
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

---

## 数据流转示例

### Step 1: OCR 识别单页

输入：`temp/toc_images/page_7.png`  
输出：`temp/toc_json/page_1.json`

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
  }
]
```

### Step 2: OCR 识别另一页

输入：`temp/toc_images/page_8.png`  
输出：`temp/toc_json/page_2.json`

```json
[
  {
    "title": "第二章 相关理论",
    "page": 18,
    "level": 1
  },
  {
    "title": "2.1 机器学习",
    "page": 20,
    "level": 2
  }
]
```

### Step 3: 合并所有页

输入：`temp/toc_json/page_*.json`  
输出：`temp/toc_merged.json`

```json
{
  "metadata": {
    "pdf_path": "/path/to/book.pdf",
    "page_offset": 15,
    "total_entries": 4,
    "generated_at": "2026-01-04T10:30:00Z"
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
    },
    {
      "title": "第二章 相关理论",
      "page": 18,
      "level": 1
    },
    {
      "title": "2.1 机器学习",
      "page": 20,
      "level": 2
    }
  ]
}
```

---

## 使用 JSON Schema 验证数据

### Python 示例

```python
import json
import jsonschema

# 加载 Schema
with open('schemas/toc_merged.schema.json', 'r') as f:
    schema = json.load(f)

# 加载待验证的数据
with open('temp/toc_merged.json', 'r') as f:
    data = json.load(f)

# 验证
try:
    jsonschema.validate(instance=data, schema=schema)
    print("✓ 数据格式正确")
except jsonschema.exceptions.ValidationError as e:
    print(f"✗ 数据格式错误: {e.message}")
```

---

## 常见问题

### Q1: 为什么使用 JSON 而不是 Python 字典文件？

**A:** JSON 格式的优势：
- 更安全（不需要执行代码）
- 标准化（有完善的 Schema 验证）
- 跨语言（可被任何语言读取）
- 易编辑（纯文本，不需要处理 Python 语法）

### Q2: 如果 OCR 识别错误怎么办？

**A:** 直接编辑 `temp/toc_json/page_N.json` 文件：
1. 找到识别错误的那一页对应的 JSON 文件
2. 用文本编辑器打开
3. 修正 `title`、`page` 或 `level` 字段
4. 保存后重新运行合并步骤

### Q3: level 如何判断？

**A:** 判断依据：
- 通过缩进：一级标题顶格，二级缩进 2 空格，三级缩进 4 空格
- 通过编号：`第一章` → level 1，`1.1` → level 2，`1.1.1` → level 3
- 通过字体：通常一级标题字体最大

### Q4: page 字段是 PDF 页码还是书籍页码？

**A:** **书籍页码**（OCR 识别出的原始页码）。  
程序会在写入 PDF 时自动应用 `page_offset` 计算实际的 PDF 页码。

公式：`PDF页码 = 书籍页码 + (offset - 1)`

---

## 扩展建议

如果需要支持更复杂的目录结构，可以扩展 Schema：

### 可选扩展字段

```json
{
  "title": "第一章 绪论",
  "page": 1,
  "level": 1,
  "id": "chapter-1",           // 唯一标识符
  "parent_id": null,           // 父节点 ID
  "style": "bold",             // 样式信息
  "color": "#000000",          // 颜色
  "is_collapsed": false        // 是否折叠
}
```

但目前的简化版本已能满足 95% 的使用场景。

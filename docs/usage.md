# 使用教程

## 基本概念

### 页码偏置

书籍实际页码与 PDF 页码的差值。例如：
- 书籍第 1 页显示为 PDF 第 11 页
- 页码偏置 = 11

### 目录页范围

目录在 PDF 中的页码范围，例如 `8-10` 表示第 8 到 10 页。

## 使用模式

### 模式 1：OCR 识别（推荐首次使用）

从 PDF 自动识别目录内容。

#### 交互式操作

```bash
python main.py
```

1. 选择模式 `1` - OCR 识别模式
2. 输入 PDF 文件路径
3. 输入目录页范围（如 `8-10`）
4. 输入页码偏置（如 `11`）
5. 确认执行

#### 命令行操作

```bash
python main.py --pdf book.pdf --range 8-10 --offset 11
```

可选参数：
- `--output`: 指定输出文件路径
- `--no-parallel`: 禁用并行处理

#### 处理流程

```
1. 提取目录页 → 导出为图片
2. OCR 识别 → 生成 JSON 文件（temp/toc_json/）
3. 合并数据 → 生成完整目录（temp/toc_merged.json）
4. 导出文本 → 供查看修改（temp/toc.txt）
5. 写入 PDF → 生成带目录的 PDF
```

### 模式 2：文本导入（适合修正或复用）

从 `toc.txt` 文件导入目录。

#### 交互式操作

```bash
python main.py
```

1. 选择模式 `2` - 文本导入模式
2. 输入 toc.txt 文件路径
3. 输入目标 PDF 文件路径
4. 确认执行

#### 命令行操作

```bash
python main.py --from-txt toc.txt --pdf book.pdf --output output.pdf
```

#### 文本格式

```
============================================================
PDF 目录
============================================================

文件: /path/to/book.pdf
页码偏置: 11
总条目数: 145

------------------------------------------------------------

第1章 标题 ... 1 (PDF: 11)
  1.1 小节 ... 2 (PDF: 12)
    1.1.1 子小节 ... 4 (PDF: 14)
```

格式要求：
- 2 个空格表示一级缩进
- 格式：`标题 ... 页码 (PDF: 实际页码)`
- 支持 1-5 级层级

## 典型工作流

### 场景 1：首次处理 PDF

```bash
# 使用 OCR 识别
python main.py --pdf book.pdf --range 8-10 --offset 11 --output book_with_toc.pdf
```

### 场景 2：修正识别错误

```bash
# 1. 先识别
python main.py --pdf book.pdf --range 8-10 --offset 11

# 2. 手动编辑 temp/toc.txt 修正错误

# 3. 重新导入
python main.py --from-txt temp/toc.txt --pdf book.pdf --output book_corrected.pdf
```

### 场景 3：批量处理

```bash
# 复用同一目录结构
python main.py --from-txt template_toc.txt --pdf book1.pdf --output book1_toc.pdf
python main.py --from-txt template_toc.txt --pdf book2.pdf --output book2_toc.pdf
```

## 高级选项

### 并行处理

默认开启，可加速多页识别：
```bash
python main.py --pdf book.pdf --range 8-15 --offset 11
```

禁用并行：
```bash
python main.py --pdf book.pdf --range 8-15 --offset 11 --no-parallel
```

### 清理临时文件

```bash
python main.py --clean
```

清理 `temp/` 和 `logs/` 目录。

## 输出说明

### 生成的文件

- `logs/toc_builder_YYYYMMDD_HHMMSS.log`: 运行日志
- `temp/toc_images/page_N.jpg`: 目录页图片
- `temp/toc_json/page_N.json`: 单页识别结果
- `temp/toc_merged.json`: 合并后的完整目录
- `temp/toc.txt`: 文本格式目录
- 输出 PDF: 带目录的 PDF 文件

### 备份机制

覆盖原文件时会自动创建备份：
- 原文件：`book.pdf`
- 备份文件：`book_backup_YYYYMMDD_HHMMSS.pdf`

## 常见问题

### Q: 识别结果不准确？

A: 
1. 检查目录页图片质量（temp/toc_images/）
2. 尝试调整 PDF 页码范围
3. 手动修正 toc.txt 后重新导入

### Q: 层级识别错误？

A: 手动编辑 toc.txt，调整缩进（2空格=1级）

### Q: 页码对应错误？

A: 检查页码偏置值是否正确

### Q: 处理速度慢？

A: 
- 确保已开启并行处理
- 减少同时处理的页数
- 检查网络连接（API 调用）

## 查看结果

使用支持 PDF 目录的阅读器查看：
- Adobe Acrobat Reader
- Preview（macOS）
- Foxit Reader
- SumatraPDF

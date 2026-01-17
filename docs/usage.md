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
2. OCR 识别 → 生成 JSON 文件（{PDF名}_temp/toc_json/）
3. 合并数据 → 生成完整目录（{PDF名}_temp/toc_merged.json）
4. 导出文本 → 生成可编辑文件（{PDF名}_temp/toc.txt）
5. 用户审核 → 打开编辑器供用户检查和修改
6. 确认写入 → 生成带目录的 PDF
```

**新增：用户审核步骤**

在步骤 4 和 6 之间，系统会：
1. 自动打开文本编辑器显示 `toc.txt`
2. 用户可以修改任何识别错误的内容
3. 保存并关闭编辑器
4. 在终端输入 `ok` 确认继续，或 `cancel` 取消

**临时文件位置**

所有临时文件现在存储在 PDF 同目录下的 `{PDF文件名}_temp/` 文件夹中，方便管理和清理。

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

### 场景 2：审核和修正识别结果

```bash
# OCR 识别后会自动进入审核流程
python main.py --pdf book.pdf --range 8-10 --offset 11

# 在审核步骤：
# 1. 系统自动打开 toc.txt 编辑器
# 2. 检查并修改识别错误的内容
# 3. 保存并关闭编辑器
# 4. 在终端输入 'ok' 确认
```

### 场景 3：手动编辑后重新导入

如果需要大量修改，可以先取消审核，稍后手动编辑：

```bash
# 1. 先识别（审核时输入 'cancel' 取消）
python main.py --pdf book.pdf --range 8-10 --offset 11

# 2. 手动编辑 {PDF名}_temp/toc.txt

# 3. 重新导入
python main.py --from-txt book_temp/toc.txt --pdf book.pdf --output book_corrected.pdf
```

### 场景 4：批量处理

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

临时文件位置：`{PDF文件名}_temp/`（在 PDF 同目录下）

- `logs/toc_builder_YYYYMMDD_HHMMSS.log`: 运行日志
- `{PDF名}_temp/toc_images/page_N.jpg`: 目录页图片
- `{PDF名}_temp/toc_json/page_N.json`: 单页识别结果
- `{PDF名}_temp/toc_merged.json`: 合并后的完整目录
- `{PDF名}_temp/toc.txt`: 文本格式目录（可编辑）
- 输出 PDF: 带目录的 PDF 文件

### 备份机制

覆盖原文件时会自动创建备份：
- 原文件：`book.pdf`
- 备份文件：`book_backup_YYYYMMDD_HHMMSS.pdf`

## 常见问题

### Q: 识别结果不准确？

A:
1. 检查目录页图片质量（{PDF名}_temp/toc_images/）
2. 尝试调整 PDF 页码范围
3. 在审核步骤手动修正 toc.txt
4. 或取消后手动编辑 toc.txt 重新导入

### Q: 审核时编辑器没有自动打开？

A:
1. 检查终端提示，可能需要手动打开文件
2. 文件路径会显示在终端中：`{PDF名}_temp/toc.txt`
3. 手动编辑后在终端输入 'ok' 继续

### Q: 如何跳过审核步骤？

A: 目前审核步骤是必需的，但你可以：
1. 按 Enter 打开编辑器
2. 直接关闭编辑器（不做修改）
3. 在终端输入 'ok' 继续

或在审核步骤输入 'cancel' 取消，稍后使用文本导入模式。

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

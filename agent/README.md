# Agent 设计文档

本文档描述 PDF 目录识别系统的 Agent 架构设计。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Main Program                         │
│                          (main.py)                           │
└───────────┬──────────────────────────────────────────────────┘
            │
            ├─► 1. PDF Extractor (utils/pdf_extractor.py)
            │      将目录页转换为图片
            │
            ├─► 2. OCR Agent (agent/ocr_agent.py)
            │      ├─► LangGraph Workflow
            │      │   ├─► Image Analysis Node
            │      │   ├─► Text Extraction Node
            │      │   └─► Structure Parser Node
            │      └─► 输出：page_N.json
            │
            ├─► 3. TOC Merger (utils/toc_merger.py)
            │      合并所有 page_N.json
            │
            └─► 4. PDF Writer (utils/pdf_writer.py)
                   将目录写入 PDF
```

---

## Agent 核心：OCR Agent

OCR Agent 是整个系统的核心，负责将目录页图片转换为结构化的 JSON 数据。

### 技术选型

- **框架**: LangGraph
- **LLM**: OpenRouter (支持多种模型)
- **推荐模型**: 
  - Claude 3.5 Sonnet (视觉+推理能力强)
  - GPT-4 Vision
  - Gemini Pro Vision

### LangGraph 工作流设计

```python
from langgraph.graph import StateGraph, END

class OCRState(TypedDict):
    image_path: str
    raw_text: str
    structured_data: list[dict]
    errors: list[str]

workflow = StateGraph(OCRState)
workflow.add_node("analyze_image", analyze_image_node)
workflow.add_node("extract_text", extract_text_node)
workflow.add_node("parse_structure", parse_structure_node)
workflow.add_node("validate_data", validate_data_node)

workflow.set_entry_point("analyze_image")
workflow.add_edge("analyze_image", "extract_text")
workflow.add_edge("extract_text", "parse_structure")
workflow.add_edge("parse_structure", "validate_data")
workflow.add_edge("validate_data", END)
```

### 节点功能说明

#### 1. analyze_image_node
**功能**: 分析图片质量和布局

```python
def analyze_image_node(state: OCRState) -> OCRState:
    """
    分析目录页图片的质量和布局特征
    - 检测图片清晰度
    - 识别文字区域
    - 判断是否为多栏布局
    - 检测页眉页脚
    """
    # 调用 Vision Model 进行初步分析
    # 返回布局信息
```

**输入**: `image_path`  
**输出**: 图片布局元数据

#### 2. extract_text_node
**功能**: 提取原始文本

```python
def extract_text_node(state: OCRState) -> OCRState:
    """
    使用 LLM 的视觉能力提取图片中的所有文本
    - 识别标题文字
    - 识别页码数字
    - 保留文本的相对位置信息
    """
    # 发送图片给 LLM
    # 提示词要求输出 "标题 ...... 页码" 格式
```

**输入**: `image_path`  
**输出**: `raw_text` (原始文本)

#### 3. parse_structure_node
**功能**: 解析结构化数据

```python
def parse_structure_node(state: OCRState) -> OCRState:
    """
    将原始文本解析为结构化的目录数据
    - 分离标题和页码
    - 识别层级（通过缩进或编号）
    - 生成符合 JSON Schema 的数据
    """
    # 使用 LLM 进行结构化解析
    # 输出格式：[{"title": "...", "page": N, "level": L}]
```

**输入**: `raw_text`  
**输出**: `structured_data` (结构化的目录项列表)

#### 4. validate_data_node
**功能**: 验证数据格式

```python
def validate_data_node(state: OCRState) -> OCRState:
    """
    使用 JSON Schema 验证数据格式
    - 检查必需字段
    - 验证数据类型
    - 检查页码逻辑（递增、合理范围）
    """
    # 使用 jsonschema.validate()
    # 如果验证失败，记录错误
```

**输入**: `structured_data`  
**输出**: 验证后的数据或错误信息

---

## Prompt 设计

### Prompt 1: 图片分析

```
你是一个专业的 OCR 分析助手。请分析这张书籍目录页的图片。

任务：
1. 判断图片质量（清晰/模糊）
2. 识别文字区域的位置
3. 判断是否为多栏布局
4. 检测是否有页眉页脚

请以 JSON 格式输出分析结果：
{
  "quality": "clear/blurry",
  "layout": "single_column/multi_column",
  "has_header": true/false,
  "has_footer": true/false
}
```

### Prompt 2: 文本提取

```
你是一个专业的 OCR 识别助手。请提取这张书籍目录页中的所有文本。

注意事项：
1. 目录通常格式为："标题 ...... 页码"
2. 保留标题的缩进信息（用空格表示）
3. 页码通常在右侧
4. 忽略页眉页脚

请逐行输出识别的文本，保持原有的缩进格式。
```

### Prompt 3: 结构化解析

```
你是一个专业的目录解析助手。请将以下目录文本解析为结构化的 JSON 数据。

输入文本：
{raw_text}

解析规则：
1. 分离标题和页码（页码通常在 "......" 之后）
2. 识别层级：
   - 无缩进或"第X章" → level: 1
   - 缩进2空格或"X.Y" → level: 2
   - 缩进4空格或"X.Y.Z" → level: 3
3. 页码必须是数字

输出格式（JSON Schema）：
[
  {
    "title": "章节标题",
    "page": 页码数字,
    "level": 层级数字(1-5)
  }
]

请直接输出 JSON 数组，不要包含任何其他文字。
```

---

## 容错机制

### 1. 识别失败重试

```python
async def ocr_with_retry(image_path: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            result = await ocr_agent.process(image_path)
            if validate_result(result):
                return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # 指数退避
```

### 2. 数据验证

```python
def validate_toc_entry(entry: dict) -> bool:
    """验证单个目录项的合法性"""
    if not isinstance(entry.get('title'), str):
        return False
    if not isinstance(entry.get('page'), int) or entry['page'] < 1:
        return False
    if not isinstance(entry.get('level'), int) or entry['level'] < 1:
        return False
    return True
```

### 3. 人工干预点

- 识别完成后，将 JSON 文件保存到 `temp/toc_json/`
- 用户可以手动编辑修正
- 程序继续读取修正后的文件进行下一步

---

## 性能优化

### 1. 并行处理

```python
import asyncio

async def process_all_images(image_paths: list[str]):
    """并行处理多张目录页"""
    tasks = [ocr_agent.process(path) for path in image_paths]
    results = await asyncio.gather(*tasks)
    return results
```

### 2. 缓存机制

```python
@lru_cache(maxsize=100)
def get_model_response(prompt: str, image_path: str):
    """缓存 LLM 响应"""
    # 避免重复调用 API
```

### 3. Token 优化

- 压缩图片大小（保持清晰度前提下）
- 简化 Prompt（去除冗余描述）
- 使用流式输出（streaming）

---

## 调试与日志

### 日志级别

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 使用示例
logger.info(f"开始处理图片: {image_path}")
logger.warning(f"识别质量较低: {quality_score}")
logger.error(f"解析失败: {error_message}")
```

### 中间结果保存

```python
# 保存原始响应（调试用）
with open(f'temp/debug/response_{page_num}.txt', 'w') as f:
    f.write(raw_response)

# 保存结构化数据
with open(f'temp/toc_json/page_{page_num}.json', 'w') as f:
    json.dump(structured_data, f, ensure_ascii=False, indent=2)
```

---

## 配置文件

### agent_config.yaml

```yaml
ocr:
  model: "anthropic/claude-3.5-sonnet"
  temperature: 0.1  # 低温度保证稳定输出
  max_tokens: 2000
  retry_attempts: 3
  timeout: 30

image:
  max_size: 2048  # 最大边长（像素）
  quality: 85      # JPEG 质量
  format: "PNG"

validation:
  min_entries_per_page: 1
  max_entries_per_page: 50
  min_page_number: 1
  max_page_number: 9999
```

---

## 测试用例

### 单元测试

```python
def test_parse_toc_entry():
    input_text = "第一章 绪论 ...... 1"
    result = parse_toc_entry(input_text)
    assert result == {
        "title": "第一章 绪论",
        "page": 1,
        "level": 1
    }

def test_detect_level():
    assert detect_level("第一章") == 1
    assert detect_level("  1.1 背景") == 2
    assert detect_level("    1.1.1 现状") == 3
```

### 集成测试

```python
async def test_full_workflow():
    # 准备测试图片
    test_image = "tests/fixtures/toc_page.png"
    
    # 运行 OCR Agent
    result = await ocr_agent.process(test_image)
    
    # 验证结果
    assert len(result) > 0
    assert all(validate_toc_entry(e) for e in result)
```

---

## 未来优化方向

1. **自适应 Prompt**: 根据识别结果质量动态调整 Prompt
2. **多模型投票**: 使用多个模型识别同一页，结果投票决定
3. **增量学习**: 收集用户修正数据，微调模型
4. **GUI 预览**: 可视化展示识别结果，支持拖拽调整层级

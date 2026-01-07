# Prompt 模板库

本目录包含 OCR Agent 使用的所有 Prompt 模板。

## 文件列表

- `system_prompt.txt` - Agent 系统提示词
- `analyze_image.txt` - 图片分析 Prompt
- `extract_text.txt` - 文本提取 Prompt
- `parse_structure.txt` - 结构化解析 Prompt
- `validate_data.txt` - 数据验证 Prompt

## 使用方法

```python
from pathlib import Path

def load_prompt(name: str) -> str:
    prompt_path = Path(__file__).parent / f"{name}.txt"
    return prompt_path.read_text(encoding='utf-8')

# 使用示例
system_prompt = load_prompt('system_prompt')
```

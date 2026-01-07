# 配置说明

## 环境变量配置

### .env 文件

项目根目录创建 `.env` 文件：

```env
# ========================================
# OpenRouter API 配置
# ========================================
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# ========================================
# 模型参数
# ========================================
TEMPERATURE=0.1
MAX_TOKENS=4000

# ========================================
# 路径配置（可选，使用默认值）
# ========================================
# TEMP_DIR=temp
# LOGS_DIR=logs
```

### 配置项说明

#### API 配置

| 配置项 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `OPENROUTER_API_KEY` | 是 | OpenRouter API 密钥 | `sk-or-v1-xxxxx` |
| `OPENROUTER_BASE_URL` | 否 | API 基础 URL | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | 否 | 使用的模型 | `anthropic/claude-3.5-sonnet` |

#### 模型参数

| 配置项 | 默认值 | 说明 | 范围 |
|--------|--------|------|------|
| `TEMPERATURE` | 0.1 | 生成温度，越低越确定 | 0.0-1.0 |
| `MAX_TOKENS` | 4000 | 最大 token 数 | 1000-8000 |

#### 路径配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `TEMP_DIR` | `temp` | 临时文件目录 |
| `LOGS_DIR` | `logs` | 日志文件目录 |

## 支持的模型

### 推荐模型

| 模型 | 速度 | 成本 | 准确度 | 适用场景 |
|------|------|------|--------|----------|
| `anthropic/claude-3.5-sonnet` | 快 | 中 | 高 | 推荐，综合最优 |
| `anthropic/claude-3-opus` | 慢 | 高 | 很高 | 复杂目录 |
| `openai/gpt-4-turbo` | 中 | 中 | 高 | 备选方案 |

### 经济型模型

| 模型 | 速度 | 成本 | 准确度 |
|------|------|------|--------|
| `anthropic/claude-3-haiku` | 很快 | 低 | 中 |
| `openai/gpt-3.5-turbo` | 快 | 低 | 中 |

根据需求在 `.env` 中修改 `OPENROUTER_MODEL`。

## config.py 配置

高级用户可直接修改 `config.py`：

### PathConfig

```python
@dataclass
class PathConfig:
    temp_dir: Path          # 临时文件目录
    logs_dir: Path          # 日志目录
    toc_images_dir: Path    # 目录图片目录
    toc_json_dir: Path      # JSON 文件目录
```

### ImageConfig

```python
@dataclass
class ImageConfig:
    dpi: int = 300          # 图片 DPI
    format: str = 'JPEG'    # 图片格式
    quality: int = 95       # JPEG 质量
```

### OCRConfig

```python
@dataclass
class OCRConfig:
    parallel: bool = True           # 并行处理
    max_workers: int = 3            # 最大并发数
    retry_times: int = 3            # 重试次数
    retry_delay: float = 1.0        # 重试延迟
```

## 日志配置

日志自动保存到 `logs/toc_builder_YYYYMMDD_HHMMSS.log`。

修改日志级别（在 `main.py`）：

```python
logging.basicConfig(
    level=logging.INFO,  # 改为 DEBUG 查看更多信息
    ...
)
```

日志级别：
- `DEBUG`: 详细调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息

## JSON Schema

目录数据验证使用 JSON Schema，位于 `schemas/` 目录：

- `toc_entry.schema.json`: 单条目录条目
- `toc_page.schema.json`: 单页目录
- `toc_merged.schema.json`: 完整目录

一般无需修改。

## 自定义 Prompt

修改 AI 提示词（`prompt/` 目录）：

- `system_prompt.txt`: 系统提示
- `extract_text.txt`: 文本提取提示
- `parse_structure.txt`: 结构解析提示
- `validate_data.txt`: 数据验证提示

注意：修改可能影响识别准确度。

## 性能优化

### 提升速度

1. 开启并行处理（默认已开启）
2. 使用更快的模型（如 `claude-3-haiku`）
3. 减少单次处理页数
4. 提高网络速度

### 提升准确度

1. 使用更强的模型（如 `claude-3-opus`）
2. 提高图片 DPI（修改 `ImageConfig.dpi`）
3. 降低 TEMPERATURE 值
4. 优化 Prompt 提示词

### 降低成本

1. 使用经济型模型
2. 减少重试次数
3. 手动修正后使用文本导入模式

# 项目架构文档

本文档详细说明了 PDF 目录自动添加工具的完整架构。

## 📁 目录结构

```
.
├── README.md                        # 项目说明文档
├── requirements.txt                 # Python 依赖包
├── .env                            # 环境变量配置（需创建）
├── .env.example                    # 环境变量模板
├── .gitignore                      # Git 忽略配置
├── config.py                       # ⭐ 配置管理模块
├── models.py                       # ⭐ 数据模型定义
├── main.py                         # ⭐ 主程序入口
│
├── schemas/                        # JSON Schema 定义
│   ├── README.md
│   ├── toc_entry.schema.json
│   ├── toc_page.schema.json
│   └── toc_merged.schema.json
│
├── examples/                       # 示例数据
│   ├── page_1.json
│   ├── page_2.json
│   └── toc_merged.json
│
├── prompt/                         # Prompt 模板
│   ├── README.md
│   ├── system_prompt.txt
│   ├── analyze_image.txt
│   ├── extract_text.txt
│   ├── parse_structure.txt
│   └── validate_data.txt
│
├── utils/                          # ⭐ 工具模块
│   ├── __init__.py
│   ├── pdf_extractor.py           # PDF 转图片
│   ├── toc_merger.py              # 目录合并
│   └── pdf_writer.py              # TOC 写入
│
├── agent/                          # ⭐ Agent 模块
│   ├── __init__.py
│   ├── README.md
│   ├── graph.py                   # LangGraph 工作流
│   └── ocr_agent.py               # OCR Agent 实现
│
└── temp/                           # 临时文件（自动生成）
    ├── toc_images/                # 导出的图片
    ├── toc_json/                  # OCR 识别结果
    └── debug/                     # 调试信息
```

---

## 🏗️ 模块架构

### 1. config.py - 配置管理模块

负责加载和管理所有配置。

#### 主要类

##### `APIConfig`
API 配置类，管理 OpenRouter API 相关配置。

**属性:**
- `base_url: str` - API 基础 URL
- `api_key: str` - API 密钥
- `model_name: str` - 模型名称
- `temperature: float` - 温度参数（默认 0.1）
- `max_tokens: int` - 最大 token 数（默认 2000）
- `timeout: int` - 超时时间（默认 30 秒）

**方法:**
```python
@classmethod
def from_env() -> APIConfig
    """从环境变量加载配置"""
```

##### `PathConfig`
路径配置类，管理项目中的所有路径。

**属性:**
- `project_root: Path` - 项目根目录
- `temp_dir: Path` - 临时文件目录
- `toc_images_dir: Path` - 图片目录
- `toc_json_dir: Path` - JSON 目录
- `schemas_dir: Path` - Schema 目录
- `prompts_dir: Path` - Prompt 目录

**方法:**
```python
def create_directories() -> None
    """创建所有必需的目录"""

def clean_temp_directories() -> None
    """清理临时目录"""
```

##### `OCRConfig`
OCR 配置类。

**属性:**
- `max_retries: int` - 最大重试次数（默认 3）
- `retry_delay: float` - 重试延迟（默认 2.0 秒）
- `image_max_size: int` - 图片最大尺寸（默认 2048）
- `image_quality: int` - 图片质量（默认 85）

##### `Config`
全局配置类，整合所有配置。

**属性:**
- `api: APIConfig`
- `paths: PathConfig`
- `ocr: OCRConfig`

#### 工具函数

```python
def get_config() -> Config
    """获取全局配置实例"""

def load_prompt(name: str) -> str
    """加载 Prompt 模板"""

def load_schema(name: str) -> dict
    """加载 JSON Schema"""
```

---

### 2. models.py - 数据模型模块

定义所有数据结构。

#### 主要类

##### `TOCEntry`
目录项数据模型。

**属性:**
- `title: str` - 标题
- `page: int` - 页码
- `level: int` - 层级（1-5）

**方法:**
```python
def to_dict() -> Dict[str, Any]
    """转换为字典"""

@classmethod
def from_dict(data: Dict) -> TOCEntry
    """从字典创建"""

def apply_offset(offset: int) -> int
    """应用页码偏置，返回 PDF 实际页码"""
```

##### `TOCPage`
单页目录数据模型。

**属性:**
- `page_number: int` - 页码
- `entries: List[TOCEntry]` - 目录项列表
- `image_path: Optional[str]` - 源图片路径

**方法:**
```python
def to_dict() -> List[Dict]
    """转换为字典列表"""

def save_to_file(file_path: str) -> None
    """保存到 JSON 文件"""

@classmethod
def load_from_file(file_path: str, page_number: int) -> TOCPage
    """从 JSON 文件加载"""
```

##### `TOCMetadata`
目录元数据。

**属性:**
- `pdf_path: str` - PDF 路径
- `page_offset: int` - 页码偏置
- `total_entries: int` - 总条目数
- `generated_at: str` - 生成时间
- `toc_page_range: Optional[str]` - 目录页范围
- `model_name: Optional[str]` - 模型名称

##### `MergedTOC`
合并后的完整目录。

**属性:**
- `metadata: TOCMetadata`
- `toc: List[TOCEntry]`

**方法:**
```python
def to_dict() -> Dict
    """转换为字典"""

def save_to_file(file_path: str) -> None
    """保存到文件"""

def get_entries_by_level(level: int) -> List[TOCEntry]
    """获取指定层级的条目"""

def validate_page_order() -> List[str]
    """验证页码顺序"""
```

---

### 3. utils/ - 工具模块

#### 3.1 pdf_extractor.py - PDF 提取模块

##### 主要函数

```python
def parse_page_range(page_range: str) -> Tuple[int, int]
    """
    解析页码范围字符串
    
    Args:
        page_range: 如 "5-12"
    Returns:
        (起始页, 结束页)
    """

def extract_single_page_to_image(
    pdf_path: str,
    page_number: int,
    output_path: str,
    dpi: int = 150,
    image_format: str = "PNG"
) -> str
    """
    提取单页为图片
    
    Returns:
        输出图片路径
    """

def extract_toc_pages_to_images(
    pdf_path: str,
    page_range: str,
    output_dir: Optional[str] = None,
    dpi: int = 150
) -> List[str]
    """
    批量提取目录页为图片
    
    Returns:
        图片路径列表
    """

def get_pdf_page_count(pdf_path: str) -> int
    """获取 PDF 总页数"""

def optimize_image_for_ocr(
    image_path: str,
    max_size: Optional[int] = None,
    quality: Optional[int] = None
) -> str
    """
    优化图片以提高 OCR 识别率
    
    Returns:
        优化后的图片路径
    """

def extract_and_optimize_toc_pages(
    pdf_path: str,
    page_range: str,
    output_dir: Optional[str] = None
) -> List[str]
    """
    提取并优化目录页（一步到位）
    
    Returns:
        优化后的图片路径列表
    """
```

#### 3.2 toc_merger.py - 目录合并模块

##### 主要函数

```python
def load_page_json_files(
    json_dir: Optional[str] = None
) -> List[TOCPage]
    """
    加载所有 page_N.json 文件
    
    Returns:
        TOCPage 对象列表（按页码排序）
    """

def merge_toc_pages(
    pages: List[TOCPage],
    pdf_path: str,
    page_offset: int,
    toc_page_range: Optional[str] = None,
    model_name: Optional[str] = None
) -> MergedTOC
    """
    合并多个单页目录
    
    Returns:
        合并后的完整目录
    """

def merge_from_directory(
    json_dir: Optional[str] = None,
    pdf_path: str = "",
    page_offset: int = 1,
    toc_page_range: Optional[str] = None,
    output_path: Optional[str] = None
) -> MergedTOC
    """
    从目录加载并合并（一步到位）
    
    Returns:
        合并后的目录对象
    """

def validate_merged_toc(merged: MergedTOC) -> Dict
    """
    验证合并后的目录
    
    Returns:
        验证结果字典，包含 is_valid, warnings, errors
    """

def print_toc_summary(merged: MergedTOC) -> None
    """打印目录摘要"""

def export_toc_to_text(merged: MergedTOC, output_path: str) -> None
    """导出为纯文本格式"""
```

#### 3.3 pdf_writer.py - PDF 写入模块

##### 主要函数

```python
def create_pdf_outline(
    merged: MergedTOC,
    apply_offset: bool = True
) -> List[Tuple[int, str, int]]
    """
    创建 PDF 大纲数据结构
    
    Returns:
        大纲列表 [(level, title, page), ...]
    """

def write_toc_to_pdf(
    pdf_path: str,
    merged: MergedTOC,
    output_path: Optional[str] = None,
    backup: bool = True
) -> str
    """
    将目录写入 PDF
    
    Returns:
        输出文件路径
    """

def get_existing_toc(pdf_path: str) -> List[Tuple]
    """获取 PDF 现有目录"""

def has_toc(pdf_path: str) -> bool
    """检查 PDF 是否已有目录"""

def validate_toc_before_write(
    pdf_path: str,
    merged: MergedTOC
) -> Dict
    """
    写入前验证
    
    Returns:
        验证结果，包含 can_write, errors, warnings
    """

def write_toc_safely(
    pdf_path: str,
    merged: MergedTOC,
    output_path: Optional[str] = None,
    force: bool = False
) -> str
    """
    安全地写入目录（带验证）
    
    Returns:
        输出文件路径
    """
```

---

### 4. agent/ - Agent 模块

#### 4.1 graph.py - LangGraph 工作流

##### OCRState (TypedDict)
LangGraph 状态定义。

**字段:**
- `image_path: str` - 图片路径
- `raw_text: Optional[str]` - 原始文本
- `structured_data: Optional[List[Dict]]` - 结构化数据
- `analysis_result: Optional[Dict]` - 分析结果
- `validation_result: Optional[Dict]` - 验证结果
- `errors: List[str]` - 错误列表
- `metadata: Dict[str, Any]` - 元数据

##### 节点函数

```python
def analyze_image_node(state: OCRState, llm_client) -> OCRState
    """节点：分析图片质量和布局"""

def extract_text_node(state: OCRState, llm_client) -> OCRState
    """节点：提取图片中的文本"""

def parse_structure_node(state: OCRState, llm_client) -> OCRState
    """节点：解析为结构化数据"""

def validate_data_node(state: OCRState, llm_client) -> OCRState
    """节点：验证数据格式"""
```

##### 工作流函数

```python
def create_ocr_workflow(llm_client) -> StateGraph
    """
    创建 OCR 工作流
    
    Returns:
        编译后的 LangGraph 工作流
    """

def create_initial_state(image_path: str) -> OCRState
    """创建初始状态"""
```

#### 4.2 ocr_agent.py - OCR Agent 实现

##### `LLMClient`
LLM 客户端封装。

**方法:**
```python
def __init__()
    """初始化客户端"""

def encode_image(image_path: str) -> str
    """编码图片为 base64"""

def analyze_image(image_path: str, prompt: str) -> str
    """分析图片（视觉）"""

def extract_text(image_path: str, prompt: str) -> str
    """提取文本"""

def complete(prompt: str) -> str
    """文本补全"""
```

##### `OCRAgent`
OCR Agent 主类。

**方法:**
```python
def __init__(llm_client: Optional[LLMClient] = None)
    """初始化 Agent"""

def process_image(image_path: str, retry: bool = True) -> OCRState
    """
    处理单张图片
    
    Returns:
        处理结果状态
    """

def process_image_to_toc_page(
    image_path: str,
    page_number: int,
    save_json: bool = True
) -> TOCPage
    """
    处理图片并转换为 TOCPage
    
    Returns:
        单页目录对象
    """
```

##### 工具函数

```python
def get_llm_client() -> LLMClient
    """获取 LLM 客户端实例"""

def process_single_image(
    image_path: str,
    page_number: int,
    agent: Optional[OCRAgent] = None
) -> TOCPage
    """处理单张图片（独立函数）"""

def process_all_images(
    image_paths: List[str],
    start_page_number: int = 1,
    parallel: bool = False
) -> List[TOCPage]
    """批量处理图片"""
```

---

### 5. main.py - 主程序

#### 主要函数

```python
def setup_environment() -> None
    """设置运行环境"""

def get_user_input() -> Tuple[str, str, int]
    """
    获取用户输入
    
    Returns:
        (pdf_path, page_range, page_offset)
    """

def step_1_extract_images(pdf_path: str, page_range: str) -> List[str]
    """步骤 1: 提取图片"""

def step_2_ocr_recognition(image_paths: List[str]) -> None
    """步骤 2: OCR 识别"""

def step_3_merge_toc(
    pdf_path: str,
    page_offset: int,
    page_range: str
) -> MergedTOC
    """步骤 3: 合并目录"""

def step_4_write_to_pdf(pdf_path: str, merged: MergedTOC) -> None
    """步骤 4: 写入 PDF"""

def main() -> None
    """主函数（交互式模式）"""

def cli() -> None
    """命令行入口"""

def run_cli_mode(
    pdf_path: str,
    page_range: str,
    page_offset: int,
    output_path: Optional[str] = None
) -> None
    """命令行模式执行"""
```

---

## 🔄 数据流

```
1. 用户输入
   ├─ PDF 路径
   ├─ 目录页范围 (7-10)
   └─ 页码偏置 (15)
   
2. PDF → 图片
   └─ utils/pdf_extractor.py
      ├─ extract_and_optimize_toc_pages()
      └─ 输出: temp/toc_images/page_*.png
   
3. 图片 → OCR
   └─ agent/ocr_agent.py
      ├─ OCRAgent.process_image()
      └─ LangGraph 工作流
         ├─ analyze_image_node
         ├─ extract_text_node
         ├─ parse_structure_node
         └─ validate_data_node
      └─ 输出: temp/toc_json/page_*.json
   
4. JSON → 合并
   └─ utils/toc_merger.py
      ├─ load_page_json_files()
      ├─ merge_toc_pages()
      └─ 输出: MergedTOC 对象
   
5. 合并目录 → PDF
   └─ utils/pdf_writer.py
      ├─ create_pdf_outline()
      ├─ write_toc_safely()
      └─ 输出: PDF with TOC
```

---

## 🎯 使用示例

### 交互式模式

```bash
python main.py
```

### 命令行模式

```bash
python main.py --pdf book.pdf --range 7-10 --offset 15
python main.py --pdf book.pdf --range 7-10 --offset 15 --output output.pdf
```

### 编程调用

```python
from config import get_config
from utils.pdf_extractor import extract_and_optimize_toc_pages
from agent.ocr_agent import OCRAgent
from utils.toc_merger import merge_from_directory
from utils.pdf_writer import write_toc_safely

# 1. 提取图片
images = extract_and_optimize_toc_pages("book.pdf", "7-10")

# 2. OCR 识别
agent = OCRAgent()
for i, img in enumerate(images, 1):
    agent.process_image_to_toc_page(img, i)

# 3. 合并
merged = merge_from_directory(
    pdf_path="book.pdf",
    page_offset=15,
    toc_page_range="7-10"
)

# 4. 写入
write_toc_safely("book.pdf", merged, force=True)
```

---

## 📊 类关系图

```
Config
├── APIConfig
├── PathConfig
└── OCRConfig

MergedTOC
├── TOCMetadata
└── List[TOCEntry]

TOCPage
└── List[TOCEntry]

OCRAgent
├── LLMClient
└── LangGraph Workflow
    └── OCRState

Main
├── utils.pdf_extractor
├── utils.toc_merger
├── utils.pdf_writer
└── agent.ocr_agent
```

---

## 🔧 扩展点

### 1. 添加新的 OCR 引擎

在 `agent/ocr_agent.py` 中创建新的 Client 类。

### 2. 自定义验证规则

在 `agent/graph.py` 的 `validate_data_node` 中添加。

### 3. 支持更多输出格式

在 `utils/toc_merger.py` 中添加导出函数。

### 4. 优化 Prompt

编辑 `prompt/` 目录下的模板文件。

---

完整架构已生成！🎉

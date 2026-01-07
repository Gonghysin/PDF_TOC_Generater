# API 文档

## 核心模块

### models.py

数据模型定义。

#### TOCEntry

目录条目。

```python
@dataclass
class TOCEntry:
    title: str      # 标题
    page: int       # 页码（书籍标注）
    level: int      # 层级（1-5）
    
    def apply_offset(self, offset: int) -> int:
        """应用页码偏置，返回 PDF 实际页码"""
        return self.page + offset - 1
```

**方法**：
- `to_dict()`: 转换为字典
- `from_dict(data)`: 从字典创建
- `apply_offset(offset)`: 计算 PDF 页码

#### TOCPage

单页目录。

```python
@dataclass
class TOCPage:
    page_number: int        # 页码
    entries: List[TOCEntry] # 目录条目列表
    
    @classmethod
    def load_from_file(cls, file_path: str, page_number: int) -> 'TOCPage':
        """从 JSON 文件加载"""
```

**方法**：
- `to_dict()`: 转换为字典
- `from_dict(data)`: 从字典创建
- `save_to_file(path)`: 保存到文件
- `load_from_file(path, page_num)`: 从文件加载

#### MergedTOC

完整目录。

```python
@dataclass
class MergedTOC:
    metadata: TOCMetadata       # 元数据
    toc: List[TOCEntry]         # 目录条目列表
```

**方法**：
- `sort_by_page()`: 按页码排序
- `get_entries_by_level(level)`: 获取指定层级条目
- `to_dict()`: 转换为字典
- `from_dict(data)`: 从字典创建
- `save_to_file(path)`: 保存到文件
- `load_from_file(path)`: 从文件加载

### utils/pdf_extractor.py

PDF 处理工具。

#### extract_and_optimize_toc_pages

提取并优化目录页。

```python
def extract_and_optimize_toc_pages(
    pdf_path: str,
    page_range: str,
    output_dir: Optional[str] = None
) -> List[str]:
    """
    提取目录页并转换为优化的图片
    
    Args:
        pdf_path: PDF 文件路径
        page_range: 页码范围，如 "5-12"
        output_dir: 输出目录（可选）
        
    Returns:
        图片路径列表
    """
```

#### get_pdf_page_count

获取 PDF 页数。

```python
def get_pdf_page_count(pdf_path: str) -> int:
    """返回 PDF 总页数"""
```

#### parse_page_range

解析页码范围。

```python
def parse_page_range(page_range: str) -> Tuple[int, int]:
    """
    解析页码范围字符串
    
    Args:
        page_range: 如 "5-12"
        
    Returns:
        (start, end) 元组
        
    Raises:
        ValueError: 格式错误
    """
```

### utils/toc_merger.py

目录合并工具。

#### load_page_json_files

加载 JSON 文件。

```python
def load_page_json_files(json_dir: Optional[str] = None) -> List[TOCPage]:
    """
    加载目录下的所有 page_N.json 文件
    
    Returns:
        TOCPage 列表，已按页码排序
    """
```

#### merge_toc_pages

合并目录页。

```python
def merge_toc_pages(
    pages: List[TOCPage],
    pdf_path: str,
    page_offset: int,
    toc_page_range: Optional[str] = None,
    model_name: Optional[str] = None
) -> MergedTOC:
    """
    合并多个单页目录为完整目录
    
    Args:
        pages: TOCPage 列表
        pdf_path: PDF 路径
        page_offset: 页码偏置
        toc_page_range: 目录页范围
        model_name: 模型名称
        
    Returns:
        MergedTOC 对象
    """
```

#### merge_from_directory

从目录合并。

```python
def merge_from_directory(
    pdf_path: str,
    page_offset: int,
    toc_page_range: str,
    json_dir: Optional[str] = None,
    output_path: Optional[str] = None,
    model_name: Optional[str] = None
) -> MergedTOC:
    """
    从目录读取 JSON 并合并
    
    自动加载、合并、验证、保存。
    """
```

#### validate_merged_toc

验证目录。

```python
def validate_merged_toc(merged: MergedTOC) -> Dict[str, Any]:
    """
    验证合并后的目录
    
    Returns:
        {
            'is_valid': bool,
            'errors': List[str],
            'warnings': List[str]
        }
    """
```

#### export_toc_to_text

导出文本格式。

```python
def export_toc_to_text(merged: MergedTOC, output_path: str) -> None:
    """导出为 toc.txt"""
```

#### import_toc_from_text_file

从文本导入。

```python
def import_toc_from_text_file(
    text_file: str,
    pdf_path: Optional[str] = None,
    page_offset: Optional[int] = None
) -> MergedTOC:
    """
    从文本文件导入目录
    
    Args:
        text_file: toc.txt 路径
        pdf_path: PDF 路径（可选）
        page_offset: 页码偏置（可选）
        
    Returns:
        MergedTOC 对象
    """
```

### utils/pdf_writer.py

PDF 写入工具。

#### create_pdf_outline

创建 PDF 大纲。

```python
def create_pdf_outline(
    merged: MergedTOC,
    apply_offset: bool = True,
    max_page: Optional[int] = None
) -> List[Tuple[int, str, int]]:
    """
    创建 PDF 大纲数据
    
    Returns:
        [(level, title, page), ...] 列表
    """
```

#### write_toc_to_pdf

写入目录到 PDF。

```python
def write_toc_to_pdf(
    pdf_path: str,
    merged: MergedTOC,
    output_path: Optional[str] = None
) -> str:
    """
    写入目录到 PDF
    
    Args:
        pdf_path: 源 PDF 路径
        merged: MergedTOC 对象
        output_path: 输出路径（可选）
        
    Returns:
        输出文件路径
    """
```

#### write_toc_safely

安全写入（带备份）。

```python
def write_toc_safely(
    pdf_path: str,
    merged: MergedTOC,
    output_path: Optional[str] = None,
    force: bool = False
) -> str:
    """
    安全写入目录，自动备份
    
    Args:
        pdf_path: 源 PDF
        merged: MergedTOC 对象
        output_path: 输出路径
        force: 强制覆盖
        
    Returns:
        输出文件路径
    """
```

#### has_toc

检查是否有目录。

```python
def has_toc(pdf_path: str) -> bool:
    """检查 PDF 是否已有目录"""
```

### agent/ocr_agent.py

OCR Agent。

#### OCRAgent

OCR 识别代理。

```python
class OCRAgent:
    def __init__(self, api_config: APIConfig):
        """初始化 Agent"""
    
    def process_image_to_toc_page(
        self,
        image_path: str,
        page_number: int
    ) -> TOCPage:
        """
        处理单张图片
        
        Args:
            image_path: 图片路径
            page_number: 页码
            
        Returns:
            TOCPage 对象
        """
```

#### process_all_images

批量处理。

```python
def process_all_images(
    image_paths: List[str],
    start_page: int = 1,
    parallel: bool = True
) -> List[TOCPage]:
    """
    处理多张图片
    
    Args:
        image_paths: 图片路径列表
        start_page: 起始页码
        parallel: 是否并行
        
    Returns:
        TOCPage 列表
    """
```

## 使用示例

### 提取 PDF 目录页

```python
from utils.pdf_extractor import extract_and_optimize_toc_pages

image_paths = extract_and_optimize_toc_pages(
    pdf_path="book.pdf",
    page_range="8-10"
)
```

### OCR 识别

```python
from agent.ocr_agent import OCRAgent, process_all_images
from config import get_config

config = get_config()
pages = process_all_images(
    image_paths=image_paths,
    start_page=8,
    parallel=True
)
```

### 合并目录

```python
from utils.toc_merger import merge_toc_pages

merged = merge_toc_pages(
    pages=pages,
    pdf_path="book.pdf",
    page_offset=11,
    toc_page_range="8-10"
)
```

### 写入 PDF

```python
from utils.pdf_writer import write_toc_safely

output_path = write_toc_safely(
    pdf_path="book.pdf",
    merged=merged,
    output_path="book_with_toc.pdf"
)
```

### 文本导入

```python
from utils.toc_merger import import_toc_from_text_file
from utils.pdf_writer import write_toc_safely

# 导入
merged = import_toc_from_text_file(
    text_file="toc.txt",
    pdf_path="book.pdf"
)

# 写入
write_toc_safely(
    pdf_path="book.pdf",
    merged=merged,
    output_path="book_with_toc.pdf"
)
```

## 错误处理

所有函数都可能抛出异常，建议使用 try-except：

```python
try:
    merged = import_toc_from_text_file("toc.txt")
except FileNotFoundError as e:
    print(f"文件不存在: {e}")
except ValueError as e:
    print(f"数据格式错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

常见异常：
- `FileNotFoundError`: 文件不存在
- `ValueError`: 参数或数据格式错误
- `RuntimeError`: 运行时错误（如 API 调用失败）

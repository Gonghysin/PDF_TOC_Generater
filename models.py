"""
数据模型模块

定义项目中使用的所有数据模型和类型。
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json


class ImageQuality(str, Enum):
    """图片质量枚举"""
    CLEAR = "clear"
    BLURRY = "blurry"
    POOR = "poor"


class LayoutType(str, Enum):
    """布局类型枚举"""
    SINGLE_COLUMN = "single_column"
    TWO_COLUMN = "two_column"
    MULTI_COLUMN = "multi_column"


class ValidationStatus(str, Enum):
    """验证状态枚举"""
    VALID = "valid"
    VALID_WITH_FIXES = "valid_with_fixes"
    INVALID = "invalid"


@dataclass
class TOCEntry:
    """
    目录项数据模型
    
    表示书籍目录中的单个条目。
    
    Attributes:
        title: 目录项标题（章节名称）
        page: 书籍中标注的页码（未加偏置）
        level: 目录层级（1=章，2=节，3=小节，等）
    """
    title: str
    page: int
    level: int
    
    def __post_init__(self):
        """验证数据的有效性"""
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title 必须是非空字符串")
        
        if not isinstance(self.page, int):
            raise ValueError("page 必须是整数")
        
        if not isinstance(self.level, int) or not (1 <= self.level <= 5):
            raise ValueError("level 必须是 1-5 之间的整数")
        
        # 清理标题
        self.title = self.title.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            dict: 字典表示
        """
        return {
            'title': self.title,
            'page': self.page,
            'level': self.level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TOCEntry':
        """
        从字典创建实例
        
        Args:
            data: 包含 title, page, level 的字典
            
        Returns:
            TOCEntry: 目录项实例
        """
        return cls(
            title=data['title'],
            page=data['page'],
            level=data['level']
        )
    
    def apply_offset(self, offset: int) -> int:
        """
        应用页码偏置，计算 PDF 实际页码
        
        Args:
            offset: 页码偏置值（书籍第1页对应PDF的第几页）
            
        Returns:
            int: PDF 实际页码
        """
        return self.page + (offset - 1)


@dataclass
class TOCPage:
    """
    单页目录数据模型
    
    表示从一页目录中识别出的所有条目。
    
    Attributes:
        page_number: 页码（在目录页中的序号，从1开始）
        entries: 该页包含的所有目录项
        image_path: 源图片路径
    """
    page_number: int
    entries: List[TOCEntry] = field(default_factory=list)
    image_path: Optional[str] = None
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """
        转换为字典列表（符合 toc_page.schema.json）
        
        Returns:
            list: 目录项字典列表
        """
        return [entry.to_dict() for entry in self.entries]
    
    @classmethod
    def from_dict(cls, page_number: int, data: List[Dict[str, Any]]) -> 'TOCPage':
        """
        从字典列表创建实例
        
        Args:
            page_number: 页码
            data: 目录项字典列表
            
        Returns:
            TOCPage: 单页目录实例
        """
        entries = [TOCEntry.from_dict(entry_data) for entry_data in data]
        return cls(page_number=page_number, entries=entries)
    
    def save_to_file(self, file_path: str) -> None:
        """
        保存到 JSON 文件
        
        Args:
            file_path: 文件路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str, page_number: int) -> 'TOCPage':
        """
        从 JSON 文件加载
        
        Args:
            file_path: 文件路径
            page_number: 页码
            
        Returns:
            TOCPage: 单页目录实例
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(page_number, data)


@dataclass
class ImageAnalysisResult:
    """
    图片分析结果数据模型
    
    存储对目录页图片的分析结果。
    
    Attributes:
        quality: 图片质量
        layout: 布局类型
        has_header: 是否有页眉
        has_footer: 是否有页脚
        has_decorations: 是否有装饰元素
        text_orientation: 文字方向
        font_size_variance: 字体大小差异
        indentation_present: 是否有缩进
        estimated_entries: 预估的目录项数量
        notes: 备注信息
    """
    quality: ImageQuality
    layout: LayoutType
    has_header: bool
    has_footer: bool
    has_decorations: bool = False
    text_orientation: str = "horizontal"
    font_size_variance: str = "medium"
    indentation_present: bool = True
    estimated_entries: int = 0
    notes: str = ""


@dataclass
class ValidationResult:
    """
    验证结果数据模型
    
    存储数据验证的结果。
    
    Attributes:
        status: 验证状态
        data: 验证后的数据
        warnings: 警告信息列表
        errors: 错误信息列表
    """
    status: ValidationStatus
    data: List[TOCEntry]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """
        判断是否验证通过
        
        Returns:
            bool: True 如果状态为 VALID 或 VALID_WITH_FIXES
        """
        return self.status in [ValidationStatus.VALID, ValidationStatus.VALID_WITH_FIXES]


@dataclass
class TOCMetadata:
    """
    目录元数据
    
    存储完整目录的元数据信息。
    
    Attributes:
        pdf_path: 原始 PDF 文件路径
        page_offset: 页码偏置值
        toc_page_range: 目录页码范围
        total_entries: 目录项总数
        generated_at: 生成时间
        model_name: 使用的 AI 模型
    """
    pdf_path: str
    page_offset: int
    total_entries: int
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    toc_page_range: Optional[str] = None
    model_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            dict: 字典表示
        """
        result = asdict(self)
        # 移除 None 值
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class MergedTOC:
    """
    合并后的完整目录数据模型
    
    包含元数据和所有目录项。
    
    Attributes:
        metadata: 元数据
        toc: 所有目录项列表
    """
    metadata: TOCMetadata
    toc: List[TOCEntry]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（符合 toc_merged.schema.json）
        
        Returns:
            dict: 字典表示
        """
        return {
            'metadata': self.metadata.to_dict(),
            'toc': [entry.to_dict() for entry in self.toc]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MergedTOC':
        """
        从字典创建实例
        
        Args:
            data: 包含 metadata 和 toc 的字典
            
        Returns:
            MergedTOC: 合并目录实例
        """
        metadata = TOCMetadata(**data['metadata'])
        toc = [TOCEntry.from_dict(entry) for entry in data['toc']]
        return cls(metadata=metadata, toc=toc)
    
    def save_to_file(self, file_path: str) -> None:
        """
        保存到 JSON 文件
        
        Args:
            file_path: 文件路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'MergedTOC':
        """
        从 JSON 文件加载
        
        Args:
            file_path: 文件路径
            
        Returns:
            MergedTOC: 合并目录实例
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_entries_by_level(self, level: int) -> List[TOCEntry]:
        """
        获取指定层级的所有目录项
        
        Args:
            level: 目录层级
            
        Returns:
            list: 该层级的目录项列表
        """
        return [entry for entry in self.toc if entry.level == level]
    
    def validate_page_order(self) -> List[str]:
        """
        验证页码顺序的合理性
        
        Returns:
            list: 警告信息列表（如果页码顺序异常）
        """
        warnings = []
        for i in range(1, len(self.toc)):
            prev_page = self.toc[i - 1].page
            curr_page = self.toc[i].page
            
            if curr_page < prev_page:
                warnings.append(
                    f"条目 {i+1} ('{self.toc[i].title}') 的页码 ({curr_page}) "
                    f"小于前一条 ({prev_page})"
                )
        
        return warnings

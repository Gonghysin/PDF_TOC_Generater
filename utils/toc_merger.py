"""
目录合并模块

负责读取和合并多个单页目录 JSON 文件。
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from models import TOCPage, TOCEntry, MergedTOC, TOCMetadata
from config import get_config

logger = logging.getLogger(__name__)


def load_page_json_files(json_dir: Optional[str] = None) -> List[TOCPage]:
    """
    加载目录下的所有 page_N.json 文件
    
    Args:
        json_dir: JSON 文件目录路径（可选，默认使用配置中的路径）
        
    Returns:
        list: TOCPage 对象列表，按页码排序
        
    Raises:
        FileNotFoundError: 如果目录不存在或没有找到任何文件
        
    Examples:
        >>> pages = load_page_json_files()
        >>> len(pages)
        4
    """
    config = get_config()
    
    if json_dir is None:
        json_dir = config.paths.toc_json_dir
    else:
        json_dir = Path(json_dir)
    
    if not json_dir.exists():
        raise FileNotFoundError(f"目录不存在: {json_dir}")
    
    # 查找所有 page_*.json 文件
    json_files = sorted(json_dir.glob('page_*.json'))
    
    if not json_files:
        raise FileNotFoundError(f"未找到任何 page_*.json 文件: {json_dir}")
    
    logger.info(f"找到 {len(json_files)} 个 JSON 文件")
    
    # 加载并解析
    pages = []
    for json_file in json_files:
        try:
            # 从文件名提取页码
            page_number = int(json_file.stem.split('_')[1])
            
            # 加载数据
            page = TOCPage.load_from_file(str(json_file), page_number)
            pages.append(page)
            
            logger.info(f"✓ 加载 {json_file.name}: {len(page.entries)} 个条目")
        
        except Exception as e:
            logger.error(f"✗ 加载文件失败 {json_file.name}: {e}")
            # 继续处理其他文件
            continue
    
    # 按页码排序
    pages.sort(key=lambda p: p.page_number)
    
    return pages


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
        pages: TOCPage 对象列表
        pdf_path: 原始 PDF 文件路径
        page_offset: 页码偏置值
        toc_page_range: 目录页码范围字符串（可选）
        model_name: 使用的 AI 模型名称（可选）
        
    Returns:
        MergedTOC: 合并后的完整目录对象
        
    Raises:
        ValueError: 如果没有提供任何页面
        
    Examples:
        >>> merged = merge_toc_pages(pages, "book.pdf", 15, "7-10")
        >>> len(merged.toc)
        45
    """
    if not pages:
        raise ValueError("没有可合并的页面数据")
    
    # 收集所有目录项
    all_entries: List[TOCEntry] = []
    filtered_count = 0
    
    for page in pages:
        for entry in page.entries:
            # 过滤掉负数页码的条目
            if entry.page >= 0:
                all_entries.append(entry)
            else:
                filtered_count += 1
                logger.warning(f"过滤掉负数页码条目: {entry.title} (page={entry.page})")
    
    if filtered_count > 0:
        logger.info(f"已过滤 {filtered_count} 个负数页码条目")
    
    # 按页码排序所有条目
    all_entries.sort(key=lambda e: e.page)
    logger.info(f"已按页码排序 {len(all_entries)} 个条目")
    
    total_entries = len(all_entries)
    
    logger.info(f"合并完成: 共 {len(pages)} 页，{total_entries} 个条目")
    
    # 创建元数据
    metadata = TOCMetadata(
        pdf_path=pdf_path,
        page_offset=page_offset,
        total_entries=total_entries,
        toc_page_range=toc_page_range,
        model_name=model_name
    )
    
    # 创建合并对象
    merged = MergedTOC(metadata=metadata, toc=all_entries)
    
    # 验证页码顺序（现在应该没有问题了）
    warnings = merged.validate_page_order()
    if warnings:
        logger.warning("发现页码顺序异常:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    return merged


def merge_from_directory(
    json_dir: Optional[str] = None,
    pdf_path: str = "",
    page_offset: int = 1,
    toc_page_range: Optional[str] = None,
    output_path: Optional[str] = None
) -> MergedTOC:
    """
    从目录加载并合并所有目录数据（一步到位）
    
    Args:
        json_dir: JSON 文件目录（可选）
        pdf_path: PDF 文件路径
        page_offset: 页码偏置
        toc_page_range: 目录页码范围（可选）
        output_path: 输出文件路径（可选，如果提供则保存）
        
    Returns:
        MergedTOC: 合并后的目录对象
        
    Examples:
        >>> merged = merge_from_directory(
        ...     pdf_path="book.pdf",
        ...     page_offset=15,
        ...     toc_page_range="7-10",
        ...     output_path="temp/toc_merged.json"
        ... )
    """
    config = get_config()
    
    # 加载所有页面
    pages = load_page_json_files(json_dir)
    
    # 获取模型名称
    model_name = config.api.model_name
    
    # 合并
    merged = merge_toc_pages(
        pages=pages,
        pdf_path=pdf_path,
        page_offset=page_offset,
        toc_page_range=toc_page_range,
        model_name=model_name
    )
    
    # 保存（如果指定了输出路径）
    if output_path:
        merged.save_to_file(output_path)
        logger.info(f"✓ 已保存合并结果到: {output_path}")
    
    return merged


def validate_merged_toc(merged: MergedTOC) -> Dict[str, Any]:
    """
    验证合并后的目录数据
    
    检查数据的完整性和一致性。
    
    Args:
        merged: 合并后的目录对象
        
    Returns:
        dict: 验证结果，包含 is_valid, warnings, errors 等字段
        
    Examples:
        >>> result = validate_merged_toc(merged)
        >>> result['is_valid']
        True
    """
    warnings = []
    errors = []
    
    # 1. 检查是否有目录项
    if not merged.toc:
        errors.append("目录为空")
    
    # 2. 检查页码顺序
    page_warnings = merged.validate_page_order()
    warnings.extend(page_warnings)
    
    # 3. 检查层级跳跃
    for i in range(1, len(merged.toc)):
        prev_level = merged.toc[i - 1].level
        curr_level = merged.toc[i].level
        
        # 层级不应该跳跃超过 1（如从 1 直接到 3）
        if curr_level > prev_level + 1:
            warnings.append(
                f"条目 {i+1} ('{merged.toc[i].title}') 的层级 ({curr_level}) "
                f"从上一条 ({prev_level}) 跳跃过大"
            )
    
    # 4. 检查页码范围
    if merged.toc:
        min_page = min(entry.page for entry in merged.toc)
        max_page = max(entry.page for entry in merged.toc)
        
        if min_page < 1:
            errors.append(f"存在无效页码: {min_page}")
        
        if max_page > 9999:
            warnings.append(f"页码过大: {max_page}")
    
    # 5. 检查重复标题
    titles = [entry.title for entry in merged.toc]
    seen = set()
    duplicates = []
    
    for title in titles:
        if title in seen:
            duplicates.append(title)
        seen.add(title)
    
    if duplicates:
        warnings.append(f"发现重复标题: {', '.join(set(duplicates))}")
    
    is_valid = len(errors) == 0
    
    return {
        'is_valid': is_valid,
        'total_entries': len(merged.toc),
        'warnings': warnings,
        'errors': errors,
        'statistics': {
            'level_1_count': len(merged.get_entries_by_level(1)),
            'level_2_count': len(merged.get_entries_by_level(2)),
            'level_3_count': len(merged.get_entries_by_level(3)),
            'level_4_count': len(merged.get_entries_by_level(4)),
            'level_5_count': len(merged.get_entries_by_level(5)),
        }
    }


def print_toc_summary(merged: MergedTOC) -> None:
    """
    打印目录摘要信息
    
    Args:
        merged: 合并后的目录对象
    """
    print("\n" + "="*60)
    print("目录摘要")
    print("="*60)
    print(f"PDF 文件: {merged.metadata.pdf_path}")
    print(f"页码偏置: {merged.metadata.page_offset}")
    print(f"总条目数: {merged.metadata.total_entries}")
    print(f"生成时间: {merged.metadata.generated_at}")
    
    if merged.metadata.model_name:
        print(f"使用模型: {merged.metadata.model_name}")
    
    print("\n层级分布:")
    for level in range(1, 6):
        count = len(merged.get_entries_by_level(level))
        if count > 0:
            print(f"  Level {level}: {count} 个条目")
    
    print("\n前 5 个条目:")
    for i, entry in enumerate(merged.toc[:5], 1):
        indent = "  " * (entry.level - 1)
        print(f"  {i}. {indent}{entry.title} ... {entry.page}")
    
    if len(merged.toc) > 5:
        print(f"  ... (还有 {len(merged.toc) - 5} 个条目)")
    
    print("="*60 + "\n")


def export_toc_to_text(merged: MergedTOC, output_path: str) -> None:
    """
    将目录导出为纯文本格式
    
    便于人工查看和校对。
    
    Args:
        merged: 合并后的目录对象
        output_path: 输出文件路径
        
    Examples:
        >>> export_toc_to_text(merged, "toc.txt")
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("PDF 目录\n")
        f.write("="*60 + "\n\n")
        f.write(f"文件: {merged.metadata.pdf_path}\n")
        f.write(f"页码偏置: {merged.metadata.page_offset}\n")
        f.write(f"总条目数: {merged.metadata.total_entries}\n\n")
        f.write("-"*60 + "\n\n")
        
        for entry in merged.toc:
            indent = "  " * (entry.level - 1)
            pdf_page = entry.apply_offset(merged.metadata.page_offset)
            f.write(f"{indent}{entry.title} ... {entry.page} (PDF: {pdf_page})\n")
    
    logger.info(f"✓ 已导出文本格式目录到: {output_path}")


def parse_toc_from_text(text_content: str) -> tuple[List[TOCEntry], Dict[str, Any]]:
    """
    从文本格式解析目录
    
    解析 export_toc_to_text() 生成的文本格式目录。
    
    Args:
        text_content: 文本内容
        
    Returns:
        tuple: (目录条目列表, 元数据字典)
        
    Raises:
        ValueError: 如果文本格式不正确
        
    Examples:
        >>> with open('toc.txt', 'r') as f:
        ...     entries, metadata = parse_toc_from_text(f.read())
    """
    import re
    
    lines = text_content.split('\n')
    entries = []
    metadata = {}
    
    # 解析元数据
    in_metadata = False
    in_toc_content = False
    
    for line in lines:
        line_stripped = line.rstrip()
        
        # 跳过标题行
        if '=' * 10 in line or line.strip() == 'PDF 目录':
            in_metadata = True
            continue
        
        # 检测到分隔线，开始解析目录内容
        if '-' * 10 in line:
            in_toc_content = True
            continue
        
        # 解析元数据
        if in_metadata and not in_toc_content:
            if line.startswith('文件:'):
                metadata['pdf_path'] = line.split(':', 1)[1].strip()
            elif line.startswith('页码偏置:'):
                metadata['page_offset'] = int(line.split(':')[1].strip())
            elif line.startswith('总条目数:'):
                metadata['total_entries'] = int(line.split(':')[1].strip())
        
        # 解析目录条目
        if in_toc_content and line_stripped:
            # 匹配格式: "  标题 ... 页码 (PDF: 实际页码)"
            # 或者: "标题 ... 页码 (PDF: 实际页码)"
            match = re.match(r'^(\s*)(.+?)\s+\.\.\.\s+(\d+)\s+\(PDF:\s+\d+\)', line_stripped)
            
            if match:
                indent = match.group(1)
                title = match.group(2).strip()
                page = int(match.group(3))
                
                # 计算层级（每2个空格为1级）
                level = len(indent) // 2 + 1
                
                # 确保层级在有效范围内
                level = max(1, min(5, level))
                
                try:
                    entry = TOCEntry(title=title, page=page, level=level)
                    entries.append(entry)
                except ValueError as e:
                    logger.warning(f"跳过无效条目: {line_stripped[:50]} - {e}")
    
    if not entries:
        raise ValueError("未能从文本中解析出任何有效的目录条目")
    
    logger.info(f"从文本解析出 {len(entries)} 个目录条目")
    
    return entries, metadata


def import_toc_from_text_file(
    text_file: str,
    pdf_path: Optional[str] = None,
    page_offset: Optional[int] = None
) -> MergedTOC:
    """
    从文本文件导入目录
    
    Args:
        text_file: 文本文件路径
        pdf_path: PDF 文件路径（如果文本中没有，则必须提供）
        page_offset: 页码偏置（如果文本中没有，则必须提供）
        
    Returns:
        MergedTOC: 合并后的目录对象
        
    Raises:
        FileNotFoundError: 如果文本文件不存在
        ValueError: 如果缺少必要的元数据
        
    Examples:
        >>> merged = import_toc_from_text_file("toc.txt")
        >>> merged = import_toc_from_text_file("toc.txt", pdf_path="book.pdf", page_offset=10)
    """
    text_path = Path(text_file)
    
    if not text_path.exists():
        raise FileNotFoundError(f"文本文件不存在: {text_file}")
    
    # 读取文件内容
    with open(text_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析目录
    entries, metadata = parse_toc_from_text(content)
    
    # 使用提供的参数或从文本中提取的元数据
    final_pdf_path = pdf_path or metadata.get('pdf_path')
    final_page_offset = page_offset if page_offset is not None else metadata.get('page_offset')
    
    if not final_pdf_path:
        raise ValueError("必须提供 pdf_path 参数或在文本文件中包含 PDF 路径信息")
    
    if final_page_offset is None:
        raise ValueError("必须提供 page_offset 参数或在文本文件中包含页码偏置信息")
    
    # 创建元数据对象
    toc_metadata = TOCMetadata(
        pdf_path=final_pdf_path,
        toc_page_range=metadata.get('toc_page_range', 'imported'),
        page_offset=final_page_offset,
        total_entries=len(entries),
        model_name="imported_from_text"
    )
    
    # 创建 MergedTOC 对象
    merged = MergedTOC(
        metadata=toc_metadata,
        toc=entries
    )
    
    logger.info(f"✓ 从文本文件导入目录: {len(entries)} 个条目")
    
    return merged

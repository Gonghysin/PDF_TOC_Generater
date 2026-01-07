"""
PDF TOC 写入模块

负责将目录数据写入 PDF 文件的元数据中。
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Tuple, Optional
import logging

from models import MergedTOC, TOCEntry

logger = logging.getLogger(__name__)


def create_pdf_outline(
    merged: MergedTOC,
    apply_offset: bool = True,
    max_page: Optional[int] = None
) -> List[Tuple[int, str, int]]:
    """
    创建 PDF 大纲数据结构
    
    将 MergedTOC 转换为 PyMuPDF 需要的大纲格式。
    
    Args:
        merged: 合并后的目录对象（条目已按页码排序）
        apply_offset: 是否应用页码偏置（默认 True）
        max_page: PDF 最大页码（可选，用于验证）
        
    Returns:
        list: 大纲列表，每个元素为 (level, title, page) 元组
        
    Examples:
        >>> outline = create_pdf_outline(merged, max_page=366)
        >>> outline[0]
        (1, '第一章 绪论', 15)
    """
    outline = []
    offset = merged.metadata.page_offset if apply_offset else 1
    filtered_count = 0
    fixed_count = 0
    
    for i, entry in enumerate(merged.toc):
        # 跳过负数页码的条目（二次保护）
        if entry.page < 0:
            filtered_count += 1
            logger.warning(f"跳过负数页码条目: {entry.title} (page={entry.page})")
            continue
        
        # 计算 PDF 实际页码
        pdf_page = entry.apply_offset(offset)
        
        # 验证应用偏移后的页码是否有效
        if pdf_page < 1:
            filtered_count += 1
            logger.warning(f"跳过无效页码条目: {entry.title} (原始page={entry.page}, 应用offset后={pdf_page})")
            continue
        
        # 验证页码是否超出 PDF 范围
        if max_page is not None and pdf_page > max_page:
            filtered_count += 1
            logger.warning(f"跳过超出范围的页码: {entry.title} (page={pdf_page}, PDF最大页={max_page})")
            continue
        
        # 修正层级以符合 PyMuPDF 要求
        level = entry.level
        if i == 0:
            # 第一个条目必须是 level 1
            if level != 1:
                logger.debug(f"修正第 1 个条目层级: {level} -> 1")
                level = 1
                fixed_count += 1
        else:
            prev_level = outline[-1][0]
            # 如果层级跳跃超过 1，修正为 prev_level + 1
            if level > prev_level + 1:
                logger.debug(f"修正层级跳跃: {entry.title[:30]} ({level} -> {prev_level + 1})")
                level = prev_level + 1
                fixed_count += 1
            # 如果层级小于 1，修正为 1
            elif level < 1:
                logger.debug(f"修正无效层级: {entry.title[:30]} ({level} -> 1)")
                level = 1
                fixed_count += 1
        
        # PyMuPDF 的大纲格式：(层级, 标题, 页码)
        outline.append((level, entry.title, pdf_page))
    
    if filtered_count > 0:
        logger.info(f"创建大纲时过滤了 {filtered_count} 个无效页码条目")
    
    if fixed_count > 0:
        logger.info(f"修正了 {fixed_count} 个层级问题")
    
    logger.info(f"创建大纲: {len(outline)} 个有效条目")
    return outline


def write_toc_to_pdf(
    pdf_path: str,
    merged: MergedTOC,
    output_path: Optional[str] = None,
    backup: bool = True
) -> str:
    """
    将目录写入 PDF 文件
    
    Args:
        pdf_path: 原始 PDF 文件路径
        merged: 合并后的目录对象
        output_path: 输出文件路径（可选，默认覆盖原文件）
        backup: 是否备份原文件（默认 True）
        
    Returns:
        str: 输出文件的路径
        
    Raises:
        FileNotFoundError: 如果 PDF 文件不存在
        ValueError: 如果目录数据为空或无效
        
    Examples:
        >>> write_toc_to_pdf("book.pdf", merged, "book_with_toc.pdf")
        'book_with_toc.pdf'
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
    
    if not merged.toc:
        raise ValueError("目录数据为空，无法写入")
    
    # 确定输出路径
    if output_path is None:
        output_path = pdf_path
    else:
        output_path = Path(output_path)
    
    # 备份原文件
    if backup and output_path == pdf_path:
        backup_path = pdf_path.with_suffix('.pdf.backup')
        import shutil
        shutil.copy2(pdf_path, backup_path)
        logger.info(f"已备份原文件到: {backup_path}")
    
    try:
        # 打开 PDF
        doc = fitz.open(str(pdf_path))
        
        # 获取 PDF 总页数
        total_pages = len(doc)
        logger.info(f"PDF 总页数: {total_pages}")
        
        # 创建大纲数据，传入总页数用于验证
        outline = create_pdf_outline(merged, max_page=total_pages)
        
        if not outline:
            raise ValueError("过滤后没有有效的目录条目")
        
        # 设置大纲
        doc.set_toc(outline)
        
        logger.info(f"✓ 已写入 {len(outline)} 个目录项")
        
        # 保存文件
        # 注意：如果覆盖原文件，必须使用 incremental=True
        if Path(output_path) == Path(pdf_path):
            # 覆盖原文件 - 使用增量保存
            doc.saveIncr()
            logger.info("使用增量保存模式（覆盖原文件）")
        else:
            # 另存为新文件 - 可以使用优化选项
            doc.save(str(output_path), garbage=4, deflate=True)
            logger.info("使用完整保存模式（新文件）")
        
        doc.close()
        
        logger.info(f"✓ 已保存到: {output_path}")
        
        return str(output_path)
    
    except Exception as e:
        logger.error(f"写入 TOC 失败: {e}")
        raise


def get_existing_toc(pdf_path: str) -> List[Tuple[int, str, int]]:
    """
    获取 PDF 现有的目录
    
    Args:
        pdf_path: PDF 文件路径
        
    Returns:
        list: 现有的目录列表，格式同 create_pdf_outline
        
    Raises:
        FileNotFoundError: 如果 PDF 文件不存在
        
    Examples:
        >>> toc = get_existing_toc("book.pdf")
        >>> len(toc)
        0  # 如果没有目录
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
    
    doc = fitz.open(str(pdf_path))
    toc = doc.get_toc()
    doc.close()
    
    return toc


def has_toc(pdf_path: str) -> bool:
    """
    检查 PDF 是否已有目录
    
    Args:
        pdf_path: PDF 文件路径
        
    Returns:
        bool: True 如果有目录，False 如果没有
        
    Examples:
        >>> has_toc("book.pdf")
        False
    """
    try:
        toc = get_existing_toc(pdf_path)
        return len(toc) > 0
    except Exception:
        return False


def compare_toc(
    pdf_path: str,
    merged: MergedTOC
) -> dict:
    """
    比较 PDF 现有目录和新目录
    
    Args:
        pdf_path: PDF 文件路径
        merged: 新的目录对象
        
    Returns:
        dict: 比较结果，包含统计信息
        
    Examples:
        >>> result = compare_toc("book.pdf", merged)
        >>> result['has_existing_toc']
        False
    """
    existing_toc = get_existing_toc(pdf_path)
    new_outline = create_pdf_outline(merged)
    
    return {
        'has_existing_toc': len(existing_toc) > 0,
        'existing_entries': len(existing_toc),
        'new_entries': len(new_outline),
        'difference': len(new_outline) - len(existing_toc)
    }


def merge_with_existing_toc(
    pdf_path: str,
    merged: MergedTOC,
    strategy: str = 'replace'
) -> List[Tuple[int, str, int]]:
    """
    将新目录与现有目录合并
    
    Args:
        pdf_path: PDF 文件路径
        merged: 新的目录对象
        strategy: 合并策略
            - 'replace': 完全替换（默认）
            - 'append': 追加到末尾
            - 'prepend': 插入到开头
            
    Returns:
        list: 合并后的目录列表
        
    Examples:
        >>> outline = merge_with_existing_toc("book.pdf", merged, 'replace')
    """
    existing_toc = get_existing_toc(pdf_path)
    new_outline = create_pdf_outline(merged)
    
    if strategy == 'replace':
        return new_outline
    elif strategy == 'append':
        return existing_toc + new_outline
    elif strategy == 'prepend':
        return new_outline + existing_toc
    else:
        raise ValueError(f"未知的合并策略: {strategy}")


def validate_toc_before_write(
    pdf_path: str,
    merged: MergedTOC
) -> dict:
    """
    写入前验证目录数据
    
    检查目录数据是否适合写入该 PDF。
    
    Args:
        pdf_path: PDF 文件路径
        merged: 目录对象
        
    Returns:
        dict: 验证结果
        
    Examples:
        >>> result = validate_toc_before_write("book.pdf", merged)
        >>> result['can_write']
        True
    """
    errors = []
    warnings = []
    
    # 检查 PDF 是否存在
    if not Path(pdf_path).exists():
        errors.append(f"PDF 文件不存在: {pdf_path}")
        return {
            'can_write': False,
            'errors': errors,
            'warnings': warnings
        }
    
    # 检查目录是否为空
    if not merged.toc:
        errors.append("目录数据为空")
    
    # 获取 PDF 页数
    try:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        doc.close()
        
        # 检查页码范围，传入总页数进行过滤
        outline = create_pdf_outline(merged, max_page=total_pages)
        
        if not outline:
            errors.append("过滤后没有有效的目录条目")
        else:
            max_page = max(item[2] for item in outline)
            min_page = min(item[2] for item in outline)
            
            # 检查是否有无效页码（虽然已经过滤，但仍做检查）
            if min_page < 1:
                errors.append(f"存在无效页码: {min_page}")
        
        # 检查是否已有目录
        if has_toc(pdf_path):
            warnings.append("PDF 已有目录，写入将覆盖现有目录")
    
    except Exception as e:
        errors.append(f"验证失败: {e}")
    
    can_write = len(errors) == 0
    
    return {
        'can_write': can_write,
        'errors': errors,
        'warnings': warnings,
        'total_entries': len(merged.toc),
        'pdf_total_pages': total_pages if 'total_pages' in locals() else 0
    }


def write_toc_safely(
    pdf_path: str,
    merged: MergedTOC,
    output_path: Optional[str] = None,
    force: bool = False
) -> str:
    """
    安全地写入目录（带验证和确认）
    
    Args:
        pdf_path: 原始 PDF 文件路径
        merged: 目录对象
        output_path: 输出文件路径（可选）
        force: 是否强制写入（忽略警告）
        
    Returns:
        str: 输出文件路径
        
    Raises:
        ValueError: 如果验证失败且未强制写入
        
    Examples:
        >>> write_toc_safely("book.pdf", merged, force=True)
        'book.pdf'
    """
    # 验证
    validation = validate_toc_before_write(pdf_path, merged)
    
    # 如果有错误，不允许写入
    if not validation['can_write']:
        error_msg = "目录验证失败:\n" + "\n".join(
            f"  - {e}" for e in validation['errors']
        )
        raise ValueError(error_msg)
    
    # 如果有警告，提示用户
    if validation['warnings'] and not force:
        warning_msg = "发现警告:\n" + "\n".join(
            f"  - {w}" for w in validation['warnings']
        )
        logger.warning(warning_msg)
        logger.warning("如需继续，请使用 force=True")
        raise ValueError("写入被中止（有警告且未强制）")
    
    # 执行写入
    return write_toc_to_pdf(pdf_path, merged, output_path, backup=True)

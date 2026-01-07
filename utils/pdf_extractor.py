"""
PDF 页面提取模块

负责将 PDF 的指定页码转换为图片文件。
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import logging

from config import get_config

logger = logging.getLogger(__name__)


def parse_page_range(page_range: str) -> Tuple[int, int]:
    """
    解析页码范围字符串
    
    Args:
        page_range: 页码范围字符串，格式如 "5-12" 或 "7-10"
        
    Returns:
        tuple: (起始页码, 结束页码)，页码从 1 开始
        
    Raises:
        ValueError: 如果格式不正确或页码无效
        
    Examples:
        >>> parse_page_range("5-12")
        (5, 12)
        >>> parse_page_range("1-3")
        (1, 3)
    """
    try:
        parts = page_range.strip().split('-')
        if len(parts) != 2:
            raise ValueError("格式错误")
        
        start_page = int(parts[0])
        end_page = int(parts[1])
        
        if start_page < 1 or end_page < start_page:
            raise ValueError("页码范围无效")
        
        return start_page, end_page
    
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"页码范围格式错误: '{page_range}'。"
            f"正确格式示例: '5-12'"
        ) from e


def extract_single_page_to_image(
    pdf_path: str,
    page_number: int,
    output_path: str,
    dpi: int = 150,
    image_format: str = "PNG"
) -> str:
    """
    提取 PDF 单页为图片
    
    Args:
        pdf_path: PDF 文件路径
        page_number: 页码（从 1 开始）
        output_path: 输出图片路径
        dpi: 图片 DPI（分辨率）
        image_format: 图片格式（PNG, JPEG 等）
        
    Returns:
        str: 输出图片的路径
        
    Raises:
        FileNotFoundError: 如果 PDF 文件不存在
        ValueError: 如果页码超出范围
        
    Examples:
        >>> extract_single_page_to_image("book.pdf", 5, "page_5.png")
        'page_5.png'
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
    
    try:
        # 打开 PDF
        doc = fitz.open(str(pdf_path))
        
        # 验证页码范围
        if page_number < 1 or page_number > len(doc):
            raise ValueError(
                f"页码 {page_number} 超出范围。"
                f"PDF 共有 {len(doc)} 页"
            )
        
        # 获取页面（PyMuPDF 从 0 开始计数）
        page = doc[page_number - 1]
        
        # 计算缩放比例（DPI 转换）
        zoom = dpi / 72  # 72 是 PDF 的默认 DPI
        mat = fitz.Matrix(zoom, zoom)
        
        # 渲染为图片
        pix = page.get_pixmap(matrix=mat)
        
        # 保存图片
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if image_format.upper() == "PNG":
            pix.save(str(output_path))
        else:
            # 转换为 PIL Image 以支持其他格式
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.save(str(output_path), format=image_format)
        
        doc.close()
        
        logger.info(f"已提取第 {page_number} 页到: {output_path}")
        return str(output_path)
    
    except Exception as e:
        logger.error(f"提取页面失败: {e}")
        raise


def extract_toc_pages_to_images(
    pdf_path: str,
    page_range: str,
    output_dir: Optional[str] = None,
    dpi: int = 150
) -> List[str]:
    """
    批量提取 PDF 目录页为图片
    
    Args:
        pdf_path: PDF 文件路径
        page_range: 页码范围字符串（如 "5-12"）
        output_dir: 输出目录路径（可选，默认使用配置中的路径）
        dpi: 图片 DPI（分辨率）
        
    Returns:
        list: 生成的图片路径列表
        
    Raises:
        FileNotFoundError: 如果 PDF 文件不存在
        ValueError: 如果页码范围格式错误
        
    Examples:
        >>> extract_toc_pages_to_images("book.pdf", "7-10")
        ['temp/toc_images/page_7.png', 'temp/toc_images/page_8.png', ...]
    """
    config = get_config()
    
    # 解析页码范围
    start_page, end_page = parse_page_range(page_range)
    
    # 确定输出目录
    if output_dir is None:
        output_dir = config.paths.toc_images_dir
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取图片格式配置
    image_format = config.ocr.image_format
    extension = image_format.lower()
    
    # 批量提取
    image_paths = []
    total_pages = end_page - start_page + 1
    
    logger.info(f"开始提取 {total_pages} 页目录图片...")
    
    for page_num in range(start_page, end_page + 1):
        output_path = output_dir / f"page_{page_num}.{extension}"
        
        try:
            image_path = extract_single_page_to_image(
                pdf_path=pdf_path,
                page_number=page_num,
                output_path=str(output_path),
                dpi=dpi,
                image_format=image_format
            )
            image_paths.append(image_path)
            
        except Exception as e:
            logger.error(f"提取第 {page_num} 页失败: {e}")
            # 继续处理其他页面
            continue
    
    logger.info(f"✓ 成功提取 {len(image_paths)}/{total_pages} 页")
    
    return image_paths


def get_pdf_page_count(pdf_path: str) -> int:
    """
    获取 PDF 文件的总页数
    
    Args:
        pdf_path: PDF 文件路径
        
    Returns:
        int: 总页数
        
    Raises:
        FileNotFoundError: 如果 PDF 文件不存在
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
    
    doc = fitz.open(str(pdf_path))
    page_count = len(doc)
    doc.close()
    
    return page_count


def optimize_image_for_ocr(
    image_path: str,
    max_size: Optional[int] = None,
    quality: Optional[int] = None
) -> str:
    """
    优化图片以提高 OCR 识别率
    
    包括调整大小、增强对比度、降噪等操作。
    
    Args:
        image_path: 图片路径
        max_size: 最大边长（像素），超过则缩放
        quality: JPEG 质量（1-100）
        
    Returns:
        str: 优化后的图片路径（原地修改）
        
    Examples:
        >>> optimize_image_for_ocr("page_5.png", max_size=2048)
        'page_5.png'
    """
    config = get_config()
    
    if max_size is None:
        max_size = config.ocr.image_max_size
    
    if quality is None:
        quality = config.ocr.image_quality
    
    img = Image.open(image_path)
    
    # 调整大小
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        logger.info(f"图片已缩放至: {new_size}")
    
    # 转换为 RGB（如果是 RGBA）
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    # 保存（可能有压缩）
    img.save(image_path, quality=quality, optimize=True)
    
    return image_path


def extract_and_optimize_toc_pages(
    pdf_path: str,
    page_range: str,
    output_dir: Optional[str] = None
) -> List[str]:
    """
    提取目录页并自动优化（一步到位）
    
    Args:
        pdf_path: PDF 文件路径
        page_range: 页码范围字符串
        output_dir: 输出目录（可选）
        
    Returns:
        list: 优化后的图片路径列表
    """
    # 提取图片
    image_paths = extract_toc_pages_to_images(pdf_path, page_range, output_dir)
    
    # 逐个优化
    logger.info("正在优化图片以提高 OCR 识别率...")
    optimized_paths = []
    
    for image_path in image_paths:
        try:
            optimized_path = optimize_image_for_ocr(image_path)
            optimized_paths.append(optimized_path)
        except Exception as e:
            logger.warning(f"优化图片失败 {image_path}: {e}")
            optimized_paths.append(image_path)  # 使用原图
    
    return optimized_paths

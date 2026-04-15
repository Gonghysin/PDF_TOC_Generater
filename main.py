
"""
PDF 目录自动添加工具 - 主程序

使用 AI Agent 自动识别 PDF 书籍的目录并写入元数据。

使用方法:
    python main.py
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from config import get_config
from models import MergedTOC
from utils.pdf_extractor import (
    extract_and_optimize_toc_pages,
    get_pdf_page_count,
    parse_page_range
)
from utils.toc_merger import (
    merge_from_directory,
    validate_merged_toc,
    print_toc_summary,
    export_toc_to_text,
    import_toc_from_text_file
)
from utils.pdf_writer import write_toc_safely, has_toc
from agent.ocr_agent import OCRAgent, process_all_images


def setup_logging() -> str:
    """
    设置日志系统，同时输出到控制台和文件
    
    Returns:
        str: 日志文件的路径
    """
    from datetime import datetime
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"toc_builder_{timestamp}.log"
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    
    return str(log_file)


logger = logging.getLogger(__name__)


def setup_environment(pdf_path: Optional[str] = None) -> None:
    """
    设置运行环境
    
    创建必需的目录结构。
    
    Args:
        pdf_path: PDF 文件路径（可选），如果提供则在 PDF 同目录创建 temp 文件夹
    """
    from config import PathConfig
    
    if pdf_path:
        # 使用 PDF 路径创建配置
        paths = PathConfig.from_pdf_path(pdf_path)
        paths.create_directories()
        logger.info(f"环境设置完成，临时文件夹: {paths.temp_dir}")
        # 更新全局配置
        config = get_config()
        config.paths = paths
    else:
        config = get_config()
        config.paths.create_directories()
        logger.info("环境设置完成")


def _sanitize_path(raw_path: str) -> str:
    """清洗用户输入的路径，去除 shell 风格的引号和转义。"""
    path = raw_path.strip()
    # 去掉外层成对引号
    if len(path) >= 2 and path[0] == path[-1] and path[0] in ('"', "'"):
        path = path[1:-1]
    # 处理常见的反斜杠转义空格（\\  ->  ）
    path = path.replace("\\ ", " ")
    return path


class _Colors:
    """CLI 颜色常量"""
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def _prompt(label: str, default: Optional[str] = None) -> str:
    """带默认值提示的输入辅助函数"""
    suffix = f" [{default}]" if default is not None else ""
    return input(f"{_Colors.CYAN}?{_Colors.RESET} {label}{suffix}: ").strip()


def _info(msg: str) -> None:
    print(f"{_Colors.CYAN}ℹ{_Colors.RESET}  {msg}")


def _ok(msg: str) -> None:
    print(f"{_Colors.GREEN}✓{_Colors.RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"{_Colors.YELLOW}⚠{_Colors.RESET}  {msg}")


def _err(msg: str) -> None:
    print(f"{_Colors.RED}✗{_Colors.RESET}  {msg}")


def _section(title: str) -> None:
    print(f"\n{_Colors.BOLD}{title}{_Colors.RESET}\n" + "-" * 40)


def get_user_input() -> tuple:
    """
    获取用户输入

    交互式获取 PDF 路径、目录页码范围、页码偏置等信息。

    Returns:
        tuple: (pdf_path, page_range, page_offset) 或 ('txt', txt_path, pdf_path)
    """
    print("\n" + "=" * 60)
    print(f"{_Colors.BOLD}PDF 目录自动添加工具{_Colors.RESET}")
    print("=" * 60 + "\n")

    print("请选择模式:")
    print("  1. OCR 识别模式（从 PDF 自动识别目录）")
    print("  2. 文本导入模式（从 toc.txt 文件导入）")

    while True:
        mode = _prompt("请选择模式 (1/2)", default="1")
        if mode in ['1', '2']:
            break
        _err("请输入 1 或 2")

    if mode == '2':
        # 文本导入模式
        return get_text_import_input()

    # OCR 识别模式
    _section("OCR 识别模式")

    # 获取 PDF 路径
    while True:
        pdf_path = _sanitize_path(_prompt("请输入 PDF 文件路径"))

        if not pdf_path:
            _err("路径不能为空")
            continue

        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            _err(f"文件不存在: {pdf_path}")
            continue

        if pdf_path_obj.suffix.lower() != '.pdf':
            _err("不是 PDF 文件")
            continue

        break

    # 显示 PDF 信息
    try:
        total_pages = get_pdf_page_count(pdf_path)
        _ok(f"PDF 总页数: {total_pages}")

        if has_toc(pdf_path):
            _warn("该 PDF 已有目录，写入将覆盖现有目录")
    except Exception as e:
        _warn(f"无法读取 PDF 信息: {e}")

    # 获取目录页码范围
    while True:
        page_range = _prompt("请输入目录页码范围 (例如 5-12)")

        try:
            start, end = parse_page_range(page_range)
            _ok(f"将提取第 {start}-{end} 页，共 {end - start + 1} 页")
            break
        except ValueError as e:
            _err(str(e))

    # 获取页码偏置（默认：目录范围最后一页的下一页）
    default_offset = str(end + 1)
    while True:
        offset_input = _prompt("请输入页码偏置 (书籍第1页是PDF的第几页)", default=default_offset)
        value = offset_input if offset_input else default_offset

        try:
            page_offset = int(value)
            if page_offset < 1:
                _err("偏置值必须 >= 1")
                continue
            _ok(f"页码偏置: {page_offset}")
            break
        except ValueError:
            _err("请输入有效的数字")

    return pdf_path, page_range, page_offset


def get_text_import_input() -> tuple:
    """
    获取文本导入模式的用户输入

    Returns:
        tuple: ('txt', txt_path, pdf_path)
    """
    _section("文本导入模式")

    # 获取文本文件路径
    while True:
        txt_path = _sanitize_path(_prompt("请输入 toc.txt 文件路径"))

        if not txt_path:
            _err("路径不能为空")
            continue

        txt_path_obj = Path(txt_path)
        if not txt_path_obj.exists():
            _err(f"文件不存在: {txt_path}")
            continue

        if txt_path_obj.suffix.lower() != '.txt':
            _err("不是文本文件")
            continue

        break

    # 获取目标 PDF 路径
    while True:
        pdf_path = _sanitize_path(_prompt("请输入目标 PDF 文件路径"))

        if not pdf_path:
            _err("路径不能为空")
            continue

        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            _err(f"文件不存在: {pdf_path}")
            continue

        if pdf_path_obj.suffix.lower() != '.pdf':
            _err("不是 PDF 文件")
            continue

        break

    # 显示 PDF 信息
    try:
        total_pages = get_pdf_page_count(pdf_path)
        _ok(f"PDF 总页数: {total_pages}")

        if has_toc(pdf_path):
            _warn("该 PDF 已有目录，写入将覆盖现有目录")
    except Exception as e:
        _warn(f"无法读取 PDF 信息: {e}")

    return 'txt', txt_path, pdf_path


def step_1_extract_images(pdf_path: str, page_range: str) -> list:
    """
    步骤 1: 提取目录页为图片

    Args:
        pdf_path: PDF 文件路径
        page_range: 页码范围

    Returns:
        list: 图片路径列表
    """
    _section("步骤 1/4: 提取目录页为图片")

    try:
        image_paths = extract_and_optimize_toc_pages(pdf_path, page_range)
        _ok(f"成功提取 {len(image_paths)} 张图片")
        return image_paths

    except Exception as e:
        logger.error(f"提取图片失败: {e}")
        _err(f"提取图片失败: {e}")
        sys.exit(1)


def step_2_ocr_recognition(image_paths: list, parallel: bool = True) -> None:
    """
    步骤 2: OCR 识别

    Args:
        image_paths: 图片路径列表
        parallel: 是否并行处理（默认 True）
    """
    _section("步骤 2/4: OCR 识别目录内容")
    if parallel:
        _info("使用并行模式，同时处理多页...")

    try:
        from agent.ocr_agent import process_all_images
        from pathlib import Path

        # 提取起始页码
        start_page = int(Path(image_paths[0]).stem.split('_')[1])

        # 处理所有图片（支持并行）
        total = len(image_paths)
        print(f"\n开始识别 {total} 页...")

        if parallel:
            # 并行处理
            import asyncio

            async def process_async():
                from agent.ocr_agent import OCRAgent
                agent = OCRAgent()
                return await _process_images_parallel(agent, image_paths, start_page)

            # 运行异步任务
            results = asyncio.run(process_async())
        else:
            # 顺序处理
            results = process_all_images(
                image_paths=image_paths,
                start_page_number=start_page,
                parallel=False
            )

        # 统计结果
        success_count = sum(1 for r in results if r.entries)
        _ok(f"识别完成: {success_count}/{total} 页成功")

        if success_count < total:
            _warn(f"{total - success_count} 页识别失败或为空")

    except Exception as e:
        logger.error(f"OCR 识别失败: {e}")
        _err(f"OCR 识别失败: {e}")
        sys.exit(1)


async def _process_images_parallel(agent, image_paths: list, start_page_number: int):
    """
    并行处理图片的异步函数
    
    Args:
        agent: OCR Agent 实例
        image_paths: 图片路径列表
        start_page_number: 起始页码
        
    Returns:
        list: TOCPage 对象列表
    """
    import asyncio
    from pathlib import Path
    
    async def process_one(image_path: str, page_number: int):
        """异步处理单张图片"""
        try:
            print(f"  正在处理第 {page_number} 页...")
            result = await asyncio.to_thread(
                agent.process_image_to_toc_page,
                image_path,
                page_number
            )
            print(f"  ✓ 第 {page_number} 页完成 ({len(result.entries)} 个条目)")
            return result
        except Exception as e:
            logger.error(f"处理失败 (页 {page_number}): {e}")
            print(f"  ✗ 第 {page_number} 页失败: {e}")
            from models import TOCPage
            return TOCPage(page_number=page_number, entries=[])
    
    # 创建任务
    tasks = [
        process_one(image_path, start_page_number + i)
        for i, image_path in enumerate(image_paths)
    ]
    
    # 并行执行
    results = await asyncio.gather(*tasks)
    
    return results


def step_3_merge_toc(
    pdf_path: str,
    page_offset: int,
    page_range: str
):
    """
    步骤 3: 合并目录数据

    Args:
        pdf_path: PDF 文件路径
        page_offset: 页码偏置
        page_range: 页码范围

    Returns:
        MergedTOC: 合并后的目录对象
    """
    _section("步骤 3/4: 合并目录数据")

    try:
        config = get_config()
        output_path = config.paths.temp_dir / 'toc_merged.json'

        merged = merge_from_directory(
            pdf_path=pdf_path,
            page_offset=page_offset,
            toc_page_range=page_range,
            output_path=str(output_path)
        )

        _ok(f"目录合并完成: {len(merged.toc)} 个条目")

        # 验证
        validation = validate_merged_toc(merged)

        if validation['warnings']:
            _warn("发现以下警告:")
            for warning in validation['warnings'][:5]:  # 只显示前5个
                print(f"  - {warning}")
            if len(validation['warnings']) > 5:
                print(f"  ... 还有 {len(validation['warnings']) - 5} 个警告")

        if not validation['is_valid']:
            _err("目录验证失败:")
            for error in validation['errors']:
                print(f"  - {error}")
            sys.exit(1)

        # 显示摘要
        print_toc_summary(merged)

        # 导出文本格式
        text_path = config.paths.temp_dir / 'toc.txt'
        export_toc_to_text(merged, str(text_path))
        _ok(f"已导出文本格式: {text_path}")

        return merged, str(text_path)

    except Exception as e:
        logger.error(f"合并目录失败: {e}")
        _err(f"合并目录失败: {e}")
        sys.exit(1)


def _open_editor(file_path: str) -> bool:
    """优先尝试用 code 打开，失败则回退系统默认编辑器。返回是否成功。"""
    import shutil
    import subprocess
    import platform

    # 优先尝试 VS Code
    code_cmd = shutil.which("code")
    if code_cmd:
        try:
            subprocess.run([code_cmd, file_path], check=True)
            return True
        except Exception:
            pass

    # 回退到系统默认编辑器
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", "-t", file_path])
        elif system == "Windows":
            subprocess.run(["notepad", file_path])
        else:
            for editor in ["xdg-open", "gedit", "nano", "vim"]:
                if shutil.which(editor):
                    subprocess.run([editor, file_path])
                    break
        return True
    except Exception as e:
        logger.warning(f"无法自动打开编辑器: {e}")
        return False


def review_toc_file(toc_txt_path: str, pdf_path: str) -> 'MergedTOC':
    """
    让用户审核并编辑 toc.txt 文件

    Args:
        toc_txt_path: toc.txt 文件路径
        pdf_path: PDF 文件路径

    Returns:
        MergedTOC: 用户审核后的目录对象
    """
    _section("步骤 3.5: 审核目录文件")
    _info(f"请审核并编辑目录文件: {toc_txt_path}")
    print("\n提示:")
    print("  1. 即将打开文本编辑器，请检查并修改目录内容")
    print("  2. 确认无误后，保存并关闭编辑器")
    print("  3. 返回终端确认")

    input("\n按 Enter 键打开编辑器...")

    if not _open_editor(toc_txt_path):
        _warn(f"无法自动打开编辑器，请手动打开文件: {toc_txt_path}")

    # 等待用户确认（默认 ok）
    while True:
        confirm = _prompt("审核完成后，请输入 ok 确认，或输入 cancel 取消", default="ok").lower()
        confirm = confirm if confirm else "ok"

        if confirm == 'cancel':
            print("已取消")
            sys.exit(0)

        if confirm == 'ok':
            break

        _err("请输入 'ok' 或 'cancel'")

    # 重新加载编辑后的文件
    print("\n正在加载审核后的目录文件...")
    try:
        merged = import_toc_from_text_file(toc_txt_path, pdf_path=pdf_path)
        _ok(f"加载成功: {len(merged.toc)} 个条目")

        # 显示更新后的摘要
        print_toc_summary(merged)

        return merged

    except Exception as e:
        logger.error(f"加载审核后的文件失败: {e}")
        _err(f"加载失败: {e}")
        print("请检查文件格式是否正确")
        sys.exit(1)



def step_4_write_to_pdf(pdf_path: str, merged) -> None:
    """
    步骤 4: 写入 PDF

    Args:
        pdf_path: PDF 文件路径
        merged: 合并后的目录对象
    """
    _section("步骤 4/4: 写入目录到 PDF")

    # 询问输出方式
    print("\n选择输出方式:")
    print("  1. 覆盖原文件（会自动备份）")
    print("  2. 另存为新文件")

    choice = _prompt("请选择 (1/2)", default="1")
    choice = choice if choice else "1"

    output_path = None
    if choice == '2':
        output_path = _prompt("请输入新文件路径")
        if not output_path:
            _err("路径不能为空")
            sys.exit(1)

    try:
        result_path = write_toc_safely(
            pdf_path=pdf_path,
            merged=merged,
            output_path=output_path,
            force=True
        )

        _ok(f"目录已成功写入: {result_path}")

        if output_path is None:
            backup_path = Path(pdf_path).with_suffix('.pdf.backup')
            _ok(f"原文件已备份: {backup_path}")

    except Exception as e:
        logger.error(f"写入 PDF 失败: {e}")
        _err(f"写入 PDF 失败: {e}")
        sys.exit(1)


def main() -> None:
    """
    主函数

    执行完整的 PDF 目录添加流程。
    """
    try:
        # 获取用户输入
        user_input = get_user_input()

        # 检查是文本导入模式还是 OCR 模式
        if user_input[0] == 'txt':
            # 文本导入模式
            _, txt_path, pdf_path = user_input

            # 设置环境（使用 PDF 路径）
            setup_environment(pdf_path)
            
            # 确认执行
            print("\n" + "="*60)
            print("配置信息:")
            print(f"  文本文件: {txt_path}")
            print(f"  目标 PDF: {pdf_path}")
            print("="*60)

            confirm = _prompt("确认导入并写入? (Y/n)", default="Y").lower()
            confirm = confirm if confirm else "y"
            if confirm != 'y':
                print("已取消")
                sys.exit(0)

            # 导入并写入
            print("\n正在解析文本文件...")
            merged = import_toc_from_text_file(txt_path, pdf_path=pdf_path)

            print_toc_summary(merged)

            step_4_write_to_pdf(pdf_path, merged)

        else:
            # OCR 识别模式
            pdf_path, page_range, page_offset = user_input

            # 设置环境（使用 PDF 路径）
            setup_environment(pdf_path)

            # 确认执行
            print("\n" + "="*60)
            print("配置信息:")
            print(f"  PDF 文件: {pdf_path}")
            print(f"  目录页范围: {page_range}")
            print(f"  页码偏置: {page_offset}")
            print("="*60)

            confirm = _prompt("确认开始处理? (Y/n)", default="Y").lower()
            confirm = confirm if confirm else "y"
            if confirm != 'y':
                print("已取消")
                sys.exit(0)
            
            # 执行流程
            print("\n开始处理...\n")

            # Step 1: 提取图片
            image_paths = step_1_extract_images(pdf_path, page_range)

            # Step 2: OCR 识别（并行）
            step_2_ocr_recognition(image_paths, parallel=True)

            # Step 3: 合并目录
            merged, toc_txt_path = step_3_merge_toc(pdf_path, page_offset, page_range)

            # Step 3.5: 用户审核 toc.txt
            merged = review_toc_file(toc_txt_path, pdf_path)

            # Step 4: 写入 PDF
            step_4_write_to_pdf(pdf_path, merged)
        
        print("\n" + "="*60)
        _ok("所有步骤完成！")
        print("="*60 + "\n")

    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)

    except Exception as e:
        logger.exception("程序执行失败")
        _err(f"程序执行失败: {e}")
        sys.exit(1)


def cli() -> None:
    """
    命令行入口
    
    支持命令行参数（可选）。
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='PDF 目录自动添加工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  交互式模式:
    python main.py
  
  命令行模式:
    python main.py --pdf book.pdf --range 7-10 --offset 15
    python main.py --pdf book.pdf --range 7-10 --offset 15 --output book_with_toc.pdf
        """
    )
    
    parser.add_argument(
        '--pdf',
        type=str,
        help='PDF 文件路径'
    )
    
    parser.add_argument(
        '--range',
        type=str,
        help='目录页码范围 (例如: 5-12)'
    )
    
    parser.add_argument(
        '--offset',
        type=int,
        help='页码偏置值'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='输出文件路径（可选）'
    )
    
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='禁用并行处理（默认启用）'
    )
    
    parser.add_argument(
        '--clean',
        action='store_true',
        help='清理临时文件后退出'
    )
    
    parser.add_argument(
        '--from-txt',
        type=str,
        metavar='TXT_FILE',
        help='从文本文件导入目录并写入 PDF（需同时提供 --pdf 和 --output）'
    )
    
    args = parser.parse_args()
    
    # 初始化日志系统
    log_file = setup_logging()
    print(f"日志文件: {log_file}\n")
    
    # 清理模式
    if args.clean:
        config = get_config()
        config.paths.clean_temp_directories()
        _ok("临时文件已清理")
        sys.exit(0)

    # 从文本文件导入模式
    if args.from_txt:
        if not args.pdf:
            _err("使用 --from-txt 时必须提供 --pdf 参数")
            sys.exit(1)
        run_import_mode(args.from_txt, args.pdf, args.output)
        sys.exit(0)
    
    # 如果提供了所有参数，使用命令行模式
    if all([args.pdf, args.range, args.offset]):
        run_cli_mode(args.pdf, args.range, args.offset, args.output, not args.no_parallel)
    else:
        # 否则使用交互式模式
        main()


def run_cli_mode(
    pdf_path: str,
    page_range: str,
    page_offset: int,
    output_path: Optional[str] = None,
    parallel: bool = True
) -> None:
    """
    命令行模式

    Args:
        pdf_path: PDF 文件路径
        page_range: 页码范围
        page_offset: 页码偏置
        output_path: 输出文件路径（可选）
        parallel: 是否并行处理（默认 True）
    """
    try:
        setup_environment(pdf_path)

        print(f"处理 PDF: {pdf_path}")
        print(f"目录范围: {page_range}")
        print(f"页码偏置: {page_offset}")
        print(f"并行处理: {'是' if parallel else '否'}")

        # 执行流程
        image_paths = step_1_extract_images(pdf_path, page_range)
        step_2_ocr_recognition(image_paths, parallel=parallel)
        merged, toc_txt_path = step_3_merge_toc(pdf_path, page_offset, page_range)

        # 用户审核
        merged = review_toc_file(toc_txt_path, pdf_path)

        # 写入
        result_path = write_toc_safely(
            pdf_path=pdf_path,
            merged=merged,
            output_path=output_path,
            force=True
        )

        print(f"\n{_Colors.GREEN}✓{_Colors.RESET} 完成: {result_path}")

    except Exception as e:
        logger.exception("命令行模式执行失败")
        _err(f"失败: {e}")
        sys.exit(1)


def run_import_mode(
    txt_path: str,
    pdf_path: str,
    output_path: Optional[str] = None
) -> None:
    """
    从文本文件导入模式

    Args:
        txt_path: 文本文件路径
        pdf_path: 目标 PDF 文件路径
        output_path: 输出文件路径（可选）
    """
    try:
        setup_environment(pdf_path)

        print("="*60)
        print("从文本文件导入目录")
        print("="*60)
        print(f"文本文件: {txt_path}")
        print(f"PDF 文件: {pdf_path}")
        if output_path:
            print(f"输出文件: {output_path}")
        print()

        # 导入目录
        print("正在解析文本文件...")
        merged = import_toc_from_text_file(txt_path, pdf_path=pdf_path)

        # 显示摘要
        print_toc_summary(merged)

        # 写入 PDF
        print("\n正在写入 PDF...")
        result_path = write_toc_safely(
            pdf_path=pdf_path,
            merged=merged,
            output_path=output_path,
            force=True
        )

        print(f"\n{_Colors.GREEN}✓{_Colors.RESET} 完成: {result_path}")

    except Exception as e:
        logger.exception("导入模式执行失败")
        _err(f"失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()

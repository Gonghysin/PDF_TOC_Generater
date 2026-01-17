"""
PDF TOC Generator - Web API

基于 FastAPI 的 RESTful API 服务，为前端提供 PDF 目录处理接口。
"""

import os
import sys
import json
import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 导入项目模块
from database import DatabaseManager
from config import get_config, PathConfig
from models import MergedTOC, TOCEntry, TOCMetadata
from utils.pdf_extractor import (
    extract_and_optimize_toc_pages,
    get_pdf_page_count,
    parse_page_range
)
from utils.toc_merger import (
    merge_from_directory,
    validate_merged_toc,
    export_toc_to_text,
    import_toc_from_text_file
)
from utils.pdf_writer import write_toc_safely, has_toc
from agent.ocr_agent import OCRAgent


# 初始化数据库管理器
db_manager = DatabaseManager("data/tasks.db")


# 初始化 FastAPI 应用
app = FastAPI(
    title="PDF TOC Generator API",
    description="基于 AI 的 PDF 目录自动识别与添加工具",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 任务状态存储（生产环境应使用 Redis 或数据库）
tasks_storage: Dict[str, Dict[str, Any]] = {}

# 上传文件存储目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ======================== Pydantic 模型 ========================

class OCRRequest(BaseModel):
    """OCR 识别请求模型"""
    pdf_path: str
    page_range: str
    page_offset: int
    parallel: bool = True


class TextImportRequest(BaseModel):
    """文本导入请求模型"""
    txt_content: str
    pdf_path: str


class TOCEditRequest(BaseModel):
    """目录编辑请求模型"""
    task_id: str
    toc_text: str


class StructuredTOCEntry(BaseModel):
    """结构化 TOC 条目模型"""
    title: str
    level: int  # 1-5
    book_page: int  # 书籍页码
    order_index: Optional[int] = None  # 排序索引（可选，自动生成）


class StructuredTOCUpdateRequest(BaseModel):
    """结构化 TOC 更新请求模型"""
    task_id: str
    entries: List[StructuredTOCEntry]
    page_offset: int  # 用于计算 PDF 页码


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PDFInfoResponse(BaseModel):
    """PDF 信息响应模型"""
    total_pages: int
    has_toc: bool
    file_size: int
    filename: str


# ======================== API 路由 ========================

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "PDF TOC Generator API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    上传 PDF 文件

    Returns:
        {
            "file_id": str,
            "filename": str,
            "path": str,
            "size": int
        }
    """
    try:
        # 验证文件类型
        if not file.filename or not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只支持 PDF 文件")

        # 生成唯一文件 ID
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"

        # 保存文件
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)

        logger.info(f"文件上传成功: {file.filename} -> {file_path}")

        return {
            "file_id": file_id,
            "filename": file.filename,
            "path": str(file_path),
            "size": len(content)
        }

    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@app.get("/api/pdf/info")
async def get_pdf_info(pdf_path: str):
    """
    获取 PDF 文件信息

    Args:
        pdf_path: PDF 文件路径

    Returns:
        PDFInfoResponse
    """
    try:
        path_obj = Path(pdf_path)

        if not path_obj.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        total_pages = get_pdf_page_count(pdf_path)
        has_existing_toc = has_toc(pdf_path)
        file_size = path_obj.stat().st_size

        return PDFInfoResponse(
            total_pages=total_pages,
            has_toc=has_existing_toc,
            file_size=file_size,
            filename=path_obj.name
        )

    except Exception as e:
        logger.error(f"获取 PDF 信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取 PDF 信息失败: {str(e)}")


@app.post("/api/ocr/start")
async def start_ocr_task(
    background_tasks: BackgroundTasks,
    pdf_path: str = Form(...),
    page_range: str = Form(...),
    page_offset: int = Form(...),
    parallel: bool = Form(True)
):
    """
    启动 OCR 识别任务

    Args:
        pdf_path: PDF 文件路径
        page_range: 页码范围（例如: "5-12"）
        page_offset: 页码偏置值
        parallel: 是否并行处理

    Returns:
        {
            "task_id": str,
            "status": str,
            "message": str
        }
    """
    try:
        # 验证参数
        parse_page_range(page_range)  # 验证页码范围格式

        # 生成任务 ID
        task_id = str(uuid.uuid4())

        # 初始化任务状态（内存）
        tasks_storage[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "任务已创建",
            "created_at": datetime.now().isoformat(),
            "pdf_path": pdf_path,
            "page_range": page_range,
            "page_offset": page_offset
        }

        # 同时保存到数据库
        db_manager.create_task({
            "task_id": task_id,
            "pdf_path": pdf_path,
            "pdf_filename": Path(pdf_path).name,
            "page_offset": page_offset,
            "page_range": page_range,
            "status": "pending",
            "progress": 0
        })

        # 在后台执行 OCR 任务
        background_tasks.add_task(
            run_ocr_task,
            task_id=task_id,
            pdf_path=pdf_path,
            page_range=page_range,
            page_offset=page_offset,
            parallel=parallel
        )

        logger.info(f"OCR 任务已创建: {task_id}")

        return {
            "task_id": task_id,
            "status": "pending",
            "message": "任务已创建，正在处理中"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建 OCR 任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@app.get("/api/task/status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态

    Args:
        task_id: 任务 ID

    Returns:
        TaskStatusResponse
    """
    # 优先从数据库读取
    task_db = db_manager.get_task(task_id)

    if task_db:
        # 从数据库获取任务信息
        task_data = {
            "task_id": task_db["task_id"],
            "status": task_db["status"],
            "progress": task_db["progress"],
            "message": task_db.get("error_message") or "处理中...",
        }

        # 如果内存中有结果，添加结果信息
        if task_id in tasks_storage and tasks_storage[task_id].get("result"):
            task_data["result"] = tasks_storage[task_id]["result"]

        return TaskStatusResponse(**task_data, error=task_db.get("error_message"))

    # 回退到内存存储
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks_storage[task_id]

    return TaskStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        result=task.get("result"),
        error=task.get("error")
    )


@app.post("/api/toc/edit")
async def edit_toc(request: TOCEditRequest):
    """
    编辑并更新目录

    Args:
        request: 包含 task_id 和编辑后的 toc_text

    Returns:
        {
            "success": bool,
            "message": str,
            "toc_preview": dict
        }
    """
    try:
        if request.task_id not in tasks_storage:
            raise HTTPException(status_code=404, detail="任务不存在")

        task = tasks_storage[request.task_id]
        pdf_path = task["pdf_path"]

        # 保存编辑后的文本到临时文件
        config = get_config()
        paths = PathConfig.from_pdf_path(pdf_path)
        toc_txt_path = paths.temp_dir / 'toc_edited.txt'

        with open(toc_txt_path, 'w', encoding='utf-8') as f:
            f.write(request.toc_text)

        # 重新解析目录
        merged = import_toc_from_text_file(str(toc_txt_path), pdf_path=pdf_path)

        # 更新任务结果
        task["result"]["merged_toc"] = merged.to_dict()
        task["result"]["toc_text"] = request.toc_text

        logger.info(f"目录编辑成功: {request.task_id}")

        return {
            "success": True,
            "message": f"目录已更新，共 {len(merged.toc)} 个条目",
            "toc_preview": {
                "total_entries": len(merged.toc),
                "entries": [entry.to_dict() for entry in merged.toc[:10]]  # 预览前 10 条
            }
        }

    except Exception as e:
        logger.error(f"编辑目录失败: {e}")
        raise HTTPException(status_code=500, detail=f"编辑失败: {str(e)}")


@app.post("/api/toc/update-structured")
async def update_structured_toc(request: StructuredTOCUpdateRequest):
    """
    更新结构化 TOC 条目

    Args:
        request: 包含 task_id, entries 和 page_offset

    Returns:
        {
            "success": bool,
            "message": str,
            "entries": List[dict],
            "toc_text": str
        }
    """
    try:
        # 验证任务存在
        task = db_manager.get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 转换为 TOCEntry 对象列表
        toc_entries = []
        invalid_entries = []

        for entry_data in request.entries:
            # 计算 PDF 页码：pdf_page = book_page + (page_offset - 1)
            # 注意：书籍页码可以是负数（摘要、前言等），但PDF页码必须≥1
            pdf_page = entry_data.book_page + (request.page_offset - 1)

            if pdf_page < 1:
                invalid_entries.append({
                    "title": entry_data.title,
                    "book_page": entry_data.book_page,
                    "pdf_page": pdf_page
                })
                logger.warning(f"跳过无效条目: {entry_data.title} (书籍页码={entry_data.book_page}, PDF页码={pdf_page})")
                continue

            toc_entry = TOCEntry(
                title=entry_data.title,
                page=pdf_page,  # 存储 PDF 页码
                level=entry_data.level
            )
            toc_entries.append(toc_entry)

        # 如果所有条目都无效，返回错误
        if not toc_entries:
            raise HTTPException(
                status_code=400,
                detail=f"所有条目的PDF页码都小于1，请检查页码偏置设置（当前偏置={request.page_offset}）"
            )

        # 如果有部分无效条目，记录警告
        if invalid_entries:
            logger.warning(f"跳过了 {len(invalid_entries)} 个PDF页码<1的条目")

        # 保存到数据库
        db_manager.save_toc_entries(request.task_id, toc_entries)

        # 更新任务的 page_offset
        db_manager.update_task(request.task_id, {
            "page_offset": request.page_offset
        })

        # 生成文本格式
        from utils.toc_merger import export_toc_to_text
        merged = MergedTOC(
            toc=toc_entries,
            metadata=TOCMetadata(
                pdf_path=task['pdf_path'],
                page_offset=request.page_offset,
                total_entries=len(toc_entries)
            )
        )

        # 导出到临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            export_toc_to_text(merged, f.name)
            with open(f.name, 'r', encoding='utf-8') as rf:
                toc_text = rf.read()
        os.remove(f.name)

        # 如果内存中有任务，同步更新
        if request.task_id in tasks_storage:
            tasks_storage[request.task_id]["result"] = {
                "merged_toc": merged.to_dict(),
                "toc_text": toc_text,
                "total_entries": len(toc_entries)
            }

        logger.info(f"结构化 TOC 已更新: {request.task_id}, {len(toc_entries)} 个条目")

        # 返回更新后的条目（包含书籍页码和 PDF 页码）
        entries_response = [
            {
                "title": entry.title,
                "level": entry.level,
                "book_page": request.entries[i].book_page,
                "pdf_page": entry.page,
                "order_index": i
            }
            for i, entry in enumerate(toc_entries)
        ]

        return {
            "success": True,
            "message": f"TOC 已更新，共 {len(toc_entries)} 个条目",
            "entries": entries_response,
            "toc_text": toc_text
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新结构化 TOC 失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@app.post("/api/toc/write")
async def write_toc_to_pdf(
    task_id: str = Form(...),
    output_filename: Optional[str] = Form(None)
):
    """
    将目录写入 PDF

    Args:
        task_id: 任务 ID
        output_filename: 输出文件名（可选）

    Returns:
        {
            "success": bool,
            "output_path": str,
            "download_url": str
        }
    """
    try:
        if task_id not in tasks_storage:
            raise HTTPException(status_code=404, detail="任务不存在")

        task = tasks_storage[task_id]

        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="任务尚未完成")

        pdf_path = task["pdf_path"]
        merged_dict = task["result"]["merged_toc"]
        merged = MergedTOC.from_dict(merged_dict)

        # 确定输出路径
        if output_filename:
            output_path = UPLOAD_DIR / output_filename
        else:
            pdf_name = Path(pdf_path).stem
            output_path = UPLOAD_DIR / f"{pdf_name}_with_toc.pdf"

        # 写入 PDF
        result_path = write_toc_safely(
            pdf_path=pdf_path,
            merged=merged,
            output_path=str(output_path),
            force=True
        )

        logger.info(f"目录已写入 PDF: {result_path}")

        return {
            "success": True,
            "output_path": result_path,
            "download_url": f"/api/download/{Path(result_path).name}"
        }

    except Exception as e:
        logger.error(f"写入 PDF 失败: {e}")
        raise HTTPException(status_code=500, detail=f"写入失败: {str(e)}")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    下载文件

    Args:
        filename: 文件名

    Returns:
        FileResponse
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/pdf'
    )


# ======================== 任务历史 API ========================

@app.get("/api/tasks")
async def list_tasks(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """
    获取任务列表（分页）

    Args:
        status: 状态过滤（可选）: pending, processing, completed, failed
        page: 页码（从 1 开始）
        page_size: 每页数量

    Returns:
        {
            "tasks": List[dict],
            "total": int,
            "page": int,
            "page_size": int,
            "total_pages": int
        }
    """
    try:
        # 计算偏移量
        offset = (page - 1) * page_size

        # 从数据库获取任务列表
        tasks = db_manager.list_tasks(status=status, limit=page_size, offset=offset)
        total = db_manager.count_tasks(status=status)
        total_pages = (total + page_size - 1) // page_size

        # 为每个任务添加 TOC 条目数量
        for task in tasks:
            task['toc_count'] = db_manager.count_toc_entries(task['task_id'])

        return {
            "tasks": tasks,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@app.get("/api/tasks/{task_id}")
async def get_task_detail(task_id: str):
    """
    获取任务详情及 TOC 条目

    Args:
        task_id: 任务 ID

    Returns:
        {
            "task": dict,
            "toc_entries": List[dict],
            "toc_text": str
        }
    """
    try:
        # 从数据库获取任务信息
        task = db_manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取 TOC 条目
        toc_entries = db_manager.get_toc_entries(task_id)

        # 转换为字典列表
        entries_dict = [
            {
                "title": entry.title,
                "page": entry.page,
                "level": entry.level
            }
            for entry in toc_entries
        ]

        # 生成文本格式（如果有条目）
        toc_text = ""
        if toc_entries:
            from utils.toc_merger import export_toc_to_text
            merged = MergedTOC(
                toc=toc_entries,
                metadata=TOCMetadata(
                    pdf_path=task['pdf_path'],
                    page_offset=task.get('page_offset', 0),
                    total_entries=len(toc_entries)
                )
            )
            # 导出到临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                export_toc_to_text(merged, f.name)
                with open(f.name, 'r', encoding='utf-8') as rf:
                    toc_text = rf.read()
            os.remove(f.name)

        return {
            "task": task,
            "toc_entries": entries_dict,
            "toc_text": toc_text,
            "toc_count": len(toc_entries)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务及其所有关联数据

    Args:
        task_id: 任务 ID

    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        # 检查任务是否存在
        task = db_manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 从数据库删除
        db_manager.delete_task(task_id)

        # 从内存删除（如果存在）
        if task_id in tasks_storage:
            del tasks_storage[task_id]

        logger.info(f"任务已删除: {task_id}")

        return {
            "success": True,
            "message": "任务已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@app.post("/api/import/text")
async def import_from_text(
    pdf_path: str = Form(...),
    txt_content: str = Form(...)
):
    """
    从文本内容导入目录

    Args:
        pdf_path: PDF 文件路径
        txt_content: 目录文本内容

    Returns:
        {
            "success": bool,
            "toc_preview": dict
        }
    """
    try:
        # 保存文本到临时文件
        config = get_config()
        paths = PathConfig.from_pdf_path(pdf_path)
        paths.create_directories()
        toc_txt_path = paths.temp_dir / 'toc_import.txt'

        with open(toc_txt_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)

        # 解析目录
        merged = import_toc_from_text_file(str(toc_txt_path), pdf_path=pdf_path)

        # 生成任务 ID（用于后续写入）
        task_id = str(uuid.uuid4())
        tasks_storage[task_id] = {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "message": "文本导入成功",
            "created_at": datetime.now().isoformat(),
            "pdf_path": pdf_path,
            "result": {
                "merged_toc": merged.to_dict(),
                "toc_text": txt_content
            }
        }

        logger.info(f"文本导入成功: {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "toc_preview": {
                "total_entries": len(merged.toc),
                "entries": [entry.to_dict() for entry in merged.toc[:10]]
            }
        }

    except Exception as e:
        logger.error(f"文本导入失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


# ======================== 后台任务函数 ========================

async def run_ocr_task(
    task_id: str,
    pdf_path: str,
    page_range: str,
    page_offset: int,
    parallel: bool = True
):
    """
    在后台运行 OCR 识别任务

    Args:
        task_id: 任务 ID
        pdf_path: PDF 文件路径
        page_range: 页码范围
        page_offset: 页码偏置
        parallel: 是否并行处理
    """
    try:
        # 更新任务状态（内存）
        tasks_storage[task_id]["status"] = "processing"
        tasks_storage[task_id]["progress"] = 10
        tasks_storage[task_id]["message"] = "正在提取目录页图片..."

        # 同步到数据库
        db_manager.update_task(task_id, {
            "status": "processing",
            "progress": 10
        })

        # Step 1: 提取图片
        from config import PathConfig
        paths = PathConfig.from_pdf_path(pdf_path)
        paths.create_directories()

        # 更新全局配置
        config = get_config()
        config.paths = paths

        image_paths = extract_and_optimize_toc_pages(pdf_path, page_range)

        tasks_storage[task_id]["progress"] = 30
        tasks_storage[task_id]["message"] = f"已提取 {len(image_paths)} 张图片，正在进行 OCR 识别..."

        # Step 2: OCR 识别
        start_page = int(Path(image_paths[0]).stem.split('_')[1])

        if parallel:
            # 并行处理
            agent = OCRAgent()
            results = await _process_images_parallel(agent, image_paths, start_page, task_id)
        else:
            # 顺序处理
            from agent.ocr_agent import process_all_images
            results = process_all_images(
                image_paths=image_paths,
                start_page_number=start_page,
                parallel=False
            )

        tasks_storage[task_id]["progress"] = 60
        tasks_storage[task_id]["message"] = "OCR 识别完成，正在合并目录数据..."

        # Step 3: 合并目录
        output_path = config.paths.temp_dir / 'toc_merged.json'
        merged = merge_from_directory(
            pdf_path=pdf_path,
            page_offset=page_offset,
            toc_page_range=page_range,
            output_path=str(output_path)
        )

        # 导出文本格式
        text_path = config.paths.temp_dir / 'toc.txt'
        export_toc_to_text(merged, str(text_path))

        with open(text_path, 'r', encoding='utf-8') as f:
            toc_text = f.read()

        tasks_storage[task_id]["progress"] = 100
        tasks_storage[task_id]["status"] = "completed"
        tasks_storage[task_id]["message"] = f"处理完成,识别到 {len(merged.toc)} 个目录条目"
        tasks_storage[task_id]["result"] = {
            "merged_toc": merged.to_dict(),
            "toc_text": toc_text,
            "total_entries": len(merged.toc)
        }

        # 同步到数据库
        db_manager.update_task(task_id, {
            "status": "completed",
            "progress": 100,
            "completed_at": datetime.now().isoformat()
        })

        # 保存 TOC 条目到数据库
        db_manager.save_toc_entries(task_id, merged.toc)

        logger.info(f"OCR 任务完成: {task_id}")

    except Exception as e:
        logger.error(f"OCR 任务失败: {task_id}, 错误: {e}")
        tasks_storage[task_id]["status"] = "failed"
        tasks_storage[task_id]["progress"] = 0
        tasks_storage[task_id]["error"] = str(e)
        tasks_storage[task_id]["message"] = f"处理失败: {str(e)}"

        # 同步到数据库
        db_manager.update_task(task_id, {
            "status": "failed",
            "progress": 0,
            "error_message": str(e)
        })


async def _process_images_parallel(agent, image_paths: list, start_page_number: int, task_id: str):
    """
    并行处理图片的异步函数

    Args:
        agent: OCR Agent 实例
        image_paths: 图片路径列表
        start_page_number: 起始页码
        task_id: 任务 ID

    Returns:
        list: TOCPage 对象列表
    """
    from models import TOCPage

    async def process_one(image_path: str, page_number: int, index: int, total: int):
        """异步处理单张图片"""
        try:
            result = await asyncio.to_thread(
                agent.process_image_to_toc_page,
                image_path,
                page_number
            )

            # 更新进度
            progress = 30 + int((index + 1) / total * 30)  # 30-60%
            tasks_storage[task_id]["progress"] = progress
            tasks_storage[task_id]["message"] = f"OCR 识别中... ({index + 1}/{total})"

            return result
        except Exception as e:
            logger.error(f"处理失败 (页 {page_number}): {e}")
            return TOCPage(page_number=page_number, entries=[])

    # 创建任务
    total = len(image_paths)
    tasks = [
        process_one(image_path, start_page_number + i, i, total)
        for i, image_path in enumerate(image_paths)
    ]

    # 并行执行
    results = await asyncio.gather(*tasks)

    return results


# ======================== 启动服务 ========================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("PDF TOC Generator API 服务")
    print("=" * 60)
    print("访问 http://localhost:8000/docs 查看 API 文档")
    print("=" * 60)

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

"""
OCR Agent 模块

核心 Agent 实现，负责图片到结构化数据的转换。
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import time
import base64
import httpx

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from models import TOCPage, TOCEntry
from config import get_config
from .graph import create_ocr_workflow, create_initial_state, OCRState

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM 客户端封装
    
    封装对 OpenRouter API 的调用，支持视觉和文本模型。
    
    Attributes:
        model: ChatOpenAI 实例
        config: API 配置
    """
    
    def __init__(self):
        """初始化 LLM 客户端"""
        config = get_config()
        
        # 配置代理
        http_client = None
        if config.api.http_proxy or config.api.https_proxy:
            # httpx 2.x 使用 proxy 或 mounts 参数
            # 对于简单的代理配置，使用 proxy 参数
            proxy_url = config.api.https_proxy or config.api.http_proxy
            http_client = httpx.Client(proxy=proxy_url)
            logger.info(f"已配置代理: {proxy_url}")
        
        self.model = ChatOpenAI(
            base_url=config.api.base_url,
            api_key=config.api.api_key,
            model=config.api.model_name,
            temperature=config.api.temperature,
            max_tokens=config.api.max_tokens,
            timeout=config.api.timeout,
            http_client=http_client
        )
        
        self.config = config.api
        logger.info(f"LLM 客户端已初始化: {config.api.model_name}")
    
    def encode_image(self, image_path: str) -> str:
        """
        将图片编码为 base64
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            str: base64 编码的图片数据
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_image(self, image_path: str, prompt: str) -> str:
        """
        分析图片（视觉理解）
        
        Args:
            image_path: 图片文件路径
            prompt: 提示词
            
        Returns:
            str: LLM 响应文本
        """
        logger.info(f"[LLM] 分析图片: {image_path}")
        
        # 编码图片
        image_base64 = self.encode_image(image_path)
        
        # 构建消息
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                }
            ]
        )
        
        # 调用模型
        response = self.model.invoke([message])
        return response.content
    
    def extract_text(self, image_path: str, prompt: str) -> str:
        """
        提取图片中的文本
        
        Args:
            image_path: 图片文件路径
            prompt: 提示词
            
        Returns:
            str: 提取的文本
        """
        logger.info(f"[LLM] 提取文本")
        return self.analyze_image(image_path, prompt)
    
    def complete(self, prompt: str) -> str:
        """
        文本补全（不需要图片）
        
        Args:
            prompt: 提示词
            
        Returns:
            str: LLM 响应文本
        """
        logger.info(f"[LLM] 文本补全")
        
        message = HumanMessage(content=prompt)
        response = self.model.invoke([message])
        return response.content


def get_llm_client() -> LLMClient:
    """
    获取 LLM 客户端实例
    
    Returns:
        LLMClient: LLM 客户端
    """
    return LLMClient()


class OCRAgent:
    """
    OCR Agent 主类
    
    管理整个 OCR 识别流程。
    
    Attributes:
        llm_client: LLM 客户端
        workflow: LangGraph 工作流
        config: OCR 配置
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化 OCR Agent
        
        Args:
            llm_client: LLM 客户端（可选，默认创建新实例）
        """
        self.llm_client = llm_client or get_llm_client()
        self.workflow = create_ocr_workflow(self.llm_client)
        self.config = get_config().ocr
        
        logger.info("OCR Agent 已初始化")
    
    def process_image(
        self,
        image_path: str,
        retry: bool = True
    ) -> OCRState:
        """
        处理单张图片
        
        Args:
            image_path: 图片文件路径
            retry: 是否启用重试机制
            
        Returns:
            OCRState: 处理结果状态
            
        Raises:
            FileNotFoundError: 如果图片文件不存在
        """
        image_path_obj = Path(image_path)
        
        if not image_path_obj.exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        logger.info(f"开始处理图片: {image_path}")
        start_time = time.time()
        
        # 创建初始状态
        initial_state = create_initial_state(image_path)
        
        # 执行工作流
        if retry:
            result = self._process_with_retry(initial_state)
        else:
            result = self.workflow.invoke(initial_state)
        
        elapsed_time = time.time() - start_time
        result['metadata']['elapsed_time'] = elapsed_time
        
        logger.info(
            f"处理完成 - 耗时: {elapsed_time:.2f}s, "
            f"识别: {len(result.get('structured_data', []))} 个条目"
        )
        
        return result
    
    def _process_with_retry(self, initial_state: OCRState) -> OCRState:
        """
        带重试机制的处理
        
        Args:
            initial_state: 初始状态
            
        Returns:
            OCRState: 处理结果
        """
        max_retries = self.config.max_retries
        retry_delay = self.config.retry_delay
        
        for attempt in range(max_retries):
            try:
                result = self.workflow.invoke(initial_state)
                
                # 检查是否成功
                if (result.get('structured_data') and 
                    not result.get('errors')):
                    return result
                
                # 如果有错误但不是最后一次尝试，重试
                if attempt < max_retries - 1:
                    logger.warning(
                        f"处理失败，{retry_delay}秒后重试 "
                        f"({attempt + 1}/{max_retries})"
                    )
                    time.sleep(retry_delay)
                    # 指数退避
                    retry_delay *= 2
                else:
                    logger.error(f"处理失败，已达最大重试次数")
                    return result
            
            except Exception as e:
                logger.error(f"处理异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
        
        return result
    
    def process_image_to_toc_page(
        self,
        image_path: str,
        page_number: int,
        save_json: bool = True
    ) -> TOCPage:
        """
        处理图片并转换为 TOCPage 对象
        
        Args:
            image_path: 图片文件路径
            page_number: 页码
            save_json: 是否保存为 JSON 文件
            
        Returns:
            TOCPage: 单页目录对象
        """
        # 处理图片
        result = self.process_image(image_path)
        
        # 转换为 TOCEntry 对象
        entries = []
        structured_data = result.get('structured_data')
        
        if structured_data and isinstance(structured_data, list):
            for entry_data in structured_data:
                try:
                    entry = TOCEntry.from_dict(entry_data)
                    entries.append(entry)
                except Exception as e:
                    logger.warning(f"跳过无效条目: {e}")
        else:
            logger.warning(f"页面 {page_number} 没有识别到有效的目录数据")
        
        # 创建 TOCPage
        toc_page = TOCPage(
            page_number=page_number,
            entries=entries,
            image_path=image_path
        )
        
        # 保存 JSON
        if save_json:
            config = get_config()
            json_path = config.paths.toc_json_dir / f"page_{page_number}.json"
            toc_page.save_to_file(str(json_path))
            logger.info(f"✓ 已保存: {json_path}")
        
        return toc_page


def process_single_image(
    image_path: str,
    page_number: int,
    agent: Optional[OCRAgent] = None
) -> TOCPage:
    """
    处理单张图片（独立函数）
    
    Args:
        image_path: 图片文件路径
        page_number: 页码
        agent: OCR Agent 实例（可选）
        
    Returns:
        TOCPage: 单页目录对象
    """
    if agent is None:
        agent = OCRAgent()
    
    return agent.process_image_to_toc_page(image_path, page_number)


def process_all_images(
    image_paths: List[str],
    start_page_number: int = 1,
    parallel: bool = False
) -> List[TOCPage]:
    """
    批量处理多张图片
    
    Args:
        image_paths: 图片文件路径列表
        start_page_number: 起始页码
        parallel: 是否并行处理（默认顺序处理）
        
    Returns:
        list: TOCPage 对象列表
    """
    agent = OCRAgent()
    
    if parallel:
        return _process_images_parallel(agent, image_paths, start_page_number)
    else:
        return _process_images_sequential(agent, image_paths, start_page_number)


def _process_images_sequential(
    agent: OCRAgent,
    image_paths: List[str],
    start_page_number: int
) -> List[TOCPage]:
    """
    顺序处理图片
    
    Args:
        agent: OCR Agent 实例
        image_paths: 图片路径列表
        start_page_number: 起始页码
        
    Returns:
        list: TOCPage 对象列表
    """
    results = []
    total = len(image_paths)
    
    for i, image_path in enumerate(image_paths, 1):
        page_number = start_page_number + i - 1
        
        logger.info(f"处理进度: {i}/{total} - 页 {page_number}")
        
        try:
            toc_page = agent.process_image_to_toc_page(
                image_path=image_path,
                page_number=page_number
            )
            results.append(toc_page)
            
        except Exception as e:
            logger.error(f"处理失败 (页 {page_number}): {e}")
            # 创建空的 TOCPage
            results.append(TOCPage(page_number=page_number, entries=[]))
    
    return results


async def _process_images_parallel(
    agent: OCRAgent,
    image_paths: List[str],
    start_page_number: int
) -> List[TOCPage]:
    """
    并行处理图片
    
    Args:
        agent: OCR Agent 实例
        image_paths: 图片路径列表
        start_page_number: 起始页码
        
    Returns:
        list: TOCPage 对象列表
    """
    async def process_one(image_path: str, page_number: int):
        """异步处理单张图片"""
        try:
            return await asyncio.to_thread(
                agent.process_image_to_toc_page,
                image_path,
                page_number
            )
        except Exception as e:
            logger.error(f"处理失败 (页 {page_number}): {e}")
            return TOCPage(page_number=page_number, entries=[])
    
    # 创建任务
    tasks = [
        process_one(image_path, start_page_number + i)
        for i, image_path in enumerate(image_paths)
    ]
    
    # 并行执行
    results = await asyncio.gather(*tasks)
    
    return results

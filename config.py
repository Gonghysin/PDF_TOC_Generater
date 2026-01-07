"""
配置管理模块

负责加载和管理项目配置，包括环境变量、API 配置、路径配置等。
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


# 加载 .env 文件
load_dotenv()


@dataclass
class APIConfig:
    """
    API 配置类
    
    存储 OpenRouter API 相关配置信息。
    
    Attributes:
        base_url: API 基础 URL
        api_key: API 密钥
        model_name: 使用的模型名称
        temperature: 生成温度参数（0-1）
        max_tokens: 最大 token 数量
        timeout: 请求超时时间（秒）
        http_proxy: HTTP 代理地址 (可选，例如: http://127.0.0.1:7890)
        https_proxy: HTTPS 代理地址 (可选，例如: http://127.0.0.1:7890)
    """
    base_url: str
    api_key: str
    model_name: str
    temperature: float = 0.1
    max_tokens: int = 16384
    timeout: int = 30
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'APIConfig':
        """
        从环境变量加载 API 配置
        
        Returns:
            APIConfig: API 配置实例
            
        Raises:
            ValueError: 如果必需的环境变量缺失
        """
        base_url = os.getenv('API_BASE_URL')
        api_key = os.getenv('API_KEY')
        model_name = os.getenv('MODEL_NAME')
        
        if not all([base_url, api_key, model_name]):
            raise ValueError(
                "缺少必需的环境变量。请确保 .env 文件中配置了 "
                "API_BASE_URL, API_KEY, MODEL_NAME"
            )
        
        return cls(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            temperature=float(os.getenv('TEMPERATURE', '0.1')),
            max_tokens=int(os.getenv('MAX_TOKENS', '2000')),
            timeout=int(os.getenv('TIMEOUT', '30')),
            http_proxy=os.getenv('HTTP_PROXY'),
            https_proxy=os.getenv('HTTPS_PROXY')
        )


@dataclass
class PathConfig:
    """
    路径配置类
    
    管理项目中使用的各种文件和目录路径。
    
    Attributes:
        project_root: 项目根目录
        temp_dir: 临时文件目录
        toc_images_dir: 目录图片保存目录
        toc_json_dir: 目录 JSON 数据保存目录
        debug_dir: 调试信息保存目录
        schemas_dir: JSON Schema 文件目录
        prompts_dir: Prompt 模板目录
    """
    project_root: Path
    temp_dir: Path
    toc_images_dir: Path
    toc_json_dir: Path
    debug_dir: Path
    schemas_dir: Path
    prompts_dir: Path
    
    @classmethod
    def default(cls) -> 'PathConfig':
        """
        创建默认路径配置
        
        Returns:
            PathConfig: 路径配置实例
        """
        project_root = Path(__file__).parent
        temp_dir = project_root / 'temp'
        
        return cls(
            project_root=project_root,
            temp_dir=temp_dir,
            toc_images_dir=temp_dir / 'toc_images',
            toc_json_dir=temp_dir / 'toc_json',
            debug_dir=temp_dir / 'debug',
            schemas_dir=project_root / 'schemas',
            prompts_dir=project_root / 'prompt'
        )
    
    def create_directories(self) -> None:
        """
        创建所有必需的目录
        
        如果目录不存在，则创建。已存在的目录不会被修改。
        """
        for dir_path in [
            self.temp_dir,
            self.toc_images_dir,
            self.toc_json_dir,
            self.debug_dir
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def clean_temp_directories(self) -> None:
        """
        清理临时目录
        
        删除 temp/ 目录下的所有文件，但保留目录结构。
        """
        import shutil
        
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        self.create_directories()


@dataclass
class OCRConfig:
    """
    OCR 配置类
    
    OCR 相关的配置参数。
    
    Attributes:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        image_max_size: 图片最大尺寸（像素）
        image_quality: 图片质量（1-100）
        image_format: 图片格式
        min_confidence: 最小置信度阈值
    """
    max_retries: int = 3
    retry_delay: float = 2.0
    image_max_size: int = 2048
    image_quality: int = 85
    image_format: str = "PNG"
    min_confidence: float = 0.6
    
    @classmethod
    def from_env(cls) -> 'OCRConfig':
        """
        从环境变量加载 OCR 配置
        
        Returns:
            OCRConfig: OCR 配置实例
        """
        return cls(
            max_retries=int(os.getenv('OCR_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('OCR_RETRY_DELAY', '2.0')),
            image_max_size=int(os.getenv('OCR_IMAGE_MAX_SIZE', '2048')),
            image_quality=int(os.getenv('OCR_IMAGE_QUALITY', '85')),
            image_format=os.getenv('OCR_IMAGE_FORMAT', 'PNG'),
            min_confidence=float(os.getenv('OCR_MIN_CONFIDENCE', '0.6'))
        )


@dataclass
class Config:
    """
    全局配置类
    
    整合所有配置项的主配置类。
    
    Attributes:
        api: API 配置
        paths: 路径配置
        ocr: OCR 配置
    """
    api: APIConfig
    paths: PathConfig
    ocr: OCRConfig
    
    @classmethod
    def load(cls) -> 'Config':
        """
        加载完整配置
        
        Returns:
            Config: 配置实例
        """
        return cls(
            api=APIConfig.from_env(),
            paths=PathConfig.default(),
            ocr=OCRConfig.from_env()
        )


# 全局配置实例
config = Config.load()


def get_config() -> Config:
    """
    获取全局配置实例
    
    Returns:
        Config: 配置实例
    """
    return config


def load_prompt(name: str) -> str:
    """
    加载 Prompt 模板
    
    Args:
        name: Prompt 文件名（不含 .txt 扩展名）
        
    Returns:
        str: Prompt 模板内容
        
    Raises:
        FileNotFoundError: 如果 Prompt 文件不存在
    """
    prompt_path = config.paths.prompts_dir / f"{name}.txt"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")
    
    return prompt_path.read_text(encoding='utf-8')


def load_schema(name: str) -> dict:
    """
    加载 JSON Schema
    
    Args:
        name: Schema 文件名（不含 .schema.json 扩展名）
        
    Returns:
        dict: JSON Schema 字典
        
    Raises:
        FileNotFoundError: 如果 Schema 文件不存在
    """
    import json
    
    schema_path = config.paths.schemas_dir / f"{name}.schema.json"
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema 文件不存在: {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)

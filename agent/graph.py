"""
LangGraph 工作流模块

定义 OCR Agent 的状态图和节点函数。
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import logging
import json
import re

from models import TOCEntry, ImageAnalysisResult, ValidationResult, ValidationStatus
from config import load_prompt

logger = logging.getLogger(__name__)


def extract_json_from_response(response: str) -> str:
    """
    从 LLM 响应中提取纯 JSON 内容
    
    处理以下情况：
    1. Markdown 代码块：```json ... ```
    2. 代码块：``` ... ```
    3. 前后有说明文字
    4. JSON 后有额外数据
    5. JSON 被截断（尝试修复）
    
    Args:
        response: LLM 原始响应
        
    Returns:
        str: 提取的 JSON 字符串
    """
    response = response.strip()
    
    # 方法1: 尝试移除 markdown 代码块标记
    # 查找 ```json 或 ``` 开头
    if '```' in response:
        # 找到第一个 ``` 的位置
        start_marker = response.find('```')
        if start_marker != -1:
            # 跳过 ```json 或 ```
            content_start = response.find('\n', start_marker) + 1
            if content_start == 0:  # 没找到换行符
                content_start = start_marker + 3
                # 跳过可能的 'json'
                if response[content_start:content_start+4] == 'json':
                    content_start += 4
            
            # 找到结束的 ```
            end_marker = response.find('```', content_start)
            if end_marker != -1:
                json_str = response[content_start:end_marker].strip()
                if json_str.startswith('[') or json_str.startswith('{'):
                    return clean_json_string(json_str)
    
    # 方法2: 查找 JSON 数组
    array_start = response.find('[')
    if array_start != -1:
        array_end = response.rfind(']')
        if array_end > array_start:
            json_str = response[array_start:array_end+1]
            return clean_json_string(json_str)
    
    # 方法3: 查找 JSON 对象
    obj_start = response.find('{')
    if obj_start != -1:
        obj_end = response.rfind('}')
        if obj_end > obj_start:
            json_str = response[obj_start:obj_end+1]
            return clean_json_string(json_str)
    
    # 如果都没找到，返回原始响应
    return response


def clean_json_string(json_str: str) -> str:
    """
    清理 JSON 字符串
    
    处理常见的 JSON 格式问题：
    - 移除尾部的逗号（trailing comma）
    - 移除 ... 省略标记
    - 修复截断的 JSON
    
    Args:
        json_str: 原始 JSON 字符串
        
    Returns:
        str: 清理后的 JSON 字符串
    """
    json_str = json_str.strip()
    
    # 移除 ... 省略标记（如果在末尾）
    json_str = re.sub(r',?\s*\.{3,}\s*$', '', json_str)
    
    # 移除尾部逗号（在 ] 或 } 前）
    json_str = re.sub(r',\s*(\]|\})', r'\1', json_str)
    
    # 如果是数组但没有闭合
    if json_str.startswith('[') and not json_str.rstrip().endswith(']'):
        # 找到最后一个完整的对象
        last_brace = json_str.rfind('}')
        if last_brace > 0:
            json_str = json_str[:last_brace + 1]
            # 添加闭合的 ]
            json_str += '\n]'
    
    # 如果是对象但没有闭合
    if json_str.startswith('{') and not json_str.rstrip().endswith('}'):
        # 尝试找到最后一个完整字段
        last_brace = json_str.rfind('}')
        last_quote = json_str.rfind('"')
        if last_brace > last_quote:
            json_str = json_str[:last_brace + 1]
        else:
            # 无法修复，添加闭合
            json_str += '\n}'
    
    return json_str


def attempt_fix_truncated_json(json_str: str) -> str:
    """
    尝试修复被截断的 JSON 字符串
    
    处理以下情况：
    1. 缺少闭合的 ]
    2. 最后一个对象不完整
    3. 额外的逗号
    
    Args:
        json_str: 可能被截断的 JSON 字符串
        
    Returns:
        str: 修复后的 JSON 字符串
    """
    json_str = json_str.strip()
    
    # 如果不是以 [ 开头，无法修复数组
    if not json_str.startswith('['):
        return json_str
    
    # 检查是否已经正确闭合
    if json_str.endswith(']'):
        return json_str
    
    # 找到最后一个完整的对象 (以 } 结尾)
    last_complete_brace = json_str.rfind('}')
    
    if last_complete_brace == -1:
        # 没有找到任何完整对象
        return json_str
    
    # 截取到最后一个完整对象
    fixed = json_str[:last_complete_brace + 1]
    
    # 移除末尾可能的逗号
    fixed = re.sub(r',\s*$', '', fixed)
    
    # 添加闭合的 ]
    fixed += '\n]'
    
    return fixed


class OCRState(TypedDict):
    """
    OCR Agent 的状态定义
    
    在 LangGraph 工作流中传递的状态数据。
    
    Attributes:
        image_path: 图片文件路径
        raw_text: 提取的原始文本
        structured_data: 结构化的目录项列表
        analysis_result: 图片分析结果
        validation_result: 数据验证结果
        errors: 错误信息列表
        metadata: 元数据（如置信度、耗时等）
    """
    image_path: str
    raw_text: Optional[str]
    structured_data: Optional[List[Dict[str, Any]]]
    analysis_result: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]


def analyze_image_node(state: OCRState, llm_client) -> OCRState:
    """
    节点：分析图片
    
    分析目录页图片的质量和布局特征。
    
    Args:
        state: 当前状态
        llm_client: LLM 客户端（由 graph 传入）
        
    Returns:
        OCRState: 更新后的状态
    """
    logger.info(f"[analyze_image] 开始分析图片: {state['image_path']}")
    
    try:
        # 加载 Prompt
        prompt = load_prompt('analyze_image')
        
        # 调用 LLM（需要传入图片）
        # 这里是伪代码，实际需要根据 LLM 客户端的 API 调整
        response = llm_client.analyze_image(
            image_path=state['image_path'],
            prompt=prompt
        )
        
        # 提取并解析 JSON
        json_str = extract_json_from_response(response)
        analysis_result = json.loads(json_str)
        
        state['analysis_result'] = analysis_result
        state['metadata']['analysis_completed'] = True
        
        logger.info(
            f"[analyze_image] 完成 - 质量: {analysis_result.get('quality')}, "
            f"布局: {analysis_result.get('layout')}"
        )
    
    except Exception as e:
        error_msg = f"图片分析失败: {e}"
        logger.error(f"[analyze_image] {error_msg}")
        state['errors'].append(error_msg)
    
    return state


def extract_text_node(state: OCRState, llm_client) -> OCRState:
    """
    节点：提取文本
    
    使用 LLM 的视觉能力提取图片中的所有文本。
    
    Args:
        state: 当前状态
        llm_client: LLM 客户端
        
    Returns:
        OCRState: 更新后的状态
    """
    logger.info(f"[extract_text] 开始提取文本")
    
    try:
        # 加载 Prompt
        prompt = load_prompt('extract_text')
        
        # 调用 LLM
        response = llm_client.extract_text(
            image_path=state['image_path'],
            prompt=prompt
        )
        
        state['raw_text'] = response.strip()
        state['metadata']['text_extracted'] = True
        
        logger.info(f"[extract_text] 完成 - 文本长度: {len(state['raw_text'])}")
    
    except Exception as e:
        error_msg = f"文本提取失败: {e}"
        logger.error(f"[extract_text] {error_msg}")
        state['errors'].append(error_msg)
    
    return state


def parse_structure_node(state: OCRState, llm_client) -> OCRState:
    """
    节点：解析结构
    
    将原始文本解析为结构化的目录数据。
    
    Args:
        state: 当前状态
        llm_client: LLM 客户端
        
    Returns:
        OCRState: 更新后的状态
    """
    logger.info(f"[parse_structure] 开始解析结构")
    
    if not state.get('raw_text'):
        error_msg = "没有可解析的文本"
        logger.error(f"[parse_structure] {error_msg}")
        state['errors'].append(error_msg)
        return state
    
    try:
        # 加载 Prompt
        prompt_template = load_prompt('parse_structure')
        prompt = prompt_template.replace('{raw_text}', state['raw_text'])
        
        # 调用 LLM
        response = llm_client.complete(prompt=prompt)
        
        # 提取并解析 JSON
        json_str = extract_json_from_response(response)
        structured_data = json.loads(json_str)
        
        # 验证数据格式
        if not isinstance(structured_data, list):
            raise ValueError("响应不是数组格式")
        
        state['structured_data'] = structured_data
        state['metadata']['structure_parsed'] = True
        
        logger.info(f"[parse_structure] 完成 - 识别到 {len(structured_data)} 个条目")
    
    except json.JSONDecodeError as e:
        error_msg = f"JSON 解析失败: {e}"
        logger.error(f"[parse_structure] {error_msg}")
        
        # 记录原始响应和提取的 JSON
        if 'response' in locals():
            logger.error(f"[parse_structure] 原始响应前500字符: {response[:500]}...")
        if 'json_str' in locals():
            logger.error(f"[parse_structure] 提取的JSON前500字符: {json_str[:500]}...")
            logger.error(f"[parse_structure] 提取的JSON后100字符: ...{json_str[-100:]}")
            
            # 尝试修复
            try:
                # 如果是 "Extra data" 错误，说明 JSON 前面部分是有效的
                # 尝试只解析到错误位置
                if "Extra data" in str(e):
                    # 从错误信息中提取位置
                    import re
                    match = re.search(r'char (\d+)', str(e))
                    if match:
                        error_pos = int(match.group(1))
                        # 截取到错误位置之前
                        truncated = json_str[:error_pos]
                        logger.info(f"[parse_structure] 检测到 Extra data，尝试截取前 {error_pos} 个字符...")
                        
                        # 尝试修复截断的部分
                        fixed_json = attempt_fix_truncated_json(truncated)
                        structured_data = json.loads(fixed_json)
                        
                        if isinstance(structured_data, list) and len(structured_data) > 0:
                            state['structured_data'] = structured_data
                            state['metadata']['structure_parsed'] = True
                            logger.info(f"[parse_structure] 修复成功 - 识别到 {len(structured_data)} 个条目")
                            return state
                else:
                    # 其他类型的 JSON 错误，尝试一般性修复
                    fixed_json = attempt_fix_truncated_json(json_str)
                    if fixed_json != json_str:
                        logger.info(f"[parse_structure] 尝试修复截断的 JSON...")
                        structured_data = json.loads(fixed_json)
                        
                        if isinstance(structured_data, list) and len(structured_data) > 0:
                            state['structured_data'] = structured_data
                            state['metadata']['structure_parsed'] = True
                            logger.info(f"[parse_structure] 修复成功 - 识别到 {len(structured_data)} 个条目")
                            return state
            except Exception as fix_error:
                logger.error(f"[parse_structure] JSON 修复失败: {fix_error}")
        
        state['errors'].append(error_msg)
    
    except Exception as e:
        error_msg = f"结构解析失败: {e}"
        logger.error(f"[parse_structure] {error_msg}")
        state['errors'].append(error_msg)
    
    return state


def validate_data_node(state: OCRState, llm_client) -> OCRState:
    """
    节点：验证数据
    
    使用 JSON Schema 和逻辑规则验证数据格式。
    
    Args:
        state: 当前状态
        llm_client: LLM 客户端（可选使用）
        
    Returns:
        OCRState: 更新后的状态
    """
    logger.info(f"[validate_data] 开始验证数据")
    
    if not state.get('structured_data'):
        error_msg = "没有可验证的数据"
        logger.error(f"[validate_data] {error_msg}")
        state['errors'].append(error_msg)
        return state
    
    try:
        # 直接验证数据结构，不使用外部 schema 文件
        # 因为 schema 文件的 $ref 引用可能无法解析
        
        # 逻辑验证
        warnings = []
        errors = []
        fixed_data = []
        
        for i, entry in enumerate(state['structured_data']):
            # 验证必需字段
            if not all(k in entry for k in ['title', 'page', 'level']):
                errors.append(f"条目 {i+1} 缺少必需字段")
                continue
            
            # 清理和修正
            title = entry['title'].strip()
            page = entry['page']
            level = entry['level']
            
            # 修正页码
            if page == 0:
                page = 1
                warnings.append(f"条目 {i+1}: 页码从 0 修正为 1")
            
            # 修正层级
            if level < 1:
                level = 1
                warnings.append(f"条目 {i+1}: 层级从 {entry['level']} 修正为 1")
            elif level > 5:
                level = 5
                warnings.append(f"条目 {i+1}: 层级从 {entry['level']} 修正为 5")
            
            fixed_data.append({
                'title': title,
                'page': page,
                'level': level
            })
        
        # 确定验证状态
        if errors:
            status = 'invalid'
        elif warnings:
            status = 'valid_with_fixes'
        else:
            status = 'valid'
        
        state['validation_result'] = {
            'status': status,
            'data': fixed_data,
            'warnings': warnings,
            'errors': errors
        }
        
        # 更新 structured_data 为修正后的数据
        if status != 'invalid':
            state['structured_data'] = fixed_data
        
        state['metadata']['validation_completed'] = True
        
        logger.info(
            f"[validate_data] 完成 - 状态: {status}, "
            f"警告: {len(warnings)}, 错误: {len(errors)}"
        )
    
    except Exception as e:
        error_msg = f"数据验证失败: {e}"
        logger.error(f"[validate_data] {error_msg}")
        state['errors'].append(error_msg)
    
    return state


def create_ocr_workflow(llm_client) -> StateGraph:
    """
    创建 OCR 工作流
    
    构建完整的 LangGraph 状态图。
    
    Args:
        llm_client: LLM 客户端实例
        
    Returns:
        StateGraph: 编译后的工作流图
        
    Examples:
        >>> from agent.ocr_agent import get_llm_client
        >>> client = get_llm_client()
        >>> workflow = create_ocr_workflow(client)
        >>> result = workflow.invoke(initial_state)
    """
    # 创建状态图
    workflow = StateGraph(OCRState)
    
    # 添加节点（使用闭包绑定 llm_client）
    workflow.add_node(
        "analyze_image",
        lambda state: analyze_image_node(state, llm_client)
    )
    workflow.add_node(
        "extract_text",
        lambda state: extract_text_node(state, llm_client)
    )
    workflow.add_node(
        "parse_structure",
        lambda state: parse_structure_node(state, llm_client)
    )
    workflow.add_node(
        "validate_data",
        lambda state: validate_data_node(state, llm_client)
    )
    
    # 设置边（定义执行顺序）
    workflow.set_entry_point("analyze_image")
    workflow.add_edge("analyze_image", "extract_text")
    workflow.add_edge("extract_text", "parse_structure")
    workflow.add_edge("parse_structure", "validate_data")
    workflow.add_edge("validate_data", END)
    
    # 编译工作流
    compiled_workflow = workflow.compile()
    
    logger.info("OCR 工作流已创建")
    
    return compiled_workflow


def create_initial_state(image_path: str) -> OCRState:
    """
    创建初始状态
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        OCRState: 初始状态字典
    """
    return {
        'image_path': image_path,
        'raw_text': None,
        'structured_data': None,
        'analysis_result': None,
        'validation_result': None,
        'errors': [],
        'metadata': {
            'analysis_completed': False,
            'text_extracted': False,
            'structure_parsed': False,
            'validation_completed': False
        }
    }

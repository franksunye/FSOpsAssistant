"""
消息格式验证器

确保所有通知消息都符合标准格式
"""

import re
from typing import Dict, List
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MessageFormatValidator:
    """消息格式验证器"""
    
    # 标准格式模式
    STANDARD_PATTERNS = [
        r"🚨.*违规通知.*",  # 违规通知格式
        r"⚠️.*逾期提醒.*",   # 逾期提醒格式
        r"🔥.*升级通知.*",   # 升级通知格式
    ]
    
    # 不规范格式模式（需要拦截）
    INVALID_PATTERNS = [
        r"紧急通知：任务ID.*",
        r"尊敬的.*您负责的商机.*",
        r"紧急：商机跟进任务.*",
    ]
    
    @classmethod
    def validate_message(cls, message: str) -> Dict[str, any]:
        """
        验证消息格式
        
        Args:
            message: 消息内容
            
        Returns:
            验证结果
        """
        result = {
            "is_valid": False,
            "format_type": "unknown",
            "issues": []
        }
        
        # 检查是否是不规范格式
        for pattern in cls.INVALID_PATTERNS:
            if re.search(pattern, message):
                result["issues"].append(f"检测到不规范格式: {pattern}")
                result["format_type"] = "invalid_llm_generated"
                logger.warning(f"Detected invalid message format: {message[:100]}...")
                return result
        
        # 检查是否是标准格式
        for pattern in cls.STANDARD_PATTERNS:
            if re.search(pattern, message):
                result["is_valid"] = True
                result["format_type"] = "standard_business"
                return result
        
        # 其他格式
        result["format_type"] = "other"
        result["issues"].append("未匹配到标准格式模式")
        
        return result
    
    @classmethod
    def fix_message_format(cls, message: str, task_info: Dict = None) -> str:
        """
        修复消息格式
        
        Args:
            message: 原始消息
            task_info: 任务信息
            
        Returns:
            修复后的消息
        """
        validation = cls.validate_message(message)
        
        if validation["is_valid"]:
            return message
        
        # 如果是不规范格式，替换为标准格式
        if validation["format_type"] == "invalid_llm_generated":
            logger.info("Converting invalid LLM message to standard format")
            
            # 提取关键信息
            order_num = "未知"
            customer = "客户"
            supervisor = "负责人"
            
            if task_info:
                order_num = task_info.get("order_num", "未知")
                customer = task_info.get("customer", "客户")
                supervisor = task_info.get("supervisor", "负责人")
            
            # 生成标准格式消息
            standard_message = f"""⚠️ **逾期工单提醒**

工单号：{order_num}
客户：{customer}
负责人：{supervisor}

请及时处理，确保客户服务质量！

🤖 来源：FSOA智能助手"""
            
            return standard_message
        
        return message


def validate_and_fix_message(message: str, task_info: Dict = None) -> str:
    """
    验证并修复消息格式（便捷函数）
    
    Args:
        message: 消息内容
        task_info: 任务信息
        
    Returns:
        修复后的消息
    """
    return MessageFormatValidator.fix_message_format(message, task_info)

"""
企业微信通知模块

提供企业微信群机器人消息发送功能
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.logger import get_logger
from ..utils.config import get_config

logger = get_logger(__name__)


class WeChatError(Exception):
    """企微相关异常"""
    pass


class WeChatClient:
    """企业微信客户端 - 使用数据库+.env混合配置"""

    def __init__(self):
        self.config = get_config()
        self.db_manager = None
        self._init_db_manager()
        self.org_webhook_mapping = self._load_org_webhooks()
        self.internal_ops_webhook = self.config.internal_ops_webhook_url
        self.session = self._create_session()

    def _init_db_manager(self):
        """初始化数据库管理器"""
        try:
            from ..data.database import get_database_manager
            self.db_manager = get_database_manager()
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            self.db_manager = None

    def _load_org_webhooks(self) -> Dict[str, str]:
        """从数据库加载组织群Webhook配置"""
        org_webhooks = {}

        if self.db_manager:
            try:
                # 从数据库加载组织群配置
                group_configs = self.db_manager.get_group_configs()
                for config in group_configs:
                    if config.enabled and config.webhook_url:
                        # 使用group_id作为组织名称
                        org_webhooks[config.group_id] = config.webhook_url

                logger.info(f"Loaded {len(org_webhooks)} organization webhooks from database")

            except Exception as e:
                logger.error(f"Failed to load organization webhooks from database: {e}")

        if not org_webhooks:
            logger.warning("No organization webhooks configured in database")
            logger.info("Please configure webhooks in [系统管理 → 企微群配置]")

        return org_webhooks


    
    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认headers
        session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "FSOA/1.0"
        })
        
        return session
    
    def send_text_message(self, group_id: str, content: str) -> bool:
        """
        发送文本消息
        
        Args:
            group_id: 群组ID
            content: 消息内容
            
        Returns:
            是否发送成功
        """
        webhook_url = self.org_webhook_mapping.get(group_id)
        if not webhook_url:
            logger.error(f"No webhook URL configured for group {group_id}")
            return False
        
        message_data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        return self._send_message(webhook_url, message_data)
    
    def send_markdown_message(self, group_id: str, content: str) -> bool:
        """
        发送Markdown消息
        
        Args:
            group_id: 群组ID
            content: Markdown内容
            
        Returns:
            是否发送成功
        """
        webhook_url = self.org_webhook_mapping.get(group_id)
        if not webhook_url:
            logger.error(f"No webhook URL configured for group {group_id}")
            return False
        
        message_data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        return self._send_message(webhook_url, message_data)
    
    def send_notification_to_org(self, org_name: str, content: str,
                                is_escalation: bool = False,
                                mention_users: List[str] = None) -> bool:
        """
        发送通知到指定组织的企微群

        Args:
            org_name: 组织名称
            content: 通知内容
            is_escalation: 是否为升级通知
            mention_users: 需要@的用户列表

        Returns:
            是否发送成功
        """
        if is_escalation:
            # 升级通知发送到内部运营群
            webhook_url = self.internal_ops_webhook
            if mention_users:
                # 添加@用户到消息内容
                mentions = " ".join([f"@{user}" for user in mention_users])
                content = f"{content}\n\n{mentions}"
        else:
            # 标准通知发送到对应组织群
            webhook_url = self.org_webhook_mapping.get(org_name)
            if not webhook_url:
                logger.warning(f"No webhook configured for org: {org_name}")
                # 降级到内部运营群
                webhook_url = self.internal_ops_webhook

        if not webhook_url:
            logger.error(f"No webhook URL available for org {org_name}")
            return False

        message_data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }

        return self._send_message(webhook_url, message_data)

    def send_card_message(self, group_id: str, title: str, description: str,
                         url: Optional[str] = None, btn_text: str = "查看详情") -> bool:
        """
        发送卡片消息
        
        Args:
            group_id: 群组ID
            title: 卡片标题
            description: 卡片描述
            url: 跳转链接
            btn_text: 按钮文本
            
        Returns:
            是否发送成功
        """
        webhook_url = self.org_webhook_mapping.get(group_id)
        if not webhook_url:
            logger.error(f"No webhook URL configured for group {group_id}")
            return False
        
        message_data = {
            "msgtype": "textcard",
            "textcard": {
                "title": title,
                "description": description,
                "url": url or "https://example.com",
                "btntxt": btn_text
            }
        }
        
        return self._send_message(webhook_url, message_data)
    
    def _send_message(self, webhook_url: str, message_data: Dict[str, Any]) -> bool:
        """
        发送消息到企微群
        
        Args:
            webhook_url: Webhook URL
            message_data: 消息数据
            
        Returns:
            是否发送成功
        """
        try:
            response = self.session.post(
                webhook_url,
                json=message_data,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("WeChat message sent successfully")
                return True
            else:
                error_msg = result.get("errmsg", "Unknown error")
                logger.error(f"WeChat API error: {error_msg}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to send WeChat message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending WeChat message: {e}")
            return False
    
    def get_available_groups(self) -> Dict[str, str]:
        """获取可用的群组列表"""
        return self.org_webhook_mapping.copy()

    def get_org_webhook_mapping(self) -> Dict[str, str]:
        """获取组织到webhook的映射"""
        return self.org_webhook_mapping.copy()

    def get_internal_ops_webhook(self) -> str:
        """获取内部运营群Webhook"""
        return self.internal_ops_webhook

    def update_org_webhook_mapping(self, org_name: str, webhook_url: str) -> bool:
        """更新组织webhook映射"""
        try:
            if self.db_manager:
                # 使用数据库更新配置
                config = self.db_manager.create_or_update_group_config(
                    group_id=org_name,
                    name=org_name,
                    webhook_url=webhook_url,
                    enabled=True
                )
                if config:
                    self.org_webhook_mapping[org_name] = webhook_url
                    logger.info(f"Updated webhook mapping for org: {org_name}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to update org webhook mapping: {e}")
            return False

    def remove_org_webhook_mapping(self, org_name: str) -> bool:
        """删除组织webhook映射"""
        try:
            if self.db_manager:
                success = self.db_manager.delete_group_config(org_name)
                if success and org_name in self.org_webhook_mapping:
                    del self.org_webhook_mapping[org_name]
                    logger.info(f"Removed webhook mapping for org: {org_name}")
                return success
            return False
        except Exception as e:
            logger.error(f"Failed to remove org webhook mapping: {e}")
            return False


# 全局客户端实例
_wechat_client: Optional[WeChatClient] = None


def get_wechat_client() -> WeChatClient:
    """获取企微客户端实例"""
    global _wechat_client
    if _wechat_client is None:
        _wechat_client = WeChatClient()
    return _wechat_client


def send_wechat_message(group_id: str, message: str, message_type: str = "text") -> bool:
    """
    发送企微消息（便捷函数）
    
    Args:
        group_id: 群组ID
        message: 消息内容
        message_type: 消息类型 (text, markdown, card)
        
    Returns:
        是否发送成功
    """
    try:
        client = get_wechat_client()
        
        if message_type == "text":
            return client.send_text_message(group_id, message)
        elif message_type == "markdown":
            return client.send_markdown_message(group_id, message)
        else:
            logger.warning(f"Unsupported message type: {message_type}, using text")
            return client.send_text_message(group_id, message)
            
    except Exception as e:
        logger.error(f"Error sending WeChat message: {e}")
        return False


def format_task_alert_message(task_info: Dict[str, Any]) -> str:
    """
    格式化任务告警消息
    
    Args:
        task_info: 任务信息
        
    Returns:
        格式化的消息内容
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    message = f"""🚨 **现场服务超时提醒**

📋 **任务信息**
• 任务ID: {task_info.get('id', 'N/A')}
• 任务标题: {task_info.get('title', 'N/A')}
• 负责人: {task_info.get('assignee', '未分配')}
• 客户: {task_info.get('customer', 'N/A')}

⏰ **时效信息**
• SLA时间: {task_info.get('sla_hours', 0)}小时
• 已用时间: {task_info.get('elapsed_hours', 0):.1f}小时
• 超时时间: {task_info.get('overdue_hours', 0):.1f}小时

📍 **服务地点**: {task_info.get('location', 'N/A')}

⚠️ **请及时处理，确保服务质量！**

🕐 发送时间: {current_time}
🤖 来源: FSOA智能助手"""
    
    return message


def format_task_alert_card(task_info: Dict[str, Any]) -> tuple:
    """
    格式化任务告警卡片消息
    
    Args:
        task_info: 任务信息
        
    Returns:
        (title, description) 元组
    """
    title = f"🚨 任务超时提醒 - {task_info.get('title', 'Unknown')}"
    
    description = f"""任务ID: {task_info.get('id', 'N/A')}
负责人: {task_info.get('assignee', '未分配')}
超时时间: {task_info.get('overdue_hours', 0):.1f}小时
客户: {task_info.get('customer', 'N/A')}

请及时处理，确保服务质量！"""
    
    return title, description

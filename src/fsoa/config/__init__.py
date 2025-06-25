"""
配置管理模块

提供各种配置管理功能
"""

from .wechat_config import WeChatConfigManager, get_wechat_config_manager

__all__ = [
    'WeChatConfigManager',
    'get_wechat_config_manager'
]

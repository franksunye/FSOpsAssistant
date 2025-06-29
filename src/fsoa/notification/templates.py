"""
消息模板模块 - 已废弃

⚠️ 此模块已废弃，请使用 BusinessNotificationFormatter 替代

提供各种通知消息的模板（兼容性保留）
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import warnings

from ..data.models import OpportunityInfo, Priority


class MessageTemplate(str, Enum):
    """消息模板类型"""
    OVERDUE_ALERT = "overdue_alert"
    ESCALATION_ALERT = "escalation_alert"
    COMPLETION_REMINDER = "completion_reminder"
    SYSTEM_NOTIFICATION = "system_notification"


class MessageFormatter:
    """消息格式化器 - 已废弃，请使用BusinessNotificationFormatter"""

    @staticmethod
    def format_overdue_alert(opportunity: OpportunityInfo, custom_message: str = None) -> str:
        """
        格式化超时告警消息 - 已废弃

        Args:
            opportunity: 商机信息
            custom_message: 自定义消息内容

        Returns:
            格式化的消息字符串
        """
        warnings.warn(
            "MessageFormatter.format_overdue_alert is deprecated. Use BusinessNotificationFormatter instead.",
            DeprecationWarning,
            stacklevel=2
        )

        if custom_message:
            return custom_message

        # 简化的兼容性实现
        return f"""⚠️ 商机超时提醒

工单号: {opportunity.order_num}
客户: {opportunity.name}
负责人: {opportunity.supervisor_name}
超时时间: {opportunity.overdue_hours:.1f}小时

请及时处理，确保服务质量！"""

    @staticmethod
    def format_escalation_alert(opportunity: OpportunityInfo, escalation_level: int = 1) -> str:
        """格式化升级告警消息 - 已废弃"""
        warnings.warn(
            "MessageFormatter.format_escalation_alert is deprecated. Use BusinessNotificationFormatter instead.",
            DeprecationWarning,
            stacklevel=2
        )

        return f"""🚨 升级通知 (级别 {escalation_level})

工单号: {opportunity.order_num}
客户: {opportunity.name}
负责人: {opportunity.supervisor_name}

需要立即处理！"""

    @staticmethod
    def format_completion_reminder(opportunity: OpportunityInfo) -> str:
        """格式化完成提醒消息 - 已废弃"""
        warnings.warn(
            "MessageFormatter.format_completion_reminder is deprecated. Use BusinessNotificationFormatter instead.",
            DeprecationWarning,
            stacklevel=2
        )

        return f"""📋 完成提醒

工单号: {opportunity.order_num}
客户: {opportunity.name}

请确认处理状态。"""

    @staticmethod
    def format_markdown_alert(opportunity: OpportunityInfo) -> str:
        """格式化Markdown告警消息 - 已废弃"""
        warnings.warn(
            "MessageFormatter.format_markdown_alert is deprecated. Use BusinessNotificationFormatter instead.",
            DeprecationWarning,
            stacklevel=2
        )

        return f"""**⚠️ 商机超时提醒**

- **工单号**: {opportunity.order_num}
- **客户**: {opportunity.name}
- **负责人**: {opportunity.supervisor_name}

请及时处理！"""

    @staticmethod
    def _get_action_suggestion(opportunity: OpportunityInfo) -> str:
        """获取行动建议 - 已废弃"""
        warnings.warn(
            "MessageFormatter._get_action_suggestion is deprecated.",
            DeprecationWarning,
            stacklevel=2
        )
        return "请联系相关负责人处理。"


def get_message_template(template_type: MessageTemplate, opportunity: OpportunityInfo,
                        **kwargs) -> str:
    """
    获取消息模板 - 已废弃

    Args:
        template_type: 模板类型
        opportunity: 商机信息
        **kwargs: 额外参数

    Returns:
        格式化的消息
    """
    warnings.warn(
        "get_message_template is deprecated. Use BusinessNotificationFormatter instead.",
        DeprecationWarning,
        stacklevel=2
    )

    if template_type == MessageTemplate.OVERDUE_ALERT:
        return MessageFormatter.format_overdue_alert(opportunity, kwargs.get('custom_message'))
    elif template_type == MessageTemplate.ESCALATION_ALERT:
        return MessageFormatter.format_escalation_alert(opportunity, kwargs.get('escalation_level', 1))
    elif template_type == MessageTemplate.COMPLETION_REMINDER:
        return MessageFormatter.format_completion_reminder(opportunity)
    else:
        return f"工单 {opportunity.order_num} 需要关注"

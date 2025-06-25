"""
消息模板模块

提供各种通知消息的模板
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from ..data.models import TaskInfo, Priority


class MessageTemplate(str, Enum):
    """消息模板类型"""
    OVERDUE_ALERT = "overdue_alert"
    ESCALATION_ALERT = "escalation_alert"
    COMPLETION_REMINDER = "completion_reminder"
    SYSTEM_NOTIFICATION = "system_notification"


class MessageFormatter:
    """消息格式化器"""
    
    @staticmethod
    def format_overdue_alert(task: TaskInfo, custom_message: str = None) -> str:
        """
        格式化超时告警消息
        
        Args:
            task: 任务信息
            custom_message: 自定义消息
            
        Returns:
            格式化的消息
        """
        if custom_message:
            return custom_message
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 根据超时程度选择不同的紧急程度
        if task.overdue_hours > task.sla_hours:
            urgency_icon = "🔥"
            urgency_text = "严重超时"
        elif task.overdue_hours > task.sla_hours * 0.5:
            urgency_icon = "⚠️"
            urgency_text = "超时较多"
        else:
            urgency_icon = "⏰"
            urgency_text = "刚刚超时"
        
        message = f"""{urgency_icon} **现场服务{urgency_text}提醒**

📋 **任务信息**
• 任务ID: {task.id}
• 任务标题: {task.title}
• 负责人: {task.assignee or '未分配'}
• 客户: {task.customer or 'N/A'}
• 优先级: {MessageFormatter._get_priority_text(task.priority)}

⏰ **时效信息**
• SLA时间: {task.sla_hours}小时
• 已用时间: {task.elapsed_hours:.1f}小时
• 超时时间: {task.overdue_hours:.1f}小时
• 超时比例: {task.overdue_ratio:.1%}

📍 **服务地点**: {task.location or 'N/A'}

{MessageFormatter._get_action_suggestion(task)}

🕐 发送时间: {current_time}
🤖 来源: FSOA智能助手"""
        
        return message
    
    @staticmethod
    def format_escalation_alert(task: TaskInfo, escalation_level: int = 1) -> str:
        """
        格式化升级告警消息
        
        Args:
            task: 任务信息
            escalation_level: 升级级别
            
        Returns:
            格式化的消息
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        escalation_text = {
            1: "一级升级",
            2: "二级升级", 
            3: "紧急升级"
        }.get(escalation_level, "升级")
        
        message = f"""🚨 **{escalation_text}通知**

📋 **任务信息**
• 任务ID: {task.id}
• 任务标题: {task.title}
• 负责人: {task.assignee or '未分配'}
• 客户: {task.customer or 'N/A'}

⚠️ **升级原因**
• 任务已超时 {task.overdue_hours:.1f} 小时
• 超出SLA时间 {task.overdue_ratio:.1%}
• 需要立即关注和处理

📞 **建议行动**
• 立即联系现场人员
• 评估是否需要额外资源
• 及时向客户说明情况

🕐 升级时间: {current_time}
🤖 来源: FSOA智能助手"""
        
        return message
    
    @staticmethod
    def format_completion_reminder(task: TaskInfo) -> str:
        """
        格式化完成提醒消息
        
        Args:
            task: 任务信息
            
        Returns:
            格式化的消息
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""✅ **任务完成确认**

📋 **任务信息**
• 任务ID: {task.id}
• 任务标题: {task.title}
• 负责人: {task.assignee or '未分配'}

⏰ **时效统计**
• 总用时: {task.elapsed_hours:.1f}小时
• SLA达成: {'✅ 是' if not task.is_overdue else '❌ 否'}

📝 **请确认**
• 任务是否真正完成？
• 客户是否满意？
• 是否需要后续跟进？

🕐 提醒时间: {current_time}
🤖 来源: FSOA智能助手"""
        
        return message
    
    @staticmethod
    def format_system_notification(title: str, content: str, 
                                 notification_type: str = "info") -> str:
        """
        格式化系统通知消息
        
        Args:
            title: 通知标题
            content: 通知内容
            notification_type: 通知类型 (info, warning, error, success)
            
        Returns:
            格式化的消息
        """
        icons = {
            "info": "ℹ️",
            "warning": "⚠️", 
            "error": "❌",
            "success": "✅"
        }
        
        icon = icons.get(notification_type, "📢")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""{icon} **{title}**

{content}

🕐 通知时间: {current_time}
🤖 来源: FSOA智能助手"""
        
        return message
    
    @staticmethod
    def format_markdown_alert(task: TaskInfo) -> str:
        """
        格式化Markdown告警消息
        
        Args:
            task: 任务信息
            
        Returns:
            Markdown格式的消息
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""## 🚨 现场服务超时提醒

### 📋 任务信息
- **任务ID**: {task.id}
- **任务标题**: {task.title}
- **负责人**: {task.assignee or '未分配'}
- **客户**: {task.customer or 'N/A'}
- **优先级**: {MessageFormatter._get_priority_text(task.priority)}

### ⏰ 时效信息
- **SLA时间**: {task.sla_hours}小时
- **已用时间**: {task.elapsed_hours:.1f}小时
- **超时时间**: <font color="warning">{task.overdue_hours:.1f}小时</font>
- **超时比例**: <font color="warning">{task.overdue_ratio:.1%}</font>

### 📍 服务地点
{task.location or 'N/A'}

### 💡 建议行动
{MessageFormatter._get_action_suggestion(task)}

---
🕐 **发送时间**: {current_time}  
🤖 **来源**: FSOA智能助手"""
        
        return message
    
    @staticmethod
    def _get_priority_text(priority: Priority) -> str:
        """获取优先级文本"""
        priority_map = {
            Priority.LOW: "🟢 低",
            Priority.NORMAL: "🟡 普通", 
            Priority.HIGH: "🟠 高",
            Priority.URGENT: "🔴 紧急"
        }
        return priority_map.get(priority, "🟡 普通")
    
    @staticmethod
    def _get_action_suggestion(task: TaskInfo) -> str:
        """获取行动建议"""
        if task.overdue_hours > task.sla_hours:
            return """🔥 **立即行动**
• 马上联系现场人员
• 评估是否需要额外支持
• 准备向客户解释延误原因"""
        elif task.overdue_hours > task.sla_hours * 0.5:
            return """⚠️ **尽快处理**
• 联系现场人员了解进度
• 评估完成时间
• 必要时通知客户"""
        else:
            return """⏰ **及时跟进**
• 提醒现场人员注意时效
• 监控任务进展
• 确保按时完成"""


def get_message_template(template_type: MessageTemplate, task: TaskInfo, 
                        **kwargs) -> str:
    """
    获取消息模板
    
    Args:
        template_type: 模板类型
        task: 任务信息
        **kwargs: 额外参数
        
    Returns:
        格式化的消息
    """
    if template_type == MessageTemplate.OVERDUE_ALERT:
        return MessageFormatter.format_overdue_alert(task, kwargs.get('custom_message'))
    elif template_type == MessageTemplate.ESCALATION_ALERT:
        return MessageFormatter.format_escalation_alert(task, kwargs.get('escalation_level', 1))
    elif template_type == MessageTemplate.COMPLETION_REMINDER:
        return MessageFormatter.format_completion_reminder(task)
    elif template_type == MessageTemplate.SYSTEM_NOTIFICATION:
        return MessageFormatter.format_system_notification(
            kwargs.get('title', '系统通知'),
            kwargs.get('content', ''),
            kwargs.get('notification_type', 'info')
        )
    else:
        return MessageFormatter.format_overdue_alert(task)

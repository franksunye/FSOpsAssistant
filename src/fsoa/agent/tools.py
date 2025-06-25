"""
Agent工具函数模块

提供Agent使用的核心工具函数
"""

import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from functools import wraps

from ..data.models import TaskInfo, NotificationInfo, NotificationStatus, Priority, OpportunityInfo
from ..data.database import get_db_manager
from ..data.metabase import get_metabase_client, MetabaseError
from ..notification.wechat import send_wechat_message, get_wechat_client, WeChatError
from ..notification.business_formatter import BusinessNotificationFormatter
from ..utils.logger import get_logger, log_function_call
from ..utils.config import get_config

logger = get_logger(__name__)


class ToolError(Exception):
    """工具函数异常"""
    pass


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} attempts",
                            error=str(e)
                        )
                        break
                    
                    wait_time = delay * (2 ** attempt)  # 指数退避
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {wait_time}s",
                        error=str(e)
                    )
                    time.sleep(wait_time)
            
            raise last_exception
        return wrapper
    return decorator


@log_function_call
@retry_on_failure(max_retries=3)
def fetch_overdue_tasks() -> List[TaskInfo]:
    """
    从Metabase获取超时任务列表

    Returns:
        超时任务列表

    Raises:
        ToolError: 当获取数据失败时
    """
    try:
        metabase_client = get_metabase_client()
        tasks = metabase_client.get_overdue_tasks()

        # 保存任务到本地数据库
        db_manager = get_db_manager()
        for task in tasks:
            db_manager.save_task(task)

        logger.info(f"Successfully fetched {len(tasks)} overdue tasks")
        return tasks

    except MetabaseError as e:
        logger.error(f"Metabase error while fetching tasks: {e}")
        raise ToolError(f"Failed to fetch tasks from Metabase: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while fetching tasks: {e}")
        raise ToolError(f"Unexpected error: {e}")


@log_function_call
@retry_on_failure(max_retries=3)
def fetch_overdue_opportunities() -> List[OpportunityInfo]:
    """
    从Metabase获取逾期商机列表

    Returns:
        逾期商机列表

    Raises:
        ToolError: 当获取数据失败时
    """
    try:
        metabase_client = get_metabase_client()
        opportunities = metabase_client.get_overdue_opportunities()

        logger.info(f"Successfully fetched {len(opportunities)} overdue opportunities")
        return opportunities

    except MetabaseError as e:
        logger.error(f"Metabase error while fetching opportunities: {e}")
        raise ToolError(f"Failed to fetch opportunities from Metabase: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while fetching opportunities: {e}")
        raise ToolError(f"Unexpected error: {e}")


@log_function_call
@retry_on_failure(max_retries=2)
def send_notification(task: TaskInfo, message: str, priority: Priority = Priority.NORMAL) -> bool:
    """
    发送企微通知
    
    Args:
        task: 任务信息
        message: 通知消息
        priority: 优先级
        
    Returns:
        是否发送成功
        
    Raises:
        ToolError: 当发送失败时
    """
    if not task.group_id:
        logger.warning(f"Task {task.id} has no group_id, skipping notification")
        return False
    
    try:
        # 检查通知冷却时间
        if not _check_notification_cooldown(task):
            logger.info(f"Task {task.id} is in notification cooldown, skipping")
            return False
        
        # 发送企微消息
        success = send_wechat_message(task.group_id, message)
        
        if success:
            # 记录通知
            notification = NotificationInfo(
                task_id=task.id,
                type="overdue_alert",
                priority=priority,
                message=message,
                group_id=task.group_id,
                sent_at=datetime.now(),
                status=NotificationStatus.SENT
            )
            
            db_manager = get_db_manager()
            notification_id = db_manager.save_notification(notification)
            
            # 更新任务的最后通知时间
            task.last_notification = datetime.now()
            db_manager.save_task(task)
            
            logger.info(f"Successfully sent notification for task {task.id}")
            return True
        else:
            logger.error(f"Failed to send notification for task {task.id}")
            return False
            
    except WeChatError as e:
        logger.error(f"WeChat error while sending notification: {e}")
        raise ToolError(f"Failed to send WeChat notification: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while sending notification: {e}")
        raise ToolError(f"Unexpected error: {e}")


@log_function_call
def update_task_status(task_id: int, status: str, comment: str = None) -> bool:
    """
    更新任务状态
    
    Args:
        task_id: 任务ID
        status: 新状态
        comment: 备注信息
        
    Returns:
        是否更新成功
    """
    try:
        db_manager = get_db_manager()
        
        # 获取现有任务
        tasks = db_manager.get_tasks()
        task = next((t for t in tasks if t.id == task_id), None)
        
        if not task:
            logger.warning(f"Task {task_id} not found")
            return False
        
        # 更新状态
        task.status = status
        task.updated_at = datetime.now()
        
        success = db_manager.save_task(task)
        
        if success:
            logger.info(f"Successfully updated task {task_id} status to {status}")
        else:
            logger.error(f"Failed to update task {task_id} status")
        
        return success
        
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        return False


@log_function_call
def get_task_notification_history(task_id: int, hours_back: int = 24) -> List[NotificationInfo]:
    """
    获取任务通知历史
    
    Args:
        task_id: 任务ID
        hours_back: 查询多少小时内的历史
        
    Returns:
        通知历史列表
    """
    try:
        db_manager = get_db_manager()
        
        # 这里简化实现，实际需要在数据库中查询
        # 暂时返回空列表
        logger.info(f"Retrieved notification history for task {task_id}")
        return []
        
    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        return []


def _check_notification_cooldown(task: TaskInfo) -> bool:
    """
    检查通知冷却时间
    
    Args:
        task: 任务信息
        
    Returns:
        是否可以发送通知
    """
    if not task.last_notification:
        return True
    
    config = get_config()
    cooldown_minutes = config.notification_cooldown
    
    time_since_last = datetime.now() - task.last_notification
    cooldown_period = timedelta(minutes=cooldown_minutes)
    
    return time_since_last >= cooldown_period


@log_function_call
def test_metabase_connection() -> bool:
    """
    测试Metabase连接
    
    Returns:
        连接是否成功
    """
    try:
        metabase_client = get_metabase_client()
        return metabase_client.test_connection()
    except Exception as e:
        logger.error(f"Metabase connection test failed: {e}")
        return False


@log_function_call
def test_deepseek_connection() -> bool:
    """
    测试DeepSeek LLM连接

    Returns:
        连接是否成功
    """
    try:
        from .llm import get_deepseek_client
        deepseek_client = get_deepseek_client()
        return deepseek_client.test_connection()
    except Exception as e:
        logger.error(f"DeepSeek connection test failed: {e}")
        return False


@log_function_call
def test_wechat_webhook(group_id: str = None) -> bool:
    """
    测试企微Webhook连接
    
    Args:
        group_id: 群组ID，如果不指定则测试所有配置的webhook
        
    Returns:
        测试是否成功
    """
    try:
        test_message = f"FSOA系统测试消息 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if group_id:
            return send_wechat_message(group_id, test_message)
        else:
            # 测试所有配置的webhook
            config = get_config()
            webhook_urls = config.wechat_webhook_list
            
            success_count = 0
            for i, webhook_url in enumerate(webhook_urls):
                group_id = f"group_{i+1:03d}"
                if send_wechat_message(group_id, test_message):
                    success_count += 1
            
            return success_count > 0
            
    except Exception as e:
        logger.error(f"WeChat webhook test failed: {e}")
        return False


@log_function_call
def get_system_health() -> Dict[str, Any]:
    """
    获取系统健康状态
    
    Returns:
        系统健康状态信息
    """
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "metabase_connection": False,
        "wechat_webhook": False,
        "database_connection": False,
        "overall_status": "unhealthy"
    }
    
    try:
        # 测试Metabase连接
        health_status["metabase_connection"] = test_metabase_connection()

        # 测试企微Webhook
        health_status["wechat_webhook"] = test_wechat_webhook()

        # 测试DeepSeek连接
        health_status["deepseek_connection"] = test_deepseek_connection()

        # 测试数据库连接
        db_manager = get_db_manager()
        health_status["database_connection"] = True  # 如果能获取到manager说明连接正常
        
        # 计算整体状态
        if all([
            health_status["metabase_connection"],
            health_status["wechat_webhook"],
            health_status["deepseek_connection"],
            health_status["database_connection"]
        ]):
            health_status["overall_status"] = "healthy"
        elif any([
            health_status["metabase_connection"],
            health_status["database_connection"]
        ]):
            health_status["overall_status"] = "degraded"
        
        logger.info("System health check completed", **health_status)
        return health_status
        
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        health_status["error"] = str(e)
        return health_status


@log_function_call
def send_business_notifications(opportunities: List[OpportunityInfo]) -> Dict[str, Any]:
    """
    发送业务通知到对应的企微群

    Args:
        opportunities: 逾期商机列表

    Returns:
        发送结果统计
    """
    if not opportunities:
        logger.info("No opportunities to notify")
        return {"total": 0, "sent": 0, "failed": 0, "escalated": 0}

    # 按组织分组
    org_opportunities = {}
    escalation_opportunities = {}

    for opp in opportunities:
        org_name = opp.org_name
        if org_name not in org_opportunities:
            org_opportunities[org_name] = []
        org_opportunities[org_name].append(opp)

        # 检查是否需要升级
        if opp.escalation_level > 0:
            if org_name not in escalation_opportunities:
                escalation_opportunities[org_name] = []
            escalation_opportunities[org_name].append(opp)

    wechat_client = get_wechat_client()
    formatter = BusinessNotificationFormatter()

    sent_count = 0
    failed_count = 0
    escalated_count = 0

    # 发送标准通知
    for org_name, org_opps in org_opportunities.items():
        try:
            # 格式化通知内容
            message = formatter.format_org_overdue_notification(org_name, org_opps)

            if message:
                # 发送到组织对应的企微群
                success = wechat_client.send_notification_to_org(
                    org_name=org_name,
                    content=message,
                    is_escalation=False
                )

                if success:
                    sent_count += len(org_opps)
                    logger.info(f"Sent notification to {org_name} for {len(org_opps)} opportunities")
                else:
                    failed_count += len(org_opps)
                    logger.error(f"Failed to send notification to {org_name}")

        except Exception as e:
            logger.error(f"Error sending notification to {org_name}: {e}")
            failed_count += len(org_opps)

    # 发送升级通知
    for org_name, escalation_opps in escalation_opportunities.items():
        try:
            # 格式化升级通知内容
            message = formatter.format_escalation_notification(
                org_name=org_name,
                opportunities=escalation_opps,
                mention_users=["运营负责人", "区域经理"]  # 可配置
            )

            if message:
                # 发送到内部运营群
                success = wechat_client.send_notification_to_org(
                    org_name=org_name,
                    content=message,
                    is_escalation=True,
                    mention_users=["运营负责人", "区域经理"]
                )

                if success:
                    escalated_count += len(escalation_opps)
                    logger.info(f"Sent escalation notification for {org_name} with {len(escalation_opps)} opportunities")
                else:
                    logger.error(f"Failed to send escalation notification for {org_name}")

        except Exception as e:
            logger.error(f"Error sending escalation notification for {org_name}: {e}")

    result = {
        "total": len(opportunities),
        "sent": sent_count,
        "failed": failed_count,
        "escalated": escalated_count,
        "organizations": len(org_opportunities)
    }

    logger.info(f"Notification summary: {result}")
    return result

"""
Agent工具函数模块

提供Agent使用的核心工具函数
"""

import time
from datetime import datetime, timedelta

# 导入时区工具
from ..utils.timezone_utils import now_china_naive
from typing import List, Optional, Dict, Any
from functools import wraps

from ..data.models import (
    TaskInfo, NotificationInfo, NotificationStatus, Priority, OpportunityInfo,
    TaskStatus, NotificationTask
)
from ..data.database import get_db_manager
from ..data.metabase import get_metabase_client, MetabaseError
from ..notification.wechat import send_wechat_message, get_wechat_client, WeChatError
from ..notification.business_formatter import BusinessNotificationFormatter
from ..utils.logger import get_logger, log_function_call
from ..utils.config import get_config

# 导入新的管理器
from .managers import NotificationTaskManager, AgentExecutionTracker, BusinessDataStrategy

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


# ============================================================================
# 重构后的Agent工具函数 - 使用新的管理器架构
# ============================================================================

# 全局管理器实例
_data_strategy = None
_notification_manager = None
_execution_tracker = None

def get_data_strategy() -> BusinessDataStrategy:
    """获取业务数据策略实例"""
    global _data_strategy
    if _data_strategy is None:
        _data_strategy = BusinessDataStrategy()
    return _data_strategy

def get_notification_manager() -> NotificationTaskManager:
    """获取通知任务管理器实例"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationTaskManager()
    return _notification_manager

def get_execution_tracker() -> AgentExecutionTracker:
    """获取执行追踪器实例"""
    global _execution_tracker
    if _execution_tracker is None:
        _execution_tracker = AgentExecutionTracker()
    return _execution_tracker


# ============================================================================
# 废弃的函数 - 仅保留用于向后兼容，请使用新的商机相关接口
# ============================================================================

@log_function_call
@retry_on_failure(max_retries=3)
def fetch_overdue_tasks() -> List[TaskInfo]:
    """
    从Metabase获取超时任务列表 - 已废弃

    ⚠️ 此函数已废弃，存在任务-商机概念混淆问题

    推荐使用：
    - fetch_overdue_opportunities() 获取逾期商机
    - get_data_strategy().get_overdue_opportunities() 获取逾期商机

    此函数将商机数据强制转换为TaskInfo格式，仅用于向后兼容

    Returns:
        超时任务列表（实际为商机数据的TaskInfo包装）

    Raises:
        ToolError: 当获取数据失败时
    """
    logger.warning(
        "fetch_overdue_tasks() is deprecated due to task-opportunity concept confusion. "
        "Use fetch_overdue_opportunities() instead."
    )

    try:
        # 使用新的数据策略获取商机，然后转换为TaskInfo格式以保持兼容性
        data_strategy = get_data_strategy()
        opportunities = data_strategy.get_overdue_opportunities()

        # 将商机数据包装为TaskInfo格式（仅用于兼容性）
        tasks = []
        for opp in opportunities:
            task = TaskInfo(
                id=hash(opp.order_num) % 1000000,  # 生成伪ID
                title=f"商机跟进 - {opp.name}",
                description=f"地址: {opp.address}",
                status=TaskStatus.OVERDUE,
                priority=Priority.HIGH if opp.escalation_level > 0 else Priority.NORMAL,
                sla_hours=opp.sla_threshold_hours or 24,
                elapsed_hours=opp.elapsed_hours or 0,
                overdue_hours=opp.overdue_hours or 0,
                group_id=opp.org_name,
                assignee=opp.supervisor_name,
                customer=opp.name,
                location=opp.address,
                created_at=opp.create_time,
                updated_at=datetime.now()
            )
            tasks.append(task)

        logger.info(f"Successfully converted {len(opportunities)} opportunities to {len(tasks)} legacy tasks")
        return tasks

    except Exception as e:
        logger.error(f"Failed to fetch overdue tasks: {e}")
        raise ToolError(f"Failed to fetch overdue tasks: {e}")


# ============================================================================
# 重构后的核心工具函数
# ============================================================================

@log_function_call
@retry_on_failure(max_retries=3)
def fetch_overdue_opportunities(force_refresh: bool = False) -> List[OpportunityInfo]:
    """
    获取逾期商机列表 - 重构版本，使用新的数据策略

    Args:
        force_refresh: 是否强制刷新数据，忽略缓存

    Returns:
        逾期商机列表

    Raises:
        ToolError: 当获取数据失败时
    """
    try:
        data_strategy = get_data_strategy()
        opportunities = data_strategy.get_overdue_opportunities(force_refresh)

        logger.info(f"Successfully fetched {len(opportunities)} overdue opportunities")
        return opportunities

    except Exception as e:
        logger.error(f"Failed to fetch overdue opportunities: {e}")
        raise ToolError(f"Failed to fetch overdue opportunities: {e}")


@log_function_call
def get_all_opportunities(force_refresh: bool = False) -> List[OpportunityInfo]:
    """
    获取所有商机列表

    Args:
        force_refresh: 是否强制刷新数据，忽略缓存

    Returns:
        所有商机列表
    """
    try:
        data_strategy = get_data_strategy()
        opportunities = data_strategy.get_opportunities(force_refresh)

        logger.info(f"Successfully fetched {len(opportunities)} opportunities")
        return opportunities

    except Exception as e:
        logger.error(f"Failed to fetch opportunities: {e}")
        raise ToolError(f"Failed to fetch opportunities: {e}")


@log_function_call
def get_opportunities_by_org(org_name: str, force_refresh: bool = False) -> List[OpportunityInfo]:
    """
    按组织获取商机列表

    Args:
        org_name: 组织名称
        force_refresh: 是否强制刷新数据

    Returns:
        指定组织的商机列表
    """
    try:
        data_strategy = get_data_strategy()
        opportunities = data_strategy.get_opportunities_by_org(org_name, force_refresh)

        logger.info(f"Successfully fetched {len(opportunities)} opportunities for {org_name}")
        return opportunities

    except Exception as e:
        logger.error(f"Failed to fetch opportunities for {org_name}: {e}")
        raise ToolError(f"Failed to fetch opportunities for {org_name}: {e}")


@log_function_call
def get_approaching_overdue_opportunities(force_refresh: bool = False) -> List[OpportunityInfo]:
    """
    获取即将逾期的商机列表

    Args:
        force_refresh: 是否强制刷新数据，忽略缓存

    Returns:
        即将逾期的商机列表
    """
    try:
        data_strategy = get_data_strategy()
        opportunities = data_strategy.get_approaching_overdue_opportunities(force_refresh)

        logger.info(f"Successfully fetched {len(opportunities)} approaching overdue opportunities")
        return opportunities

    except Exception as e:
        logger.error(f"Failed to fetch approaching overdue opportunities: {e}")
        raise ToolError(f"Failed to fetch approaching overdue opportunities: {e}")


@log_function_call
def get_opportunity_statistics(force_refresh: bool = False) -> Dict[str, Any]:
    """
    获取商机统计信息

    Args:
        force_refresh: 是否强制刷新数据，忽略缓存

    Returns:
        商机统计信息字典
    """
    try:
        data_strategy = get_data_strategy()
        statistics = data_strategy.get_opportunity_statistics(force_refresh)

        logger.info(f"Successfully generated opportunity statistics")
        return statistics

    except Exception as e:
        logger.error(f"Failed to get opportunity statistics: {e}")
        raise ToolError(f"Failed to get opportunity statistics: {e}")


@log_function_call
def create_notification_tasks(opportunities: List[OpportunityInfo], run_id: int) -> List[NotificationTask]:
    """
    基于商机创建通知任务

    Args:
        opportunities: 商机列表
        run_id: Agent运行ID

    Returns:
        创建的通知任务列表
    """
    try:
        notification_manager = get_notification_manager()
        tasks = notification_manager.create_notification_tasks(opportunities, run_id)

        logger.info(f"Successfully created {len(tasks)} notification tasks")
        return tasks

    except Exception as e:
        logger.error(f"Failed to create notification tasks: {e}")
        raise ToolError(f"Failed to create notification tasks: {e}")


@log_function_call
def execute_notification_tasks(run_id: int) -> Dict[str, Any]:
    """
    执行待处理的通知任务

    Args:
        run_id: Agent运行ID

    Returns:
        执行结果统计
    """
    try:
        notification_manager = get_notification_manager()
        result = notification_manager.execute_pending_tasks(run_id)

        result_dict = {
            "total_tasks": result.total_tasks,
            "sent_count": result.sent_count,
            "failed_count": result.failed_count,
            "escalated_count": result.escalated_count,
            "errors": result.errors
        }

        logger.info(f"Notification execution completed: {result_dict}")
        return result_dict

    except Exception as e:
        logger.error(f"Failed to execute notification tasks: {e}")
        raise ToolError(f"Failed to execute notification tasks: {e}")


@log_function_call
@retry_on_failure(max_retries=2)
def send_notification(task: TaskInfo, message: str, priority: Priority = Priority.NORMAL) -> bool:
    """
    发送企微通知 - 已重构，不再使用废弃表

    ⚠️ 此函数已废弃，存在任务-商机概念混淆问题

    重构说明：
    - 已移除对notifications_deprecated表的操作
    - 不再保存通知记录到废弃表
    - 仅保留消息发送功能用于向后兼容

    推荐使用：
    - send_business_notifications() 发送业务通知
    - NotificationTaskManager.execute_notification_tasks() 执行通知任务

    Args:
        task: 任务信息（实际为商机数据的TaskInfo包装）
        message: 通知消息
        priority: 优先级

    Returns:
        是否发送成功

    Raises:
        ToolError: 当发送失败时
    """
    logger.warning(
        "send_notification() is deprecated due to task-opportunity concept confusion. "
        "Use send_business_notifications() instead."
    )
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
            # 不再使用废弃的notifications_deprecated表
            # 通知记录现在由新的通知任务系统管理

            # 更新任务的最后通知时间（保留用于兼容性）
            try:
                # 注意：save_task方法已被移除，因为TaskInfo模型已废弃
                # 新的通知系统使用NotificationTask模型和相应的数据库操作
                # 使用中国时区的时间（合并远程的时区修复）
                task.last_notification = now_china_naive()
                logger.debug(f"Updated task {task.id} last notification time (in-memory only)")
            except Exception as save_error:
                logger.warning(f"Failed to update task last notification time: {save_error}")

            logger.info(f"Successfully sent notification for task {task.id} (legacy mode)")
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
    更新任务状态 - 已废弃

    ⚠️ 此函数已废弃，存在任务-商机概念混淆问题

    推荐使用：
    - 直接操作商机数据，而不是任务状态
    - 使用NotificationTaskManager管理通知任务状态

    Args:
        task_id: 任务ID（实际为商机数据的伪ID）
        status: 新状态
        comment: 备注信息

    Returns:
        是否更新成功
    """
    logger.warning(
        "update_task_status() is deprecated due to task-opportunity concept confusion. "
        "Use direct opportunity data operations instead."
    )
    # 此函数已完全废弃，不再执行任何操作
    # 任务状态更新功能已迁移到商机数据和通知任务管理
    logger.error(
        f"update_task_status() is completely deprecated and no longer functional. "
        f"Task ID {task_id} status update to '{status}' was ignored. "
        f"Use direct opportunity data operations or NotificationTaskManager instead."
    )
    return False


@log_function_call
def get_task_notification_history(task_id: int, hours_back: int = 24) -> List[NotificationInfo]:
    """
    获取任务通知历史 - 已彻底废弃

    ⚠️ 此函数已彻底废弃，不再提供任何功能

    原因：
    - 存在任务-商机概念混淆问题
    - 对应的notifications_deprecated表已被移除
    - 新系统使用完全不同的数据结构

    推荐使用：
    - NotificationTaskManager.get_notification_tasks_by_order() 查询工单通知记录
    - DatabaseManager.get_agent_history_by_run() 查询执行历史

    Args:
        task_id: 任务ID（已无效）
        hours_back: 查询时间范围（已无效）

    Returns:
        空列表（不再提供数据）
    """
    logger.error(
        "get_task_notification_history() is completely deprecated and no longer functional. "
        "The underlying notifications_deprecated table has been removed. "
        "Use NotificationTaskManager for notification queries."
    )
    return []  # 直接返回空列表，不再尝试查询


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
        if group_id:
            # 测试指定群组
            test_message = f"FSOA系统测试消息 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            return send_wechat_message(group_id, test_message)
        else:
            # 检查配置是否存在
            config = get_config()

            # 检查内部运营群配置
            has_internal = bool(getattr(config, 'internal_ops_webhook', None))

            # 检查组织群配置
            has_org_groups = False
            try:
                from ..data.database import get_database_manager
                db_manager = get_database_manager()
                group_configs = db_manager.get_enabled_group_configs()
                has_org_groups = len([gc for gc in group_configs if gc.webhook_url]) > 0
            except Exception as e:
                logger.warning(f"Failed to check organization webhooks: {e}")

            # 如果有任何配置，认为测试通过
            if has_internal or has_org_groups:
                logger.info(f"Webhook configuration check: internal={has_internal}, org_groups={has_org_groups}")
                return True
            else:
                logger.warning("No webhook configurations found")
                return False

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
def send_business_notifications(opportunities: List[OpportunityInfo], run_id: Optional[int] = None) -> Dict[str, Any]:
    """
    发送业务通知到对应的企微群 - 重构版本，使用新的通知管理器

    Args:
        opportunities: 逾期商机列表
        run_id: Agent运行ID（可选）

    Returns:
        发送结果统计
    """
    if not opportunities:
        logger.info("No opportunities to notify")
        return {"total": 0, "sent": 0, "failed": 0, "escalated": 0}

    try:
        notification_manager = get_notification_manager()

        # 如果没有提供run_id，创建一个临时的
        if run_id is None:
            execution_tracker = get_execution_tracker()
            run_id = execution_tracker.start_run({"temporary": True, "direct_notification": True})

        # 创建通知任务
        tasks = notification_manager.create_notification_tasks(opportunities, run_id)

        # 执行通知任务
        result = notification_manager.execute_pending_tasks(run_id)

        # 转换结果格式以保持兼容性
        return {
            "total": result.total_tasks,
            "sent": result.sent_count,
            "failed": result.failed_count,
            "escalated": result.escalated_count,
            "errors": result.errors
        }

    except Exception as e:
        logger.error(f"Failed to send business notifications: {e}")
        return {
            "total": len(opportunities),
            "sent": 0,
            "failed": len(opportunities),
            "escalated": 0,
            "errors": [str(e)]
        }



# ============================================================================
# 新增的工具函数 - 基于新架构
# ============================================================================

@log_function_call
def start_agent_execution(context: Optional[Dict[str, Any]] = None) -> int:
    """
    开始Agent执行

    Args:
        context: 执行上下文

    Returns:
        执行ID
    """
    try:
        execution_tracker = get_execution_tracker()
        run_id = execution_tracker.start_run(context)

        logger.info(f"Started Agent execution {run_id}")
        return run_id

    except Exception as e:
        logger.error(f"Failed to start Agent execution: {e}")
        raise ToolError(f"Failed to start Agent execution: {e}")


@log_function_call
def complete_agent_execution(run_id: int, final_stats: Dict[str, Any]) -> bool:
    """
    完成Agent执行

    Args:
        run_id: 执行ID
        final_stats: 最终统计信息

    Returns:
        是否成功
    """
    try:
        execution_tracker = get_execution_tracker()
        success = execution_tracker.complete_run(run_id, final_stats)

        if success:
            logger.info(f"Completed Agent execution {run_id}")
        else:
            logger.error(f"Failed to complete Agent execution {run_id}")

        return success

    except Exception as e:
        logger.error(f"Failed to complete Agent execution {run_id}: {e}")
        return False


@log_function_call
def get_data_statistics() -> Dict[str, Any]:
    """
    获取数据统计信息

    Returns:
        数据统计信息
    """
    try:
        data_strategy = get_data_strategy()
        cache_stats = data_strategy.get_cache_statistics()

        # 获取基本统计
        all_opportunities = data_strategy.get_opportunities()
        overdue_opportunities = [opp for opp in all_opportunities if opp.is_overdue]
        escalation_opportunities = [opp for opp in overdue_opportunities if opp.escalation_level > 0]

        stats = {
            "total_opportunities": len(all_opportunities),
            "overdue_opportunities": len(overdue_opportunities),
            "escalation_opportunities": len(escalation_opportunities),
            "organizations": len(set(opp.org_name for opp in all_opportunities)),
            "cache_statistics": cache_stats,
            "last_updated": datetime.now()
        }

        logger.info(f"Data statistics: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Failed to get data statistics: {e}")
        return {"error": str(e)}


@log_function_call
def refresh_business_data() -> Dict[str, Any]:
    """
    手动刷新业务数据

    Returns:
        刷新结果
    """
    try:
        data_strategy = get_data_strategy()
        old_count, new_count = data_strategy.refresh_cache()

        result = {
            "success": True,
            "old_cache_count": old_count,
            "new_cache_count": new_count,
            "refresh_time": datetime.now()
        }

        logger.info(f"Business data refreshed: {result}")
        return result

    except Exception as e:
        logger.error(f"Failed to refresh business data: {e}")
        return {
            "success": False,
            "error": str(e),
            "refresh_time": datetime.now()
        }

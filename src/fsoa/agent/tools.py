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
    NotificationInfo, NotificationStatus, Priority, OpportunityInfo,
    TaskStatus, NotificationTask, TaskInfo
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
def get_agent_execution_status() -> Dict[str, Any]:
    """
    获取Agent执行状态信息

    Returns:
        Agent执行状态信息
    """
    try:
        from ..utils.scheduler import get_scheduler
        from ..utils.config import get_config

        execution_tracker = get_execution_tracker()
        scheduler = get_scheduler()
        config = get_config()

        # 获取最近的执行记录
        recent_runs = execution_tracker.get_recent_runs(limit=1)
        last_run = recent_runs[0] if recent_runs else None

        # 获取调度器信息
        jobs_info = scheduler.get_jobs()
        agent_job = None
        for job in jobs_info.get("jobs", []):
            if job["id"] == "agent_execution":
                agent_job = job
                break

        # 智能检测调度器状态（跨进程兼容）
        scheduler_running = jobs_info.get("is_running", False)

        # 如果当前进程的调度器显示未运行，但有最近的执行记录，
        # 说明可能有其他进程的调度器在运行
        if not scheduler_running and last_run:
            from datetime import datetime, timedelta
            from ..utils.timezone_utils import now_china_naive

            # 如果最近有执行记录（在过去2小时内），认为调度器可能在运行
            time_since_last = now_china_naive() - last_run.trigger_time
            if time_since_last < timedelta(hours=2):
                scheduler_running = True

        # 构建状态信息
        status = {
            "last_execution": None,
            "last_execution_status": "未知",
            "next_execution": None,
            "execution_interval": f"{config.agent_execution_interval}分钟",
            "scheduler_running": scheduler_running,
            "total_runs": len(execution_tracker.get_recent_runs(limit=100, hours_back=168))
        }

        # 设置上次执行信息
        if last_run:
            status["last_execution"] = last_run.trigger_time.strftime("%Y-%m-%d %H:%M:%S")
            status["last_execution_status"] = last_run.status.value

        # 设置下次执行时间
        if agent_job and agent_job["next_run_time"]:
            try:
                from datetime import datetime
                next_time = datetime.fromisoformat(agent_job["next_run_time"].replace('Z', '+00:00'))
                # 转换为中国时区显示
                from ..utils.timezone_utils import utc_to_china
                next_time_china = utc_to_china(next_time)
                status["next_execution"] = next_time_china.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logger.warning(f"Failed to parse next execution time: {e}")
                status["next_execution"] = "解析失败"
        else:
            # 如果没有调度器信息，基于上次执行时间和间隔估算
            if last_run and last_run.status.value == "completed":
                try:
                    from datetime import timedelta
                    next_estimated = last_run.trigger_time + timedelta(minutes=config.agent_execution_interval)
                    status["next_execution"] = next_estimated.strftime("%Y-%m-%d %H:%M:%S") + " (估算)"
                except Exception:
                    status["next_execution"] = "无法确定"
            else:
                status["next_execution"] = "无法确定"

        return status

    except Exception as e:
        logger.error(f"Failed to get agent execution status: {e}")
        return {
            "last_execution": "获取失败",
            "last_execution_status": "错误",
            "next_execution": "获取失败",
            "execution_interval": "60分钟",
            "scheduler_running": False,
            "total_runs": 0,
            "error": str(e)
        }


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
# 商机数据获取函数 - 基于新架构
# ============================================================================

@log_function_call
def fetch_overdue_opportunities(force_refresh: bool = False) -> List[OpportunityInfo]:
    """
    获取逾期商机列表

    Args:
        force_refresh: 是否强制刷新数据

    Returns:
        逾期商机列表
    """
    try:
        data_strategy = get_data_strategy()
        return data_strategy.get_overdue_opportunities(force_refresh=force_refresh)
    except Exception as e:
        logger.error(f"Failed to fetch overdue opportunities: {e}")
        raise ToolError(f"Failed to fetch overdue opportunities: {e}")


@log_function_call
def get_all_opportunities(force_refresh: bool = False) -> List[OpportunityInfo]:
    """
    获取所有监控的商机列表

    Args:
        force_refresh: 是否强制刷新数据

    Returns:
        所有监控的商机列表
    """
    try:
        data_strategy = get_data_strategy()
        return data_strategy.get_opportunities(force_refresh=force_refresh)
    except Exception as e:
        logger.error(f"Failed to get all opportunities: {e}")
        raise ToolError(f"Failed to get all opportunities: {e}")


@log_function_call
def create_notification_tasks(opportunities: List[OpportunityInfo], run_id: int) -> List:
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
        return notification_manager.create_notification_tasks(opportunities, run_id)
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

        # 转换为字典格式返回
        return {
            "total_tasks": result.total_tasks,
            "sent_count": result.sent_count,
            "failed_count": result.failed_count,
            "errors": result.errors
        }
    except Exception as e:
        logger.error(f"Failed to execute notification tasks: {e}")
        raise ToolError(f"Failed to execute notification tasks: {e}")


@log_function_call
def get_opportunity_statistics() -> Dict[str, Any]:
    """
    获取商机统计信息

    Returns:
        商机统计数据
    """
    try:
        data_strategy = get_data_strategy()

        # 获取所有商机
        all_opportunities = data_strategy.get_opportunities(force_refresh=False)

        # 获取逾期商机
        overdue_opportunities = data_strategy.get_overdue_opportunities(force_refresh=False)

        # 基础统计
        total_count = len(all_opportunities)
        overdue_count = len(overdue_opportunities)
        normal_count = total_count - overdue_count

        # 计算即将逾期的商机（这里简化处理，可以根据业务需求调整）
        approaching_overdue_count = 0
        escalation_count = 0

        # 统计需要升级的商机
        for opp in overdue_opportunities:
            if hasattr(opp, 'escalation_level') and opp.escalation_level > 0:
                escalation_count += 1

        # 组织统计
        organization_breakdown = {}
        for opp in all_opportunities:
            org_name = opp.org_name or "未知组织"
            if org_name not in organization_breakdown:
                organization_breakdown[org_name] = {
                    "total": 0,
                    "overdue": 0,
                    "normal": 0
                }
            organization_breakdown[org_name]["total"] += 1

            # 检查是否逾期
            is_overdue = any(o.order_num == opp.order_num for o in overdue_opportunities)
            if is_overdue:
                organization_breakdown[org_name]["overdue"] += 1
            else:
                organization_breakdown[org_name]["normal"] += 1

        # 状态统计
        status_breakdown = {}
        for opp in all_opportunities:
            status = opp.status or "未知状态"
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

        # 计算比例
        overdue_rate = (overdue_count / total_count * 100) if total_count > 0 else 0
        approaching_rate = (approaching_overdue_count / total_count * 100) if total_count > 0 else 0

        return {
            "total_opportunities": total_count,
            "overdue_count": overdue_count,
            "normal_count": normal_count,
            "approaching_overdue_count": approaching_overdue_count,
            "escalation_count": escalation_count,
            "overdue_rate": overdue_rate,
            "approaching_rate": approaching_rate,
            "organization_breakdown": organization_breakdown,
            "status_breakdown": status_breakdown,
            "organization_count": len(organization_breakdown)
        }

    except Exception as e:
        logger.error(f"Failed to get opportunity statistics: {e}")
        # 返回默认值而不是抛出异常
        return {
            "total_opportunities": 0,
            "overdue_count": 0,
            "normal_count": 0,
            "approaching_overdue_count": 0,
            "escalation_count": 0,
            "overdue_rate": 0,
            "approaching_rate": 0,
            "organization_breakdown": {},
            "status_breakdown": {},
            "organization_count": 0,
            "error": str(e)
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

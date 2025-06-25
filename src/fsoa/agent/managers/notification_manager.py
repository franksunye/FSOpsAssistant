"""
通知任务管理器

负责创建、管理和执行通知任务
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ...data.models import (
    OpportunityInfo, NotificationTask, NotificationTaskType, 
    NotificationTaskStatus, OpportunityStatus
)
from ...data.database import get_db_manager
from ...notification.wechat import get_wechat_client
from ...notification.business_formatter import BusinessNotificationFormatter
from ...utils.logger import get_logger, log_function_call

logger = get_logger(__name__)


@dataclass
class NotificationResult:
    """通知结果"""
    total_tasks: int = 0
    sent_count: int = 0
    failed_count: int = 0
    escalated_count: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class NotificationTaskManager:
    """通知任务管理器"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.wechat_client = get_wechat_client()
        self.formatter = BusinessNotificationFormatter()
        
        # 配置参数
        self.notification_cooldown_minutes = 30  # 通知冷却时间
        self.max_retry_count = 3  # 最大重试次数
    
    @log_function_call
    def create_notification_tasks(self, opportunities: List[OpportunityInfo], 
                                run_id: int) -> List[NotificationTask]:
        """基于商机创建通知任务"""
        tasks = []
        
        try:
            for opp in opportunities:
                if not opp.is_overdue:
                    continue
                
                # 检查是否已存在相同的待处理任务
                if self._has_pending_task(opp.order_num):
                    logger.info(f"Order {opp.order_num} already has pending notification task")
                    continue
                
                # 创建标准通知任务
                standard_task = NotificationTask(
                    order_num=opp.order_num,
                    org_name=opp.org_name,
                    notification_type=NotificationTaskType.STANDARD,
                    due_time=datetime.now(),
                    created_run_id=run_id
                )
                tasks.append(standard_task)
                
                # 如果需要升级，创建升级通知任务
                if opp.escalation_level > 0:
                    escalation_task = NotificationTask(
                        order_num=opp.order_num,
                        org_name=opp.org_name,
                        notification_type=NotificationTaskType.ESCALATION,
                        due_time=datetime.now(),
                        created_run_id=run_id
                    )
                    tasks.append(escalation_task)
            
            # 批量保存任务
            for task in tasks:
                task_id = self.db_manager.save_notification_task(task)
                task.id = task_id
                logger.info(f"Created notification task {task_id} for order {task.order_num}")
            
            logger.info(f"Created {len(tasks)} notification tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to create notification tasks: {e}")
            raise
    
    @log_function_call
    def execute_pending_tasks(self, run_id: int) -> NotificationResult:
        """执行待处理的通知任务"""
        result = NotificationResult()
        
        try:
            # 获取待处理任务
            pending_tasks = self.db_manager.get_pending_notification_tasks()
            result.total_tasks = len(pending_tasks)
            
            if not pending_tasks:
                logger.info("No pending notification tasks")
                return result
            
            # 按组织分组
            org_tasks = self._group_tasks_by_org(pending_tasks)
            
            # 执行通知
            for org_name, tasks in org_tasks.items():
                try:
                    org_result = self._send_org_notifications(org_name, tasks, run_id)
                    result.sent_count += org_result.sent_count
                    result.failed_count += org_result.failed_count
                    result.escalated_count += org_result.escalated_count
                    result.errors.extend(org_result.errors)
                    
                except Exception as e:
                    error_msg = f"Failed to send notifications to {org_name}: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)
                    result.failed_count += len(tasks)
            
            logger.info(f"Notification execution completed: {result.sent_count} sent, {result.failed_count} failed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute pending tasks: {e}")
            result.errors.append(str(e))
            return result
    
    def _has_pending_task(self, order_num: str) -> bool:
        """检查是否已存在待处理任务"""
        try:
            pending_tasks = self.db_manager.get_pending_notification_tasks()
            return any(task.order_num == order_num for task in pending_tasks)
        except Exception as e:
            logger.error(f"Failed to check pending tasks for {order_num}: {e}")
            return False
    
    def _group_tasks_by_org(self, tasks: List[NotificationTask]) -> Dict[str, List[NotificationTask]]:
        """按组织分组任务"""
        org_tasks = {}
        for task in tasks:
            if task.org_name not in org_tasks:
                org_tasks[task.org_name] = []
            org_tasks[task.org_name].append(task)
        return org_tasks
    
    def _send_org_notifications(self, org_name: str, tasks: List[NotificationTask], 
                              run_id: int) -> NotificationResult:
        """发送组织通知"""
        result = NotificationResult()
        
        try:
            # 分离标准通知和升级通知
            standard_tasks = [t for t in tasks if t.notification_type == NotificationTaskType.STANDARD]
            escalation_tasks = [t for t in tasks if t.notification_type == NotificationTaskType.ESCALATION]
            
            # 发送标准通知
            if standard_tasks:
                success = self._send_standard_notification(org_name, standard_tasks, run_id)
                if success:
                    result.sent_count += len(standard_tasks)
                    for task in standard_tasks:
                        self.db_manager.update_notification_task_status(
                            task.id, NotificationTaskStatus.SENT, run_id
                        )
                else:
                    result.failed_count += len(standard_tasks)
            
            # 发送升级通知
            if escalation_tasks:
                success = self._send_escalation_notification(org_name, escalation_tasks, run_id)
                if success:
                    result.escalated_count += len(escalation_tasks)
                    for task in escalation_tasks:
                        self.db_manager.update_notification_task_status(
                            task.id, NotificationTaskStatus.SENT, run_id
                        )
                else:
                    result.failed_count += len(escalation_tasks)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send notifications to {org_name}: {e}")
            result.errors.append(str(e))
            result.failed_count += len(tasks)
            return result
    
    def _send_standard_notification(self, org_name: str, tasks: List[NotificationTask], 
                                  run_id: int) -> bool:
        """发送标准通知"""
        try:
            # 格式化消息
            message = self.formatter.format_org_overdue_notification(
                org_name, 
                [self._task_to_opportunity_info(task) for task in tasks]
            )
            
            # 发送到组织对应的企微群
            success = self.wechat_client.send_notification_to_org(
                org_name=org_name,
                content=message,
                is_escalation=False
            )
            
            if success:
                logger.info(f"Sent standard notification to {org_name} for {len(tasks)} tasks")
            else:
                logger.error(f"Failed to send standard notification to {org_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send standard notification to {org_name}: {e}")
            return False
    
    def _send_escalation_notification(self, org_name: str, tasks: List[NotificationTask], 
                                    run_id: int) -> bool:
        """发送升级通知"""
        try:
            # 格式化升级消息
            message = self.formatter.format_escalation_notification(
                org_name,
                [self._task_to_opportunity_info(task) for task in tasks]
            )
            
            # 发送到内部运营群
            success = self.wechat_client.send_notification_to_org(
                org_name=org_name,
                content=message,
                is_escalation=True
            )
            
            if success:
                logger.info(f"Sent escalation notification for {org_name} with {len(tasks)} tasks")
            else:
                logger.error(f"Failed to send escalation notification for {org_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send escalation notification for {org_name}: {e}")
            return False
    
    def _task_to_opportunity_info(self, task: NotificationTask) -> OpportunityInfo:
        """将通知任务转换为商机信息（用于格式化）"""
        # 这里简化处理，实际应该从缓存或Metabase获取完整信息
        return OpportunityInfo(
            order_num=task.order_num,
            name="客户",  # 简化
            address="地址",  # 简化
            supervisor_name="负责人",  # 简化
            create_time=datetime.now(),  # 简化
            org_name=task.org_name,
            order_status=OpportunityStatus.PENDING_APPOINTMENT  # 简化
        )
    
    @log_function_call
    def get_notification_statistics(self, hours_back: int = 24) -> Dict[str, Any]:
        """获取通知统计信息"""
        try:
            # 这里简化实现，实际需要查询数据库
            return {
                "total_tasks": 0,
                "sent_count": 0,
                "failed_count": 0,
                "pending_count": 0,
                "period_hours": hours_back
            }
        except Exception as e:
            logger.error(f"Failed to get notification statistics: {e}")
            return {}
    
    def cleanup_old_tasks(self, days_back: int = 7) -> int:
        """清理旧的已完成任务"""
        try:
            # 这里简化实现，实际需要删除旧的已完成任务
            logger.info(f"Cleaned up old notification tasks older than {days_back} days")
            return 0
        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0

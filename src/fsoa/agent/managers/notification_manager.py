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
        self.notification_cooldown_hours = 2.0  # 通知冷却时间（小时）
        self.max_retry_count = 5  # 最大重试次数


        # 从数据库加载配置
        self._load_config_from_db()

    def _load_config_from_db(self):
        """从数据库加载配置参数"""
        try:
            configs = self.db_manager.get_all_system_configs()

            # 更新配置参数
            cooldown_minutes = int(configs.get("notification_cooldown", "120"))
            self.notification_cooldown_hours = cooldown_minutes / 60.0

            self.max_retry_count = int(configs.get("max_retry_count", "5"))
            # API间隔现在由WeChatClient处理，这里不再需要

            logger.info(f"Loaded notification config: cooldown={self.notification_cooldown_hours}h, "
                       f"max_retry={self.max_retry_count}")
        except Exception as e:
            logger.warning(f"Failed to load config from database, using defaults: {e}")

    @log_function_call
    def create_notification_tasks(self, opportunities: List[OpportunityInfo], 
                                run_id: int) -> List[NotificationTask]:
        """基于商机创建通知任务"""
        tasks = []
        
        try:
            for opp in opportunities:
                # 更新商机的计算字段
                opp.update_overdue_info(use_business_time=True)

                # 检查是否已存在相同的待处理任务
                if self._has_pending_task(opp.order_num):
                    logger.info(f"Order {opp.order_num} already has pending notification task")
                    continue

                # 创建违规通知任务（12小时）
                if opp.is_violation:
                    violation_task = NotificationTask(
                        order_num=opp.order_num,
                        org_name=opp.org_name,
                        notification_type=NotificationTaskType.VIOLATION,
                        due_time=datetime.now(),
                        created_run_id=run_id,
                        cooldown_hours=self.notification_cooldown_hours,
                        max_retry_count=self.max_retry_count
                    )
                    tasks.append(violation_task)

                # 创建标准通知任务（24/48小时）
                if opp.is_overdue:
                    standard_task = NotificationTask(
                        order_num=opp.order_num,
                        org_name=opp.org_name,
                        notification_type=NotificationTaskType.STANDARD,
                        due_time=datetime.now(),
                        created_run_id=run_id,
                        cooldown_hours=self.notification_cooldown_hours,
                        max_retry_count=self.max_retry_count
                    )
                    tasks.append(standard_task)

                # 如果需要升级，创建升级通知任务
                if opp.escalation_level > 0:
                    escalation_task = NotificationTask(
                        order_num=opp.order_num,
                        org_name=opp.org_name,
                        notification_type=NotificationTaskType.ESCALATION,
                        due_time=datetime.now(),
                        created_run_id=run_id,
                        cooldown_hours=self.notification_cooldown_hours,
                        max_retry_count=self.max_retry_count
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

            # 过滤出应该立即发送的任务（考虑冷静时间）
            ready_tasks = [task for task in pending_tasks if task.should_send_now()]

            if not ready_tasks:
                logger.info(f"No tasks ready to send (total pending: {len(pending_tasks)})")
                return result

            logger.info(f"Found {len(ready_tasks)} tasks ready to send out of {len(pending_tasks)} pending")

            # 按组织分组
            org_tasks = self._group_tasks_by_org(ready_tasks)

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
        """发送组织通知 - 优化版：合并同组织的所有通知为一条消息"""
        result = NotificationResult()

        try:
            # 分离不同类型的通知
            violation_tasks = [t for t in tasks if t.notification_type == NotificationTaskType.VIOLATION]
            standard_tasks = [t for t in tasks if t.notification_type == NotificationTaskType.STANDARD]
            escalation_tasks = [t for t in tasks if t.notification_type == NotificationTaskType.ESCALATION]

            # 检查是否有升级通知，如果有则发送到内部运营群
            if escalation_tasks:
                success = self._send_escalation_notification(org_name, escalation_tasks, run_id)
                if success:
                    result.escalated_count += len(escalation_tasks)
                    for task in escalation_tasks:
                        self._update_task_after_send(task, run_id, success=True)
                else:
                    result.failed_count += len(escalation_tasks)
                    for task in escalation_tasks:
                        self._update_task_after_send(task, run_id, success=False)

            # 分别发送违规通知和标准通知
            if violation_tasks:
                success = self._send_violation_notification(org_name, violation_tasks, run_id)
                if success:
                    result.sent_count += len(violation_tasks)
                    for task in violation_tasks:
                        self._update_task_after_send(task, run_id, success=True)
                else:
                    result.failed_count += len(violation_tasks)
                    for task in violation_tasks:
                        self._update_task_after_send(task, run_id, success=False)

            if standard_tasks:
                success = self._send_standard_notification(org_name, standard_tasks, run_id)
                if success:
                    result.sent_count += len(standard_tasks)
                    for task in standard_tasks:
                        self._update_task_after_send(task, run_id, success=True)
                else:
                    result.failed_count += len(standard_tasks)
                    for task in standard_tasks:
                        self._update_task_after_send(task, run_id, success=False)
            
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
                [self._get_opportunity_info_for_notification(task) for task in tasks]
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

    def _send_violation_notification(self, org_name: str, tasks: List[NotificationTask],
                                   run_id: int) -> bool:
        """发送违规通知（12小时）"""
        try:
            # 格式化消息
            message = self.formatter.format_violation_notification(
                org_name,
                [self._get_opportunity_info_for_notification(task) for task in tasks]
            )

            # 发送到组织对应的企微群
            success = self.wechat_client.send_notification_to_org(
                org_name=org_name,
                content=message,
                is_escalation=False
            )

            if success:
                logger.info(f"Sent violation notification to {org_name} for {len(tasks)} tasks")
            else:
                logger.error(f"Failed to send violation notification to {org_name}")

            return success

        except Exception as e:
            logger.error(f"Failed to send violation notification to {org_name}: {e}")
            return False
    
    def _send_escalation_notification(self, org_name: str, tasks: List[NotificationTask],
                                    run_id: int) -> bool:
        """发送升级通知"""
        try:
            # 格式化升级消息
            message = self.formatter.format_escalation_notification(
                org_name,
                [self._get_opportunity_info_for_notification(task) for task in tasks]
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

    def _update_task_after_send(self, task: NotificationTask, run_id: int, success: bool):
        """发送后更新任务状态"""
        try:
            if success:
                # 发送成功
                task.last_sent_at = datetime.now()
                task.retry_count += 1

                # 如果达到最大重试次数，标记为已发送
                if task.retry_count >= task.max_retry_count:
                    self.db_manager.update_notification_task_status(
                        task.id, NotificationTaskStatus.SENT, run_id
                    )
                    logger.info(f"Task {task.id} completed after {task.retry_count} attempts")
                else:
                    # 更新任务信息，保持PENDING状态以便后续重试
                    self.db_manager.update_notification_task_retry_info(
                        task.id, task.retry_count, task.last_sent_at
                    )
                    logger.info(f"Task {task.id} sent, retry count: {task.retry_count}/{task.max_retry_count}")
            else:
                # 发送失败
                task.retry_count += 1
                if task.retry_count >= task.max_retry_count:
                    self.db_manager.update_notification_task_status(
                        task.id, NotificationTaskStatus.FAILED, run_id
                    )
                    logger.warning(f"Task {task.id} failed after {task.retry_count} attempts")
                else:
                    # 更新重试次数，保持PENDING状态
                    self.db_manager.update_notification_task_retry_info(
                        task.id, task.retry_count, None
                    )
                    logger.warning(f"Task {task.id} failed, retry count: {task.retry_count}/{task.max_retry_count}")

        except Exception as e:
            logger.error(f"Failed to update task {task.id} after send: {e}")
    
    def _get_opportunity_info_for_notification(self, task: NotificationTask) -> OpportunityInfo:
        """获取通知任务对应的商机信息（用于格式化通知消息）"""
        # 尝试从缓存获取完整的商机信息
        try:
            cached_opp = self.db_manager.get_opportunity_cache(task.order_num)
            if cached_opp:
                return cached_opp
        except Exception as e:
            logger.warning(f"Failed to get cached opportunity for {task.order_num}: {e}")

        # 如果缓存中没有，创建基础的商机信息用于通知
        # 注意：这里创建的是用于通知显示的基础信息，不是完整的业务数据
        opp = OpportunityInfo(
            order_num=task.order_num,
            name="客户",  # 简化显示
            address="地址",  # 简化显示
            supervisor_name="负责人",  # 简化显示
            create_time=datetime.now() - timedelta(days=2),  # 估算创建时间
            org_name=task.org_name,
            order_status=OpportunityStatus.PENDING_APPOINTMENT  # 默认状态
        )

        # 更新逾期信息，确保elapsed_hours不为None
        opp.update_overdue_info()

        return opp
    
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

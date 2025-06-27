"""
通知任务管理器

负责创建、管理和执行通知任务
"""

from datetime import timedelta

# 导入时区工具
from ...utils.timezone_utils import now_china_naive
from typing import List, Dict, Any
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
            # 用于跟踪当前批次中已创建的任务，避免重复
            created_tasks_tracker = set()

            for opp in opportunities:
                # 更新商机的计算字段
                opp.update_overdue_info(use_business_time=True)

                # 创建违规通知任务（12小时）
                if opp.is_violation:
                    task_key = (opp.order_num, NotificationTaskType.VIOLATION)
                    # 检查数据库中是否已存在 + 检查当前批次中是否已创建
                    if (not self._has_pending_task(opp.order_num, NotificationTaskType.VIOLATION) and
                        task_key not in created_tasks_tracker):
                        violation_task = NotificationTask(
                            order_num=opp.order_num,
                            org_name=opp.org_name,
                            notification_type=NotificationTaskType.VIOLATION,
                            due_time=now_china_naive(),
                            created_run_id=run_id,
                            cooldown_hours=self.notification_cooldown_hours,
                            max_retry_count=self.max_retry_count
                        )
                        tasks.append(violation_task)
                        created_tasks_tracker.add(task_key)
                    else:
                        logger.info(f"Order {opp.order_num} already has pending/recent VIOLATION notification")

                # 创建标准通知任务（24/48小时）
                if opp.is_overdue:
                    task_key = (opp.order_num, NotificationTaskType.STANDARD)
                    # 检查数据库中是否已存在 + 检查当前批次中是否已创建
                    if (not self._has_pending_task(opp.order_num, NotificationTaskType.STANDARD) and
                        task_key not in created_tasks_tracker):
                        standard_task = NotificationTask(
                            order_num=opp.order_num,
                            org_name=opp.org_name,
                            notification_type=NotificationTaskType.STANDARD,
                            due_time=now_china_naive(),
                            created_run_id=run_id,
                            cooldown_hours=self.notification_cooldown_hours,
                            max_retry_count=self.max_retry_count
                        )
                        tasks.append(standard_task)
                        created_tasks_tracker.add(task_key)
                    else:
                        logger.info(f"Order {opp.order_num} already has pending/recent STANDARD notification")

                # 如果需要升级，创建升级通知任务
                if opp.escalation_level > 0:
                    task_key = (opp.order_num, NotificationTaskType.ESCALATION)
                    # 检查数据库中是否已存在 + 检查当前批次中是否已创建
                    if (not self._has_pending_task(opp.order_num, NotificationTaskType.ESCALATION) and
                        task_key not in created_tasks_tracker):
                        escalation_task = NotificationTask(
                            order_num=opp.order_num,
                            org_name=opp.org_name,
                            notification_type=NotificationTaskType.ESCALATION,
                            due_time=now_china_naive(),
                            created_run_id=run_id,
                            cooldown_hours=self.notification_cooldown_hours,
                            max_retry_count=self.max_retry_count
                        )
                        tasks.append(escalation_task)
                        created_tasks_tracker.add(task_key)
                    else:
                        logger.info(f"Order {opp.order_num} already has pending/recent ESCALATION notification")
            
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
    
    def _has_pending_task(self, order_num: str, notification_type: NotificationTaskType = None) -> bool:
        """检查是否已存在待处理任务或在冷却期内的已发送任务

        Args:
            order_num: 订单号
            notification_type: 通知类型，如果指定则只检查该类型的通知
        """
        try:
            # 检查是否有待处理任务
            pending_tasks = self.db_manager.get_pending_notification_tasks()
            if notification_type:
                # 检查特定类型的待处理任务
                if any(task.order_num == order_num and task.notification_type == notification_type
                       for task in pending_tasks):
                    return True
            else:
                # 检查任意类型的待处理任务（向后兼容）
                if any(task.order_num == order_num for task in pending_tasks):
                    return True

            # 检查是否在冷却期内已发送过相同类型的通知
            cooldown_cutoff = now_china_naive() - timedelta(hours=self.notification_cooldown_hours)

            if notification_type:
                # 检查特定类型的最近通知
                recent_tasks = self.db_manager.get_recent_notification_tasks(
                    order_num,
                    since=cooldown_cutoff,
                    notification_type=notification_type.value
                )
                if recent_tasks:
                    logger.info(f"Order {order_num} has recent {notification_type.value} notifications within cooldown period")
                    return True
            else:
                # 检查任意类型的最近通知（向后兼容）
                recent_tasks = self.db_manager.get_recent_notification_tasks(
                    order_num,
                    since=cooldown_cutoff
                )
                if recent_tasks:
                    logger.info(f"Order {order_num} has recent notifications within cooldown period")
                    return True

            return False
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
    
    def _format_notification_message(self, org_name: str, tasks: List[NotificationTask],
                                   notification_type: NotificationTaskType) -> str:
        """格式化通知消息"""
        try:
            # 获取商机信息并按工单号去重
            opportunities_dict = {}
            for task in tasks:
                if task.order_num not in opportunities_dict:
                    opportunities_dict[task.order_num] = task.to_opportunity_info()

            opportunities = list(opportunities_dict.values())

            if self.use_llm_formatting and self.llm_client:
                # 使用LLM格式化
                return self._format_with_llm(org_name, opportunities, notification_type)
            else:
                # 使用标准模板
                return self._format_with_template(org_name, opportunities, notification_type)

        except Exception as e:
            logger.error(f"Failed to format message: {e}")
            # 降级到标准模板 - 使用简化的商机信息
            opportunities = [self._get_opportunity_info_for_notification(tasks[0])] if tasks else []
            return self._format_with_template(org_name, opportunities, notification_type)
    
    def _format_with_llm(self, org_name: str, opportunities: List[OpportunityInfo],
                        notification_type: NotificationTaskType) -> str:
        """使用LLM格式化消息"""
        try:
            # 构建LLM提示词
            prompt = self._build_llm_formatting_prompt(org_name, opportunities, notification_type)
            
            response = self.llm_client.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 低温度确保格式一致性
                max_tokens=800
            )
            
            message = response.choices[0].message.content.strip()
            logger.info(f"Generated LLM message for {org_name}")
            return message
            
        except Exception as e:
            logger.error(f"LLM formatting failed: {e}")
            # 降级到标准模板
            return self._format_with_template(org_name, opportunities, notification_type)
    
    def _format_with_template(self, org_name: str, opportunities: List[OpportunityInfo],
                            notification_type: NotificationTaskType) -> str:
        """使用标准模板格式化消息"""
        if notification_type == NotificationTaskType.VIOLATION:
            return self.formatter.format_violation_notification(org_name, opportunities)
        elif notification_type == NotificationTaskType.ESCALATION:
            return self.formatter.format_escalation_notification(org_name, opportunities)
        else:
            return self.formatter.format_org_overdue_notification(org_name, opportunities)
    
    def _build_llm_formatting_prompt(self, org_name: str, opportunities: List[OpportunityInfo],
                                   notification_type: NotificationTaskType) -> str:
        """构建LLM格式化提示词"""
        type_desc = {
            NotificationTaskType.VIOLATION: "违规通知（12小时未处理）",
            NotificationTaskType.STANDARD: "逾期提醒（24/48小时）",
            NotificationTaskType.ESCALATION: "升级通知（运营介入）"
        }
        
        opp_list = []
        for i, opp in enumerate(opportunities, 1):
            opp_list.append(f"{i}. 工单号：{opp.order_num}")
            opp_list.append(f"   客户：{opp.name}")
            opp_list.append(f"   地址：{opp.address}")
            opp_list.append(f"   负责人：{opp.supervisor_name}")
            opp_list.append(f"   已过时长：{opp.elapsed_hours:.1f}小时")
            opp_list.append("")
        
        prompt = f"""请为以下{type_desc.get(notification_type, "通知")}生成专业的企微群消息。

组织：{org_name}
通知类型：{type_desc.get(notification_type)}
工单信息：
{chr(10).join(opp_list)}

要求：
1. 使用适当的emoji（🚨违规、⚠️逾期、🔥升级）
2. 格式清晰，信息完整
3. 语气专业但紧迫
4. 包含明确的行动指示
5. 长度控制在500字以内

请直接返回消息内容，不需要解释。"""
        
        return prompt

    def _send_standard_notification(self, org_name: str, tasks: List[NotificationTask],
                                  run_id: int) -> bool:
        """发送标准通知"""
        try:
            # 格式化消息
            message = self._format_notification_message(org_name, tasks, NotificationTaskType.STANDARD)

            # 保存消息内容到任务记录中
            for task in tasks:
                if not task.message:  # 只在首次发送时保存消息
                    task.message = message
                    self.db_manager.update_notification_task_message(task.id, message)

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
            message = self._format_notification_message(org_name, tasks, NotificationTaskType.VIOLATION)

            # 保存消息内容到任务记录中
            for task in tasks:
                if not task.message:  # 只在首次发送时保存消息
                    task.message = message
                    self.db_manager.update_notification_task_message(task.id, message)

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
            # 格式化升级消息 - 按工单号去重
            opportunities_dict = {}
            for task in tasks:
                if task.order_num not in opportunities_dict:
                    opportunities_dict[task.order_num] = self._get_opportunity_info_for_notification(task)

            opportunities = list(opportunities_dict.values())
            message = self.formatter.format_escalation_notification(org_name, opportunities)

            # 保存消息内容到任务记录中
            for task in tasks:
                if not task.message:  # 只在首次发送时保存消息
                    task.message = message
                    self.db_manager.update_notification_task_message(task.id, message)

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
                # 发送成功，立即标记为已发送
                task.last_sent_at = now_china_naive()
                task.retry_count += 1

                self.db_manager.update_notification_task_status(
                    task.id, NotificationTaskStatus.SENT, run_id
                )
                logger.info(f"Task {task.id} completed successfully after {task.retry_count} attempts")
            else:
                # 发送失败，增加重试次数
                task.retry_count += 1
                if task.retry_count >= task.max_retry_count:
                    # 达到最大重试次数，标记为失败
                    self.db_manager.update_notification_task_status(
                        task.id, NotificationTaskStatus.FAILED, run_id
                    )
                    logger.warning(f"Task {task.id} failed after {task.retry_count} attempts")
                else:
                    # 更新重试次数，保持PENDING状态以便后续重试
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

        # 尝试从数据策略管理器获取最新数据
        try:
            from .data_strategy import get_data_strategy_manager
            data_manager = get_data_strategy_manager()
            all_opportunities = data_manager.get_opportunities()

            # 查找匹配的商机
            for opp in all_opportunities:
                if opp.order_num == task.order_num:
                    return opp
        except Exception as e:
            logger.warning(f"Failed to get opportunity from data manager for {task.order_num}: {e}")

        # 如果都获取不到，创建基础的商机信息用于通知
        # 注意：这里创建的是用于通知显示的基础信息，不是完整的业务数据
        opp = OpportunityInfo(
            order_num=task.order_num,
            name="客户",  # 简化显示
            address="地址",  # 简化显示
            supervisor_name="负责人",  # 简化显示
            create_time=now_china_naive() - timedelta(days=2),  # 估算创建时间
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
            from datetime import timedelta
            from ...utils.timezone_utils import now_china_naive
            from ...data.database import NotificationTaskTable

            # 计算时间范围
            end_time = now_china_naive()
            start_time = end_time - timedelta(hours=hours_back)

            with self.db_manager.get_session() as session:
                # 查询指定时间范围内的所有任务
                all_tasks = session.query(NotificationTaskTable).filter(
                    NotificationTaskTable.created_at >= start_time
                ).all()

                # 统计各种状态的任务数量
                total_tasks = len(all_tasks)
                sent_count = len([t for t in all_tasks if t.status in ['sent', 'confirmed']])
                failed_count = len([t for t in all_tasks if t.status == 'failed'])
                pending_count = len([t for t in all_tasks if t.status == 'pending'])

                # 如果没有指定时间范围的数据，查询所有历史数据
                if total_tasks == 0:
                    all_historical_tasks = session.query(NotificationTaskTable).all()
                    total_tasks = len(all_historical_tasks)
                    sent_count = len([t for t in all_historical_tasks if t.status in ['sent', 'confirmed']])
                    failed_count = len([t for t in all_historical_tasks if t.status == 'failed'])
                    pending_count = len([t for t in all_historical_tasks if t.status == 'pending'])

                logger.info(f"Notification statistics: {total_tasks} total, {sent_count} sent, {failed_count} failed, {pending_count} pending")

                return {
                    "total_tasks": total_tasks,
                    "sent_count": sent_count,
                    "failed_count": failed_count,
                    "pending_count": pending_count,
                    "period_hours": hours_back,
                    "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S")
                }

        except Exception as e:
            logger.error(f"Failed to get notification statistics: {e}")
            return {
                "total_tasks": 0,
                "sent_count": 0,
                "failed_count": 0,
                "pending_count": 0,
                "period_hours": hours_back,
                "error": str(e)
            }
    
    def cleanup_old_tasks(self, days_back: int = 7) -> int:
        """清理旧的已完成任务

        Args:
            days_back: 清理多少天前的任务，默认7天

        Returns:
            清理的任务数量
        """
        try:
            from datetime import timedelta
            from ...utils.timezone_utils import now_china_naive
            from ...data.database import NotificationTaskTable

            # 计算截止时间
            cutoff_time = now_china_naive() - timedelta(days=days_back)

            with self.db_manager.get_session() as session:
                # 查询要清理的任务（已完成且超过指定天数）
                old_tasks_query = session.query(NotificationTaskTable).filter(
                    NotificationTaskTable.created_at < cutoff_time,
                    NotificationTaskTable.status.in_(['sent', 'confirmed', 'failed'])
                )

                # 获取要删除的任务数量
                count_to_delete = old_tasks_query.count()

                if count_to_delete > 0:
                    # 记录要删除的任务信息
                    logger.info(f"Found {count_to_delete} old notification tasks to cleanup (older than {days_back} days)")

                    # 执行删除
                    deleted_count = old_tasks_query.delete()
                    session.commit()

                    logger.info(f"Successfully cleaned up {deleted_count} old notification tasks")
                    return deleted_count
                else:
                    logger.info(f"No old notification tasks found to cleanup (older than {days_back} days)")
                    return 0

        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0

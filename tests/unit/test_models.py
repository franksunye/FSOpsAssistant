"""
数据模型测试
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.fsoa.data.models import (
    TaskInfo, TaskStatus, Priority, NotificationInfo, NotificationStatus,
    AgentExecution, AgentStatus, DecisionResult
)


class TestTaskInfo:
    """测试TaskInfo模型"""
    
    def test_task_info_creation(self):
        """测试任务信息创建"""
        task = TaskInfo(
            id=1,
            title="测试任务",
            status=TaskStatus.IN_PROGRESS,
            sla_hours=8,
            elapsed_hours=10,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert task.id == 1
        assert task.title == "测试任务"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.sla_hours == 8
        assert task.elapsed_hours == 10
    
    def test_task_overdue_calculation(self):
        """测试超时时间计算"""
        task = TaskInfo(
            id=1,
            title="超时任务",
            status=TaskStatus.IN_PROGRESS,
            sla_hours=8,
            elapsed_hours=10,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert task.overdue_hours == 2  # 10 - 8 = 2
        assert task.is_overdue is True
        assert task.overdue_ratio == 1.25  # 10 / 8 = 1.25
    
    def test_task_not_overdue(self):
        """测试未超时任务"""
        task = TaskInfo(
            id=1,
            title="正常任务",
            status=TaskStatus.IN_PROGRESS,
            sla_hours=8,
            elapsed_hours=6,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert task.overdue_hours == 0
        assert task.is_overdue is False
        assert task.overdue_ratio == 0.75  # 6 / 8 = 0.75
    
    def test_task_validation_error(self):
        """测试数据验证错误"""
        with pytest.raises(ValidationError):
            TaskInfo(
                id=1,
                title="",  # 空标题
                status=TaskStatus.IN_PROGRESS,
                sla_hours=-1,  # 负数SLA
                elapsed_hours=10,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )


class TestNotificationInfo:
    """测试NotificationInfo模型"""
    
    def test_notification_creation(self):
        """测试通知信息创建"""
        notification = NotificationInfo(
            task_id=1,
            type="overdue_alert",
            message="任务超时提醒",
            group_id="group_001"
        )
        
        assert notification.task_id == 1
        assert notification.type == "overdue_alert"
        assert notification.message == "任务超时提醒"
        assert notification.group_id == "group_001"
        assert notification.status == NotificationStatus.PENDING
        assert notification.retry_count == 0
    
    def test_notification_with_priority(self):
        """测试带优先级的通知"""
        notification = NotificationInfo(
            task_id=1,
            type="escalation_alert",
            priority=Priority.HIGH,
            message="升级提醒",
            group_id="group_001"
        )
        
        assert notification.priority == Priority.HIGH


class TestAgentExecution:
    """测试AgentExecution模型"""
    
    def test_agent_execution_creation(self):
        """测试Agent执行记录创建"""
        start_time = datetime.now()
        execution = AgentExecution(
            id="exec_001",
            start_time=start_time,
            status=AgentStatus.RUNNING
        )
        
        assert execution.id == "exec_001"
        assert execution.start_time == start_time
        assert execution.status == AgentStatus.RUNNING
        assert execution.tasks_processed == 0
        assert execution.notifications_sent == 0
        assert execution.errors == []
    
    def test_execution_time_calculation(self):
        """测试执行时间计算"""
        start_time = datetime.now()
        end_time = datetime.now()
        
        execution = AgentExecution(
            id="exec_001",
            start_time=start_time,
            end_time=end_time,
            status=AgentStatus.RUNNING
        )
        
        # 执行时间应该被自动计算
        assert execution.execution_time_seconds is not None
        assert execution.execution_time_seconds >= 0


class TestDecisionResult:
    """测试DecisionResult模型"""
    
    def test_decision_result_creation(self):
        """测试决策结果创建"""
        result = DecisionResult(
            action="notify",
            priority=Priority.HIGH,
            message="需要立即处理",
            reasoning="任务已严重超时",
            confidence=0.9,
            llm_used=True
        )
        
        assert result.action == "notify"
        assert result.priority == Priority.HIGH
        assert result.message == "需要立即处理"
        assert result.reasoning == "任务已严重超时"
        assert result.confidence == 0.9
        assert result.llm_used is True
    
    def test_decision_result_defaults(self):
        """测试决策结果默认值"""
        result = DecisionResult(action="skip")
        
        assert result.action == "skip"
        assert result.priority == Priority.NORMAL
        assert result.message is None
        assert result.reasoning is None
        assert result.confidence == 1.0
        assert result.llm_used is False
    
    def test_confidence_validation(self):
        """测试置信度验证"""
        # 正常范围
        result = DecisionResult(action="notify", confidence=0.5)
        assert result.confidence == 0.5
        
        # 边界值
        result = DecisionResult(action="notify", confidence=0.0)
        assert result.confidence == 0.0
        
        result = DecisionResult(action="notify", confidence=1.0)
        assert result.confidence == 1.0
        
        # 超出范围应该报错
        with pytest.raises(ValidationError):
            DecisionResult(action="notify", confidence=1.5)
        
        with pytest.raises(ValidationError):
            DecisionResult(action="notify", confidence=-0.1)

"""
数据模型定义

使用Pydantic定义数据模型，确保类型安全和数据验证
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """任务状态枚举"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class NotificationStatus(str, Enum):
    """通知状态枚举"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


class AgentStatus(str, Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class Priority(str, Enum):
    """优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskInfo(BaseModel):
    """任务信息模型"""
    id: int
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: Priority = Priority.NORMAL
    sla_hours: int = Field(gt=0, description="SLA时间（小时）")
    elapsed_hours: float = Field(ge=0, description="已用时间（小时）")
    overdue_hours: float = Field(ge=0, default=0, description="超时时间（小时）")
    group_id: Optional[str] = None
    assignee: Optional[str] = None
    customer: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_notification: Optional[datetime] = None

    @validator('overdue_hours', always=True)
    def calculate_overdue_hours(cls, v, values):
        """计算超时时间"""
        elapsed = values.get('elapsed_hours', 0)
        sla = values.get('sla_hours', 0)
        return max(0, elapsed - sla)

    @property
    def is_overdue(self) -> bool:
        """是否超时"""
        return self.overdue_hours > 0

    @property
    def overdue_ratio(self) -> float:
        """超时比例"""
        if self.sla_hours == 0:
            return 0
        return self.elapsed_hours / self.sla_hours


class NotificationInfo(BaseModel):
    """通知信息模型"""
    id: Optional[int] = None
    task_id: int
    type: str = Field(description="通知类型")
    priority: Priority = Priority.NORMAL
    message: str
    group_id: str
    sent_at: Optional[datetime] = None
    status: NotificationStatus = NotificationStatus.PENDING
    delivery_status: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class AgentExecution(BaseModel):
    """Agent执行记录模型"""
    id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: AgentStatus = AgentStatus.RUNNING
    tasks_processed: int = 0
    notifications_sent: int = 0
    errors: List[str] = []
    context: Dict[str, Any] = {}
    execution_time_seconds: Optional[float] = None

    @validator('execution_time_seconds', always=True)
    def calculate_execution_time(cls, v, values):
        """计算执行时间"""
        start = values.get('start_time')
        end = values.get('end_time')
        if start and end:
            return (end - start).total_seconds()
        return v


class AgentHistory(BaseModel):
    """Agent执行历史模型"""
    id: Optional[int] = None
    run_id: str
    step_name: str
    input_data: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    timestamp: datetime
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None


class SystemConfig(BaseModel):
    """系统配置模型"""
    key: str
    value: str
    description: Optional[str] = None
    updated_at: datetime


class GroupConfig(BaseModel):
    """群组配置模型"""
    group_id: str
    name: str
    webhook_url: str
    enabled: bool = True
    max_notifications_per_hour: int = 10
    notification_cooldown_minutes: int = 30
    created_at: datetime
    updated_at: datetime


class MetabaseQuery(BaseModel):
    """Metabase查询模型"""
    query: str
    database_id: int = 1
    parameters: Dict[str, Any] = {}


class DecisionContext(BaseModel):
    """决策上下文模型"""
    task: TaskInfo
    history: List[NotificationInfo] = []
    group_config: Optional[GroupConfig] = None
    system_config: Dict[str, str] = {}


class DecisionResult(BaseModel):
    """决策结果模型"""
    action: str = Field(description="决策动作: skip, notify, escalate")
    priority: Priority = Priority.NORMAL
    message: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: float = Field(ge=0, le=1, default=1.0)
    llm_used: bool = False

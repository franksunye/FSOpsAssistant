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


class OpportunityStatus(str, Enum):
    """商机状态枚举"""
    PENDING_APPOINTMENT = "待预约"
    TEMPORARILY_NOT_VISITING = "暂不上门"
    APPOINTED = "已预约"
    COMPLETED = "已完成"
    CANCELLED = "已取消"


class OpportunityInfo(BaseModel):
    """商机信息模型 - 基于真实的 Metabase Card 1712 数据结构"""

    order_num: str = Field(..., description="工单号")
    name: str = Field(..., description="客户姓名")
    address: str = Field(..., description="客户地址")
    supervisor_name: str = Field(..., description="负责销售人员")
    create_time: datetime = Field(..., description="创建时间")
    org_name: str = Field(..., description="所属组织")
    order_status: OpportunityStatus = Field(..., description="商机状态")

    # 计算字段
    elapsed_hours: Optional[float] = Field(None, description="已经过时长(小时)")
    is_overdue: Optional[bool] = Field(None, description="是否逾期")
    overdue_hours: Optional[float] = Field(None, description="逾期时长(小时)")
    sla_threshold_hours: Optional[int] = Field(None, description="SLA阈值(小时)")
    escalation_level: Optional[int] = Field(0, description="升级级别 0=正常 1=升级")

    @validator('create_time', pre=True)
    def parse_create_time(cls, v):
        """解析创建时间字符串"""
        if isinstance(v, str):
            # 处理各种可能的时间格式
            try:
                # 处理 ISO 格式带时区的时间 "2025-06-14T16:33:00.144+08:00"
                if 'T' in v and '+' in v:
                    # 移除毫秒和时区信息
                    v_clean = v.split('.')[0] if '.' in v else v.split('+')[0]
                    return datetime.strptime(v_clean, "%Y-%m-%dT%H:%M:%S")
                # 处理 "2025-6-14, 16:33" 格式
                elif ', ' in v:
                    return datetime.strptime(v, "%Y-%m-%d, %H:%M")
                # 处理标准 ISO 格式
                elif 'T' in v:
                    v_clean = v.split('.')[0] if '.' in v else v
                    return datetime.strptime(v_clean, "%Y-%m-%dT%H:%M:%S")
                # 处理日期时间格式
                elif ' ' in v:
                    return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                # 处理纯日期格式
                else:
                    return datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                # 如果都失败，返回当前时间并记录警告
                import logging
                logging.warning(f"Failed to parse create_time: {v}, using current time")
                return datetime.now()
        return v

    def calculate_elapsed_hours(self) -> float:
        """计算已经过时长"""
        if not self.elapsed_hours:
            now = datetime.now()
            delta = now - self.create_time
            self.elapsed_hours = delta.total_seconds() / 3600
        return self.elapsed_hours

    def get_sla_threshold(self) -> int:
        """获取SLA阈值"""
        if self.order_status == OpportunityStatus.PENDING_APPOINTMENT:
            return 24  # 待预约：24小时
        elif self.order_status == OpportunityStatus.TEMPORARILY_NOT_VISITING:
            return 48  # 暂不上门：48小时
        else:
            return 0  # 其他状态不需要监控

    def check_overdue_status(self) -> tuple[bool, float, int]:
        """检查逾期状态

        Returns:
            tuple: (是否逾期, 逾期时长, 升级级别)
        """
        elapsed = self.calculate_elapsed_hours()
        threshold = self.get_sla_threshold()

        if threshold == 0:
            return False, 0, 0

        if elapsed > threshold:
            overdue_hours = elapsed - threshold

            # 判断升级级别
            if self.order_status == OpportunityStatus.PENDING_APPOINTMENT:
                # 待预约：超过48小时升级
                escalation_level = 1 if elapsed > 48 else 0
            elif self.order_status == OpportunityStatus.TEMPORARILY_NOT_VISITING:
                # 暂不上门：超过72小时升级
                escalation_level = 1 if elapsed > 72 else 0
            else:
                escalation_level = 0

            return True, overdue_hours, escalation_level

        return False, 0, 0

    def update_overdue_info(self):
        """更新逾期相关信息"""
        is_overdue, overdue_hours, escalation_level = self.check_overdue_status()
        self.is_overdue = is_overdue
        self.overdue_hours = overdue_hours
        self.escalation_level = escalation_level
        self.sla_threshold_hours = self.get_sla_threshold()

    class Config:
        """Pydantic配置"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

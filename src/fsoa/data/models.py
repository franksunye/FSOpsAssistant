"""
数据模型定义

使用Pydantic定义数据模型，确保类型安全和数据验证
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator

# 导入时区工具
from ..utils.timezone_utils import now_china_naive


# ============================================================================
# Agent相关的状态枚举
# ============================================================================

class AgentRunStatus(str, Enum):
    """Agent运行状态枚举"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationTaskStatus(str, Enum):
    """通知任务状态枚举"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CONFIRMED = "confirmed"


class NotificationTaskType(str, Enum):
    """通知任务类型枚举"""
    VIOLATION = "violation"    # 违规通知（12小时）
    STANDARD = "standard"      # 标准通知（24/48小时）
    ESCALATION = "escalation"  # 升级通知（24/48小时）


# ============================================================================
# 业务相关的状态枚举
# ============================================================================

class OpportunityStatus(str, Enum):
    """商机状态枚举"""
    PENDING_APPOINTMENT = "待预约"
    TEMPORARILY_NOT_VISITING = "暂不上门"
    COMPLETED = "已完成"
    CANCELLED = "已取消"


# ============================================================================
# 兼容性枚举 - 逐步废弃
# ============================================================================

class TaskStatus(str, Enum):
    """任务状态枚举 - 已废弃"""
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


# ============================================================================
# 新的数据模型 - 重构后的设计
# ============================================================================

class AgentRun(BaseModel):
    """Agent执行记录模型"""
    id: Optional[int] = None
    trigger_time: datetime
    end_time: Optional[datetime] = None
    status: AgentRunStatus
    context: Optional[Dict[str, Any]] = None
    opportunities_processed: int = 0
    notifications_sent: int = 0
    errors: Optional[List[str]] = None
    created_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """执行时长（秒）"""
        if self.end_time and self.trigger_time:
            return (self.end_time - self.trigger_time).total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == AgentRunStatus.RUNNING


class AgentHistory(BaseModel):
    """Agent执行历史模型"""
    id: Optional[int] = None
    run_id: int
    step_name: str = Field(..., description="执行步骤名称")
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    timestamp: datetime
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class NotificationTask(BaseModel):
    """通知任务模型"""
    id: Optional[int] = None
    order_num: str = Field(..., description="工单号")
    org_name: str = Field(..., description="组织名称")
    notification_type: NotificationTaskType = Field(..., description="通知类型")
    due_time: datetime = Field(..., description="应该通知的时间")
    status: NotificationTaskStatus = NotificationTaskStatus.PENDING
    message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_run_id: Optional[int] = None
    sent_run_id: Optional[int] = None
    retry_count: int = 0
    max_retry_count: int = Field(5, description="最大重试次数")
    cooldown_hours: float = Field(2.0, description="冷静时间（小时）")
    last_sent_at: Optional[datetime] = Field(None, description="最后发送时间")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_pending(self) -> bool:
        """是否待发送"""
        return self.status == NotificationTaskStatus.PENDING

    @property
    def is_overdue(self) -> bool:
        """是否逾期未发送"""
        return self.is_pending and now_china_naive() > self.due_time

    @property
    def is_in_cooldown(self) -> bool:
        """是否在冷静期内"""
        if not self.last_sent_at:
            return False

        cooldown_delta = timedelta(hours=self.cooldown_hours)
        return now_china_naive() - self.last_sent_at < cooldown_delta

    @property
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.retry_count < self.max_retry_count and not self.is_in_cooldown

    def should_send_now(self) -> bool:
        """是否应该立即发送"""
        if not self.is_pending:
            return False

        # 如果是第一次发送
        if self.retry_count == 0:
            return now_china_naive() >= self.due_time

        # 如果是重试，需要检查冷静时间
        return self.can_retry and not self.is_in_cooldown


# ============================================================================
# 废弃的模型 - 保留用于兼容性
# ============================================================================

class TaskInfo(BaseModel):
    """任务信息模型 - 已废弃，请使用OpportunityInfo"""
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
    """
    通知信息模型 - 已废弃

    ⚠️ 此模型已废弃，仅保留用于向后兼容

    推荐使用：
    - NotificationTask 模型用于新的通知任务系统

    此模型不再对应数据库表，仅用于内存中的数据传递
    """
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


# 旧的AgentHistory定义已被上面的新设计替代


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
    is_violation: Optional[bool] = Field(None, description="是否违规(12小时)")
    is_overdue: Optional[bool] = Field(None, description="是否逾期")
    is_approaching_overdue: Optional[bool] = Field(None, description="是否即将逾期")
    overdue_hours: Optional[float] = Field(None, description="逾期时长(小时)")
    sla_threshold_hours: Optional[int] = Field(None, description="SLA阈值(小时)")
    escalation_level: Optional[int] = Field(0, description="升级级别 0=正常 1=升级")
    sla_progress_ratio: Optional[float] = Field(None, description="SLA进度比例 0-1")

    # 缓存相关字段
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")
    source_hash: Optional[str] = Field(None, description="数据源哈希值")
    cache_version: Optional[int] = Field(1, description="缓存版本")

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
                return now_china_naive()
        return v

    def calculate_elapsed_hours(self, use_business_time: bool = True) -> float:
        """
        计算已经过时长

        Args:
            use_business_time: 是否使用工作时间计算，默认True

        Returns:
            已经过时长（小时）
        """
        if not self.elapsed_hours:
            now = now_china_naive()

            if use_business_time:
                # 使用工作时间计算
                from ..utils.business_time import calculate_business_elapsed_hours
                self.elapsed_hours = calculate_business_elapsed_hours(self.create_time, now)
            else:
                # 使用自然时间计算
                delta = now - self.create_time
                self.elapsed_hours = delta.total_seconds() / 3600

        return self.elapsed_hours

    def get_sla_threshold(self, threshold_type: str = "standard") -> int:
        """
        获取SLA阈值

        Args:
            threshold_type: 阈值类型
                - "violation": 违规阈值（12小时）
                - "standard": 标准阈值（24小时待预约，48小时暂不上门）
                - "escalation": 升级阈值（24小时待预约，48小时暂不上门）

        Returns:
            SLA阈值（工作小时）
        """
        if self.order_status == OpportunityStatus.PENDING_APPOINTMENT:
            if threshold_type == "violation":
                return 12  # 待预约：12小时违规
            elif threshold_type == "standard":
                return 24  # 待预约：24小时标准
            elif threshold_type == "escalation":
                return 24  # 待预约：24小时升级
        elif self.order_status == OpportunityStatus.TEMPORARILY_NOT_VISITING:
            if threshold_type == "violation":
                return 12  # 暂不上门：12小时违规（与待预约相同）
            elif threshold_type == "standard":
                return 48  # 暂不上门：48小时标准
            elif threshold_type == "escalation":
                return 48  # 暂不上门：48小时升级

        return 0  # 其他状态不需要监控

    def check_overdue_status(self, use_business_time: bool = True) -> tuple[bool, bool, bool, float, int, float]:
        """
        检查逾期状态

        Args:
            use_business_time: 是否使用工作时间计算

        Returns:
            tuple: (是否违规, 是否逾期, 是否即将逾期, 逾期时长, 升级级别, SLA进度比例)
        """
        elapsed = self.calculate_elapsed_hours(use_business_time)

        # 获取各种阈值
        violation_threshold = self.get_sla_threshold("violation")
        standard_threshold = self.get_sla_threshold("standard")
        escalation_threshold = self.get_sla_threshold("escalation")

        if standard_threshold == 0:
            return False, False, False, 0, 0, 0.0

        # 计算SLA进度比例（基于标准阈值）
        sla_progress = elapsed / standard_threshold if standard_threshold > 0 else 0.0

        # 判断是否违规（12小时）
        is_violation = elapsed > violation_threshold if violation_threshold > 0 else False

        # 判断是否逾期（标准阈值）
        is_overdue = elapsed > standard_threshold
        overdue_hours = max(0, elapsed - standard_threshold) if is_overdue else 0

        # 判断是否即将逾期（达到标准阈值的80%）
        is_approaching_overdue = not is_overdue and sla_progress >= 0.8

        # 判断升级级别（基于升级阈值）
        escalation_level = 0
        if escalation_threshold > 0 and elapsed > escalation_threshold:
            escalation_level = 1

        return is_violation, is_overdue, is_approaching_overdue, overdue_hours, escalation_level, sla_progress

    def update_overdue_info(self, use_business_time: bool = True):
        """
        更新逾期相关信息

        Args:
            use_business_time: 是否使用工作时间计算
        """
        is_violation, is_overdue, is_approaching_overdue, overdue_hours, escalation_level, sla_progress = self.check_overdue_status(use_business_time)

        # 更新字段
        self.is_violation = is_violation
        self.is_overdue = is_overdue
        self.is_approaching_overdue = is_approaching_overdue
        self.overdue_hours = overdue_hours
        self.escalation_level = escalation_level
        self.sla_threshold_hours = self.get_sla_threshold("standard")
        self.sla_progress_ratio = sla_progress

    def generate_source_hash(self) -> str:
        """生成数据源哈希值，用于检测数据变化"""
        import hashlib

        # 使用核心业务字段生成哈希
        core_data = f"{self.order_num}|{self.name}|{self.address}|{self.supervisor_name}|{self.create_time}|{self.org_name}|{self.order_status}"
        return hashlib.md5(core_data.encode()).hexdigest()

    def update_cache_info(self):
        """更新缓存相关信息"""
        self.last_updated = now_china_naive()
        self.source_hash = self.generate_source_hash()

    def is_cache_valid(self, cache_ttl_hours: int = 1) -> bool:
        """检查缓存是否有效"""
        if not self.last_updated:
            return False

        cache_age = now_china_naive() - self.last_updated
        return cache_age.total_seconds() < (cache_ttl_hours * 3600)

    def should_cache(self) -> bool:
        """判断是否应该缓存此商机"""
        # 缓存所有需要监控的商机（有SLA阈值的状态）
        if self.sla_threshold_hours and self.sla_threshold_hours > 0:
            return True

        return False

    class Config:
        """Pydantic配置"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

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
    """通知任务类型枚举 - 两级SLA体系"""
    REMINDER = "reminder"      # 提醒通知（4/8小时）→ 服务商群
    ESCALATION = "escalation"  # 升级通知（8/16小时）→ 运营群

    # 🔧 修复：移除有问题的向后兼容别名
    # 原来的 VIOLATION = "reminder" 和 STANDARD = "escalation"
    # 导致枚举值重复，引起分类错误
    # 如果需要处理旧数据，应该在数据库层面进行迁移


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
    order_num: str = Field(..., description="工单号或任务标识符")
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
    # task: TaskInfo  # 已废弃
    history: List[NotificationTask] = []  # 🔧 修复：使用NotificationTask替代废弃的NotificationInfo
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
                from ..utils.business_time import BusinessTimeCalculator
                self.elapsed_hours = BusinessTimeCalculator.calculate_elapsed_business_hours(self.create_time, now)
            else:
                # 使用自然时间计算
                delta = now - self.create_time
                self.elapsed_hours = delta.total_seconds() / 3600

        return self.elapsed_hours

    def get_sla_threshold(self, threshold_type: str = "reminder") -> int:
        """
        获取SLA阈值 - 两级体系

        Args:
            threshold_type: 阈值类型
                - "reminder": 提醒阈值（4/8小时）→ 服务商群
                - "escalation": 升级阈值（8/16小时）→ 运营群

        Returns:
            SLA阈值（工作小时）
        """
        # 尝试从数据库获取配置
        try:
            from .database import get_database_manager
            db_manager = get_database_manager()

            if self.order_status == OpportunityStatus.PENDING_APPOINTMENT:
                config_key = f"sla_pending_{threshold_type}"
            elif self.order_status == OpportunityStatus.TEMPORARILY_NOT_VISITING:
                config_key = f"sla_not_visiting_{threshold_type}"
            else:
                return 0  # 其他状态不需要监控

            config_value = db_manager.get_system_config(config_key)
            if config_value:
                return int(config_value)

        except Exception:
            # 如果数据库获取失败，使用默认值
            pass

        # 默认值
        if self.order_status == OpportunityStatus.PENDING_APPOINTMENT:
            defaults = {"reminder": 4, "escalation": 8}
        elif self.order_status == OpportunityStatus.TEMPORARILY_NOT_VISITING:
            defaults = {"reminder": 8, "escalation": 16}
        else:
            return 0

        return defaults.get(threshold_type, 0)

    def check_overdue_status(self, use_business_time: bool = True) -> tuple[bool, bool, bool, float, int, float]:
        """
        检查逾期状态 - 两级SLA体系

        Args:
            use_business_time: 是否使用工作时间计算

        Returns:
            tuple: (是否需要提醒, 是否需要升级, 是否即将升级, 逾期时长, 升级级别, SLA进度比例)
        """
        # 如果已经有elapsed_hours，使用现有值，否则重新计算
        if self.elapsed_hours is None:
            elapsed = self.calculate_elapsed_hours(use_business_time)
        else:
            elapsed = self.elapsed_hours

        # 获取两级阈值
        reminder_threshold = self.get_sla_threshold("reminder")
        escalation_threshold = self.get_sla_threshold("escalation")

        if escalation_threshold == 0:
            return False, False, False, 0, 0, 0.0

        # 计算SLA进度比例（基于升级阈值）
        sla_progress = elapsed / escalation_threshold if escalation_threshold > 0 else 0.0

        # 判断是否需要提醒（4/8小时）
        is_reminder = elapsed > reminder_threshold if reminder_threshold > 0 else False

        # 判断是否需要升级（8/16小时）
        is_escalation = elapsed > escalation_threshold

        # 判断是否即将升级（达到升级阈值的80%）
        is_approaching_escalation = not is_escalation and sla_progress >= 0.8

        # 计算逾期时长（基于升级阈值）
        overdue_hours = max(0, elapsed - escalation_threshold) if is_escalation else 0

        # 升级级别：0=正常，1=需要升级
        escalation_level = 1 if is_escalation else 0

        return is_reminder, is_escalation, is_approaching_escalation, overdue_hours, escalation_level, sla_progress

    def update_overdue_info(self, use_business_time: bool = True):
        """
        更新逾期相关信息

        Args:
            use_business_time: 是否使用工作时间计算
        """
        is_reminder, is_escalation, is_approaching_escalation, overdue_hours, escalation_level, sla_progress = self.check_overdue_status(use_business_time)

        # 更新字段（保持向后兼容）
        self.is_violation = is_reminder      # 提醒状态映射到原来的违规字段
        self.is_overdue = is_escalation      # 升级状态映射到原来的逾期字段
        self.is_approaching_overdue = is_approaching_escalation
        self.overdue_hours = overdue_hours
        self.escalation_level = escalation_level
        self.sla_threshold_hours = self.get_sla_threshold("escalation")  # 使用升级阈值作为主要阈值
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


# ==================== 兼容性存根 ====================
# 为了避免导入错误，提供TaskInfo的兼容性存根
# 新代码应该使用OpportunityInfo

class TaskInfo:
    """
    TaskInfo兼容性存根 - 已废弃
    
    ⚠️ 此类已废弃，仅用于避免导入错误
    新代码请使用OpportunityInfo
    """
    def __init__(self, **kwargs):
        raise DeprecationWarning(
            "TaskInfo is deprecated. Use OpportunityInfo instead."
        )

# 兼容性导入
__all__ = [
    'OpportunityInfo', 'OpportunityStatus', 'NotificationTask', 
    'NotificationTaskType', 'NotificationTaskStatus', 'NotificationInfo',
    'NotificationStatus', 'Priority', 'TaskStatus', 'AgentRun', 'AgentRunStatus',
    'AgentHistory', 'GroupConfig', 'MetabaseQuery', 'DecisionContext',
    'TaskInfo'  # 兼容性存根
]

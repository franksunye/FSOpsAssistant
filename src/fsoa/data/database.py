"""
数据库操作模块

使用SQLAlchemy进行数据库操作，支持SQLite
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..utils.logger import get_logger
from .models import (
    OpportunityInfo, NotificationInfo, AgentExecution,
    SystemConfig, GroupConfig, NotificationStatus, AgentStatus,
    OpportunityStatus, AgentRun, AgentHistory, NotificationTask,
    AgentRunStatus, NotificationTaskStatus, NotificationTaskType,
    TaskInfo, TaskStatus  # 保留用于兼容性
)

logger = get_logger(__name__)

Base = declarative_base()


# ============================================================================
# 新的数据库表结构 - 重构后的设计
# ============================================================================

class AgentRunTable(Base):
    """Agent执行记录表"""
    __tablename__ = 'agent_runs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(50), nullable=False)  # 'running', 'completed', 'failed'
    context = Column(JSON)  # 执行上下文和结果统计
    opportunities_processed = Column(Integer, default=0)
    notifications_sent = Column(Integer, default=0)
    errors = Column(JSON)  # 错误信息列表
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AgentHistoryTable(Base):
    """Agent执行明细表"""
    __tablename__ = 'agent_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, nullable=False)  # 关联agent_runs.id
    step_name = Column(String(100), nullable=False)  # 'fetch_data', 'analyze', 'send_notifications'
    input_data = Column(JSON)  # 输入数据
    output_data = Column(JSON)  # 输出数据
    timestamp = Column(DateTime, nullable=False)
    duration_seconds = Column(Float)  # 执行耗时
    error_message = Column(Text)  # 错误信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class NotificationTaskTable(Base):
    """通知任务记录表"""
    __tablename__ = 'notification_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_num = Column(String(100), nullable=False)  # 关联的工单号
    org_name = Column(String(255), nullable=False)  # 组织名称
    notification_type = Column(String(100), nullable=False)  # 'violation', 'standard', 'escalation'
    due_time = Column(DateTime, nullable=False)  # 应该通知的时间
    status = Column(String(50), default='pending')  # 'pending', 'sent', 'failed', 'confirmed'
    message = Column(Text)  # 通知内容
    sent_at = Column(DateTime)  # 实际发送时间
    created_run_id = Column(Integer)  # 创建此任务的Agent运行ID
    sent_run_id = Column(Integer)  # 发送此通知的Agent运行ID
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class OpportunityCacheTable(Base):
    """业务数据缓存表 - Agent和业务系统关联的证明"""
    __tablename__ = 'opportunity_cache'

    order_num = Column(String(100), primary_key=True)  # 工单号作为主键
    customer_name = Column(String(255))
    address = Column(String(500))
    supervisor_name = Column(String(100))
    create_time = Column(DateTime)
    org_name = Column(String(255))
    status = Column(String(50))

    # 计算字段
    elapsed_hours = Column(Float)
    is_overdue = Column(Boolean)
    escalation_level = Column(Integer, default=0)

    # 缓存管理字段
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    source_hash = Column(String(64))  # 用于检测数据变化
    cache_version = Column(Integer, default=1)  # 缓存版本

    # 系统字段
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ============================================================================
# 旧的表结构 - 待移除
# ============================================================================

# TaskTable (tasks_deprecated) 已被彻底移除
# 所有任务功能现在直接使用商机数据，不再维护单独的任务表


# NotificationTable (notifications_deprecated) 已被彻底移除
# 所有通知功能现在使用 NotificationTaskTable (notification_tasks)


# AgentExecutionTable (agent_executions_deprecated) 已被彻底移除
# 所有Agent执行记录功能现在使用 AgentRunTable (agent_runs) + AgentHistoryTable (agent_history)


# 旧的AgentHistoryTable已被新设计替代，见上面的新表结构


class SystemConfigTable(Base):
    """系统配置表"""
    __tablename__ = 'system_config'
    
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, nullable=False)


class GroupConfigTable(Base):
    """群组配置表"""
    __tablename__ = 'group_config'
    
    group_id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    webhook_url = Column(String(500), nullable=False)
    enabled = Column(Boolean, default=True)
    max_notifications_per_hour = Column(Integer, default=10)
    notification_cooldown_minutes = Column(Integer, default=30)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str = "sqlite:///fsoa.db"):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def init_database(self):
        """初始化数据库"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database initialized successfully")
            
            # 初始化默认配置
            self._init_default_config()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _init_default_config(self):
        """初始化默认配置"""
        default_configs = [
            ("agent_execution_interval", "60", "Agent执行间隔（分钟）"),
            ("max_notifications_per_hour", "10", "每小时最大通知数"),
            ("notification_cooldown", "30", "通知冷却时间（分钟）"),
            ("webhook_api_interval", "3", "Webhook API发送间隔（秒）"),
            ("escalation_threshold", "4", "升级阈值（小时）"),
            ("use_llm_optimization", "true", "是否使用LLM优化"),
            ("llm_temperature", "0.1", "LLM温度参数"),
        ]
        
        with self.get_session() as session:
            for key, value, description in default_configs:
                existing = session.query(SystemConfigTable).filter_by(key=key).first()
                if not existing:
                    config = SystemConfigTable(
                        key=key,
                        value=value,
                        description=description,
                        updated_at=datetime.now()
                    )
                    session.add(config)
            session.commit()
    
    @contextmanager
    def get_session(self):
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # save_task() 方法已被移除
    # 所有任务功能现在直接使用商机数据，不再维护单独的任务表
    
    # get_tasks() 方法已被移除
    # 所有任务查询功能现在直接使用商机数据，不再维护单独的任务表
    
    # save_notification() 方法已被移除
    # 所有通知记录现在通过 NotificationTaskTable 管理
    
    # save_agent_execution() 方法已被移除
    # 所有Agent执行记录功能现在使用 AgentRunTable (agent_runs) + AgentHistoryTable (agent_history)
    
    def get_system_config(self, key: str) -> Optional[str]:
        """获取系统配置"""
        try:
            with self.get_session() as session:
                config = session.query(SystemConfigTable).filter_by(key=key).first()
                return config.value if config else None
        except Exception as e:
            logger.error(f"Failed to get system config {key}: {e}")
            return None

    def get_all_system_configs(self) -> Dict[str, str]:
        """获取所有系统配置"""
        try:
            with self.get_session() as session:
                configs = session.query(SystemConfigTable).all()
                return {config.key: config.value for config in configs}
        except Exception as e:
            logger.error(f"Failed to get all system configs: {e}")
            return {}
    
    def set_system_config(self, key: str, value: str, description: str = None) -> bool:
        """设置系统配置"""
        try:
            with self.get_session() as session:
                config = SystemConfigTable(
                    key=key,
                    value=value,
                    description=description,
                    updated_at=datetime.now()
                )
                session.merge(config)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to set system config {key}: {e}")
            return False
    
    # _task_table_to_model() 方法已被移除
    # 所有任务数据转换功能现在直接使用商机数据模型，不再维护单独的任务表

    # ============================================================================
    # 新的数据操作方法 - 重构后的设计
    # ============================================================================

    def save_agent_run(self, agent_run: 'AgentRun') -> int:
        """保存Agent执行记录"""
        try:
            with self.get_session() as session:
                run_record = AgentRunTable(
                    trigger_time=agent_run.trigger_time,
                    end_time=agent_run.end_time,
                    status=agent_run.status.value,
                    context=agent_run.context,
                    opportunities_processed=agent_run.opportunities_processed,
                    notifications_sent=agent_run.notifications_sent,
                    errors=agent_run.errors,
                    created_at=agent_run.created_at or datetime.utcnow()
                )
                session.add(run_record)
                session.commit()
                session.refresh(run_record)
                return run_record.id
        except Exception as e:
            logger.error(f"Failed to save agent run: {e}")
            raise

    def update_agent_run(self, run_id: int, updates: Dict[str, Any]) -> bool:
        """更新Agent执行记录"""
        try:
            with self.get_session() as session:
                run_record = session.query(AgentRunTable).filter_by(id=run_id).first()
                if run_record:
                    for key, value in updates.items():
                        if hasattr(run_record, key):
                            setattr(run_record, key, value)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update agent run {run_id}: {e}")
            return False

    def save_agent_history(self, history: 'AgentHistory') -> bool:
        """保存Agent执行历史"""
        try:
            with self.get_session() as session:
                history_record = AgentHistoryTable(
                    run_id=history.run_id,
                    step_name=history.step_name,
                    input_data=history.input_data,
                    output_data=history.output_data,
                    timestamp=history.timestamp,
                    duration_seconds=history.duration_seconds,
                    error_message=history.error_message,
                    created_at=history.created_at or datetime.utcnow()
                )
                session.add(history_record)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save agent history: {e}")
            return False

    def get_agent_runs(self, limit: int = 50, hours_back: int = 168) -> List['AgentRun']:
        """获取Agent执行记录列表"""
        try:
            with self.get_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

                runs = session.query(AgentRunTable)\
                    .filter(AgentRunTable.trigger_time >= cutoff_time)\
                    .order_by(AgentRunTable.trigger_time.desc())\
                    .limit(limit)\
                    .all()

                result = []
                for run in runs:
                    agent_run = AgentRun(
                        id=run.id,
                        trigger_time=run.trigger_time,
                        end_time=run.end_time,
                        status=AgentRunStatus(run.status),
                        context=run.context or {},
                        opportunities_processed=run.opportunities_processed,
                        notifications_sent=run.notifications_sent,
                        errors=run.errors or [],
                        created_at=run.created_at
                    )
                    result.append(agent_run)

                return result

        except Exception as e:
            logger.error(f"Failed to get agent runs: {e}")
            return []

    def get_agent_run_statistics(self, hours_back: int = 24) -> Dict[str, Any]:
        """获取Agent运行统计信息"""
        try:
            with self.get_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

                # 基本统计
                total_runs = session.query(AgentRunTable)\
                    .filter(AgentRunTable.trigger_time >= cutoff_time)\
                    .count()

                successful_runs = session.query(AgentRunTable)\
                    .filter(AgentRunTable.trigger_time >= cutoff_time)\
                    .filter(AgentRunTable.status == 'completed')\
                    .count()

                failed_runs = session.query(AgentRunTable)\
                    .filter(AgentRunTable.trigger_time >= cutoff_time)\
                    .filter(AgentRunTable.status == 'failed')\
                    .count()

                # 计算平均执行时间
                completed_runs = session.query(AgentRunTable)\
                    .filter(AgentRunTable.trigger_time >= cutoff_time)\
                    .filter(AgentRunTable.status == 'completed')\
                    .filter(AgentRunTable.end_time.isnot(None))\
                    .all()

                total_duration = 0
                duration_count = 0
                total_opportunities = 0
                total_notifications = 0

                for run in completed_runs:
                    if run.end_time and run.trigger_time:
                        duration = (run.end_time - run.trigger_time).total_seconds()
                        total_duration += duration
                        duration_count += 1

                    total_opportunities += run.opportunities_processed or 0
                    total_notifications += run.notifications_sent or 0

                avg_duration = total_duration / duration_count if duration_count > 0 else 0

                return {
                    "total_runs": total_runs,
                    "successful_runs": successful_runs,
                    "failed_runs": failed_runs,
                    "running_runs": total_runs - successful_runs - failed_runs,
                    "success_rate": round(successful_runs / total_runs * 100, 2) if total_runs > 0 else 0,
                    "average_duration_seconds": round(avg_duration, 2),
                    "total_opportunities_processed": total_opportunities,
                    "total_notifications_sent": total_notifications,
                    "period_hours": hours_back
                }

        except Exception as e:
            logger.error(f"Failed to get agent run statistics: {e}")
            return {}

    def get_agent_history_by_run(self, run_id: int) -> List['AgentHistory']:
        """获取指定运行的执行历史"""
        try:
            with self.get_session() as session:
                histories = session.query(AgentHistoryTable)\
                    .filter(AgentHistoryTable.run_id == run_id)\
                    .order_by(AgentHistoryTable.timestamp)\
                    .all()

                result = []
                for history in histories:
                    agent_history = AgentHistory(
                        id=history.id,
                        run_id=history.run_id,
                        step_name=history.step_name,
                        input_data=history.input_data or {},
                        output_data=history.output_data or {},
                        timestamp=history.timestamp,
                        duration_seconds=history.duration_seconds,
                        error_message=history.error_message,
                        created_at=history.created_at
                    )
                    result.append(agent_history)

                return result

        except Exception as e:
            logger.error(f"Failed to get agent history for run {run_id}: {e}")
            return []

    def get_step_performance_statistics(self, step_name: Optional[str] = None,
                                      hours_back: int = 24) -> Dict[str, Any]:
        """获取步骤性能统计"""
        try:
            with self.get_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

                query = session.query(AgentHistoryTable)\
                    .join(AgentRunTable, AgentHistoryTable.run_id == AgentRunTable.id)\
                    .filter(AgentRunTable.trigger_time >= cutoff_time)

                if step_name:
                    query = query.filter(AgentHistoryTable.step_name == step_name)

                histories = query.all()

                total_executions = len(histories)
                successful_executions = len([h for h in histories if not h.error_message])
                failed_executions = total_executions - successful_executions

                durations = [h.duration_seconds for h in histories if h.duration_seconds is not None]

                return {
                    "step_name": step_name or "all",
                    "total_executions": total_executions,
                    "successful_executions": successful_executions,
                    "failed_executions": failed_executions,
                    "success_rate": round(successful_executions / total_executions * 100, 2) if total_executions > 0 else 0,
                    "average_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0,
                    "min_duration_seconds": round(min(durations), 2) if durations else 0,
                    "max_duration_seconds": round(max(durations), 2) if durations else 0,
                    "period_hours": hours_back
                }

        except Exception as e:
            logger.error(f"Failed to get step performance statistics: {e}")
            return {}

    def save_notification_task(self, task: 'NotificationTask') -> int:
        """保存通知任务"""
        try:
            with self.get_session() as session:
                task_record = NotificationTaskTable(
                    order_num=task.order_num,
                    org_name=task.org_name,
                    notification_type=task.notification_type.value,
                    due_time=task.due_time,
                    status=task.status.value,
                    message=task.message,
                    sent_at=task.sent_at,
                    created_run_id=task.created_run_id,
                    sent_run_id=task.sent_run_id,
                    retry_count=task.retry_count,
                    created_at=task.created_at or datetime.utcnow(),
                    updated_at=task.updated_at or datetime.utcnow()
                )
                session.add(task_record)
                session.commit()
                session.refresh(task_record)
                return task_record.id
        except Exception as e:
            logger.error(f"Failed to save notification task: {e}")
            raise

    def get_pending_notification_tasks(self) -> List['NotificationTask']:
        """获取待处理的通知任务"""
        try:
            with self.get_session() as session:
                from .models import NotificationTask, NotificationTaskStatus, NotificationTaskType

                records = session.query(NotificationTaskTable).filter_by(
                    status=NotificationTaskStatus.PENDING.value
                ).all()

                tasks = []
                for record in records:
                    task = NotificationTask(
                        id=record.id,
                        order_num=record.order_num,
                        org_name=record.org_name,
                        notification_type=NotificationTaskType(record.notification_type),
                        due_time=record.due_time,
                        status=NotificationTaskStatus(record.status),
                        message=record.message,
                        sent_at=record.sent_at,
                        created_run_id=record.created_run_id,
                        sent_run_id=record.sent_run_id,
                        retry_count=record.retry_count,
                        created_at=record.created_at,
                        updated_at=record.updated_at
                    )
                    tasks.append(task)

                return tasks
        except Exception as e:
            logger.error(f"Failed to get pending notification tasks: {e}")
            return []

    def update_notification_task_status(self, task_id: int, status: 'NotificationTaskStatus',
                                      sent_run_id: Optional[int] = None) -> bool:
        """更新通知任务状态"""
        try:
            with self.get_session() as session:
                task_record = session.query(NotificationTaskTable).filter_by(id=task_id).first()
                if task_record:
                    task_record.status = status.value
                    task_record.updated_at = datetime.utcnow()
                    if status.value == 'sent':
                        task_record.sent_at = datetime.utcnow()
                        if sent_run_id:
                            task_record.sent_run_id = sent_run_id
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update notification task {task_id}: {e}")
            return False

    def update_notification_task_retry_info(self, task_id: int, retry_count: int,
                                          last_sent_at: Optional[datetime] = None) -> bool:
        """更新通知任务重试信息"""
        try:
            with self.get_session() as session:
                task_record = session.query(NotificationTaskTable).filter_by(id=task_id).first()
                if task_record:
                    task_record.retry_count = retry_count
                    task_record.updated_at = datetime.utcnow()
                    if last_sent_at:
                        # 这里需要在数据库表中添加last_sent_at字段
                        # 暂时使用sent_at字段存储最后发送时间
                        task_record.sent_at = last_sent_at
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update notification task retry info {task_id}: {e}")
            return False

    def save_opportunity_cache(self, opportunity: 'OpportunityInfo') -> bool:
        """保存商机缓存"""
        try:
            with self.get_session() as session:
                # 更新缓存信息
                opportunity.update_cache_info()

                cache_record = OpportunityCacheTable(
                    order_num=opportunity.order_num,
                    customer_name=opportunity.name,
                    address=opportunity.address,
                    supervisor_name=opportunity.supervisor_name,
                    create_time=opportunity.create_time,
                    org_name=opportunity.org_name,
                    status=opportunity.order_status.value if hasattr(opportunity.order_status, 'value') else str(opportunity.order_status),
                    elapsed_hours=opportunity.elapsed_hours,
                    is_overdue=opportunity.is_overdue,
                    escalation_level=opportunity.escalation_level,
                    last_updated=opportunity.last_updated,
                    source_hash=opportunity.source_hash,
                    cache_version=opportunity.cache_version,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.merge(cache_record)  # 使用merge支持更新
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save opportunity cache {opportunity.order_num}: {e}")
            return False

    def get_opportunity_cache(self, order_num: str) -> Optional['OpportunityInfo']:
        """获取商机缓存"""
        try:
            with self.get_session() as session:
                from .models import OpportunityInfo, OpportunityStatus

                record = session.query(OpportunityCacheTable).filter_by(order_num=order_num).first()
                if record:
                    opportunity = OpportunityInfo(
                        order_num=record.order_num,
                        name=record.customer_name,
                        address=record.address,
                        supervisor_name=record.supervisor_name,
                        create_time=record.create_time,
                        org_name=record.org_name,
                        order_status=OpportunityStatus(record.status),
                        elapsed_hours=record.elapsed_hours,
                        is_overdue=record.is_overdue,
                        escalation_level=record.escalation_level,
                        last_updated=record.last_updated,
                        source_hash=record.source_hash,
                        cache_version=record.cache_version
                    )
                    return opportunity
                return None
        except Exception as e:
            logger.error(f"Failed to get opportunity cache {order_num}: {e}")
            return None

    def get_cached_opportunities(self, cache_ttl_hours: int = 1) -> List['OpportunityInfo']:
        """获取有效的缓存商机列表"""
        try:
            with self.get_session() as session:
                from .models import OpportunityInfo, OpportunityStatus

                # 计算缓存过期时间
                cutoff_time = datetime.utcnow() - timedelta(hours=cache_ttl_hours)

                records = session.query(OpportunityCacheTable).filter(
                    OpportunityCacheTable.last_updated > cutoff_time
                ).all()

                opportunities = []
                for record in records:
                    opportunity = OpportunityInfo(
                        order_num=record.order_num,
                        name=record.customer_name,
                        address=record.address,
                        supervisor_name=record.supervisor_name,
                        create_time=record.create_time,
                        org_name=record.org_name,
                        order_status=OpportunityStatus(record.status),
                        elapsed_hours=record.elapsed_hours,
                        is_overdue=record.is_overdue,
                        escalation_level=record.escalation_level,
                        last_updated=record.last_updated,
                        source_hash=record.source_hash,
                        cache_version=record.cache_version
                    )
                    opportunities.append(opportunity)

                return opportunities
        except Exception as e:
            logger.error(f"Failed to get cached opportunities: {e}")
            return []

    # ==================== 群组配置管理 ====================

    def get_group_configs(self) -> List[GroupConfigTable]:
        """获取所有群组配置"""
        with self.get_session() as session:
            return session.query(GroupConfigTable).all()

    def get_enabled_group_configs(self) -> List[GroupConfigTable]:
        """获取启用的群组配置"""
        with self.get_session() as session:
            return session.query(GroupConfigTable).filter(
                GroupConfigTable.enabled == True
            ).all()

    def get_group_config_by_id(self, group_id: str) -> Optional[GroupConfigTable]:
        """根据群组ID获取配置"""
        with self.get_session() as session:
            return session.query(GroupConfigTable).filter(
                GroupConfigTable.group_id == group_id
            ).first()

    def create_or_update_group_config(self, group_id: str, name: str, webhook_url: str,
                                    enabled: bool = True, max_notifications_per_hour: int = 10,
                                    notification_cooldown_minutes: int = 30) -> GroupConfigTable:
        """创建或更新群组配置"""
        with self.get_session() as session:
            # 查找现有配置
            existing = session.query(GroupConfigTable).filter(
                GroupConfigTable.group_id == group_id
            ).first()

            now = datetime.now()

            if existing:
                # 更新现有配置
                existing.name = name
                existing.webhook_url = webhook_url
                existing.enabled = enabled
                existing.max_notifications_per_hour = max_notifications_per_hour
                existing.notification_cooldown_minutes = notification_cooldown_minutes
                existing.updated_at = now
                config = existing
            else:
                # 创建新配置
                config = GroupConfigTable(
                    group_id=group_id,
                    name=name,
                    webhook_url=webhook_url,
                    enabled=enabled,
                    max_notifications_per_hour=max_notifications_per_hour,
                    notification_cooldown_minutes=notification_cooldown_minutes,
                    created_at=now,
                    updated_at=now
                )
                session.add(config)

            session.commit()
            return config

    def delete_group_config(self, group_id: str) -> bool:
        """删除群组配置"""
        with self.get_session() as session:
            config = session.query(GroupConfigTable).filter(
                GroupConfigTable.group_id == group_id
            ).first()

            if config:
                session.delete(config)
                session.commit()
                return True
            return False


# 全局数据库管理器实例
db_manager = None

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    global db_manager
    if db_manager is None:
        from ..utils.config import get_config
        config = get_config()
        db_manager = DatabaseManager(config.database_url)
    return db_manager

# 别名，保持兼容性
get_database_manager = get_db_manager

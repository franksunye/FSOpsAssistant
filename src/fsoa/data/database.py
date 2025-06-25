"""
数据库操作模块

使用SQLAlchemy进行数据库操作，支持SQLite
"""

import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..utils.logger import get_logger
from .models import (
    TaskInfo, NotificationInfo, AgentExecution, AgentHistory,
    SystemConfig, GroupConfig, TaskStatus, NotificationStatus, AgentStatus
)

logger = get_logger(__name__)

Base = declarative_base()


class TaskTable(Base):
    """任务表"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), nullable=False)
    priority = Column(String(50), default='normal')
    sla_hours = Column(Integer, nullable=False)
    elapsed_hours = Column(Float, nullable=False)
    overdue_hours = Column(Float, default=0)
    group_id = Column(String(100))
    assignee = Column(String(100))
    customer = Column(String(255))
    location = Column(String(255))
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_notification = Column(DateTime)


class NotificationTable(Base):
    """通知表"""
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False)
    type = Column(String(100), nullable=False)
    priority = Column(String(50), default='normal')
    message = Column(Text, nullable=False)
    group_id = Column(String(100), nullable=False)
    sent_at = Column(DateTime)
    status = Column(String(50), default='pending')
    delivery_status = Column(String(50))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)


class AgentExecutionTable(Base):
    """Agent执行记录表"""
    __tablename__ = 'agent_executions'
    
    id = Column(String(100), primary_key=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(50), nullable=False)
    tasks_processed = Column(Integer, default=0)
    notifications_sent = Column(Integer, default=0)
    errors = Column(JSON)
    context = Column(JSON)
    execution_time_seconds = Column(Float)


class AgentHistoryTable(Base):
    """Agent执行历史表"""
    __tablename__ = 'agent_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), nullable=False)
    step_name = Column(String(100), nullable=False)
    input_data = Column(JSON)
    output_data = Column(JSON)
    timestamp = Column(DateTime, nullable=False)
    duration_seconds = Column(Float)
    error_message = Column(Text)


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
    
    def save_task(self, task: TaskInfo) -> bool:
        """保存任务信息"""
        try:
            with self.get_session() as session:
                task_record = TaskTable(
                    id=task.id,
                    title=task.title,
                    description=task.description,
                    status=task.status.value,
                    priority=task.priority.value,
                    sla_hours=task.sla_hours,
                    elapsed_hours=task.elapsed_hours,
                    overdue_hours=task.overdue_hours,
                    group_id=task.group_id,
                    assignee=task.assignee,
                    customer=task.customer,
                    location=task.location,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    last_notification=task.last_notification
                )
                session.merge(task_record)  # 使用merge支持更新
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save task {task.id}: {e}")
            return False
    
    def get_tasks(self, status: Optional[TaskStatus] = None, 
                  group_id: Optional[str] = None) -> List[TaskInfo]:
        """获取任务列表"""
        try:
            with self.get_session() as session:
                query = session.query(TaskTable)
                
                if status:
                    query = query.filter(TaskTable.status == status.value)
                if group_id:
                    query = query.filter(TaskTable.group_id == group_id)
                
                tasks = query.all()
                return [self._task_table_to_model(task) for task in tasks]
        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return []
    
    def save_notification(self, notification: NotificationInfo) -> Optional[int]:
        """保存通知记录"""
        try:
            with self.get_session() as session:
                notification_record = NotificationTable(
                    task_id=notification.task_id,
                    type=notification.type,
                    priority=notification.priority.value,
                    message=notification.message,
                    group_id=notification.group_id,
                    sent_at=notification.sent_at,
                    status=notification.status.value,
                    delivery_status=notification.delivery_status,
                    error_message=notification.error_message,
                    retry_count=notification.retry_count
                )
                session.add(notification_record)
                session.commit()
                return notification_record.id
        except Exception as e:
            logger.error(f"Failed to save notification: {e}")
            return None
    
    def save_agent_execution(self, execution: AgentExecution) -> bool:
        """保存Agent执行记录"""
        try:
            with self.get_session() as session:
                execution_record = AgentExecutionTable(
                    id=execution.id,
                    start_time=execution.start_time,
                    end_time=execution.end_time,
                    status=execution.status.value,
                    tasks_processed=execution.tasks_processed,
                    notifications_sent=execution.notifications_sent,
                    errors=execution.errors,
                    context=execution.context,
                    execution_time_seconds=execution.execution_time_seconds
                )
                session.merge(execution_record)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save agent execution: {e}")
            return False
    
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
    
    def _task_table_to_model(self, task_record: TaskTable) -> TaskInfo:
        """将数据库记录转换为模型"""
        return TaskInfo(
            id=task_record.id,
            title=task_record.title,
            description=task_record.description,
            status=TaskStatus(task_record.status),
            priority=task_record.priority,
            sla_hours=task_record.sla_hours,
            elapsed_hours=task_record.elapsed_hours,
            overdue_hours=task_record.overdue_hours,
            group_id=task_record.group_id,
            assignee=task_record.assignee,
            customer=task_record.customer,
            location=task_record.location,
            created_at=task_record.created_at,
            updated_at=task_record.updated_at,
            last_notification=task_record.last_notification
        )


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

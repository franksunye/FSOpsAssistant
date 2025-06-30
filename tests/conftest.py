"""
测试配置文件

提供测试fixtures和配置
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock

# 设置测试环境变量
os.environ.update({
    "DEEPSEEK_API_KEY": "test-key",
    "METABASE_URL": "http://test-metabase",
    "METABASE_USERNAME": "test-user",
    "METABASE_PASSWORD": "test-pass",
    "INTERNAL_OPS_WEBHOOK": "http://test-webhook",
    "DATABASE_URL": "sqlite:///test.db",
    "LOG_LEVEL": "DEBUG",
    "DEBUG": "True",
    "TESTING": "True"
})

# 添加项目路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.fsoa.data.models import (
    OpportunityInfo, OpportunityStatus, Priority, NotificationTask,
    NotificationTaskType, NotificationTaskStatus, AgentRun, AgentRunStatus
)
from src.fsoa.data.database import DatabaseManager
from src.fsoa.utils.config import Config


@pytest.fixture(scope="session")
def test_database():
    """创建测试数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # 初始化测试数据库
    db_manager = DatabaseManager(f"sqlite:///{db_path}")
    db_manager.init_database()

    yield db_path

    # 清理
    os.unlink(db_path)


@pytest.fixture
def test_config(test_database):
    """测试配置"""
    return Config(
        deepseek_api_key="test-key",
        metabase_url="http://test-metabase",
        metabase_username="test-user",
        metabase_password="test-pass",
        internal_ops_webhook="http://test-webhook",
        database_url=f"sqlite:///{test_database}",
        log_level="DEBUG",
        debug=True,
        testing=True
    )


@pytest.fixture
def sample_opportunity():
    """示例商机数据"""
    return OpportunityInfo(
        order_num="GD20250001",
        name="张三",
        address="北京市朝阳区建国路1号",
        supervisor_name="李销售",
        create_time=datetime.now() - timedelta(hours=6),
        org_name="测试公司A",
        order_status=OpportunityStatus.PENDING_APPOINTMENT,
        elapsed_hours=6.0,
        sla_threshold_hours=4,
        is_overdue=True,
        overdue_hours=2.0
    )


@pytest.fixture
def overdue_opportunity():
    """超时商机数据"""
    return OpportunityInfo(
        order_num="GD20250002",
        name="李四",
        address="上海市浦东新区陆家嘴1号",
        supervisor_name="王销售",
        create_time=datetime.now() - timedelta(hours=10),
        org_name="测试公司B",
        order_status=OpportunityStatus.TEMPORARILY_NOT_VISITING,
        elapsed_hours=10.0,
        sla_threshold_hours=8,
        is_overdue=True,
        overdue_hours=2.0
    )


@pytest.fixture
def sample_notification_task():
    """示例通知任务"""
    return NotificationTask(
        order_num="GD20250001",
        org_name="测试公司A",
        notification_type=NotificationTaskType.REMINDER,
        due_time=datetime.now() - timedelta(minutes=30),
        status=NotificationTaskStatus.PENDING,
        message="测试通知消息"
    )


@pytest.fixture
def sample_agent_run():
    """示例Agent运行记录"""
    return AgentRun(
        trigger_time=datetime.now(),
        status=AgentRunStatus.RUNNING,
        opportunities_processed=0,
        notifications_sent=0
    )


@pytest.fixture
def multiple_opportunities():
    """多个商机数据用于测试"""
    return [
        OpportunityInfo(
            order_num="GD20250001",
            name="张三",
            address="北京市朝阳区",
            supervisor_name="李销售",
            create_time=datetime.now() - timedelta(hours=6),
            org_name="测试公司A",
            order_status=OpportunityStatus.PENDING_APPOINTMENT,
            elapsed_hours=6.0,
            sla_threshold_hours=4
        ),
        OpportunityInfo(
            order_num="GD20250002",
            name="李四",
            address="上海市浦东新区",
            supervisor_name="王销售",
            create_time=datetime.now() - timedelta(hours=2),
            org_name="测试公司B",
            order_status=OpportunityStatus.PENDING_APPOINTMENT,
            elapsed_hours=2.0,
            sla_threshold_hours=4
        ),
        OpportunityInfo(
            order_num="GD20250003",
            name="王五",
            address="深圳市南山区",
            supervisor_name="赵销售",
            create_time=datetime.now() - timedelta(hours=12),
            org_name="测试公司C",
            order_status=OpportunityStatus.TEMPORARILY_NOT_VISITING,
            elapsed_hours=12.0,
            sla_threshold_hours=8
        )
    ]


@pytest.fixture
def mock_metabase_client():
    """Mock Metabase客户端"""
    mock_client = Mock()
    mock_client.authenticate.return_value = True
    mock_client.test_connection.return_value = True
    mock_client.get_overdue_opportunities.return_value = []
    mock_client.query_card.return_value = []
    return mock_client


@pytest.fixture
def mock_wechat_client():
    """Mock 企微客户端"""
    mock_client = Mock()
    mock_client.send_text_message.return_value = True
    mock_client.send_markdown_message.return_value = True
    mock_client.test_webhook.return_value = True
    return mock_client


@pytest.fixture
def mock_deepseek_client():
    """Mock DeepSeek客户端"""
    mock_client = Mock()
    mock_client.test_connection.return_value = True
    mock_client.analyze_task_priority.return_value = Mock(
        action="notify",
        priority=Priority.HIGH,
        llm_used=True,
        confidence=0.9
    )
    mock_client.generate_notification_message.return_value = "测试通知消息"
    return mock_client

"""
测试配置文件

提供测试fixtures和配置
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock

# 添加项目路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.fsoa.data.models import TaskInfo, TaskStatus, Priority
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
        wechat_webhook_urls="http://test-webhook1,http://test-webhook2",
        database_url=f"sqlite:///{test_database}",
        log_level="DEBUG",
        debug=True,
        testing=True
    )


@pytest.fixture
def sample_task():
    """示例任务数据"""
    return TaskInfo(
        id=1001,
        title="测试任务",
        description="这是一个测试任务",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.NORMAL,
        sla_hours=8,
        elapsed_hours=10,
        group_id="group_001",
        assignee="张三",
        customer="测试客户",
        location="北京市",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def overdue_task():
    """超时任务数据"""
    return TaskInfo(
        id=1002,
        title="超时任务",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH,
        sla_hours=4,
        elapsed_hours=6,
        group_id="group_002",
        assignee="李四",
        customer="紧急客户",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def mock_metabase_client():
    """Mock Metabase客户端"""
    mock_client = Mock()
    mock_client.authenticate.return_value = True
    mock_client.test_connection.return_value = True
    mock_client.get_overdue_tasks.return_value = []
    return mock_client


@pytest.fixture
def mock_wechat_client():
    """Mock 企微客户端"""
    mock_client = Mock()
    mock_client.send_text_message.return_value = True
    mock_client.send_markdown_message.return_value = True
    return mock_client

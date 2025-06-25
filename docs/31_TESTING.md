# FSOA 测试指南

Field Service Operations Assistant - 测试策略和实施指南

## 1. 测试策略

### 1.1 测试金字塔
```
        ┌─────────────┐
        │   E2E Tests │  ← 少量，关键业务流程
        │     (5%)    │
        ├─────────────┤
        │ Integration │  ← 中等，模块间交互
        │ Tests (25%) │
        ├─────────────┤
        │ Unit Tests  │  ← 大量，单个函数/类
        │   (70%)     │
        └─────────────┘
```

### 1.2 测试原则
- **快速反馈**：单元测试秒级完成，集成测试分钟级
- **可靠稳定**：测试结果一致，减少flaky tests
- **易于维护**：测试代码清晰，便于修改和扩展
- **业务导向**：优先测试核心业务逻辑和用户场景

### 1.3 测试范围
- **核心功能**：Agent执行、任务检测、通知发送
- **集成点**：Metabase API、企微Webhook、LLM调用
- **边界条件**：异常处理、网络故障、数据异常
- **性能要求**：响应时间、并发处理、资源使用

## 2. 单元测试

### 2.1 测试框架
- **pytest**：主要测试框架
- **pytest-mock**：Mock和Patch功能
- **pytest-cov**：代码覆盖率统计
- **pytest-asyncio**：异步代码测试

### 2.2 测试结构
```
tests/unit/
├── test_agent/
│   ├── test_orchestrator.py    # Agent编排器测试
│   ├── test_tools.py          # 工具函数测试
│   └── test_decision.py       # 决策引擎测试
├── test_data/
│   ├── test_models.py         # 数据模型测试
│   ├── test_database.py       # 数据库操作测试
│   └── test_metabase.py       # Metabase集成测试
├── test_notification/
│   ├── test_wechat.py         # 企微通知测试
│   └── test_templates.py      # 消息模板测试
└── test_utils/
    ├── test_config.py         # 配置管理测试
    └── test_scheduler.py      # 任务调度测试
```

### 2.3 测试示例
```python
# tests/unit/test_agent/test_tools.py
import pytest
from unittest.mock import Mock, patch
from fsoa.agent.tools import fetch_overdue_tasks, send_notification
from fsoa.data.models import TaskInfo

class TestFetchOverdueTasks:
    """测试任务获取功能"""

    @pytest.fixture
    def mock_metabase_data(self):
        return [
            {
                "id": 1,
                "title": "测试任务1",
                "status": "in_progress",
                "sla_hours": 8,
                "elapsed_hours": 10,
                "group_id": "group_001"
            },
            {
                "id": 2,
                "title": "测试任务2",
                "status": "in_progress",
                "sla_hours": 4,
                "elapsed_hours": 3,
                "group_id": "group_002"
            }
        ]

    @patch('fsoa.data.metabase.MetabaseClient')
    def test_fetch_overdue_tasks_success(self, mock_client, mock_metabase_data):
        """测试成功获取超时任务"""
        # Arrange
        mock_client.return_value.query.return_value = mock_metabase_data

        # Act
        tasks = fetch_overdue_tasks()

        # Assert
        assert len(tasks) == 1  # 只有任务1超时
        assert tasks[0].id == 1
        assert tasks[0].elapsed_hours > tasks[0].sla_hours
        mock_client.return_value.query.assert_called_once()

    @patch('fsoa.data.metabase.MetabaseClient')
    def test_fetch_overdue_tasks_empty_result(self, mock_client):
        """测试无超时任务的情况"""
        # Arrange
        mock_client.return_value.query.return_value = []

        # Act
        tasks = fetch_overdue_tasks()

        # Assert
        assert len(tasks) == 0

    @patch('fsoa.data.metabase.MetabaseClient')
    def test_fetch_overdue_tasks_connection_error(self, mock_client):
        """测试连接错误处理"""
        # Arrange
        mock_client.return_value.query.side_effect = ConnectionError("Network error")

        # Act & Assert
        with pytest.raises(DataSourceError):
            fetch_overdue_tasks()

class TestSendNotification:
    """测试通知发送功能"""

    @patch('requests.post')
    def test_send_notification_success(self, mock_post):
        """测试成功发送通知"""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"errcode": 0}

        task = TaskInfo(
            id=1,
            title="测试任务",
            status="in_progress",
            sla_hours=8,
            elapsed_hours=10,
            group_id="group_001"
        )

        # Act
        result = send_notification(task, "测试消息")

        # Assert
        assert result is True
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_send_notification_webhook_error(self, mock_post):
        """测试Webhook错误处理"""
        # Arrange
        mock_post.side_effect = requests.RequestException("Webhook error")

        task = TaskInfo(id=1, title="测试", status="in_progress",
                       sla_hours=8, elapsed_hours=10, group_id="group_001")

        # Act & Assert
        with pytest.raises(NotificationError):
            send_notification(task, "测试消息")
```

### 2.4 运行单元测试
```bash
# 运行所有单元测试
pytest tests/unit/

# 运行特定测试文件
pytest tests/unit/test_agent/test_tools.py

# 运行特定测试方法
pytest tests/unit/test_agent/test_tools.py::TestFetchOverdueTasks::test_fetch_overdue_tasks_success

# 生成覆盖率报告
pytest tests/unit/ --cov=src/fsoa --cov-report=html

# 并行运行测试
pytest tests/unit/ -n auto
```

## 3. 集成测试

### 3.1 测试范围
- **数据库集成**：SQLite操作的完整流程
- **外部API集成**：Metabase、企微、DeepSeek API
- **Agent工作流**：完整的Agent执行流程
- **UI集成**：Streamlit界面的关键功能

### 3.2 测试环境
```python
# tests/integration/conftest.py
import pytest
import tempfile
import os
from fsoa.data.database import init_database
from fsoa.utils.config import Config

@pytest.fixture(scope="session")
def test_database():
    """创建测试数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # 初始化测试数据库
    init_database(db_path)

    yield db_path

    # 清理
    os.unlink(db_path)

@pytest.fixture
def test_config(test_database):
    """测试配置"""
    return Config(
        database_url=f"sqlite:///{test_database}",
        metabase_url="http://test-metabase",
        deepseek_api_key="test-key",
        wechat_webhook_urls=["http://test-webhook"]
    )
```

### 3.3 集成测试示例
```python
# tests/integration/test_agent_workflow.py
import pytest
from unittest.mock import patch, Mock
from fsoa.agent.orchestrator import AgentOrchestrator

class TestAgentWorkflow:
    """测试Agent完整工作流程"""

    @patch('fsoa.data.metabase.MetabaseClient')
    @patch('fsoa.notification.wechat.send_wechat_message')
    def test_complete_workflow_with_overdue_tasks(
        self, mock_send_message, mock_metabase, test_config
    ):
        """测试有超时任务的完整流程"""
        # Arrange
        mock_metabase.return_value.query.return_value = [
            {
                "id": 1,
                "title": "超时任务",
                "status": "in_progress",
                "sla_hours": 8,
                "elapsed_hours": 12,
                "group_id": "group_001"
            }
        ]
        mock_send_message.return_value = True

        orchestrator = AgentOrchestrator(test_config)

        # Act
        result = orchestrator.execute()

        # Assert
        assert result.status == "completed"
        assert result.tasks_processed == 1
        assert result.notifications_sent == 1
        mock_send_message.assert_called_once()

    @patch('fsoa.data.metabase.MetabaseClient')
    def test_workflow_with_no_overdue_tasks(self, mock_metabase, test_config):
        """测试无超时任务的流程"""
        # Arrange
        mock_metabase.return_value.query.return_value = []
        orchestrator = AgentOrchestrator(test_config)

        # Act
        result = orchestrator.execute()

        # Assert
        assert result.status == "completed"
        assert result.tasks_processed == 0
        assert result.notifications_sent == 0
```

## 4. 端到端测试

### 4.1 测试场景
- **完整业务流程**：从数据获取到通知发送的全链路
- **用户操作流程**：通过UI进行的典型操作
- **异常恢复流程**：系统故障后的恢复能力

### 4.2 E2E测试示例
```python
# tests/e2e/test_full_workflow.py
import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

class TestFullWorkflow:
    """端到端测试"""

    @pytest.fixture
    def browser(self):
        """浏览器fixture"""
        driver = webdriver.Chrome()
        yield driver
        driver.quit()

    def test_manual_agent_execution(self, browser):
        """测试手动触发Agent执行"""
        # 打开应用
        browser.get("http://localhost:8501")

        # 等待页面加载
        time.sleep(2)

        # 点击手动执行按钮
        execute_button = browser.find_element(By.TEXT, "手动执行")
        execute_button.click()

        # 等待执行完成
        time.sleep(5)

        # 验证执行结果
        status_element = browser.find_element(By.CLASS_NAME, "agent-status")
        assert "执行完成" in status_element.text
```

## 5. 性能测试

### 5.1 测试指标
- **响应时间**：Agent执行时间 < 30秒
- **并发处理**：支持100个并发任务
- **内存使用**：峰值内存 < 512MB
- **数据库性能**：查询响应时间 < 100ms

### 5.2 性能测试示例
```python
# tests/performance/test_agent_performance.py
import pytest
import time
from concurrent.futures import ThreadPoolExecutor
from fsoa.agent.orchestrator import AgentOrchestrator

class TestAgentPerformance:
    """Agent性能测试"""

    def test_execution_time(self, test_config):
        """测试执行时间"""
        orchestrator = AgentOrchestrator(test_config)

        start_time = time.time()
        result = orchestrator.execute()
        execution_time = time.time() - start_time

        assert execution_time < 30  # 30秒内完成
        assert result.status == "completed"

    def test_concurrent_execution(self, test_config):
        """测试并发执行"""
        orchestrator = AgentOrchestrator(test_config)

        def execute_agent():
            return orchestrator.execute()

        # 并发执行10个Agent
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(execute_agent) for _ in range(10)]
            results = [future.result() for future in futures]

        # 验证所有执行都成功
        assert all(result.status == "completed" for result in results)
```

## 6. 测试数据管理

### 6.1 测试数据策略
- **固定数据**：使用fixtures提供稳定的测试数据
- **随机数据**：使用faker生成随机测试数据
- **边界数据**：测试极值和边界条件
- **异常数据**：测试错误和异常情况

### 6.2 测试数据示例
```python
# tests/fixtures/test_data.py
import pytest
from faker import Faker
from fsoa.data.models import TaskInfo

fake = Faker('zh_CN')

@pytest.fixture
def sample_tasks():
    """示例任务数据"""
    return [
        TaskInfo(
            id=1,
            title="设备维护任务",
            status="in_progress",
            sla_hours=8,
            elapsed_hours=10,
            group_id="group_001"
        ),
        TaskInfo(
            id=2,
            title="故障排查任务",
            status="in_progress",
            sla_hours=4,
            elapsed_hours=6,
            group_id="group_002"
        )
    ]

@pytest.fixture
def random_task():
    """随机任务数据"""
    return TaskInfo(
        id=fake.random_int(min=1, max=1000),
        title=fake.sentence(),
        status=fake.random_element(["in_progress", "completed", "cancelled"]),
        sla_hours=fake.random_int(min=1, max=24),
        elapsed_hours=fake.random_int(min=0, max=48),
        group_id=f"group_{fake.random_int(min=1, max=10):03d}"
    )
```

## 7. 持续集成

### 7.1 CI/CD流程
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt

    - name: Run unit tests
      run: pytest tests/unit/ --cov=src/fsoa

    - name: Run integration tests
      run: pytest tests/integration/

    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

### 7.2 测试报告
- **覆盖率报告**：目标80%以上代码覆盖率
- **性能报告**：监控执行时间趋势
- **质量报告**：代码质量和测试质量指标

## 8. 测试最佳实践

### 8.1 编写原则
- **AAA模式**：Arrange-Act-Assert结构清晰
- **单一职责**：每个测试只验证一个功能点
- **独立性**：测试之间不相互依赖
- **可重复性**：测试结果稳定一致

### 8.2 命名规范
```python
# 测试方法命名：test_[功能]_[场景]_[期望结果]
def test_fetch_tasks_with_valid_params_returns_task_list():
    pass

def test_send_notification_with_invalid_webhook_raises_error():
    pass

def test_agent_execution_with_no_tasks_completes_successfully():
    pass
```

### 8.3 Mock使用
- **外部依赖**：Mock所有外部API调用
- **时间相关**：Mock时间函数确保测试稳定
- **随机性**：Mock随机函数确保结果可预测
- **文件系统**：Mock文件操作避免副作用

---
> 测试是保证代码质量的重要手段，持续完善测试覆盖率和测试质量
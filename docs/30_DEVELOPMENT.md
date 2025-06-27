# FSOA 开发指南

Field Service Operations Assistant - 开发规范和最佳实践

## 1. 开发环境设置

### 1.1 系统要求
- Python 3.9+
- SQLite 3.x
- Git 2.x+

### 1.2 环境配置

```bash
# 克隆项目
git clone https://github.com/franksunye/FSOpsAssistant.git
cd FSOpsAssistant

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 初始化数据库
python scripts/init_db.py

# 启动Web界面（仅Web界面，用于开发测试）
python scripts/start_web.py

# 启动Agent服务（仅后台服务，无Web界面）
python scripts/start_agent.py

# 启动完整应用（Web界面+Agent服务，推荐）
python scripts/start_full_app.py
```

### 1.3 环境验证

```bash
# 运行测试套件
python scripts/run_tests.py

# 预期输出：
# ✅ 单元测试通过
# ✅ 集成测试通过
# ✅ 管理器组件测试通过
# ✅ Agent工作流测试通过

## 2. 部署指南

### 2.1 快速部署

#### 环境要求
- Python 3.9+
- Git
- 网络连接（访问Metabase和企微）

#### 部署步骤
```bash
# 1. 克隆项目
git clone https://github.com/franksunye/FSOpsAssistant.git
cd FSOpsAssistant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境
cp .env.example .env
nano .env  # 编辑配置文件

# 4. 初始化数据库
python scripts/init_db.py

# 5. 启动应用
python scripts/start_full_app.py  # Web + Agent
```

### 2.2 配置说明

#### 核心配置项
```env
# 数据库配置
DATABASE_URL=sqlite:///fsoa.db

# Metabase配置
METABASE_BASE_URL=https://your-metabase.com
METABASE_USERNAME=your-username
METABASE_PASSWORD=your-password

# 企微配置
WECHAT_WEBHOOK_LIST=["https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"]

# 通知配置
NOTIFICATION_COOLDOWN=120  # 2小时冷静时间
MAX_RETRY_COUNT=5          # 最大重试次数
```

### 2.3 生产部署

#### 推荐架构
```
┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   FSOA App      │
│   (反向代理)     │◄───┤   (Streamlit)   │
└─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   FSOA Agent    │
                       │   (后台服务)     │
                       └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   SQLite/       │
                       │   PostgreSQL    │
                       └─────────────────┘
```

#### 系统服务配置
```bash
# Agent服务
sudo nano /etc/systemd/system/fsoa-agent.service
```

```ini
[Unit]
Description=FSOA Agent Service
After=network.target

[Service]
Type=simple
User=fsoa
WorkingDirectory=/home/fsoa/FSOpsAssistant
Environment=PATH=/home/fsoa/FSOpsAssistant/venv/bin
ExecStart=/home/fsoa/FSOpsAssistant/venv/bin/python scripts/start_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2.4 升级指南

#### 从v0.1.x升级到v0.2.0
```bash
# 1. 备份数据
cp fsoa.db fsoa_backup_$(date +%Y%m%d).db

# 2. 更新代码
git pull origin main
pip install -r requirements.txt

# 3. 数据库迁移
python scripts/migrate_notification_tasks.py

# 4. 重启服务
python scripts/start_full_app.py
```

### 2.5 监控和维护

#### 日志查看
```bash
# 应用日志
tail -f logs/fsoa.log

# 系统服务日志
sudo journalctl -u fsoa-agent -f
```

#### 健康检查
```bash
# 检查服务状态
sudo systemctl status fsoa-agent

# 检查数据库
python scripts/test_database.py

# 检查外部连接
python scripts/test_connections.py
```

#### 备份策略
```bash
# 数据库备份
cp fsoa.db backups/fsoa_$(date +%Y%m%d_%H%M%S).db

# 自动备份脚本
crontab -e
# 添加: 0 2 * * * /home/fsoa/backup_fsoa.sh
```

# 验证系统健康状态
# 通过Web界面：[系统管理 → 系统测试] 进行全面验证
```

### 1.4 配置文件
```bash
# .env 文件示例
DEEPSEEK_API_KEY=your_deepseek_api_key
METABASE_URL=your_metabase_url
METABASE_USERNAME=your_username
METABASE_PASSWORD=your_password
# 企微配置已迁移到Web界面：[系统管理 → 企微群配置]
DATABASE_URL=sqlite:///fsoa.db
LOG_LEVEL=INFO
```

## 2. 项目结构

```
FSOpsAssistant/
├── src/
│   ├── fsoa/
│   │   ├── __init__.py
│   │   ├── agent/              # Agent核心模块
│   │   │   ├── orchestrator.py # Agent编排器
│   │   │   ├── tools.py        # 工具函数
│   │   │   └── decision.py     # 决策引擎
│   │   ├── data/               # 数据层
│   │   │   ├── models.py       # 数据模型
│   │   │   ├── database.py     # 数据库操作
│   │   │   └── metabase.py     # Metabase集成
│   │   ├── notification/       # 通知模块
│   │   │   ├── wechat.py       # 企微集成
│   │   │   └── templates.py    # 消息模板
│   │   ├── ui/                 # UI模块
│   │   │   ├── app.py          # Streamlit应用
│   │   │   └── components.py   # UI组件
│   │   └── utils/              # 工具模块
│   │       ├── config.py       # 配置管理
│   │       ├── logger.py       # 日志管理
│   │       └── scheduler.py    # 任务调度
├── tests/                      # 测试文件
├── scripts/                    # 脚本文件
├── docs/                       # 文档
├── requirements.txt            # 依赖列表
├── .env.example               # 环境变量示例
└── README.md                  # 项目说明
```

## 3. 开发规范

### 3.1 代码风格
- **PEP 8**：遵循Python官方代码规范
- **类型注解**：使用Type Hints提高代码可读性
- **文档字符串**：使用Google风格的docstring
- **命名规范**：
  - 类名：PascalCase (e.g., `TaskProcessor`)
  - 函数名：snake_case (e.g., `fetch_overdue_tasks`)
  - 常量：UPPER_CASE (e.g., `MAX_RETRY_COUNT`)

### 3.2 代码示例
```python
from typing import List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class TaskInfo(BaseModel):
    """任务信息模型"""
    id: int
    title: str
    status: str
    sla_hours: int
    elapsed_hours: float
    group_id: Optional[str] = None

def fetch_overdue_tasks(sla_threshold: float = 1.0) -> List[TaskInfo]:
    """
    获取超时任务列表

    Args:
        sla_threshold: SLA阈值倍数，默认1.0表示刚好超时

    Returns:
        超时任务列表

    Raises:
        ConnectionError: 当无法连接到数据源时
    """
    try:
        # 实现逻辑
        logger.info(f"Fetching overdue tasks with threshold: {sla_threshold}")
        return []
    except Exception as e:
        logger.error(f"Failed to fetch overdue tasks: {e}")
        raise
```

### 3.3 错误处理
```python
# 统一错误处理模式
class FSOAError(Exception):
    """FSOA基础异常类"""
    pass

class DataSourceError(FSOAError):
    """数据源异常"""
    pass

class NotificationError(FSOAError):
    """通知发送异常"""
    pass

# 使用示例
def send_notification(message: str) -> bool:
    try:
        # 发送逻辑
        return True
    except requests.RequestException as e:
        raise NotificationError(f"Failed to send notification: {e}")
```

## 4. Agent开发指南

### 4.1 LangGraph使用
```python
from langgraph import StateGraph, ToolNode, END
from typing import TypedDict

class AgentState(TypedDict):
    """Agent状态定义"""
    tasks: List[TaskInfo]
    notifications_sent: int
    errors: List[str]

def create_agent_graph() -> StateGraph:
    """创建Agent执行图"""
    graph = StateGraph(AgentState)

    # 定义节点
    fetch_node = ToolNode(tool=fetch_overdue_tasks)
    analyze_node = ToolNode(tool=analyze_tasks)
    notify_node = ToolNode(tool=send_notifications)

    # 定义边
    graph.add_edge("start", "fetch")
    graph.add_edge("fetch", "analyze")
    graph.add_conditional_edge(
        "analyze",
        lambda state: "notify" if state["tasks"] else "end",
        {"notify": "notify", "end": END}
    )
    graph.add_edge("notify", END)

    return graph
```

### 4.2 工具函数开发
```python
from functools import wraps
import time

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(delay * (2 ** attempt))  # 指数退避
            return None
        return wrapper
    return decorator

@retry_on_failure(max_retries=3)
def fetch_from_metabase(query: str) -> List[dict]:
    """从Metabase获取数据"""
    # 实现逻辑
    pass
```

### 4.3 LLM集成
```python
from openai import OpenAI

class DecisionEngine:
    """决策引擎"""

    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

    def analyze_task_priority(self, task: TaskInfo) -> dict:
        """分析任务优先级"""
        prompt = f"""
        分析以下任务的紧急程度和处理建议：

        任务ID: {task.id}
        任务标题: {task.title}
        当前状态: {task.status}
        SLA时间: {task.sla_hours}小时
        已用时间: {task.elapsed_hours}小时
        超时程度: {task.elapsed_hours / task.sla_hours:.1f}倍

        请返回JSON格式：
        {{
            "priority": "low|normal|high|urgent",
            "action": "skip|notify|escalate",
            "message": "建议的通知消息",
            "reasoning": "决策理由"
        }}
        """

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        return json.loads(response.choices[0].message.content)
```

## 5. 测试指南

### 5.1 测试结构
```
tests/
├── unit/                   # 单元测试
│   ├── test_agent.py
│   ├── test_data.py
│   └── test_notification.py
├── integration/            # 集成测试
│   ├── test_metabase.py
│   └── test_wechat.py
├── e2e/                   # 端到端测试
│   └── test_full_workflow.py
└── fixtures/              # 测试数据
    └── sample_data.json
```

### 5.2 测试示例
```python
import pytest
from unittest.mock import Mock, patch
from fsoa.agent.tools import fetch_overdue_tasks

class TestTaskFetching:
    """任务获取测试"""

    @pytest.fixture
    def mock_metabase_response(self):
        return [
            {
                "id": 1,
                "title": "测试任务",
                "status": "in_progress",
                "sla_hours": 8,
                "elapsed_hours": 10
            }
        ]

    @patch('fsoa.data.metabase.MetabaseClient')
    def test_fetch_overdue_tasks_success(self, mock_client, mock_metabase_response):
        """测试成功获取超时任务"""
        mock_client.return_value.query.return_value = mock_metabase_response

        tasks = fetch_overdue_tasks()

        assert len(tasks) == 1
        assert tasks[0].id == 1
        assert tasks[0].elapsed_hours > tasks[0].sla_hours

    @patch('fsoa.data.metabase.MetabaseClient')
    def test_fetch_overdue_tasks_connection_error(self, mock_client):
        """测试连接错误处理"""
        mock_client.return_value.query.side_effect = ConnectionError("Connection failed")

        with pytest.raises(DataSourceError):
            fetch_overdue_tasks()
```

### 5.3 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_agent.py

# 运行测试并生成覆盖率报告
pytest --cov=src/fsoa --cov-report=html

# 运行测试并显示详细输出
pytest -v -s
```

## 6. 部署指南

### 6.1 本地开发部署
```bash
# 启动Streamlit应用
streamlit run src/fsoa/ui/app.py

# 启动Agent调度器
python src/fsoa/utils/scheduler.py

# 查看日志
tail -f logs/fsoa.log
```

### 6.2 生产环境部署
```bash
# 使用Docker部署
docker build -t fsoa:latest .
docker run -d --name fsoa -p 8501:8501 -v ./data:/app/data fsoa:latest

# 使用docker-compose
docker-compose up -d
```

## 7. 监控和调试

### 7.1 日志配置
```python
# 日志配置示例
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': 'logs/fsoa.log',
        },
    },
    'loggers': {
        'fsoa': {
            'handlers': ['default', 'file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}
```

### 7.2 性能监控
```python
import time
from functools import wraps

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    return wrapper
```

---
> 开发指南持续更新，确保团队开发效率和代码质量
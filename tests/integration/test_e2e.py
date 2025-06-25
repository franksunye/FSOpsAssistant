"""
端到端集成测试

测试完整的业务流程
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# 添加项目路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.fsoa.agent.orchestrator import AgentOrchestrator
from src.fsoa.agent.decision import DecisionEngine, DecisionMode
from src.fsoa.data.database import DatabaseManager
from src.fsoa.data.models import TaskInfo, TaskStatus, Priority
from src.fsoa.utils.config import Config


class TestEndToEndWorkflow:
    """端到端工作流测试"""
    
    @pytest.fixture
    def test_db_manager(self):
        """创建测试数据库管理器"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        db_manager = DatabaseManager(f"sqlite:///{db_path}")
        db_manager.init_database()
        
        yield db_manager
        
        # 清理
        os.unlink(db_path)
    
    @pytest.fixture
    def test_config(self, test_db_manager):
        """测试配置"""
        return Config(
            deepseek_api_key="test-key",
            metabase_url="http://test-metabase",
            metabase_username="test-user",
            metabase_password="test-pass",
            wechat_webhook_urls="http://test-webhook",
            database_url="sqlite:///test.db",
            use_llm_optimization=False,  # 使用规则模式避免LLM调用
            debug=True,
            testing=True
        )
    
    @pytest.fixture
    def sample_overdue_tasks(self):
        """示例超时任务"""
        return [
            TaskInfo(
                id=1001,
                title="紧急设备维护",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.HIGH,
                sla_hours=4,
                elapsed_hours=6,  # 超时2小时
                group_id="group_001",
                assignee="张三",
                customer="重要客户A",
                location="北京市朝阳区",
                created_at=datetime.now() - timedelta(hours=6),
                updated_at=datetime.now()
            ),
            TaskInfo(
                id=1002,
                title="常规检查任务",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.NORMAL,
                sla_hours=8,
                elapsed_hours=10,  # 超时2小时
                group_id="group_002",
                assignee="李四",
                customer="普通客户B",
                location="上海市浦东区",
                created_at=datetime.now() - timedelta(hours=10),
                updated_at=datetime.now()
            ),
            TaskInfo(
                id=1003,
                title="严重故障处理",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.URGENT,
                sla_hours=2,
                elapsed_hours=5,  # 严重超时3小时
                group_id="group_001",
                assignee="王五",
                customer="VIP客户C",
                location="深圳市南山区",
                created_at=datetime.now() - timedelta(hours=5),
                updated_at=datetime.now()
            )
        ]
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    @patch('src.fsoa.agent.tools.send_wechat_message')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_complete_agent_workflow(self, mock_db_manager, mock_send_wechat, 
                                   mock_metabase_client, test_db_manager, 
                                   sample_overdue_tasks):
        """测试完整的Agent工作流"""
        # Arrange
        # Mock Metabase客户端
        mock_client = Mock()
        mock_client.get_overdue_tasks.return_value = sample_overdue_tasks
        mock_metabase_client.return_value = mock_client
        
        # Mock 企微发送
        mock_send_wechat.return_value = True
        
        # Mock 数据库管理器
        mock_db_manager.return_value = test_db_manager
        
        # 创建Agent
        orchestrator = AgentOrchestrator()
        
        # Act
        result = orchestrator.execute(dry_run=False)
        
        # Assert
        assert result.status.value in ["idle", "completed"]
        assert result.tasks_processed == 3  # 处理了3个任务
        assert result.notifications_sent >= 0  # 发送了通知
        
        # 验证Metabase调用
        mock_client.get_overdue_tasks.assert_called_once()
        
        # 验证数据库保存
        assert test_db_manager.save_agent_execution.call_count >= 1
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    @patch('src.fsoa.agent.tools.send_wechat_message')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_agent_workflow_with_no_tasks(self, mock_db_manager, mock_send_wechat, 
                                        mock_metabase_client, test_db_manager):
        """测试无超时任务的工作流"""
        # Arrange
        mock_client = Mock()
        mock_client.get_overdue_tasks.return_value = []  # 无超时任务
        mock_metabase_client.return_value = mock_client
        
        mock_db_manager.return_value = test_db_manager
        
        orchestrator = AgentOrchestrator()
        
        # Act
        result = orchestrator.execute(dry_run=False)
        
        # Assert
        assert result.tasks_processed == 0
        assert result.notifications_sent == 0
        assert len(result.errors) == 0
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_agent_workflow_with_metabase_error(self, mock_db_manager, mock_metabase_client, 
                                              test_db_manager):
        """测试Metabase错误的处理"""
        # Arrange
        mock_client = Mock()
        mock_client.get_overdue_tasks.side_effect = Exception("Metabase connection failed")
        mock_metabase_client.return_value = mock_client
        
        mock_db_manager.return_value = test_db_manager
        
        orchestrator = AgentOrchestrator()
        
        # Act
        result = orchestrator.execute(dry_run=False)
        
        # Assert
        assert len(result.errors) > 0
        assert "Metabase connection failed" in str(result.errors)
    
    def test_decision_engine_integration(self, sample_overdue_tasks):
        """测试决策引擎集成"""
        # 测试不同决策模式
        modes = [DecisionMode.RULE_ONLY, DecisionMode.HYBRID]
        
        for mode in modes:
            decision_engine = DecisionEngine(mode)
            
            for task in sample_overdue_tasks:
                result = decision_engine.make_decision(task)
                
                # 验证决策结果
                assert result.action in ["skip", "notify", "escalate"]
                assert result.priority in [Priority.LOW, Priority.NORMAL, Priority.HIGH, Priority.URGENT]
                assert result.confidence >= 0 and result.confidence <= 1
                
                # 验证严重超时任务会被升级
                if task.overdue_ratio >= 2.0:
                    assert result.action == "escalate"
                    assert result.priority == Priority.URGENT


class TestSystemIntegration:
    """系统集成测试"""
    
    def test_database_operations(self):
        """测试数据库操作集成"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            # 创建数据库管理器
            db_manager = DatabaseManager(f"sqlite:///{db_path}")
            db_manager.init_database()
            
            # 测试任务保存和查询
            task = TaskInfo(
                id=1001,
                title="集成测试任务",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.NORMAL,
                sla_hours=8,
                elapsed_hours=10,
                group_id="test_group",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 保存任务
            success = db_manager.save_task(task)
            assert success is True
            
            # 查询任务
            tasks = db_manager.get_tasks(status=TaskStatus.IN_PROGRESS)
            assert len(tasks) >= 1
            
            # 验证任务数据
            saved_task = next((t for t in tasks if t.id == 1001), None)
            assert saved_task is not None
            assert saved_task.title == "集成测试任务"
            assert saved_task.is_overdue is True
            
        finally:
            os.unlink(db_path)
    
    @patch('src.fsoa.notification.wechat.requests.post')
    def test_notification_integration(self, mock_post):
        """测试通知系统集成"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_response
        
        # 创建测试任务
        task = TaskInfo(
            id=1001,
            title="通知测试任务",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            sla_hours=4,
            elapsed_hours=6,
            group_id="test_group",
            assignee="测试人员",
            customer="测试客户",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Act
        from src.fsoa.notification.wechat import send_wechat_message
        result = send_wechat_message("test_group", "测试消息")
        
        # Assert
        assert result is True
        mock_post.assert_called_once()
        
        # 验证请求参数
        call_args = mock_post.call_args
        assert "json" in call_args.kwargs
        assert call_args.kwargs["json"]["msgtype"] == "text"
        assert "测试消息" in call_args.kwargs["json"]["text"]["content"]


class TestPerformanceIntegration:
    """性能集成测试"""
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    @patch('src.fsoa.agent.tools.send_wechat_message')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_agent_performance_with_many_tasks(self, mock_db_manager, mock_send_wechat, 
                                             mock_metabase_client):
        """测试大量任务的Agent性能"""
        # 创建大量测试任务
        large_task_list = []
        for i in range(100):
            task = TaskInfo(
                id=i + 1,
                title=f"性能测试任务{i+1}",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.NORMAL,
                sla_hours=8,
                elapsed_hours=10,  # 都是超时任务
                group_id=f"group_{i % 5 + 1:03d}",
                assignee=f"测试人员{i % 10 + 1}",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            large_task_list.append(task)
        
        # Mock设置
        mock_client = Mock()
        mock_client.get_overdue_tasks.return_value = large_task_list
        mock_metabase_client.return_value = mock_client
        
        mock_send_wechat.return_value = True
        
        mock_db = Mock()
        mock_db.save_agent_execution.return_value = True
        mock_db.save_task.return_value = True
        mock_db.save_notification.return_value = 1
        mock_db_manager.return_value = mock_db
        
        # 执行性能测试
        orchestrator = AgentOrchestrator()
        
        start_time = datetime.now()
        result = orchestrator.execute(dry_run=False)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # 性能断言
        assert execution_time < 60  # 应在60秒内完成
        assert result.tasks_processed == 100
        assert len(result.errors) == 0

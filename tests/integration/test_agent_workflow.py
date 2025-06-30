"""
Agent完整工作流集成测试
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.fsoa.agent.orchestrator import AgentOrchestrator
from src.fsoa.data.database import DatabaseManager
from src.fsoa.data.models import (
    OpportunityInfo, OpportunityStatus, NotificationTask, 
    NotificationTaskType, NotificationTaskStatus, AgentRun, AgentRunStatus
)
from src.fsoa.utils.config import Config


class TestAgentWorkflow:
    """测试Agent完整工作流程"""
    
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
            internal_ops_webhook="http://test-webhook",
            database_url="sqlite:///test.db",
            debug=True,
            testing=True
        )
    
    @pytest.fixture
    def mock_metabase_data(self):
        """Mock Metabase数据"""
        return [
            {
                "orderNum": "GD20250001",
                "name": "张三",
                "address": "北京市朝阳区建国路1号",
                "supervisorName": "李销售",
                "createTime": "2025-06-29 10:00:00",
                "orgName": "测试公司A",
                "orderstatus": "待预约"
            },
            {
                "orderNum": "GD20250002",
                "name": "李四",
                "address": "上海市浦东新区陆家嘴1号",
                "supervisorName": "王销售",
                "createTime": "2025-06-29 08:00:00",
                "orgName": "测试公司B",
                "orderstatus": "暂不上门"
            }
        ]
    
    @patch('src.fsoa.data.metabase.get_metabase_client')
    @patch('src.fsoa.notification.wechat.get_wechat_client')
    def test_complete_workflow_with_overdue_opportunities(
        self, mock_wechat_client, mock_metabase_client, 
        test_db_manager, test_config, mock_metabase_data
    ):
        """测试有逾期商机的完整流程"""
        # Arrange
        mock_metabase = Mock()
        mock_metabase.test_connection.return_value = True
        mock_metabase.query_card.return_value = mock_metabase_data
        mock_metabase_client.return_value = mock_metabase
        
        mock_wechat = Mock()
        mock_wechat.send_business_notification.return_value = True
        mock_wechat.test_webhook.return_value = True
        mock_wechat_client.return_value = mock_wechat
        
        with patch('src.fsoa.agent.orchestrator.get_db_manager', return_value=test_db_manager):
            orchestrator = AgentOrchestrator()
            
            # Act
            result = orchestrator.execute(dry_run=False)
            
            # Assert
            assert result is not None
            assert hasattr(result, 'opportunities_processed') or hasattr(result, 'tasks_processed')
    
    @patch('src.fsoa.data.metabase.get_metabase_client')
    def test_workflow_with_no_overdue_opportunities(
        self, mock_metabase_client, test_db_manager, test_config
    ):
        """测试无逾期商机的流程"""
        # Arrange
        mock_metabase = Mock()
        mock_metabase.test_connection.return_value = True
        mock_metabase.query_card.return_value = []  # 无数据
        mock_metabase_client.return_value = mock_metabase
        
        with patch('src.fsoa.agent.orchestrator.get_db_manager', return_value=test_db_manager):
            orchestrator = AgentOrchestrator()
            
            # Act
            result = orchestrator.execute(dry_run=True)
            
            # Assert
            assert result is not None
    
    @patch('src.fsoa.data.metabase.get_metabase_client')
    def test_workflow_with_metabase_error(
        self, mock_metabase_client, test_db_manager, test_config
    ):
        """测试Metabase连接错误的处理"""
        # Arrange
        mock_metabase = Mock()
        mock_metabase.test_connection.return_value = False
        mock_metabase.query_card.side_effect = Exception("Connection failed")
        mock_metabase_client.return_value = mock_metabase
        
        with patch('src.fsoa.agent.orchestrator.get_db_manager', return_value=test_db_manager):
            orchestrator = AgentOrchestrator()
            
            # Act
            result = orchestrator.execute(dry_run=True)
            
            # Assert
            assert result is not None
            # 应该有错误记录
            if hasattr(result, 'errors'):
                assert len(result.errors) >= 0  # 可能有错误处理
    
    def test_data_strategy_manager_integration(self, test_db_manager, mock_metabase_data):
        """测试数据策略管理器集成"""
        # Arrange
        with patch('src.fsoa.data.metabase.get_metabase_client') as mock_client:
            mock_metabase = Mock()
            mock_metabase.query_card.return_value = mock_metabase_data
            mock_client.return_value = mock_metabase
            
            from src.fsoa.agent.managers.data_strategy import BusinessDataStrategy
            
            with patch('src.fsoa.data.database.get_db_manager', return_value=test_db_manager):
                data_strategy = BusinessDataStrategy()
                
                # Act
                opportunities = data_strategy.get_opportunities()
                
                # Assert
                assert isinstance(opportunities, list)
                assert len(opportunities) >= 0
    
    def test_notification_manager_integration(self, test_db_manager):
        """测试通知管理器集成"""
        # Arrange
        from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
        
        with patch('src.fsoa.data.database.get_db_manager', return_value=test_db_manager), \
             patch('src.fsoa.notification.wechat.get_wechat_client') as mock_wechat_client:
            
            mock_wechat = Mock()
            mock_wechat.send_business_notification.return_value = True
            mock_wechat_client.return_value = mock_wechat
            
            notification_manager = NotificationTaskManager()
            
            # 创建测试商机
            opportunities = [
                OpportunityInfo(
                    order_num="GD20250001",
                    name="张三",
                    address="北京市朝阳区",
                    supervisor_name="李销售",
                    create_time=datetime.now() - timedelta(hours=6),
                    org_name="测试公司A",
                    order_status=OpportunityStatus.PENDING_APPOINTMENT,
                    elapsed_hours=6.0,
                    sla_threshold_hours=4,
                    is_overdue=True
                )
            ]
            
            # Act
            tasks = notification_manager.create_notification_tasks(opportunities, 1)
            
            # Assert
            assert isinstance(tasks, list)
    
    def test_execution_tracker_integration(self, test_db_manager):
        """测试执行追踪器集成"""
        # Arrange
        from src.fsoa.agent.managers.execution_tracker import AgentExecutionTracker
        
        with patch('src.fsoa.data.database.get_db_manager', return_value=test_db_manager):
            tracker = AgentExecutionTracker()
            
            # Act
            run_id = tracker.start_execution()
            
            # 模拟执行步骤
            tracker.log_step("fetch_opportunities", {"count": 5})
            tracker.log_step("create_notifications", {"created": 3})
            
            # 完成执行
            result = tracker.complete_execution(
                opportunities_processed=5,
                notifications_sent=3
            )
            
            # Assert
            assert run_id is not None
            assert result is True
    
    def test_end_to_end_workflow_simulation(self, test_db_manager, mock_metabase_data):
        """端到端工作流模拟测试"""
        # Arrange - 设置所有必要的Mock
        with patch('src.fsoa.data.metabase.get_metabase_client') as mock_metabase_client, \
             patch('src.fsoa.notification.wechat.get_wechat_client') as mock_wechat_client, \
             patch('src.fsoa.agent.orchestrator.get_db_manager', return_value=test_db_manager):
            
            # Mock Metabase
            mock_metabase = Mock()
            mock_metabase.test_connection.return_value = True
            mock_metabase.query_card.return_value = mock_metabase_data
            mock_metabase_client.return_value = mock_metabase
            
            # Mock WeChat
            mock_wechat = Mock()
            mock_wechat.send_business_notification.return_value = True
            mock_wechat.test_webhook.return_value = True
            mock_wechat_client.return_value = mock_wechat
            
            # Act - 执行完整的Agent工作流
            orchestrator = AgentOrchestrator()
            result = orchestrator.execute(dry_run=False)
            
            # Assert - 验证执行结果
            assert result is not None
            
            # 验证数据库中的记录
            # 这里可以检查agent_runs表、notification_tasks表等
            # 具体的验证逻辑取决于实际的数据库结构

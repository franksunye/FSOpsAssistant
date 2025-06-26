"""
工具函数测试
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

from src.fsoa.agent.tools import (
    
    test_metabase_connection, test_wechat_webhook, get_system_health
)
from src.fsoa.data.models import TaskStatus, Priority, NotificationInfo


class TestFetchOverdueTasks:
    """测试任务获取功能"""
    
    @patch('src.fsoa.agent.tools.get_data_strategy')
    def test_fetch_overdue_tasks_success(self, mock_data_strategy, sample_task):
        """测试成功获取超时任务 - 已更新为使用新的数据策略"""
        # Arrange
        mock_strategy = Mock()
        mock_strategy.get_overdue_opportunities.return_value = []  # 返回空的商机列表
        mock_data_strategy.return_value = mock_strategy

        # Act
        tasks = fetch_overdue_tasks()

        # Assert
        assert isinstance(tasks, list)
        # 注意：此方法已废弃，主要测试其不会崩溃
        mock_strategy.get_overdue_opportunities.assert_called_once()
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    def test_fetch_overdue_tasks_empty_result(self, mock_metabase_client):
        """测试无超时任务的情况"""
        # Arrange
        mock_client = Mock()
        mock_client.get_overdue_tasks.return_value = []
        mock_metabase_client.return_value = mock_client
        
        # Act
        tasks = fetch_overdue_tasks()
        
        # Assert
        assert len(tasks) == 0
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    def test_fetch_overdue_tasks_metabase_error(self, mock_metabase_client):
        """测试Metabase错误处理"""
        # Arrange
        mock_client = Mock()
        mock_client.get_overdue_tasks.side_effect = Exception("Connection error")
        mock_metabase_client.return_value = mock_client
        
        # Act & Assert
        with pytest.raises(Exception):
            fetch_overdue_tasks()


class TestSendNotification:
    """测试通知发送功能"""
    
    @patch('src.fsoa.agent.tools.send_wechat_message')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_send_notification_success(self, mock_db_manager, mock_send_wechat, sample_task):
        """测试成功发送通知 - 已更新为使用新的通知系统"""
        # Arrange
        mock_send_wechat.return_value = True

        mock_db = Mock()
        # 注意：save_notification 和 save_task 方法已被移除，但保留 mock 以防测试中有引用
        mock_db_manager.return_value = mock_db

        # Act
        result = send_notification(sample_task, "测试消息")

        # Assert
        assert result is True
        mock_send_wechat.assert_called_once()
        # 注意：不再验证 save_notification 和 save_task 调用，因为这些方法已被移除
    
    def test_send_notification_no_group_id(self, sample_task):
        """测试无群组ID的情况"""
        # Arrange
        sample_task.group_id = None
        
        # Act
        result = send_notification(sample_task, "测试消息")
        
        # Assert
        assert result is False
    
    @patch('src.fsoa.agent.tools.send_wechat_message')
    def test_send_notification_wechat_error(self, mock_send_wechat, sample_task):
        """测试企微发送失败"""
        # Arrange
        mock_send_wechat.return_value = False
        
        # Act
        result = send_notification(sample_task, "测试消息")
        
        # Assert
        assert result is False
    
    @patch('src.fsoa.agent.tools._check_notification_cooldown')
    def test_send_notification_cooldown(self, mock_check_cooldown, sample_task):
        """测试通知冷却时间"""
        # Arrange
        mock_check_cooldown.return_value = False
        
        # Act
        result = send_notification(sample_task, "测试消息")
        
        # Assert
        assert result is False


class TestUpdateTaskStatus:
    """测试任务状态更新 - 已废弃功能的兼容性测试"""

    def test_update_task_status_deprecated(self, sample_task):
        """测试废弃的任务状态更新功能"""
        # Act - 调用已废弃的函数
        result = update_task_status(sample_task.id, "completed")

        # Assert - 废弃的函数应该返回 False
        assert result is False

    def test_update_task_status_not_found(self):
        """测试任务不存在的情况 - 废弃功能"""
        # Act - 调用已废弃的函数
        result = update_task_status(9999, "completed")

        # Assert - 废弃的函数应该返回 False
        assert result is False


class TestSystemHealth:
    """测试系统健康检查"""
    
    @patch('src.fsoa.agent.tools.test_metabase_connection')
    @patch('src.fsoa.agent.tools.test_wechat_webhook')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_get_system_health_all_healthy(self, mock_db_manager, mock_test_wechat, mock_test_metabase):
        """测试所有组件健康的情况"""
        # Arrange
        mock_test_metabase.return_value = True
        mock_test_wechat.return_value = True
        mock_db_manager.return_value = Mock()
        
        # Act
        health = get_system_health()
        
        # Assert
        assert health["metabase_connection"] is True
        assert health["wechat_webhook"] is True
        assert health["database_connection"] is True
        assert health["overall_status"] == "healthy"
    
    @patch('src.fsoa.agent.tools.test_metabase_connection')
    @patch('src.fsoa.agent.tools.test_wechat_webhook')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_get_system_health_degraded(self, mock_db_manager, mock_test_wechat, mock_test_metabase):
        """测试部分组件异常的情况"""
        # Arrange
        mock_test_metabase.return_value = True
        mock_test_wechat.return_value = False
        mock_db_manager.return_value = Mock()
        
        # Act
        health = get_system_health()
        
        # Assert
        assert health["metabase_connection"] is True
        assert health["wechat_webhook"] is False
        assert health["database_connection"] is True
        assert health["overall_status"] == "degraded"
    
    @patch('src.fsoa.agent.tools.test_metabase_connection')
    @patch('src.fsoa.agent.tools.test_wechat_webhook')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_get_system_health_unhealthy(self, mock_db_manager, mock_test_wechat, mock_test_metabase):
        """测试所有组件异常的情况"""
        # Arrange
        mock_test_metabase.return_value = False
        mock_test_wechat.return_value = False
        mock_db_manager.side_effect = Exception("DB Error")
        
        # Act
        health = get_system_health()
        
        # Assert
        assert health["overall_status"] == "unhealthy"

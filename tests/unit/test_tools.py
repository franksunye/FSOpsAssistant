"""
工具函数测试
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

from src.fsoa.agent.tools import (
    fetch_overdue_tasks, send_notification, update_task_status,
    test_metabase_connection, test_wechat_webhook, get_system_health
)
from src.fsoa.data.models import TaskInfo, TaskStatus, Priority, NotificationInfo


class TestFetchOverdueTasks:
    """测试任务获取功能"""
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_fetch_overdue_tasks_success(self, mock_db_manager, mock_metabase_client, sample_task):
        """测试成功获取超时任务"""
        # Arrange
        mock_client = Mock()
        mock_client.get_overdue_tasks.return_value = [sample_task]
        mock_metabase_client.return_value = mock_client
        
        mock_db = Mock()
        mock_db.save_task.return_value = True
        mock_db_manager.return_value = mock_db
        
        # Act
        tasks = fetch_overdue_tasks()
        
        # Assert
        assert len(tasks) == 1
        assert tasks[0].id == sample_task.id
        mock_client.get_overdue_tasks.assert_called_once()
        mock_db.save_task.assert_called_once()
    
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
        """测试成功发送通知"""
        # Arrange
        mock_send_wechat.return_value = True
        
        mock_db = Mock()
        mock_db.save_notification.return_value = 1
        mock_db.save_task.return_value = True
        mock_db_manager.return_value = mock_db
        
        # Act
        result = send_notification(sample_task, "测试消息")
        
        # Assert
        assert result is True
        mock_send_wechat.assert_called_once()
        mock_db.save_notification.assert_called_once()
        mock_db.save_task.assert_called_once()
    
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
    """测试任务状态更新"""
    
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_update_task_status_success(self, mock_db_manager, sample_task):
        """测试成功更新任务状态"""
        # Arrange
        mock_db = Mock()
        mock_db.get_tasks.return_value = [sample_task]
        mock_db.save_task.return_value = True
        mock_db_manager.return_value = mock_db
        
        # Act
        result = update_task_status(sample_task.id, "completed")
        
        # Assert
        assert result is True
        mock_db.save_task.assert_called_once()
    
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_update_task_status_not_found(self, mock_db_manager):
        """测试任务不存在的情况"""
        # Arrange
        mock_db = Mock()
        mock_db.get_tasks.return_value = []
        mock_db_manager.return_value = mock_db
        
        # Act
        result = update_task_status(9999, "completed")
        
        # Assert
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

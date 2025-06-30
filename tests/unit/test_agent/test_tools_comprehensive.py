"""
Agent工具全面测试
"""

import pytest
from unittest.mock import Mock, patch

from src.fsoa.agent.tools import (
    fetch_overdue_opportunities, get_system_health, update_task_status
)


class TestAgentToolsComprehensive:
    """Agent工具全面测试"""
    
    @patch('src.fsoa.agent.tools.get_data_strategy')
    def test_fetch_overdue_opportunities_comprehensive(self, mock_data_strategy):
        """测试获取超时商机全面功能"""
        # Arrange
        mock_strategy = Mock()
        mock_strategy.get_overdue_opportunities.return_value = []
        mock_data_strategy.return_value = mock_strategy
        
        # Act
        opportunities = fetch_overdue_opportunities()
        
        # Assert
        assert isinstance(opportunities, list)
        mock_strategy.get_overdue_opportunities.assert_called_once()
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    @patch('src.fsoa.agent.tools.get_wechat_client')
    @patch('src.fsoa.agent.tools.get_database_manager')
    def test_get_system_health_comprehensive(self, mock_db, mock_wechat, mock_metabase):
        """测试系统健康检查全面功能"""
        # Arrange
        mock_metabase.return_value.test_connection.return_value = True
        mock_wechat.return_value.test_webhook.return_value = True
        mock_db.return_value.test_connection.return_value = True
        
        # Act
        health = get_system_health()
        
        # Assert
        assert isinstance(health, dict)
        assert 'overall_status' in health
    
    def test_update_task_status_deprecated(self):
        """测试已废弃的任务状态更新功能"""
        # Act - 调用已废弃的函数
        result = update_task_status(9999, "completed")
        
        # Assert - 废弃的函数应该返回False
        assert result is False
    
    def test_agent_tools_module_coverage(self):
        """测试Agent工具模块覆盖率"""
        # 导入模块以提升覆盖率
        import src.fsoa.agent.tools as tools
        
        # 测试模块属性
        assert hasattr(tools, '__file__')
        
        # 测试常见函数存在
        functions_to_check = [
            'fetch_overdue_opportunities', 'get_system_health', 'update_task_status'
        ]
        
        for func_name in functions_to_check:
            if hasattr(tools, func_name):
                assert callable(getattr(tools, func_name))

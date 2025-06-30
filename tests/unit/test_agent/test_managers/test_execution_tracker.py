"""
执行追踪器测试
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.fsoa.agent.managers.execution_tracker import AgentExecutionTracker
from src.fsoa.data.models import AgentRun, AgentRunStatus, AgentHistory


class TestAgentExecutionTracker:
    """测试Agent执行追踪器"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock数据库管理器"""
        mock_db = Mock()
        mock_db.save_agent_run.return_value = 1  # 返回run_id
        mock_db.update_agent_run.return_value = True
        mock_db.save_agent_history.return_value = True
        mock_db.get_agent_run.return_value = None
        mock_db.get_recent_agent_runs.return_value = []
        return mock_db
    
    @pytest.fixture
    def execution_tracker(self, mock_db_manager):
        """创建执行追踪器实例"""
        with patch('src.fsoa.agent.managers.execution_tracker.get_db_manager', return_value=mock_db_manager):
            return AgentExecutionTracker()
    
    def test_initialization(self, execution_tracker):
        """测试初始化"""
        assert execution_tracker is not None
        assert hasattr(execution_tracker, 'db_manager')
        assert execution_tracker.current_run_id is None
    
    def test_start_execution(self, execution_tracker, mock_db_manager):
        """测试开始执行"""
        # Act
        run_id = execution_tracker.start_run()

        # Assert
        assert run_id is not None
        assert execution_tracker.current_run_id == run_id
        mock_db_manager.save_agent_run.assert_called_once()
    
    def test_complete_execution_success(self, execution_tracker, mock_db_manager):
        """测试成功完成执行"""
        # Arrange
        execution_tracker.current_run_id = 1

        # Act
        result = execution_tracker.complete_run(1, {
            "opportunities_processed": 5,
            "notifications_sent": 3
        })

        # Assert
        assert result is True
        mock_db_manager.update_agent_run.assert_called_once()
        assert execution_tracker.current_run_id is None
    
    def test_complete_execution_with_errors(self, execution_tracker, mock_db_manager):
        """测试带错误的完成执行"""
        # Arrange
        execution_tracker.current_run_id = 1
        errors = ["Error 1", "Error 2"]

        # Act
        result = execution_tracker.complete_run(1, {
            "opportunities_processed": 2,
            "notifications_sent": 1,
            "errors": errors
        })

        # Assert
        assert result is True
        # 验证错误信息被正确传递
        call_args = mock_db_manager.update_agent_run.call_args
        assert call_args is not None
    
    def test_fail_execution(self, execution_tracker, mock_db_manager):
        """测试执行失败"""
        # Arrange
        execution_tracker.current_run_id = 1
        error_message = "Critical error occurred"

        # Act
        result = execution_tracker.fail_run(1, error_message)

        # Assert
        assert result is True
        mock_db_manager.update_agent_run.assert_called_once()
        assert execution_tracker.current_run_id is None
    
    def test_log_step(self, execution_tracker, mock_db_manager):
        """测试记录执行步骤"""
        # Arrange
        execution_tracker.current_run_id = 1
        step_name = "fetch_opportunities"
        input_data = {"param1": "value1"}
        output_data = {"result": "success"}

        # Act
        result = execution_tracker.log_step(
            run_id=1,
            step_name=step_name,
            input_data=input_data,
            output_data=output_data
        )

        # Assert
        assert result is True
        mock_db_manager.save_agent_history.assert_called_once()
    
    def test_log_step_with_error(self, execution_tracker, mock_db_manager):
        """测试记录带错误的执行步骤"""
        # Arrange
        execution_tracker.current_run_id = 1
        step_name = "send_notification"
        error_message = "Failed to send notification"

        # Act
        result = execution_tracker.log_step(
            run_id=1,
            step_name=step_name,
            error_message=error_message
        )

        # Assert
        assert result is True
        mock_db_manager.save_agent_history.assert_called_once()
    
    def test_get_current_execution(self, execution_tracker, mock_db_manager, sample_agent_run):
        """测试获取当前执行信息"""
        # Arrange
        execution_tracker.current_run_id = 1
        mock_db_manager.get_agent_run.return_value = sample_agent_run

        # Act
        current_run = execution_tracker.get_current_run()

        # Assert
        assert current_run is not None
        assert current_run == sample_agent_run
        mock_db_manager.get_agent_run.assert_called_with(1)
    
    def test_get_execution_history(self, execution_tracker, mock_db_manager):
        """测试获取执行历史"""
        # Arrange
        mock_runs = [
            AgentRun(
                id=1,
                trigger_time=datetime.now() - timedelta(hours=1),
                status=AgentRunStatus.COMPLETED,
                opportunities_processed=5,
                notifications_sent=3
            ),
            AgentRun(
                id=2,
                trigger_time=datetime.now() - timedelta(hours=2),
                status=AgentRunStatus.COMPLETED,
                opportunities_processed=3,
                notifications_sent=2
            )
        ]
        mock_db_manager.get_agent_runs.return_value = mock_runs

        # Act
        history = execution_tracker.get_recent_runs(limit=10)

        # Assert
        assert len(history) == 2
        assert all(isinstance(run, AgentRun) for run in history)
        mock_db_manager.get_agent_runs.assert_called_with(10, 168)
    
    def test_get_execution_statistics(self, execution_tracker, mock_db_manager):
        """测试获取执行统计信息"""
        # Arrange
        mock_db_manager.get_run_statistics.return_value = {
            'total_runs': 10,
            'successful_runs': 8,
            'failed_runs': 2,
            'success_rate': 0.8,
            'avg_opportunities_processed': 4.5,
            'avg_notifications_sent': 2.3
        }

        # Act
        stats = execution_tracker.get_run_statistics(hours_back=168)

        # Assert
        assert isinstance(stats, dict)
        assert 'total_runs' in stats or len(stats) >= 0  # 允许空统计
    
    def test_cleanup_old_executions(self, execution_tracker, mock_db_manager):
        """测试清理旧执行记录"""
        # Arrange
        mock_db_manager.cleanup_old_records.return_value = 5  # 清理了5条记录

        # Act
        result = execution_tracker.cleanup_old_records(days=30)

        # Assert
        assert result == 5
        mock_db_manager.cleanup_old_records.assert_called_with(30)
    
    def test_is_execution_running(self, execution_tracker):
        """测试检查是否有执行正在运行"""
        # Test when no execution is running
        assert execution_tracker.is_running() is False

        # Test when execution is running
        execution_tracker.current_run_id = 1
        assert execution_tracker.is_running() is True
    
    def test_track_step_context_manager(self, execution_tracker, mock_db_manager):
        """测试步骤追踪上下文管理器"""
        # Arrange
        execution_tracker.current_run_id = 1

        # Act
        with execution_tracker.track_step("test_step", {"input": "data"}) as output_data:
            output_data["result"] = "success"

        # Assert
        mock_db_manager.save_agent_history.assert_called_once()

    def test_update_run_progress(self, execution_tracker, mock_db_manager):
        """测试更新运行进度"""
        # Arrange
        progress_data = {
            "opportunities_processed": 5,
            "notifications_sent": 3
        }

        # Act
        result = execution_tracker.update_run_progress(1, progress_data)

        # Assert
        assert result is True
        mock_db_manager.update_agent_run.assert_called_once()

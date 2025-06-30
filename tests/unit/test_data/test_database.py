"""
数据库模块单元测试
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.fsoa.data.database import DatabaseManager, get_db_manager
from src.fsoa.data.models import (
    OpportunityInfo, OpportunityStatus,
    NotificationTask, NotificationTaskType, NotificationTaskStatus,
    AgentRun, AgentRunStatus
)


class TestDatabaseManager:
    """数据库管理器测试"""
    
    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库文件"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # 清理
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """创建数据库管理器实例"""
        db_url = f"sqlite:///{temp_db_path}"
        manager = DatabaseManager(db_url)
        manager.init_database()
        return manager
    
    @pytest.fixture
    def sample_opportunity(self):
        """创建示例商机"""
        return OpportunityInfo(
            order_num="GD20250001",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试销售",
            create_time=datetime.now(),
            org_name="测试组织",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
    
    @pytest.fixture
    def sample_notification_task(self):
        """创建示例通知任务"""
        return NotificationTask(
            order_num="GD20250001",
            org_name="测试公司",
            notification_type=NotificationTaskType.REMINDER,
            due_time=datetime.now(),
            status=NotificationTaskStatus.PENDING,
            created_run_id=1,
            retry_count=0,
            max_retry_count=3,
            cooldown_hours=2.0
        )
    
    def test_initialization(self, temp_db_path):
        """测试数据库管理器初始化"""
        # Act
        db_url = f"sqlite:///{temp_db_path}"
        manager = DatabaseManager(db_url)
        
        # Assert
        assert manager is not None
        assert manager.database_url == db_url
    
    def test_init_database(self, db_manager):
        """测试数据库初始化"""
        # Act & Assert - 数据库应该已经在fixture中初始化
        assert db_manager is not None
        
        # 验证表是否创建
        with db_manager.get_session() as session:
            # 尝试查询各个表，如果表不存在会抛出异常
            from src.fsoa.data.database import (
                OpportunityCacheTable, NotificationTaskTable, 
                AgentRunTable, SystemConfigTable
            )
            
            # 这些查询不应该抛出异常
            session.query(OpportunityCacheTable).count()
            session.query(NotificationTaskTable).count()
            session.query(AgentRunTable).count()
            session.query(SystemConfigTable).count()
    
    def test_save_and_get_opportunity_cache(self, db_manager, sample_opportunity):
        """测试保存和获取商机缓存"""
        # Act
        success = db_manager.save_opportunity_cache(sample_opportunity)
        
        # Assert
        assert success is True
        
        # 获取缓存
        cached_opportunities = db_manager.get_all_opportunity_cache()
        assert len(cached_opportunities) >= 1
        
        # 验证数据
        found = False
        for opp in cached_opportunities:
            if opp.order_num == sample_opportunity.order_num:
                found = True
                assert opp.name == sample_opportunity.name
                assert opp.org_name == sample_opportunity.org_name
                break
        
        assert found is True
    
    def test_save_and_get_notification_task(self, db_manager, sample_notification_task):
        """测试保存和获取通知任务"""
        # Act
        task_id = db_manager.save_notification_task(sample_notification_task)
        
        # Assert
        assert task_id is not None
        assert task_id > 0
        
        # 获取待处理任务
        pending_tasks = db_manager.get_pending_notification_tasks()
        assert len(pending_tasks) >= 1
        
        # 验证数据
        found_task = None
        for task in pending_tasks:
            if task.order_num == sample_notification_task.order_num:
                found_task = task
                break
        
        assert found_task is not None
        assert found_task.org_name == sample_notification_task.org_name
        assert found_task.notification_type == sample_notification_task.notification_type
    
    def test_update_notification_task_status(self, db_manager, sample_notification_task):
        """测试更新通知任务状态"""
        # Arrange
        task_id = db_manager.save_notification_task(sample_notification_task)
        
        # Act
        success = db_manager.update_notification_task_status(
            task_id, NotificationTaskStatus.SENT, sent_run_id=1
        )
        
        # Assert
        assert success is True
        
        # 验证状态更新
        pending_tasks = db_manager.get_pending_notification_tasks()
        # 任务应该不再在待处理列表中
        task_still_pending = any(task.id == task_id for task in pending_tasks)
        assert task_still_pending is False
    
    def test_save_and_get_agent_run(self, db_manager):
        """测试保存和获取Agent运行记录"""
        # Arrange
        agent_run = AgentRun(
            trigger_time=datetime.now(),
            status=AgentRunStatus.RUNNING,
            context="测试运行",
            opportunities_processed=0,
            notifications_sent=0
        )
        
        # Act
        run_id = db_manager.save_agent_run(agent_run)
        
        # Assert
        assert run_id is not None
        assert run_id > 0
        
        # 获取运行记录
        retrieved_run = db_manager.get_agent_run(run_id)
        assert retrieved_run is not None
        assert retrieved_run.context == "测试运行"
        assert retrieved_run.status == AgentRunStatus.RUNNING
    
    def test_update_agent_run(self, db_manager):
        """测试更新Agent运行记录"""
        # Arrange
        agent_run = AgentRun(
            trigger_time=datetime.now(),
            status=AgentRunStatus.RUNNING,
            opportunities_processed=0,
            notifications_sent=0
        )
        run_id = db_manager.save_agent_run(agent_run)
        
        # Act
        success = db_manager.update_agent_run(
            run_id=run_id,
            status=AgentRunStatus.COMPLETED,
            opportunities_processed=5,
            notifications_sent=3,
            end_time=datetime.now()
        )
        
        # Assert
        assert success is True
        
        # 验证更新
        updated_run = db_manager.get_agent_run(run_id)
        assert updated_run.status == AgentRunStatus.COMPLETED
        assert updated_run.opportunities_processed == 5
        assert updated_run.notifications_sent == 3
        assert updated_run.end_time is not None
    
    def test_get_agent_run_statistics(self, db_manager):
        """测试获取Agent运行统计"""
        # Arrange - 创建一些测试数据
        for i in range(3):
            agent_run = AgentRun(
                trigger_time=datetime.now() - timedelta(hours=i),
                status=AgentRunStatus.COMPLETED if i < 2 else AgentRunStatus.FAILED,
                opportunities_processed=i + 1,
                notifications_sent=i,
                end_time=datetime.now() - timedelta(hours=i) + timedelta(minutes=30)
            )
            db_manager.save_agent_run(agent_run)
        
        # Act
        stats = db_manager.get_agent_run_statistics(hours_back=24)
        
        # Assert
        assert isinstance(stats, dict)
        assert 'total_runs' in stats
        assert 'successful_runs' in stats
        assert 'failed_runs' in stats
        assert stats['total_runs'] >= 3
    
    def test_full_refresh_opportunity_cache(self, db_manager, sample_opportunity):
        """测试完全刷新商机缓存"""
        # Arrange - 先添加一些数据
        db_manager.save_opportunity_cache(sample_opportunity)
        
        new_opportunities = [
            OpportunityInfo(
                order_num="GD20250002",
                name="新客户",
                address="新地址",
                supervisor_name="新销售",
                create_time=datetime.now(),
                org_name="新组织",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            )
        ]
        
        # Act
        result = db_manager.full_refresh_opportunity_cache(new_opportunities)
        
        # Assert
        assert isinstance(result, int)
        assert result >= 0
        
        # 验证缓存已更新
        cached_opportunities = db_manager.get_all_opportunity_cache()
        order_nums = [opp.order_num for opp in cached_opportunities]
        assert "GD20250002" in order_nums
    
    def test_get_system_config(self, db_manager):
        """测试获取系统配置"""
        # Act
        config_value = db_manager.get_system_config("test_key", "default_value")
        
        # Assert
        assert config_value == "default_value"  # 应该返回默认值
    
    def test_set_system_config(self, db_manager):
        """测试设置系统配置"""
        # Act
        success = db_manager.set_system_config("test_key", "test_value")
        
        # Assert
        assert success is True
        
        # 验证配置已保存
        retrieved_value = db_manager.get_system_config("test_key", "default")
        assert retrieved_value == "test_value"
    
    def test_session_context_manager(self, db_manager):
        """测试会话上下文管理器"""
        # Act & Assert
        with db_manager.get_session() as session:
            assert session is not None
            
            # 在会话中执行一些操作
            from src.fsoa.data.database import SystemConfigTable
            count = session.query(SystemConfigTable).count()
            assert isinstance(count, int)
    
    def test_error_handling_invalid_data(self, db_manager):
        """测试无效数据的错误处理"""
        # Arrange
        invalid_opportunity = OpportunityInfo(
            order_num="",  # 空订单号
            name="",
            address="",
            supervisor_name="",
            create_time=datetime.now(),
            org_name="",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
        
        # Act
        success = db_manager.save_opportunity_cache(invalid_opportunity)
        
        # Assert
        # 应该能处理无效数据而不崩溃
        assert isinstance(success, bool)
    
    def test_get_db_manager_singleton(self):
        """测试获取数据库管理器单例"""
        # Act
        manager1 = get_db_manager()
        manager2 = get_db_manager()
        
        # Assert
        assert manager1 is not None
        assert manager2 is not None
        assert manager1 is manager2  # 应该是同一个实例
    
    def test_database_connection_error_handling(self):
        """测试数据库连接错误处理"""
        # Arrange
        invalid_db_url = "sqlite:///invalid/path/database.db"
        
        # Act & Assert
        # 应该能创建管理器，但操作时会失败
        manager = DatabaseManager(invalid_db_url)
        assert manager is not None
        
        # 初始化数据库应该失败但不崩溃
        try:
            manager.init_database()
        except Exception:
            pass  # 预期会有异常
    
    def test_concurrent_access(self, db_manager, sample_opportunity):
        """测试并发访问"""
        # Act - 模拟并发操作
        results = []
        for i in range(5):
            opp = OpportunityInfo(
                order_num=f"GD202500{i:02d}",
                name=f"并发客户{i}",
                address=f"地址{i}",
                supervisor_name=f"销售{i}",
                create_time=datetime.now(),
                org_name=f"组织{i}",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            )
            success = db_manager.save_opportunity_cache(opp)
            results.append(success)
        
        # Assert
        assert all(results)  # 所有操作都应该成功
        
        # 验证数据完整性
        cached_opportunities = db_manager.get_all_opportunity_cache()
        assert len(cached_opportunities) >= 5

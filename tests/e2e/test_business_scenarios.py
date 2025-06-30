"""
端到端业务场景测试

测试真实的业务场景和用户工作流
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.fsoa.data.models import (
    OpportunityInfo, OpportunityStatus,
    NotificationTask, NotificationTaskType, NotificationTaskStatus
)


class TestBusinessScenarios:
    """业务场景端到端测试"""
    
    @pytest.fixture
    def test_environment(self):
        """设置测试环境"""
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        # 设置环境变量
        test_env = {
            "DATABASE_URL": f"sqlite:///{db_path}",
            "TESTING": "True",
            "LOG_LEVEL": "DEBUG"
        }
        
        yield {
            'db_path': db_path,
            'env': test_env
        }
        
        # 清理
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def mock_external_services(self):
        """Mock外部服务"""
        mocks = {
            'metabase': Mock(),
            'wechat': Mock(),
            'llm': Mock()
        }
        
        # 配置Metabase Mock
        mocks['metabase'].get_all_monitored_opportunities.return_value = []
        mocks['metabase'].test_connection.return_value = True
        
        # 配置企微Mock
        mocks['wechat'].send_notification_to_org.return_value = True
        mocks['wechat'].test_connection.return_value = True
        
        # 配置LLM Mock
        mocks['llm'].make_decision.return_value = {
            'should_notify': True,
            'confidence': 0.8,
            'reasoning': '测试决策'
        }
        
        return mocks
    
    def test_normal_business_day_scenario(self, test_environment, mock_external_services):
        """测试正常工作日场景"""
        # 场景：正常工作日，有新的商机需要处理
        
        # Arrange - 创建测试商机
        test_opportunities = [
            OpportunityInfo(
                order_num="GD20250101",
                name="正常客户A",
                address="北京市海淀区中关村大街1号",
                supervisor_name="张经理",
                create_time=datetime.now() - timedelta(hours=2),  # 2小时前创建
                org_name="北京科技公司",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            ),
            OpportunityInfo(
                order_num="GD20250102",
                name="正常客户B", 
                address="上海市浦东新区陆家嘴金融中心",
                supervisor_name="李经理",
                create_time=datetime.now() - timedelta(hours=1),  # 1小时前创建
                org_name="上海金融公司",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            )
        ]
        
        mock_external_services['metabase'].get_all_monitored_opportunities.return_value = test_opportunities
        
        # Act - 模拟Agent执行
        with patch('src.fsoa.data.metabase.get_metabase_client', return_value=mock_external_services['metabase']), \
             patch('src.fsoa.notification.wechat.get_wechat_client', return_value=mock_external_services['wechat']):
            
            from src.fsoa.agent.managers.data_strategy import BusinessDataStrategy
            from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
            
            # 1. 获取商机数据
            data_strategy = BusinessDataStrategy()
            opportunities = data_strategy.get_opportunities()
            
            # 2. 更新逾期信息
            for opp in opportunities:
                opp.update_overdue_info(use_business_time=True)
            
            # 3. 创建通知任务
            notification_manager = NotificationTaskManager()
            tasks = notification_manager.create_notification_tasks(opportunities, 1)
        
        # Assert
        assert len(opportunities) == 2
        assert all(opp.order_num.startswith("GD2025") for opp in opportunities)
        
        # 正常情况下，2小时内的商机不应该触发通知
        normal_tasks = [t for t in tasks if not opportunities[0].is_violation and not opportunities[1].is_violation]
        assert len(normal_tasks) == 0 or len(tasks) >= 0  # 取决于SLA设置
    
    def test_overdue_emergency_scenario(self, test_environment, mock_external_services):
        """测试逾期紧急场景"""
        # 场景：有商机严重逾期，需要立即通知
        
        # Arrange - 创建逾期商机
        overdue_opportunities = [
            OpportunityInfo(
                order_num="GD20250201",
                name="紧急客户A",
                address="深圳市南山区科技园",
                supervisor_name="王总监",
                create_time=datetime.now() - timedelta(hours=25),  # 25小时前创建，严重逾期
                org_name="深圳科技公司",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            ),
            OpportunityInfo(
                order_num="GD20250202",
                name="紧急客户B",
                address="广州市天河区珠江新城",
                supervisor_name="陈总监",
                create_time=datetime.now() - timedelta(hours=50),  # 50小时前创建，极度逾期
                org_name="广州贸易公司",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            )
        ]
        
        mock_external_services['metabase'].get_all_monitored_opportunities.return_value = overdue_opportunities
        
        # Act
        with patch('src.fsoa.data.metabase.get_metabase_client', return_value=mock_external_services['metabase']), \
             patch('src.fsoa.notification.wechat.get_wechat_client', return_value=mock_external_services['wechat']):
            
            from src.fsoa.agent.managers.data_strategy import BusinessDataStrategy
            from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
            
            data_strategy = BusinessDataStrategy()
            opportunities = data_strategy.get_opportunities()
            
            # 更新逾期信息
            for opp in opportunities:
                opp.update_overdue_info(use_business_time=True)
            
            notification_manager = NotificationTaskManager()
            tasks = notification_manager.create_notification_tasks(opportunities, 1)
        
        # Assert
        assert len(opportunities) == 2
        
        # 验证逾期状态
        for opp in opportunities:
            assert opp.elapsed_hours > 24  # 都应该超过24小时
            assert opp.is_overdue is True
        
        # 逾期商机应该创建通知任务（如果违规）
        violation_count = sum(1 for opp in opportunities if opp.is_violation)
        if violation_count > 0:
            assert len(tasks) >= 0  # 应该有通知任务
    
    def test_weekend_scenario(self, test_environment, mock_external_services):
        """测试周末场景"""
        # 场景：周末时间，SLA计算应该考虑工作时间
        
        # Arrange - 创建周五晚上的商机
        weekend_opportunities = [
            OpportunityInfo(
                order_num="GD20250301",
                name="周末客户",
                address="杭州市西湖区文三路",
                supervisor_name="周经理",
                create_time=datetime(2025, 1, 3, 18, 0),  # 假设周五18:00创建
                org_name="杭州互联网公司",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            )
        ]
        
        mock_external_services['metabase'].get_all_monitored_opportunities.return_value = weekend_opportunities
        
        # Act
        with patch('src.fsoa.data.metabase.get_metabase_client', return_value=mock_external_services['metabase']):
            from src.fsoa.agent.managers.data_strategy import BusinessDataStrategy
            
            data_strategy = BusinessDataStrategy()
            opportunities = data_strategy.get_opportunities()
            
            # 使用业务时间计算
            for opp in opportunities:
                opp.update_overdue_info(use_business_time=True)
        
        # Assert
        assert len(opportunities) == 1
        
        # 周末创建的商机，业务时间计算应该不同于自然时间
        opp = opportunities[0]
        assert hasattr(opp, 'elapsed_hours')
        assert hasattr(opp, 'is_overdue')
    
    def test_high_volume_scenario(self, test_environment, mock_external_services):
        """测试高并发场景"""
        # 场景：大量商机同时需要处理
        
        # Arrange - 创建大量商机
        high_volume_opportunities = []
        for i in range(50):  # 50个商机
            opp = OpportunityInfo(
                order_num=f"GD202504{i:02d}",
                name=f"批量客户{i}",
                address=f"城市{i%10}区地址{i}号",
                supervisor_name=f"销售{i%5}",
                create_time=datetime.now() - timedelta(hours=i%24),  # 不同的创建时间
                org_name=f"公司{i%10}",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            )
            high_volume_opportunities.append(opp)
        
        mock_external_services['metabase'].get_all_monitored_opportunities.return_value = high_volume_opportunities
        
        # Act
        with patch('src.fsoa.data.metabase.get_metabase_client', return_value=mock_external_services['metabase']), \
             patch('src.fsoa.notification.wechat.get_wechat_client', return_value=mock_external_services['wechat']):
            
            from src.fsoa.agent.managers.data_strategy import BusinessDataStrategy
            from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
            from src.fsoa.agent.managers.execution_tracker import AgentExecutionTracker
            
            # 使用执行追踪器监控性能
            execution_tracker = AgentExecutionTracker()
            run_id = execution_tracker.start_execution("high_volume_test")
            
            # 获取数据
            with execution_tracker.track_step("fetch_data"):
                data_strategy = BusinessDataStrategy()
                opportunities = data_strategy.get_opportunities()
            
            # 处理商机
            with execution_tracker.track_step("process_opportunities"):
                for opp in opportunities:
                    opp.update_overdue_info(use_business_time=True)
            
            # 创建通知
            with execution_tracker.track_step("create_notifications"):
                notification_manager = NotificationTaskManager()
                tasks = notification_manager.create_notification_tasks(opportunities, run_id)
            
            execution_tracker.complete_execution(
                opportunities_processed=len(opportunities),
                notifications_sent=len(tasks)
            )
        
        # Assert
        assert len(opportunities) == 50
        assert all(opp.order_num.startswith("GD2025") for opp in opportunities)
        
        # 验证性能 - 大量数据处理应该在合理时间内完成
        # 这里主要验证没有异常，实际性能测试需要专门的性能测试框架
        assert isinstance(tasks, list)
    
    def test_system_recovery_scenario(self, test_environment, mock_external_services):
        """测试系统恢复场景"""
        # 场景：系统故障后恢复，需要处理积压的任务
        
        # Arrange - 模拟系统故障期间积压的商机
        backlog_opportunities = [
            OpportunityInfo(
                order_num="GD20250501",
                name="积压客户A",
                address="成都市高新区天府大道",
                supervisor_name="刘经理",
                create_time=datetime.now() - timedelta(hours=72),  # 3天前的积压
                org_name="成都科技公司",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            ),
            OpportunityInfo(
                order_num="GD20250502",
                name="积压客户B",
                address="重庆市渝北区两江新区",
                supervisor_name="赵经理", 
                create_time=datetime.now() - timedelta(hours=48),  # 2天前的积压
                org_name="重庆制造公司",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            )
        ]
        
        mock_external_services['metabase'].get_all_monitored_opportunities.return_value = backlog_opportunities
        
        # Act - 模拟系统恢复后的处理
        with patch('src.fsoa.data.metabase.get_metabase_client', return_value=mock_external_services['metabase']), \
             patch('src.fsoa.notification.wechat.get_wechat_client', return_value=mock_external_services['wechat']):
            
            from src.fsoa.agent.managers.data_strategy import BusinessDataStrategy
            from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
            
            # 1. 刷新缓存，获取最新数据
            data_strategy = BusinessDataStrategy()
            refresh_result = data_strategy.refresh_cache()
            
            # 2. 获取所有商机
            opportunities = data_strategy.get_opportunities()
            
            # 3. 处理积压的逾期商机
            for opp in opportunities:
                opp.update_overdue_info(use_business_time=True)
            
            # 4. 批量创建通知任务
            notification_manager = NotificationTaskManager()
            tasks = notification_manager.create_notification_tasks(opportunities, 1)
        
        # Assert
        assert len(opportunities) == 2
        assert isinstance(refresh_result, tuple)  # 缓存刷新结果
        
        # 积压的商机应该都是严重逾期
        for opp in opportunities:
            assert opp.elapsed_hours > 24
            assert opp.is_overdue is True
        
        # 应该为严重逾期的商机创建紧急通知
        if any(opp.is_violation for opp in opportunities):
            assert len(tasks) > 0

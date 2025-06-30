"""
LLM业务集成测试

测试LLM在完整业务流程中的工作情况，验证端到端的功能
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.fsoa.agent.orchestrator import AgentOrchestrator
from src.fsoa.agent.decision import DecisionEngine, DecisionMode
from src.fsoa.data.models import (
    OpportunityInfo, OpportunityStatus, DecisionContext,
    NotificationTask, NotificationTaskType, NotificationTaskStatus,
    GroupConfig, Priority
)
from src.fsoa.utils.timezone_utils import now_china_naive


class TestLLMBusinessIntegration:
    """LLM业务集成测试"""

    @pytest.fixture
    def mock_database_manager(self):
        """Mock数据库管理器"""
        mock_db = Mock()
        mock_db.get_system_config.side_effect = lambda key: {
            "use_llm_optimization": "true",
            "llm_temperature": "0.1",
            "notification_send_interval": "3"
        }.get(key)
        return mock_db

    @pytest.fixture
    def mock_metabase_client(self):
        """Mock Metabase客户端"""
        mock_client = Mock()
        
        # 模拟返回需要处理的商机数据
        sample_opportunities = [
            {
                "orderNum": "BIZ001",
                "name": "重要客户A",
                "address": "北京市朝阳区",
                "supervisorName": "张经理",
                "createTime": (now_china_naive() - timedelta(hours=10)).isoformat(),
                "orgName": "北京分公司",
                "orderstatus": "待预约"
            },
            {
                "orderNum": "BIZ002", 
                "name": "普通客户B",
                "address": "上海市浦东区",
                "supervisorName": "李经理",
                "createTime": (now_china_naive() - timedelta(hours=6)).isoformat(),
                "orgName": "上海分公司",
                "orderstatus": "暂不上门"
            }
        ]
        
        mock_client.execute_query.return_value = sample_opportunities
        return mock_client

    @pytest.fixture
    def mock_deepseek_client(self):
        """Mock DeepSeek客户端"""
        mock_client = Mock()
        
        def mock_analyze_priority(opportunity, context=None):
            """根据商机信息返回不同的LLM决策"""
            if "重要客户" in opportunity.name:
                return Mock(
                    action="escalate",
                    priority=Priority.URGENT,
                    message="重要客户需要立即处理",
                    reasoning="基于客户重要性和超时情况，建议立即升级处理",
                    confidence=0.9,
                    llm_used=True
                )
            else:
                return Mock(
                    action="notify",
                    priority=Priority.NORMAL,
                    message="标准通知处理",
                    reasoning="普通客户按标准流程处理",
                    confidence=0.7,
                    llm_used=True
                )
        
        mock_client.analyze_task_priority.side_effect = mock_analyze_priority
        mock_client.test_connection.return_value = True
        return mock_client

    @pytest.fixture
    def mock_wechat_client(self):
        """Mock微信客户端"""
        mock_client = Mock()
        mock_client.send_notification_to_org.return_value = True
        return mock_client

    @patch('src.fsoa.data.database.get_database_manager')
    @patch('src.fsoa.data.metabase.get_metabase_client')
    @patch('src.fsoa.agent.llm.get_deepseek_client')
    @patch('src.fsoa.notification.wechat.get_wechat_client')
    def test_complete_llm_workflow(self, mock_wechat, mock_deepseek, mock_metabase, mock_db,
                                  mock_database_manager, mock_metabase_client, 
                                  mock_deepseek_client, mock_wechat_client):
        """测试完整的LLM工作流程"""
        # Arrange
        mock_db.return_value = mock_database_manager
        mock_metabase.return_value = mock_metabase_client
        mock_deepseek.return_value = mock_deepseek_client
        mock_wechat.return_value = mock_wechat_client

        # 模拟数据库操作
        mock_database_manager.create_agent_run.return_value = 1
        mock_database_manager.get_pending_notification_tasks.return_value = []
        mock_database_manager.create_notification_task.return_value = None
        mock_database_manager.update_agent_run.return_value = None

        orchestrator = AgentOrchestrator()

        # Act
        result = orchestrator.run_agent()

        # Assert
        assert result is not None
        
        # 验证LLM客户端被调用
        assert mock_deepseek_client.analyze_task_priority.called
        
        # 验证不同客户得到不同的处理策略
        call_args_list = mock_deepseek_client.analyze_task_priority.call_args_list
        assert len(call_args_list) >= 1  # 至少有一次LLM调用
        
        # 验证通知发送
        assert mock_wechat_client.send_notification_to_org.called

    @patch('src.fsoa.data.database.get_database_manager')
    @patch('src.fsoa.agent.llm.get_deepseek_client')
    def test_llm_context_building_with_history(self, mock_deepseek, mock_db, 
                                              mock_database_manager, mock_deepseek_client):
        """测试LLM上下文构建包含历史信息"""
        # Arrange
        mock_db.return_value = mock_database_manager
        mock_deepseek.return_value = mock_deepseek_client

        # 模拟历史通知任务
        historical_tasks = [
            NotificationTask(
                order_num="BIZ001",
                org_name="北京分公司",
                notification_type=NotificationTaskType.REMINDER,
                due_time=now_china_naive() - timedelta(hours=2),
                status=NotificationTaskStatus.SENT,
                sent_at=now_china_naive() - timedelta(hours=2, minutes=5)
            )
        ]

        # 创建决策上下文
        context = DecisionContext(
            history=historical_tasks,
            system_config={"use_llm_optimization": "true"}
        )

        # 创建测试商机
        opportunity = OpportunityInfo(
            order_num="BIZ001",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试负责人",
            create_time=now_china_naive() - timedelta(hours=10),
            org_name="北京分公司",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )

        engine = DecisionEngine()

        # Act
        context_dict = engine._build_context_dict(opportunity, context)

        # Assert
        assert "notification_history" in context_dict
        assert len(context_dict["notification_history"]) == 1
        
        history_item = context_dict["notification_history"][0]
        assert history_item["type"] == "reminder"
        assert history_item["order_num"] == "BIZ001"
        assert history_item["org_name"] == "北京分公司"
        assert history_item["status"] == "sent"

    @patch('src.fsoa.agent.llm.OpenAI')
    def test_llm_api_error_graceful_degradation(self, mock_openai):
        """测试LLM API错误时的优雅降级"""
        # Arrange
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API服务不可用")
        mock_openai.return_value = mock_client

        with patch('src.fsoa.utils.config.get_config') as mock_config:
            mock_config.return_value.deepseek_api_key = "test_key"
            mock_config.return_value.deepseek_base_url = "https://test.api.url"

        engine = DecisionEngine(mode=DecisionMode.LLM_FALLBACK)
        
        opportunity = OpportunityInfo(
            order_num="TEST001",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试负责人",
            create_time=now_china_naive() - timedelta(hours=30),  # 超时
            org_name="测试组织",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )

        # Act
        result = engine.make_decision(opportunity)

        # Assert
        # 应该降级到规则引擎决策
        assert result is not None
        assert result.llm_used is False
        assert result.action in ["skip", "notify", "escalate"]

    def test_llm_prompt_construction_includes_business_context(self):
        """测试LLM提示词构建包含业务上下文"""
        # Arrange
        with patch('src.fsoa.utils.config.get_config') as mock_config:
            mock_config.return_value.deepseek_api_key = "test_key"
            mock_config.return_value.deepseek_base_url = "https://test.api.url"
            
            from src.fsoa.agent.llm import DeepSeekClient
            client = DeepSeekClient()

        opportunity = OpportunityInfo(
            order_num="BIZ001",
            name="重要客户A",
            address="北京市朝阳区重要商务区",
            supervisor_name="张总监",
            create_time=now_china_naive() - timedelta(hours=10),
            org_name="北京分公司",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )

        context = {
            "notification_history": [
                {
                    "type": "reminder",
                    "sent_at": (now_china_naive() - timedelta(hours=2)).isoformat(),
                    "status": "sent"
                }
            ],
            "group_config": {
                "name": "北京分公司群",
                "cooldown_minutes": 30
            }
        }

        # Act
        prompt = client._build_priority_analysis_prompt(opportunity, context)

        # Assert
        # 验证提示词包含关键业务信息
        assert "BIZ001" in prompt
        assert "重要客户A" in prompt
        assert "北京市朝阳区" in prompt
        assert "张总监" in prompt
        assert "北京分公司" in prompt
        assert "待预约" in prompt
        
        # 验证包含上下文信息
        assert "notification_history" in prompt or "通知历史" in prompt
        assert "group_config" in prompt or "群组配置" in prompt

    @patch('src.fsoa.data.database.get_database_manager')
    def test_llm_configuration_from_database(self, mock_db, mock_database_manager):
        """测试从数据库读取LLM配置"""
        # Arrange
        mock_db.return_value = mock_database_manager
        mock_database_manager.get_system_config.side_effect = lambda key: {
            "use_llm_optimization": "true",
            "llm_temperature": "0.2"
        }.get(key)

        engine = DecisionEngine()

        # Act
        use_llm = engine._check_llm_optimization_enabled()

        # Assert
        assert use_llm is True
        mock_database_manager.get_system_config.assert_called_with("use_llm_optimization")

    def test_decision_result_merging_logic(self):
        """测试决策结果合并逻辑"""
        # Arrange
        from src.fsoa.data.models import DecisionResult
        
        rule_result = DecisionResult(
            action="notify",
            priority=Priority.NORMAL,
            message="规则建议通知",
            reasoning="基于超时规则",
            confidence=1.0,
            llm_used=False
        )

        llm_result = DecisionResult(
            action="escalate",
            priority=Priority.HIGH,
            message="LLM建议升级",
            reasoning="基于客户重要性分析",
            confidence=0.8,
            llm_used=True
        )

        engine = DecisionEngine()

        # Act
        merged_result = engine._merge_decisions(rule_result, llm_result)

        # Assert
        assert merged_result.action == "escalate"  # 使用LLM的决策
        assert merged_result.priority == Priority.HIGH
        assert merged_result.llm_used is True
        assert "规则建议" in merged_result.reasoning
        assert "LLM分析" in merged_result.reasoning
        assert merged_result.confidence == min(rule_result.confidence, llm_result.confidence)

    def test_llm_safety_check_prevents_aggressive_decisions(self):
        """测试LLM安全检查防止过于激进的决策"""
        # Arrange
        from src.fsoa.data.models import DecisionResult
        
        rule_result = DecisionResult(
            action="skip",  # 规则建议跳过
            priority=Priority.LOW,
            reasoning="未达到处理阈值",
            confidence=1.0
        )

        llm_result = DecisionResult(
            action="escalate",  # LLM建议升级（过于激进）
            priority=Priority.URGENT,
            reasoning="LLM过度分析",
            confidence=0.9,
            llm_used=True
        )

        engine = DecisionEngine()

        # Act
        merged_result = engine._merge_decisions(rule_result, llm_result)

        # Assert
        # 应该降级到规则结果，因为LLM建议过于激进
        assert merged_result.action == "skip"
        assert merged_result.llm_used is False

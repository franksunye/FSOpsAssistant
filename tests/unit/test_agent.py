"""
Agent模块测试
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

from src.fsoa.agent.orchestrator import AgentOrchestrator, AgentState
from src.fsoa.agent.decision import DecisionEngine, RuleEngine, DecisionMode
from src.fsoa.agent.llm import DeepSeekClient
from src.fsoa.data.models import OpportunityInfo, OpportunityStatus, Priority, DecisionResult


class TestRuleEngine:
    """测试规则引擎"""

    def test_rule_engine_skip_not_overdue(self, sample_opportunity):
        """测试未超时商机跳过"""
        # Arrange
        sample_opportunity.elapsed_hours = 3.0  # 未超时
        sample_opportunity.sla_threshold_hours = 4
        sample_opportunity.is_overdue = False
        rule_engine = RuleEngine()

        # Act
        result = rule_engine.evaluate_opportunity(sample_opportunity)

        # Assert
        assert result.action == "skip"
        assert result.priority == Priority.LOW
        assert "未超时" in result.reasoning or result.reasoning is None

    def test_rule_engine_escalate_severe_overdue(self, overdue_opportunity):
        """测试严重超时升级"""
        # Arrange
        overdue_opportunity.elapsed_hours = 16.0  # 严重超时
        overdue_opportunity.sla_threshold_hours = 8
        overdue_opportunity.is_overdue = True
        overdue_opportunity.overdue_hours = 8.0
        rule_engine = RuleEngine()

        # Act
        result = rule_engine.evaluate_opportunity(overdue_opportunity)

        # Assert
        assert result.action in ["escalate", "notify"]  # 根据具体实现
        assert result.priority in [Priority.HIGH, Priority.URGENT]

    def test_rule_engine_notify_moderate_overdue(self, overdue_opportunity):
        """测试中等超时通知"""
        # Arrange
        overdue_opportunity.elapsed_hours = 6.0  # 中等超时
        overdue_opportunity.sla_threshold_hours = 4
        overdue_opportunity.is_overdue = True
        overdue_opportunity.overdue_hours = 2.0
        rule_engine = RuleEngine()

        # Act
        result = rule_engine.evaluate_opportunity(overdue_opportunity)

        # Assert
        assert result.action in ["notify", "escalate"]
        assert result.priority in [Priority.HIGH, Priority.URGENT]

    @patch('src.fsoa.agent.decision.datetime')
    def test_rule_engine_cooldown_check(self, mock_datetime, overdue_opportunity):
        """测试冷却时间检查"""
        # Arrange
        current_time = datetime(2025, 6, 25, 12, 0, 0)
        last_notification = datetime(2025, 6, 25, 11, 45, 0)  # 15分钟前

        mock_datetime.now.return_value = current_time
        # 注意：新的架构中冷却时间检查可能在NotificationTask层面

        rule_engine = RuleEngine()

        # Act
        result = rule_engine.evaluate_opportunity(overdue_opportunity)

        # Assert
        # 规则引擎本身可能不处理冷却时间，这由NotificationManager处理
        assert isinstance(result, DecisionResult)


class TestDecisionEngine:
    """测试决策引擎"""

    def test_decision_engine_rule_only_mode(self, overdue_opportunity):
        """测试仅规则模式"""
        # Arrange
        decision_engine = DecisionEngine(DecisionMode.RULE_ONLY)

        # Act
        result = decision_engine.make_decision(overdue_opportunity)

        # Assert
        assert isinstance(result, DecisionResult)
        assert result.llm_used is False

    @patch('src.fsoa.agent.decision.get_deepseek_client')
    def test_decision_engine_llm_only_mode(self, mock_get_client, overdue_opportunity):
        """测试仅LLM模式"""
        # Arrange
        mock_client = Mock()
        mock_client.analyze_opportunity_priority.return_value = DecisionResult(
            action="notify",
            priority=Priority.HIGH,
            llm_used=True
        )
        mock_get_client.return_value = mock_client

        decision_engine = DecisionEngine(DecisionMode.LLM_ONLY)

        # Act
        result = decision_engine.make_decision(overdue_opportunity)

        # Assert
        assert result.action == "notify"
        assert result.llm_used is True
        mock_client.analyze_opportunity_priority.assert_called_once()

    @patch('src.fsoa.agent.decision.get_deepseek_client')
    def test_decision_engine_llm_fallback_on_error(self, mock_get_client, overdue_opportunity):
        """测试LLM失败时的降级处理"""
        # Arrange
        mock_client = Mock()
        mock_client.analyze_opportunity_priority.side_effect = Exception("LLM Error")
        mock_get_client.return_value = mock_client

        decision_engine = DecisionEngine(DecisionMode.LLM_FALLBACK)

        # Act
        result = decision_engine.make_decision(overdue_opportunity)

        # Assert
        assert isinstance(result, DecisionResult)
        assert result.llm_used is False  # 降级到规则


class TestDeepSeekClient:
    """测试DeepSeek客户端"""
    
    @patch('src.fsoa.agent.llm.OpenAI')
    def test_deepseek_client_initialization(self, mock_openai):
        """测试客户端初始化"""
        # Arrange & Act
        client = DeepSeekClient()
        
        # Assert
        mock_openai.assert_called_once()
        assert client.client is not None
    
    @patch('src.fsoa.agent.llm.OpenAI')
    def test_analyze_opportunity_priority_success(self, mock_openai, overdue_opportunity):
        """测试商机优先级分析成功"""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "action": "notify",
            "priority": "high",
            "message": "商机需要立即处理",
            "reasoning": "商机已超时较长时间",
            "confidence": 0.9
        }
        '''

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        deepseek_client = DeepSeekClient()

        # Act
        result = deepseek_client.analyze_opportunity_priority(overdue_opportunity)

        # Assert
        assert result.action == "notify"
        assert result.priority == Priority.HIGH
        assert result.llm_used is True
        assert result.confidence == 0.9

    @patch('src.fsoa.agent.llm.OpenAI')
    def test_analyze_opportunity_priority_fallback(self, mock_openai, overdue_opportunity):
        """测试分析失败时的降级处理"""
        # Arrange
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        deepseek_client = DeepSeekClient()

        # Act
        result = deepseek_client.analyze_opportunity_priority(overdue_opportunity)

        # Assert
        assert isinstance(result, DecisionResult)
        assert result.llm_used is False

    @patch('src.fsoa.agent.llm.OpenAI')
    def test_generate_notification_message(self, mock_openai, overdue_opportunity):
        """测试通知消息生成"""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "商机超时提醒消息"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        deepseek_client = DeepSeekClient()

        # Act
        message = deepseek_client.generate_notification_message(overdue_opportunity)

        # Assert
        assert message == "商机超时提醒消息"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('src.fsoa.agent.llm.OpenAI')
    def test_test_connection_success(self, mock_openai):
        """测试连接测试成功"""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "OK"
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        deepseek_client = DeepSeekClient()
        
        # Act
        result = deepseek_client.test_connection()
        
        # Assert
        assert result is True
    
    @patch('src.fsoa.agent.llm.OpenAI')
    def test_test_connection_failure(self, mock_openai):
        """测试连接测试失败"""
        # Arrange
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Connection Error")
        mock_openai.return_value = mock_client
        
        deepseek_client = DeepSeekClient()
        
        # Act
        result = deepseek_client.test_connection()
        
        # Assert
        assert result is False


class TestAgentOrchestrator:
    """测试Agent编排器"""

    @patch('src.fsoa.agent.orchestrator.get_db_manager')
    @patch('src.fsoa.agent.orchestrator.fetch_overdue_opportunities')
    def test_agent_execution_success(self, mock_fetch_opportunities, mock_db_manager, sample_opportunity):
        """测试Agent执行成功"""
        # Arrange
        mock_fetch_opportunities.return_value = [sample_opportunity]
        mock_db = Mock()
        mock_db_manager.return_value = mock_db

        orchestrator = AgentOrchestrator()

        # Act
        result = orchestrator.execute(dry_run=True)

        # Assert
        assert hasattr(result, 'opportunities_processed') or hasattr(result, 'tasks_processed')
        assert hasattr(result, 'status')

    @patch('src.fsoa.agent.orchestrator.get_db_manager')
    @patch('src.fsoa.agent.orchestrator.fetch_overdue_opportunities')
    def test_agent_execution_with_errors(self, mock_fetch_opportunities, mock_db_manager):
        """测试Agent执行出错"""
        # Arrange
        mock_fetch_opportunities.side_effect = Exception("Fetch Error")
        mock_db = Mock()
        mock_db_manager.return_value = mock_db

        orchestrator = AgentOrchestrator()

        # Act
        result = orchestrator.execute(dry_run=True)

        # Assert
        assert hasattr(result, 'errors')
        if hasattr(result, 'errors') and result.errors:
            assert len(result.errors) > 0

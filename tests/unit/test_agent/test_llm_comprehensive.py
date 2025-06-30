"""
LLM模块综合测试

测试LLM与业务流程的真实串联，验证context机制和决策流程
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.fsoa.agent.llm import DeepSeekClient, DeepSeekError
from src.fsoa.agent.decision import DecisionEngine, DecisionMode
from src.fsoa.data.models import (
    OpportunityInfo, OpportunityStatus, DecisionContext, DecisionResult,
    NotificationTask, NotificationTaskType, NotificationTaskStatus,
    GroupConfig, Priority
)
from src.fsoa.utils.timezone_utils import now_china_naive


class TestLLMComprehensive:
    """LLM综合功能测试"""

    @pytest.fixture
    def sample_opportunity(self):
        """创建测试商机"""
        return OpportunityInfo(
            order_num="TEST001",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试负责人",
            create_time=now_china_naive() - timedelta(hours=10),
            org_name="测试组织",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )

    @pytest.fixture
    def sample_notification_tasks(self):
        """创建测试通知任务历史"""
        base_time = now_china_naive() - timedelta(hours=2)
        return [
            NotificationTask(
                order_num="TEST001",
                org_name="测试组织",
                notification_type=NotificationTaskType.REMINDER,
                due_time=base_time,
                status=NotificationTaskStatus.SENT,
                sent_at=base_time + timedelta(minutes=5)
            ),
            NotificationTask(
                order_num="TEST001",
                org_name="测试组织",
                notification_type=NotificationTaskType.ESCALATION,
                due_time=base_time + timedelta(hours=1),
                status=NotificationTaskStatus.PENDING
            )
        ]

    @pytest.fixture
    def sample_group_config(self):
        """创建测试群组配置"""
        return GroupConfig(
            group_id="test_group",
            name="测试群组",
            webhook_url="https://test.webhook.url",
            enabled=True,
            notification_cooldown_minutes=30,
            created_at=now_china_naive(),
            updated_at=now_china_naive()
        )

    @pytest.fixture
    def sample_decision_context(self, sample_notification_tasks, sample_group_config):
        """创建测试决策上下文"""
        return DecisionContext(
            history=sample_notification_tasks,
            group_config=sample_group_config,
            system_config={
                "use_llm_optimization": "true",
                "llm_temperature": "0.1"
            }
        )

    def test_build_context_dict_with_full_context(self, sample_opportunity, sample_decision_context):
        """测试完整上下文字典构建"""
        # Arrange
        engine = DecisionEngine()
        
        # Act
        context_dict = engine._build_context_dict(sample_opportunity, sample_decision_context)
        
        # Assert
        assert "notification_history" in context_dict
        assert len(context_dict["notification_history"]) == 2
        
        # 验证通知历史格式
        first_notif = context_dict["notification_history"][0]
        assert "type" in first_notif
        assert "sent_at" in first_notif
        assert "status" in first_notif
        assert "order_num" in first_notif
        assert "org_name" in first_notif
        assert "due_time" in first_notif
        
        # 验证群组配置
        assert "group_config" in context_dict
        group_config = context_dict["group_config"]
        assert group_config["name"] == "测试群组"
        assert group_config["webhook_url"] == "https://test.webhook.url"
        assert group_config["enabled"] is True
        assert group_config["cooldown_minutes"] == 30
        
        # 验证系统配置
        assert "system_config" in context_dict
        assert context_dict["system_config"]["use_llm_optimization"] == "true"

    def test_build_context_dict_empty_context(self, sample_opportunity):
        """测试空上下文的处理"""
        # Arrange
        engine = DecisionEngine()
        
        # Act
        context_dict = engine._build_context_dict(sample_opportunity, None)
        
        # Assert
        assert "current_time" in context_dict
        assert "notification_history" not in context_dict
        assert "group_config" not in context_dict

    @patch('src.fsoa.agent.llm.OpenAI')
    def test_deepseek_client_analyze_with_context(self, mock_openai, sample_opportunity, sample_decision_context):
        """测试DeepSeek客户端带上下文的分析"""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "action": "notify",
            "priority": "high",
            "message": "基于历史通知记录，建议立即处理",
            "reasoning": "客户已有多次通知记录，需要升级处理",
            "confidence": 0.85
        })

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        with patch('src.fsoa.utils.config.get_config') as mock_config:
            mock_config.return_value.deepseek_api_key = "test_key"
            mock_config.return_value.deepseek_base_url = "https://test.api.url"
            
            client = DeepSeekClient()

        # 构建上下文
        engine = DecisionEngine()
        context_dict = engine._build_context_dict(sample_opportunity, sample_decision_context)

        # Act
        result = client.analyze_task_priority(sample_opportunity, context_dict)

        # Assert
        assert result.action == "notify"
        assert result.priority == Priority.HIGH
        assert result.llm_used is True
        assert result.confidence == 0.85
        assert "历史通知记录" in result.reasoning

        # 验证API调用参数
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        
        # 验证提示词包含上下文信息
        prompt = call_args[1]['messages'][0]['content']
        assert "notification_history" in prompt or "通知历史" in prompt

    @patch('src.fsoa.agent.llm.OpenAI')
    def test_deepseek_client_api_failure_handling(self, mock_openai, sample_opportunity):
        """测试DeepSeek API失败处理"""
        # Arrange
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API连接失败")
        mock_openai.return_value = mock_client

        with patch('src.fsoa.utils.config.get_config') as mock_config:
            mock_config.return_value.deepseek_api_key = "test_key"
            mock_config.return_value.deepseek_base_url = "https://test.api.url"
            
            client = DeepSeekClient()

        # Act
        result = client.analyze_task_priority(sample_opportunity)

        # Assert - 应该返回降级结果
        assert result.action == "skip"  # 降级到规则决策
        assert result.llm_used is False

    @patch('src.fsoa.data.database.get_database_manager')
    @patch('src.fsoa.agent.llm.get_deepseek_client')
    def test_decision_engine_hybrid_mode_with_llm_enabled(self, mock_get_client, mock_get_db, 
                                                         sample_opportunity, sample_decision_context):
        """测试混合模式下LLM启用的决策流程"""
        # Arrange
        # Mock数据库配置
        mock_db = Mock()
        mock_db.get_system_config.return_value = "true"  # 启用LLM
        mock_get_db.return_value = mock_db

        # Mock LLM客户端
        mock_llm_result = DecisionResult(
            action="escalate",
            priority=Priority.URGENT,
            message="LLM建议升级处理",
            reasoning="基于上下文分析，需要立即升级",
            confidence=0.9,
            llm_used=True
        )
        mock_client = Mock()
        mock_client.analyze_task_priority.return_value = mock_llm_result
        mock_get_client.return_value = mock_client

        # 创建超时商机
        overdue_opportunity = sample_opportunity.copy()
        overdue_opportunity.create_time = now_china_naive() - timedelta(hours=30)  # 超时

        engine = DecisionEngine(mode=DecisionMode.HYBRID)

        # Act
        result = engine.make_decision(overdue_opportunity, sample_decision_context)

        # Assert
        assert result.llm_used is True
        assert result.action == "escalate"
        assert result.priority == Priority.URGENT
        
        # 验证LLM被调用时传入了正确的上下文
        mock_client.analyze_task_priority.assert_called_once()
        call_args = mock_client.analyze_task_priority.call_args
        context_arg = call_args[0][1]  # 第二个参数是context
        
        assert "notification_history" in context_arg
        assert "group_config" in context_arg
        assert "rule_suggestion" in context_arg

    def test_llm_result_parsing_invalid_json(self):
        """测试LLM结果解析 - 无效JSON"""
        # Arrange
        with patch('src.fsoa.utils.config.get_config') as mock_config:
            mock_config.return_value.deepseek_api_key = "test_key"
            mock_config.return_value.deepseek_base_url = "https://test.api.url"
            
            client = DeepSeekClient()

        invalid_json = "这不是有效的JSON格式"

        # Act
        result = client._parse_decision_result(invalid_json)

        # Assert - 应该返回安全的默认值
        assert result["action"] == "notify"
        assert result["priority"] == "normal"
        assert "解析失败" in result["reasoning"]
        assert result["confidence"] == 0.5

    def test_llm_result_parsing_missing_fields(self):
        """测试LLM结果解析 - 缺少必需字段"""
        # Arrange
        with patch('src.fsoa.utils.config.get_config') as mock_config:
            mock_config.return_value.deepseek_api_key = "test_key"
            mock_config.return_value.deepseek_base_url = "https://test.api.url"
            
            client = DeepSeekClient()

        incomplete_json = json.dumps({
            "action": "notify",
            # 缺少priority和reasoning
        })

        # Act
        result = client._parse_decision_result(incomplete_json)

        # Assert - 应该使用默认值填充
        assert result["action"] == "notify"
        assert result["priority"] == "normal"  # 默认值
        assert "reasoning" in result  # 应该有默认reasoning

    @patch('src.fsoa.agent.llm.OpenAI')
    def test_deepseek_connection_test(self, mock_openai):
        """测试DeepSeek连接测试功能"""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "OK"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        with patch('src.fsoa.utils.config.get_config') as mock_config:
            mock_config.return_value.deepseek_api_key = "test_key"
            mock_config.return_value.deepseek_base_url = "https://test.api.url"
            
            client = DeepSeekClient()

        # Act
        result = client.test_connection()

        # Assert
        assert result is True
        mock_client.chat.completions.create.assert_called_once()

    def test_context_dict_includes_current_time(self, sample_opportunity):
        """测试上下文字典包含当前时间信息"""
        # Arrange
        engine = DecisionEngine()
        
        # Act
        context_dict = engine._build_context_dict(sample_opportunity)
        
        # Assert
        assert "current_time" in context_dict
        time_info = context_dict["current_time"]
        assert "timestamp" in time_info
        assert "hour" in time_info
        assert "weekday" in time_info
        assert "is_business_hours" in time_info

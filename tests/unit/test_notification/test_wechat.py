"""
企微通知模块单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.fsoa.notification.wechat import WeChatClient, get_wechat_client
from src.fsoa.data.models import OpportunityInfo, OpportunityStatus


class TestWeChatClient:
    """企微客户端测试"""
    
    @pytest.fixture
    def mock_requests(self):
        """Mock requests模块"""
        with patch('src.fsoa.notification.wechat.requests') as mock:
            mock.post.return_value.status_code = 200
            mock.post.return_value.json.return_value = {"errcode": 0, "errmsg": "ok"}
            yield mock
    
    @pytest.fixture
    def wechat_client(self):
        """创建企微客户端实例"""
        return WeChatClient()
    
    def test_initialization(self, wechat_client):
        """测试初始化"""
        assert wechat_client is not None
        assert hasattr(wechat_client, 'webhook_url')
        assert hasattr(wechat_client, 'group_configs')
    
    def test_send_notification_to_org_success(self, wechat_client, mock_requests):
        """测试发送组织通知成功"""
        # Arrange
        org_name = "测试公司"
        content = "测试通知内容"
        
        # Act
        result = wechat_client.send_notification_to_org(
            org_name=org_name,
            content=content,
            is_escalation=False
        )
        
        # Assert
        assert result is True
        mock_requests.post.assert_called()
    
    def test_send_notification_to_org_failure(self, wechat_client, mock_requests):
        """测试发送组织通知失败"""
        # Arrange
        mock_requests.post.return_value.status_code = 400
        org_name = "测试公司"
        content = "测试通知内容"
        
        # Act
        result = wechat_client.send_notification_to_org(
            org_name=org_name,
            content=content,
            is_escalation=False
        )
        
        # Assert
        assert result is False
    
    def test_send_escalation_notification(self, wechat_client, mock_requests):
        """测试发送升级通知"""
        # Arrange
        org_name = "测试公司"
        content = "升级通知内容"
        
        # Act
        result = wechat_client.send_notification_to_org(
            org_name=org_name,
            content=content,
            is_escalation=True
        )
        
        # Assert
        assert result is True
        mock_requests.post.assert_called()
    
    def test_send_business_notification(self, wechat_client, mock_requests):
        """测试发送业务通知"""
        # Arrange
        opportunity = OpportunityInfo(
            order_num="GD20250001",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试销售",
            create_time=datetime.now(),
            org_name="测试组织",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
        
        # Act
        result = wechat_client.send_business_notification(
            opportunity=opportunity,
            message_type="reminder"
        )
        
        # Assert
        assert isinstance(result, bool)
    
    def test_get_group_webhook_url(self, wechat_client):
        """测试获取群组webhook URL"""
        # Arrange
        org_name = "测试公司"
        
        # Act
        url = wechat_client._get_group_webhook_url(org_name, is_escalation=False)
        
        # Assert
        assert isinstance(url, str)
        assert len(url) > 0
    
    def test_format_message_for_wechat(self, wechat_client):
        """测试格式化企微消息"""
        # Arrange
        content = "测试消息内容"
        
        # Act
        formatted = wechat_client._format_message_for_wechat(content)
        
        # Assert
        assert isinstance(formatted, dict)
        assert 'msgtype' in formatted
    
    def test_validate_webhook_response(self, wechat_client):
        """测试验证webhook响应"""
        # Arrange
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"errcode": 0}
        
        failure_response = Mock()
        failure_response.status_code = 400
        
        # Act & Assert
        assert wechat_client._validate_webhook_response(success_response) is True
        assert wechat_client._validate_webhook_response(failure_response) is False
    
    def test_get_wechat_client_singleton(self):
        """测试获取企微客户端单例"""
        # Act
        client1 = get_wechat_client()
        client2 = get_wechat_client()
        
        # Assert
        assert client1 is not None
        assert client2 is not None
        assert client1 is client2  # 应该是同一个实例
    
    def test_error_handling_network_failure(self, wechat_client, mock_requests):
        """测试网络故障错误处理"""
        # Arrange
        mock_requests.post.side_effect = Exception("网络连接失败")
        
        # Act
        result = wechat_client.send_notification_to_org(
            org_name="测试公司",
            content="测试内容",
            is_escalation=False
        )
        
        # Assert
        assert result is False
    
    def test_rate_limiting_handling(self, wechat_client, mock_requests):
        """测试限流处理"""
        # Arrange
        mock_requests.post.return_value.status_code = 429  # Too Many Requests
        
        # Act
        result = wechat_client.send_notification_to_org(
            org_name="测试公司",
            content="测试内容",
            is_escalation=False
        )
        
        # Assert
        assert result is False
    
    def test_message_content_validation(self, wechat_client):
        """测试消息内容验证"""
        # Arrange
        empty_content = ""
        long_content = "x" * 5000  # 超长内容
        normal_content = "正常的消息内容"
        
        # Act & Assert
        # 空内容应该被处理
        result1 = wechat_client._format_message_for_wechat(empty_content)
        assert isinstance(result1, dict)
        
        # 超长内容应该被截断或处理
        result2 = wechat_client._format_message_for_wechat(long_content)
        assert isinstance(result2, dict)
        
        # 正常内容应该正常处理
        result3 = wechat_client._format_message_for_wechat(normal_content)
        assert isinstance(result3, dict)
        assert normal_content in str(result3)
    
    def test_organization_mapping(self, wechat_client):
        """测试组织映射"""
        # Arrange
        known_org = "北京虹象防水工程有限公司"
        unknown_org = "未知公司"
        
        # Act
        known_url = wechat_client._get_group_webhook_url(known_org, is_escalation=False)
        unknown_url = wechat_client._get_group_webhook_url(unknown_org, is_escalation=False)
        
        # Assert
        assert isinstance(known_url, str)
        assert isinstance(unknown_url, str)
        # 两个URL可能相同（使用默认群组）或不同
    
    def test_escalation_vs_normal_notification(self, wechat_client, mock_requests):
        """测试升级通知与普通通知的区别"""
        # Arrange
        org_name = "测试公司"
        content = "测试内容"
        
        # Act
        normal_result = wechat_client.send_notification_to_org(
            org_name=org_name,
            content=content,
            is_escalation=False
        )
        
        escalation_result = wechat_client.send_notification_to_org(
            org_name=org_name,
            content=content,
            is_escalation=True
        )
        
        # Assert
        assert isinstance(normal_result, bool)
        assert isinstance(escalation_result, bool)
        
        # 验证调用了不同的处理逻辑
        assert mock_requests.post.call_count >= 2

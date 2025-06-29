"""
Metabase集成模块

提供与Metabase的API集成，获取业务数据
"""

import requests
from typing import List, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.logger import get_logger
from ..utils.config import get_config
from .models import OpportunityInfo, OpportunityStatus

logger = get_logger(__name__)


class MetabaseError(Exception):
    """Metabase相关异常"""
    pass


class MetabaseClient:
    """Metabase客户端"""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session_token = None
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def authenticate(self) -> bool:
        """认证并获取会话令牌"""
        try:
            auth_url = f"{self.base_url}/api/session"
            auth_data = {
                "username": self.username,
                "password": self.password
            }
            
            response = self.session.post(auth_url, json=auth_data, timeout=30)
            response.raise_for_status()
            
            auth_result = response.json()
            self.session_token = auth_result.get("id")
            
            if self.session_token:
                # 设置认证头
                self.session.headers.update({
                    "X-Metabase-Session": self.session_token,
                    "Content-Type": "application/json"
                })
                logger.info("Metabase authentication successful")
                return True
            else:
                logger.error("Failed to get session token from Metabase")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Metabase authentication failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Metabase authentication: {e}")
            return False
    
    def query_database(self, query: str, database_id: int = 1, 
                      parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行数据库查询"""
        if not self.session_token:
            if not self.authenticate():
                raise MetabaseError("Failed to authenticate with Metabase")
        
        try:
            query_url = f"{self.base_url}/api/dataset"
            query_data = {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": query,
                    "template-tags": parameters or {}
                }
            }
            
            response = self.session.post(query_url, json=query_data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # 解析查询结果
            if "data" in result:
                columns = [col["name"] for col in result["data"]["cols"]]
                rows = result["data"]["rows"]
                
                # 转换为字典列表
                return [dict(zip(columns, row)) for row in rows]
            else:
                logger.warning("No data returned from Metabase query")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Metabase query failed: {e}")
            raise MetabaseError(f"Query execution failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during Metabase query: {e}")
            raise MetabaseError(f"Unexpected query error: {e}")
    
    def query_card(self, card_id: int) -> List[Dict[str, Any]]:
        """查询指定的 Metabase Card 数据"""
        if not self.session_token:
            if not self.authenticate():
                raise MetabaseError("Failed to authenticate with Metabase")

        try:
            card_url = f"{self.base_url}/api/card/{card_id}/query"

            response = self.session.post(card_url, timeout=60)
            response.raise_for_status()

            result = response.json()

            # 解析查询结果
            if "data" in result:
                columns = [col["name"] for col in result["data"]["cols"]]
                rows = result["data"]["rows"]

                # 转换为字典列表
                data = [dict(zip(columns, row)) for row in rows]
                logger.info(f"Successfully retrieved {len(data)} records from card {card_id}")
                return data
            else:
                logger.warning(f"No data returned from Metabase card {card_id}")
                return []

        except requests.RequestException as e:
            logger.error(f"Metabase card {card_id} query failed: {e}")
            raise MetabaseError(f"Card query failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during card {card_id} query: {e}")
            raise MetabaseError(f"Unexpected card query error: {e}")

    def get_field_service_opportunities(self) -> List[Dict[str, Any]]:
        """获取现场服务商机数据 (Card 1712)"""
        try:
            # 使用 Card 1712 获取真实的商机数据
            raw_data = self.query_card(1712)

            # 数据验证和清理
            validated_data = []
            for record in raw_data:
                try:
                    # 验证必需字段 - 注意实际字段名可能有前缀
                    required_fields = ['orderNum', 'name', 'address', 'createTime', 'orgName', 'orderstatus']
                    supervisor_field = 'exts.supervisorName' if 'exts.supervisorName' in record else 'supervisorName'

                    # 检查基础字段
                    missing_fields = [f for f in required_fields if f not in record]
                    if supervisor_field not in record:
                        missing_fields.append('supervisorName')

                    if not missing_fields:
                        # 标准化字段名
                        if 'exts.supervisorName' in record:
                            record['supervisorName'] = record['exts.supervisorName']
                        validated_data.append(record)
                    else:
                        logger.warning(f"Record missing required fields: {missing_fields}")

                except Exception as e:
                    logger.warning(f"Failed to validate record: {e}")
                    continue

            logger.info(f"Retrieved {len(validated_data)} valid opportunity records")
            return validated_data

        except Exception as e:
            logger.error(f"Failed to get field service opportunities: {e}")
            return []

    def get_all_monitored_opportunities(self) -> List[OpportunityInfo]:
        """获取所有需要监控的商机列表（包括逾期和即将逾期）"""
        try:
            raw_opportunities = self.get_field_service_opportunities()
            opportunities = []

            for raw_opp in raw_opportunities:
                try:
                    # 转换为商机模型
                    opportunity = self._convert_raw_opportunity_to_model(raw_opp)

                    # 更新逾期信息
                    opportunity.update_overdue_info()

                    # 只返回需要监控的商机（有SLA阈值的状态）
                    if opportunity.sla_threshold_hours and opportunity.sla_threshold_hours > 0:
                        opportunities.append(opportunity)

                except Exception as e:
                    logger.warning(f"Failed to convert opportunity {raw_opp.get('orderNum', 'unknown')}: {e}")
                    continue

            logger.info(f"Found {len(opportunities)} monitored opportunities")
            return opportunities

        except Exception as e:
            logger.error(f"Failed to get monitored opportunities: {e}")
            return []

    def get_overdue_opportunities(self) -> List[OpportunityInfo]:
        """获取逾期的商机列表"""
        try:
            all_opportunities = self.get_all_monitored_opportunities()
            overdue_opportunities = [opp for opp in all_opportunities if opp.is_overdue]

            logger.info(f"Found {len(overdue_opportunities)} overdue opportunities")
            return overdue_opportunities

        except Exception as e:
            logger.error(f"Failed to get overdue opportunities: {e}")
            return []

    def _convert_raw_opportunity_to_model(self, raw_opp: Dict[str, Any]) -> OpportunityInfo:
        """将原始商机数据转换为OpportunityInfo模型"""
        try:
            # 状态映射
            status_mapping = {
                '待预约': OpportunityStatus.PENDING_APPOINTMENT,
                '暂不上门': OpportunityStatus.TEMPORARILY_NOT_VISITING,
                '已预约': OpportunityStatus.APPOINTED,
                '已完成': OpportunityStatus.COMPLETED,
                '已取消': OpportunityStatus.CANCELLED
            }

            # 获取状态，如果不在映射中则使用原值
            order_status = status_mapping.get(
                raw_opp.get('orderstatus', ''),
                raw_opp.get('orderstatus', OpportunityStatus.PENDING_APPOINTMENT)
            )

            return OpportunityInfo(
                order_num=str(raw_opp.get('orderNum', '')),
                name=str(raw_opp.get('name', '')),
                address=str(raw_opp.get('address', '')),
                supervisor_name=str(raw_opp.get('supervisorName', '')),
                create_time=raw_opp.get('createTime', ''),  # validator会处理字符串转换
                org_name=str(raw_opp.get('orgName', '')),
                order_status=order_status
            )

        except Exception as e:
            logger.error(f"Failed to convert raw opportunity data: {e}")
            raise
    
    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """
        获取超时任务列表 - 已废弃

        ⚠️ 此方法已废弃，存在任务-商机概念混淆问题

        推荐使用：
        - get_overdue_opportunities() 获取逾期商机
        - get_all_monitored_opportunities() 获取所有监控商机

        此方法不再返回实际数据，仅保留接口兼容性

        Returns:
            空列表（此方法已废弃）
        """
        logger.warning(
            "get_overdue_tasks() is deprecated due to task-opportunity concept confusion. "
            "Use get_overdue_opportunities() instead. Returning empty list."
        )

        # 不再尝试创建TaskInfo实例，因为它会抛出DeprecationWarning
        # 直接返回空列表以保持接口兼容性
        return []
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            if self.authenticate():
                # 执行简单查询测试
                test_query = "SELECT 1 as test"
                result = self.query_database(test_query)
                return len(result) > 0
            return False
        except Exception as e:
            logger.error(f"Metabase connection test failed: {e}")
            return False


def get_metabase_client() -> MetabaseClient:
    """获取Metabase客户端实例"""
    config = get_config()
    return MetabaseClient(
        base_url=config.metabase_url,
        username=config.metabase_username,
        password=config.metabase_password
    )

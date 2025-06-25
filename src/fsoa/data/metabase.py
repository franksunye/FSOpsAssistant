"""
Metabase集成模块

提供与Metabase的API集成，获取业务数据
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.logger import get_logger
from ..utils.config import get_config
from .models import TaskInfo, TaskStatus, Priority

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
    
    def get_field_service_tasks(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """获取现场服务任务数据"""
        # 示例查询 - 实际使用时需要根据具体的数据库结构调整
        query = """
        SELECT 
            task_id as id,
            task_title as title,
            task_description as description,
            task_status as status,
            priority_level as priority,
            sla_hours,
            ROUND((JULIANDAY('now') - JULIANDAY(created_at)) * 24, 2) as elapsed_hours,
            assigned_group as group_id,
            assignee_name as assignee,
            customer_name as customer,
            service_location as location,
            created_at,
            updated_at,
            last_notification_time as last_notification
        FROM field_service_tasks 
        WHERE created_at >= datetime('now', '-{hours} hours')
        AND task_status IN ('in_progress', 'assigned', 'pending')
        ORDER BY created_at DESC
        """.format(hours=hours_back)
        
        try:
            return self.query_database(query)
        except Exception as e:
            logger.error(f"Failed to get field service tasks: {e}")
            return []
    
    def get_overdue_tasks(self) -> List[TaskInfo]:
        """获取超时任务列表"""
        try:
            raw_tasks = self.get_field_service_tasks()
            tasks = []
            
            for raw_task in raw_tasks:
                try:
                    # 数据转换和验证
                    task = self._convert_raw_task_to_model(raw_task)
                    
                    # 只返回超时的任务
                    if task.is_overdue:
                        tasks.append(task)
                        
                except Exception as e:
                    logger.warning(f"Failed to convert task {raw_task.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Found {len(tasks)} overdue tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get overdue tasks: {e}")
            return []
    
    def _convert_raw_task_to_model(self, raw_task: Dict[str, Any]) -> TaskInfo:
        """将原始任务数据转换为TaskInfo模型"""
        # 状态映射
        status_mapping = {
            'in_progress': TaskStatus.IN_PROGRESS,
            'assigned': TaskStatus.IN_PROGRESS,
            'pending': TaskStatus.IN_PROGRESS,
            'completed': TaskStatus.COMPLETED,
            'cancelled': TaskStatus.CANCELLED,
            'overdue': TaskStatus.OVERDUE
        }
        
        # 优先级映射
        priority_mapping = {
            'low': Priority.LOW,
            'normal': Priority.NORMAL,
            'high': Priority.HIGH,
            'urgent': Priority.URGENT,
            'critical': Priority.URGENT
        }
        
        # 解析时间字段
        def parse_datetime(dt_str):
            if not dt_str:
                return None
            try:
                # 尝试多种时间格式
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(dt_str, fmt)
                    except ValueError:
                        continue
                # 如果都失败，返回当前时间
                logger.warning(f"Failed to parse datetime: {dt_str}")
                return datetime.now()
            except Exception:
                return datetime.now()
        
        return TaskInfo(
            id=int(raw_task.get('id', 0)),
            title=str(raw_task.get('title', 'Unknown Task')),
            description=raw_task.get('description'),
            status=status_mapping.get(
                raw_task.get('status', '').lower(), 
                TaskStatus.IN_PROGRESS
            ),
            priority=priority_mapping.get(
                raw_task.get('priority', '').lower(), 
                Priority.NORMAL
            ),
            sla_hours=int(raw_task.get('sla_hours', 8)),
            elapsed_hours=float(raw_task.get('elapsed_hours', 0)),
            group_id=raw_task.get('group_id'),
            assignee=raw_task.get('assignee'),
            customer=raw_task.get('customer'),
            location=raw_task.get('location'),
            created_at=parse_datetime(raw_task.get('created_at')),
            updated_at=parse_datetime(raw_task.get('updated_at')),
            last_notification=parse_datetime(raw_task.get('last_notification'))
        )
    
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

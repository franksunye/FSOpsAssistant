"""
配置管理模块

使用环境变量和.env文件管理配置
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class Config(BaseSettings):
    """应用配置"""
    
    # DeepSeek LLM配置
    deepseek_api_key: str = Field(..., env="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field("https://api.deepseek.com", env="DEEPSEEK_BASE_URL")
    
    # Metabase配置
    metabase_url: str = Field(..., env="METABASE_URL")
    metabase_username: str = Field(..., env="METABASE_USERNAME")
    metabase_password: str = Field(..., env="METABASE_PASSWORD")
    metabase_database_id: int = Field(1, env="METABASE_DATABASE_ID")
    
    # 内部运营群配置 - 开发人员配置，用于升级通知
    internal_ops_webhook: str = Field(..., env="INTERNAL_OPS_WEBHOOK")

    # 组织群配置已迁移到数据库 group_config 表
    # 请使用 [系统管理 → 企微群配置] 进行管理
    
    # 数据库配置
    database_url: str = Field("sqlite:///fsoa.db", env="DATABASE_URL")
    
    # 日志配置
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/fsoa.log", env="LOG_FILE")
    
    # Agent配置
    agent_execution_interval: int = Field(60, env="AGENT_EXECUTION_INTERVAL")
    agent_max_retries: int = Field(3, env="AGENT_MAX_RETRIES")
    agent_timeout: int = Field(300, env="AGENT_TIMEOUT")

    # LLM配置
    use_llm_optimization: bool = Field(True, env="USE_LLM_OPTIMIZATION")
    llm_temperature: float = Field(0.1, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(1000, env="LLM_MAX_TOKENS")
    
    # 通知配置
    notification_cooldown: int = Field(120, env="NOTIFICATION_COOLDOWN")  # 2小时=120分钟
    max_notifications_per_hour: int = Field(10, env="MAX_NOTIFICATIONS_PER_HOUR")
    escalation_threshold_hours: int = Field(4, env="ESCALATION_THRESHOLD_HOURS")
    max_retry_count: int = Field(5, env="MAX_RETRY_COUNT")  # 最大重试次数
    
    # 开发配置
    debug: bool = Field(False, env="DEBUG")
    testing: bool = Field(False, env="TESTING")
    
    @property
    def internal_ops_webhook_url(self) -> str:
        """获取内部运营群Webhook URL"""
        return self.internal_ops_webhook
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.debug or self.testing

    @property
    def wechat_webhook_list(self) -> List[str]:
        """兼容性属性：获取企微Webhook列表"""
        try:
            # 使用数据库+.env混合方案
            webhooks = []

            # 添加内部运营群webhook
            if self.internal_ops_webhook:
                webhooks.append(self.internal_ops_webhook)

            # 从数据库获取组织群webhooks
            try:
                from ..data.database import get_database_manager
                db_manager = get_database_manager()
                group_configs = db_manager.get_enabled_group_configs()

                for config in group_configs:
                    if config.webhook_url and config.webhook_url not in webhooks:
                        webhooks.append(config.webhook_url)
            except Exception as e:
                # 延迟导入避免循环导入
                try:
                    from .logger import get_logger
                    logger = get_logger(__name__)
                    logger.warning(f"Failed to load org webhooks from database: {e}")
                except:
                    pass  # 忽略日志错误

            return webhooks
        except Exception:
            # 最后的降级方案
            return [self.internal_ops_webhook] if self.internal_ops_webhook else []

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config():
    """重新加载配置"""
    global _config
    # 清除环境变量缓存
    import os
    for key in list(os.environ.keys()):
        if key.startswith(('DEEPSEEK_', 'METABASE_', 'WECHAT_', 'AGENT_', 'NOTIFICATION_', 'LLM_', 'DATABASE_', 'LOG_', 'DEBUG', 'TESTING')):
            del os.environ[key]

    # 重新加载 .env 文件
    load_dotenv(override=True)
    _config = None  # 强制重新创建配置实例

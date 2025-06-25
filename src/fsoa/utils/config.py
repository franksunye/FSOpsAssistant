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
    
    # 企微配置
    wechat_webhook_urls: str = Field(..., env="WECHAT_WEBHOOK_URLS")
    
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
    notification_cooldown: int = Field(30, env="NOTIFICATION_COOLDOWN")
    max_notifications_per_hour: int = Field(10, env="MAX_NOTIFICATIONS_PER_HOUR")
    escalation_threshold_hours: int = Field(4, env="ESCALATION_THRESHOLD_HOURS")
    
    # 开发配置
    debug: bool = Field(False, env="DEBUG")
    testing: bool = Field(False, env="TESTING")
    
    @property
    def wechat_webhook_list(self) -> List[str]:
        """获取企微Webhook URL列表 - 兼容性方法，建议使用新配置管理器"""
        # 优先使用新配置管理器
        try:
            from ..config.wechat_config import get_wechat_config_manager
            config_manager = get_wechat_config_manager()
            org_mapping = config_manager.get_org_webhook_mapping()
            # 返回所有配置的webhook URL
            webhook_urls = [url for url in org_mapping.values() if url]
            if webhook_urls:
                return webhook_urls
        except Exception:
            pass

        # 回退到旧配置方式
        return [url.strip() for url in self.wechat_webhook_urls.split(',') if url.strip()]

    def get_wechat_config_manager(self):
        """获取企微配置管理器"""
        try:
            from ..config.wechat_config import get_wechat_config_manager
            return get_wechat_config_manager()
        except ImportError:
            return None
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.debug or self.testing
    
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

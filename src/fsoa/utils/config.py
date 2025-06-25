"""
配置管理模块

使用环境变量和.env文件管理配置
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field
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
    
    # 通知配置
    notification_cooldown: int = Field(30, env="NOTIFICATION_COOLDOWN")
    max_notifications_per_hour: int = Field(10, env="MAX_NOTIFICATIONS_PER_HOUR")
    escalation_threshold_hours: int = Field(4, env="ESCALATION_THRESHOLD_HOURS")
    
    # 开发配置
    debug: bool = Field(False, env="DEBUG")
    testing: bool = Field(False, env="TESTING")
    
    @property
    def wechat_webhook_list(self) -> List[str]:
        """获取企微Webhook URL列表"""
        return [url.strip() for url in self.wechat_webhook_urls.split(',') if url.strip()]
    
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
    load_dotenv(override=True)
    _config = Config()

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
    
    # Agent配置（技术配置）
    # 注意：业务配置如执行间隔、最大重试次数等已迁移到数据库，通过Web UI管理
    agent_timeout: int = Field(300, env="AGENT_TIMEOUT")  # Agent执行超时时间（秒）

    # LLM配置（技术配置）
    # 注意：LLM优化开关、温度参数等已迁移到数据库，通过Web UI管理
    use_llm_message_formatting: bool = Field(False, env="USE_LLM_MESSAGE_FORMATTING")  # 实验性功能
    llm_max_tokens: int = Field(1000, env="LLM_MAX_TOKENS")  # LLM响应最大token数

    # 通知配置（技术配置）
    # 注意：大部分通知配置已迁移到数据库，通过Web UI管理
    max_retry_count: int = Field(5, env="MAX_RETRY_COUNT")  # 降级方案的最大重试次数
    
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
        if key.startswith(('DEEPSEEK_', 'METABASE_', 'INTERNAL_OPS_', 'AGENT_', 'LLM_', 'DATABASE_', 'LOG_', 'DEBUG', 'TESTING')):
            del os.environ[key]

    # 重新加载 .env 文件
    load_dotenv(override=True)
    _config = None  # 强制重新创建配置实例

"""
企微群配置管理模块

管理orgName到webhook URL的映射配置
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class WeChatConfigManager:
    """企微群配置管理器"""
    
    def __init__(self, config_file: str = "config/wechat_groups.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Loaded WeChat config from {self.config_file}")
                return config
            except Exception as e:
                logger.error(f"Failed to load WeChat config: {e}")
                return self._get_default_config()
        else:
            logger.info("WeChat config file not found, using default config")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "org_webhook_mapping": {
                "三河市中豫防水工程有限公司": "",
                "北京华夏防水工程有限公司": "",
                "上海东方防水技术有限公司": "",
                "广州南方防水科技有限公司": "",
                "深圳特区防水工程有限公司": ""
            },
            "internal_ops_webhook": "",
            "mention_users": {
                "escalation": ["运营负责人", "区域经理"],
                "emergency": ["总经理", "运营总监"]
            },
            "notification_settings": {
                "enable_standard_notifications": True,
                "enable_escalation_notifications": True,
                "enable_summary_notifications": False,
                "max_items_per_notification": 10,
                "cooldown_minutes": 30
            }
        }
    
    def _save_config(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved WeChat config to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save WeChat config: {e}")
            return False
    
    def get_org_webhook_mapping(self) -> Dict[str, str]:
        """获取组织到webhook的映射"""
        return self._config.get("org_webhook_mapping", {}).copy()
    
    def get_org_webhook(self, org_name: str) -> Optional[str]:
        """获取指定组织的webhook URL"""
        return self._config.get("org_webhook_mapping", {}).get(org_name)
    
    def set_org_webhook(self, org_name: str, webhook_url: str) -> bool:
        """设置组织的webhook URL"""
        try:
            if "org_webhook_mapping" not in self._config:
                self._config["org_webhook_mapping"] = {}
            
            self._config["org_webhook_mapping"][org_name] = webhook_url
            return self._save_config()
        except Exception as e:
            logger.error(f"Failed to set org webhook: {e}")
            return False
    
    def remove_org_webhook(self, org_name: str) -> bool:
        """删除组织的webhook配置"""
        try:
            if org_name in self._config.get("org_webhook_mapping", {}):
                del self._config["org_webhook_mapping"][org_name]
                return self._save_config()
            return True
        except Exception as e:
            logger.error(f"Failed to remove org webhook: {e}")
            return False
    
    def get_internal_ops_webhook(self) -> str:
        """获取内部运营群webhook"""
        return self._config.get("internal_ops_webhook", "")
    
    def set_internal_ops_webhook(self, webhook_url: str) -> bool:
        """设置内部运营群webhook"""
        try:
            self._config["internal_ops_webhook"] = webhook_url
            return self._save_config()
        except Exception as e:
            logger.error(f"Failed to set internal ops webhook: {e}")
            return False
    
    def get_mention_users(self, level: str = "escalation") -> List[str]:
        """获取需要@的用户列表"""
        return self._config.get("mention_users", {}).get(level, [])
    
    def set_mention_users(self, level: str, users: List[str]) -> bool:
        """设置需要@的用户列表"""
        try:
            if "mention_users" not in self._config:
                self._config["mention_users"] = {}
            
            self._config["mention_users"][level] = users
            return self._save_config()
        except Exception as e:
            logger.error(f"Failed to set mention users: {e}")
            return False
    
    def get_notification_settings(self) -> Dict:
        """获取通知设置"""
        return self._config.get("notification_settings", {})
    
    def update_notification_settings(self, settings: Dict) -> bool:
        """更新通知设置"""
        try:
            if "notification_settings" not in self._config:
                self._config["notification_settings"] = {}
            
            self._config["notification_settings"].update(settings)
            return self._save_config()
        except Exception as e:
            logger.error(f"Failed to update notification settings: {e}")
            return False
    
    def get_all_orgs(self) -> List[str]:
        """获取所有配置的组织列表"""
        return list(self._config.get("org_webhook_mapping", {}).keys())
    
    def validate_config(self) -> Dict[str, List[str]]:
        """验证配置的有效性"""
        issues = {
            "missing_webhooks": [],
            "invalid_webhooks": [],
            "missing_settings": []
        }
        
        # 检查组织webhook配置
        org_mapping = self._config.get("org_webhook_mapping", {})
        for org_name, webhook_url in org_mapping.items():
            if not webhook_url:
                issues["missing_webhooks"].append(f"组织 {org_name} 缺少webhook配置")
            elif not webhook_url.startswith("https://qyapi.weixin.qq.com/"):
                issues["invalid_webhooks"].append(f"组织 {org_name} 的webhook格式无效")
        
        # 检查内部运营群配置
        internal_webhook = self._config.get("internal_ops_webhook", "")
        if not internal_webhook:
            issues["missing_webhooks"].append("缺少内部运营群webhook配置")
        elif not internal_webhook.startswith("https://qyapi.weixin.qq.com/"):
            issues["invalid_webhooks"].append("内部运营群webhook格式无效")
        
        # 检查必要设置
        if not self._config.get("mention_users"):
            issues["missing_settings"].append("缺少@用户配置")
        
        if not self._config.get("notification_settings"):
            issues["missing_settings"].append("缺少通知设置配置")
        
        return issues
    
    def export_config(self) -> str:
        """导出配置为JSON字符串"""
        try:
            return json.dumps(self._config, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            return "{}"
    
    def import_config(self, config_json: str) -> bool:
        """从JSON字符串导入配置"""
        try:
            new_config = json.loads(config_json)
            self._config = new_config
            return self._save_config()
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return False


# 全局配置管理器实例
_config_manager: Optional[WeChatConfigManager] = None


def get_wechat_config_manager() -> WeChatConfigManager:
    """获取企微配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = WeChatConfigManager()
    return _config_manager

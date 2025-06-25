#!/usr/bin/env python3
"""
测试配置修复是否成功
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_config_loading():
    """测试配置加载"""
    print("🔍 测试配置加载...")
    
    try:
        from src.fsoa.utils.config import get_config
        config = get_config()
        
        print(f"✅ 配置加载成功")
        print(f"📊 数据库: {config.database_url}")
        print(f"🔗 Metabase: {config.metabase_url}")
        print(f"🔑 DeepSeek API Key: {'已配置' if config.deepseek_api_key else '未配置'}")
        print(f"📱 内部运营群Webhook: {'已配置' if config.internal_ops_webhook else '未配置'}")
        
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

def test_wechat_config():
    """测试企微配置"""
    print("\n🔍 测试企微配置...")
    
    try:
        from src.fsoa.config.wechat_config import get_wechat_config_manager
        
        config_manager = get_wechat_config_manager()
        
        # 获取配置
        org_mapping = config_manager.get_org_webhook_mapping()
        internal_webhook = config_manager.get_internal_ops_webhook()
        mention_users = config_manager.get_mention_users("escalation")
        notification_settings = config_manager.get_notification_settings()
        
        print(f"✅ 企微配置加载成功")
        print(f"📋 组织映射数量: {len(org_mapping)}")
        print(f"🏢 内部运营群: {'已配置' if internal_webhook else '未配置'}")
        print(f"👥 @用户数量: {len(mention_users)}")
        print(f"⚙️  通知设置: {len(notification_settings)} 项")
        
        return True
    except Exception as e:
        print(f"❌ 企微配置失败: {e}")
        return False

def test_compatibility():
    """测试兼容性属性"""
    print("\n🔍 测试兼容性属性...")
    
    try:
        from src.fsoa.utils.config import get_config
        config = get_config()
        
        # 测试兼容性属性
        webhook_list = config.wechat_webhook_list
        print(f"✅ wechat_webhook_list 属性可用: {len(webhook_list)} 个URL")
        
        # 测试企微配置管理器
        wechat_config = config.get_wechat_config_manager()
        if wechat_config:
            print(f"✅ get_wechat_config_manager 方法可用")
        else:
            print(f"⚠️ get_wechat_config_manager 返回 None")
        
        return True
    except Exception as e:
        print(f"❌ 兼容性测试失败: {e}")
        return False

def test_environment_cleanup():
    """测试环境变量清理"""
    print("\n🔍 测试环境变量清理...")
    
    # 检查是否还有旧的环境变量
    old_vars = []
    for key in os.environ:
        if key == 'WECHAT_WEBHOOK_URLS':
            old_vars.append(key)
    
    if old_vars:
        print(f"⚠️ 发现旧环境变量: {old_vars}")
        return False
    else:
        print(f"✅ 旧环境变量已清理")
        return True

def main():
    """主函数"""
    print("🧪 FSOA配置修复测试")
    print("=" * 50)
    
    tests = [
        ("配置加载", test_config_loading),
        ("企微配置", test_wechat_config),
        ("兼容性属性", test_compatibility),
        ("环境变量清理", test_environment_cleanup),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n📊 测试结果汇总")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！配置修复成功！")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

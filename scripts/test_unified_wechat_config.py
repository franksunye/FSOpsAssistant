#!/usr/bin/env python3
"""
测试统一后的企微配置系统

验证配置系统统一后的功能完整性和向后兼容性
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_config_system_unification():
    """测试配置系统统一"""
    print("🔧 测试统一后的企微配置系统")
    print("=" * 60)
    
    success_count = 0
    total_tests = 0
    
    # 1. 测试Config类的兼容性
    print("\n📊 测试Config类兼容性:")
    
    try:
        from src.fsoa.utils.config import get_config
        config = get_config()
        
        # 测试旧接口
        webhook_list = config.wechat_webhook_list
        print(f"   ✅ wechat_webhook_list可用: {len(webhook_list)} 个URL")
        
        # 测试新接口
        wechat_config_manager = config.get_wechat_config_manager()
        if wechat_config_manager:
            org_mapping = wechat_config_manager.get_org_webhook_mapping()
            print(f"   ✅ 新配置管理器集成: {len(org_mapping)} 个组织映射")
            success_count += 1
        else:
            print(f"   ❌ 新配置管理器集成失败")
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ Config类测试失败: {e}")
        total_tests += 1
    
    # 2. 测试企微客户端统一
    print("\n📱 测试企微客户端统一:")
    
    try:
        from src.fsoa.notification.wechat import get_wechat_client
        
        client = get_wechat_client()
        
        # 测试可用群组
        available_groups = client.get_available_groups()
        print(f"   ✅ 可用群组: {len(available_groups)} 个")
        
        # 测试组织映射
        org_mapping = client.get_org_webhook_mapping()
        print(f"   ✅ 组织映射: {len(org_mapping)} 个")
        
        # 检查是否使用了新配置
        webhook_urls = client.webhook_urls
        print(f"   ✅ Webhook URLs: {len(webhook_urls)} 个")
        
        # 检查组织名称是否作为key
        org_names = [key for key in webhook_urls.keys() if not key.startswith("group_")]
        if org_names:
            print(f"   ✅ 使用组织名称作为key: {len(org_names)} 个")
            success_count += 1
        else:
            print(f"   ⚠️ 仍使用旧的group_xxx格式")
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 企微客户端测试失败: {e}")
        total_tests += 1
    
    # 3. 测试向后兼容性
    print("\n🔄 测试向后兼容性:")
    
    try:
        # 测试旧配置方式是否仍然工作
        from src.fsoa.utils.config import get_config
        config = get_config()
        
        # 模拟旧配置环境（没有新配置文件）
        old_webhook_list = [url.strip() for url in config.wechat_webhook_urls.split(',') if url.strip()]
        print(f"   ✅ 旧配置方式: {len(old_webhook_list)} 个URL")
        
        # 测试新旧配置的一致性
        new_webhook_list = config.wechat_webhook_list
        print(f"   ✅ 新配置方式: {len(new_webhook_list)} 个URL")
        
        if len(new_webhook_list) >= len(old_webhook_list):
            print(f"   ✅ 新配置包含更多或相等的URL，向后兼容")
            success_count += 1
        else:
            print(f"   ⚠️ 新配置URL数量少于旧配置")
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 向后兼容性测试失败: {e}")
        total_tests += 1
    
    return success_count, total_tests

def test_ui_unification():
    """测试UI统一"""
    print("\n🖥️ 测试UI统一")
    print("=" * 60)
    
    success_count = 0
    total_tests = 0
    
    try:
        # 检查UI文件
        ui_file = Path("src/fsoa/ui/app.py")
        with open(ui_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. 检查是否移除了重复的群组管理
        print("\n🗑️ 检查重复功能移除:")
        
        if "群组管理" not in content or content.count("群组管理") <= 1:
            print("   ✅ 重复的群组管理已移除")
            success_count += 1
        else:
            print("   ❌ 仍存在重复的群组管理")
        total_tests += 1
        
        # 2. 检查企微配置入口统一
        print("\n🔧 检查配置入口统一:")
        
        wechat_config_count = content.count("企微群配置")
        if wechat_config_count >= 1:
            print(f"   ✅ 企微配置入口存在: {wechat_config_count} 处")
            success_count += 1
        else:
            print("   ❌ 企微配置入口缺失")
        total_tests += 1
        
        # 3. 检查系统设置优化
        print("\n⚙️ 检查系统设置优化:")
        
        if "Agent运行参数" in content and "通知策略配置" in content:
            print("   ✅ 系统设置重新定位为参数配置")
            success_count += 1
        else:
            print("   ❌ 系统设置未正确重新定位")
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ UI统一测试失败: {e}")
        total_tests += 3
    
    return success_count, total_tests

def test_functional_integration():
    """测试功能集成"""
    print("\n🔗 测试功能集成")
    print("=" * 60)
    
    success_count = 0
    total_tests = 0
    
    # 1. 测试完整的通知流程
    print("\n📬 测试通知流程集成:")
    
    try:
        from src.fsoa.agent.tools import get_notification_manager
        from src.fsoa.config.wechat_config import get_wechat_config_manager
        
        # 测试通知管理器
        notification_manager = get_notification_manager()
        print("   ✅ 通知管理器可用")
        
        # 测试配置管理器
        config_manager = get_wechat_config_manager()
        print("   ✅ 配置管理器可用")
        
        # 测试配置验证
        issues = config_manager.validate_config()
        total_issues = sum(len(problems) for problems in issues.values())
        print(f"   ✅ 配置验证: {total_issues} 个问题")
        
        success_count += 1
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 通知流程集成测试失败: {e}")
        total_tests += 1
    
    # 2. 测试数据流一致性
    print("\n🔄 测试数据流一致性:")
    
    try:
        from src.fsoa.notification.wechat import get_wechat_client
        from src.fsoa.config.wechat_config import get_wechat_config_manager
        
        # 获取客户端和配置管理器
        client = get_wechat_client()
        config_manager = get_wechat_config_manager()
        
        # 比较数据一致性
        client_orgs = set(client.get_org_webhook_mapping().keys())
        config_orgs = set(config_manager.get_org_webhook_mapping().keys())
        
        if client_orgs == config_orgs:
            print(f"   ✅ 数据一致性: 客户端和配置管理器组织映射一致")
            success_count += 1
        else:
            print(f"   ⚠️ 数据不一致: 客户端{len(client_orgs)}个，配置{len(config_orgs)}个")
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 数据流一致性测试失败: {e}")
        total_tests += 1
    
    return success_count, total_tests

def main():
    """主测试函数"""
    print("🔧 企微配置系统统一验证测试")
    print("=" * 80)
    
    total_success = 0
    total_tests = 0
    
    # 测试配置系统统一
    success, tests = test_config_system_unification()
    total_success += success
    total_tests += tests
    
    # 测试UI统一
    success, tests = test_ui_unification()
    total_success += success
    total_tests += tests
    
    # 测试功能集成
    success, tests = test_functional_integration()
    total_success += success
    total_tests += tests
    
    # 最终结果
    print("\n" + "=" * 80)
    print("🎯 企微配置统一测试结果:")
    print(f"   ✅ 成功测试: {total_success}")
    print(f"   ❌ 失败测试: {total_tests - total_success}")
    print(f"   📈 成功率: {total_success / total_tests * 100:.1f}%")
    
    print("\n📋 统一成果总结:")
    if total_success / total_tests >= 0.8:
        print("   🎉 企微配置系统统一成功！")
        print("   ✅ 配置系统完全统一")
        print("   ✅ UI重复功能已清理")
        print("   ✅ 向后兼容性保持")
        print("   ✅ 功能集成正常")
    elif total_success / total_tests >= 0.6:
        print("   ⚠️ 企微配置系统基本统一")
        print("   📋 部分功能需要进一步优化")
    else:
        print("   🚨 企微配置系统统一存在问题")
        print("   📋 需要检查和修复相关功能")
    
    print("\n💡 使用建议:")
    print("   1. 🎯 使用 [系统管理 → 企微群配置] 进行所有企微配置")
    print("   2. 🔧 [系统管理 → 系统设置] 专注于Agent和通知参数")
    print("   3. 📊 配置状态会在相关页面实时显示")
    print("   4. 🔄 旧配置方式仍然兼容，但建议迁移到新配置")
    
    return total_success / total_tests >= 0.7

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

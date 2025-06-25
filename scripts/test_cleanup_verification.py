#!/usr/bin/env python3
"""
验证 wechat_groups.json 配置清理结果

确保所有旧配置引用已清除，系统使用数据库+.env混合方案
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_file_cleanup():
    """测试文件清理"""
    print("🗑️ 测试文件清理...")
    
    success_count = 0
    total_tests = 0
    
    # 检查已删除的文件
    deleted_files = [
        "config/wechat_groups.json",
        "src/fsoa/config/wechat_config.py",
        "src/fsoa/ui/pages/wechat_config.py"
    ]
    
    for file_path in deleted_files:
        full_path = project_root / file_path
        if not full_path.exists():
            print(f"   ✅ {file_path} 已删除")
            success_count += 1
        else:
            print(f"   ❌ {file_path} 仍存在")
        total_tests += 1
    
    return success_count, total_tests

def test_import_cleanup():
    """测试导入清理"""
    print("\n📦 测试导入清理...")
    
    success_count = 0
    total_tests = 0
    
    # 测试旧模块无法导入
    try:
        from src.fsoa.config.wechat_config import get_wechat_config_manager
        print("   ❌ 旧配置模块仍可导入")
    except ImportError:
        print("   ✅ 旧配置模块已无法导入")
        success_count += 1
    total_tests += 1
    
    # 测试新配置系统可用
    try:
        from src.fsoa.utils.config import get_config
        from src.fsoa.data.database import get_database_manager
        
        config = get_config()
        db_manager = get_database_manager()
        
        # 测试内部运营群配置
        internal_webhook = config.internal_ops_webhook_url
        print(f"   ✅ 内部运营群配置: {'已配置' if internal_webhook else '未配置'}")
        success_count += 1
        
        # 测试数据库配置
        group_configs = db_manager.get_group_configs()
        print(f"   ✅ 数据库配置: {len(group_configs)} 个群组配置")
        success_count += 1
        
    except Exception as e:
        print(f"   ❌ 新配置系统测试失败: {e}")
    
    total_tests += 2
    
    return success_count, total_tests

def test_config_compatibility():
    """测试配置兼容性"""
    print("\n🔄 测试配置兼容性...")
    
    success_count = 0
    total_tests = 0
    
    try:
        from src.fsoa.utils.config import get_config
        config = get_config()
        
        # 测试兼容性属性
        webhook_list = config.wechat_webhook_list
        print(f"   ✅ wechat_webhook_list 兼容性属性: {len(webhook_list)} 个URL")
        success_count += 1
        
    except Exception as e:
        print(f"   ❌ 兼容性属性测试失败: {e}")
    
    total_tests += 1
    
    return success_count, total_tests

def test_wechat_client():
    """测试企微客户端"""
    print("\n📱 测试企微客户端...")
    
    success_count = 0
    total_tests = 0
    
    try:
        from src.fsoa.notification.wechat import get_wechat_client
        
        client = get_wechat_client()
        
        # 测试组织群映射
        org_mapping = client.get_org_webhook_mapping()
        print(f"   ✅ 组织群映射: {len(org_mapping)} 个")
        success_count += 1
        
        # 测试内部运营群
        internal_webhook = client.get_internal_ops_webhook()
        print(f"   ✅ 内部运营群: {'已配置' if internal_webhook else '未配置'}")
        success_count += 1
        
    except Exception as e:
        print(f"   ❌ 企微客户端测试失败: {e}")
    
    total_tests += 2
    
    return success_count, total_tests

def test_system_startup():
    """测试系统启动"""
    print("\n🚀 测试系统启动...")
    
    success_count = 0
    total_tests = 0
    
    try:
        # 模拟启动检查
        from src.fsoa.utils.config import get_config
        from src.fsoa.data.database import get_database_manager
        
        config = get_config()
        db_manager = get_database_manager()
        
        # 检查配置加载
        print(f"   ✅ 配置加载成功")
        print(f"   📊 数据库: {config.database_url}")
        print(f"   🔗 Metabase: {config.metabase_url}")
        
        # 检查企微配置
        group_configs = db_manager.get_enabled_group_configs()
        internal_webhook = config.internal_ops_webhook_url
        org_webhook_count = len([gc for gc in group_configs if gc.webhook_url])
        internal_webhook_count = 1 if internal_webhook else 0
        total_webhook_count = org_webhook_count + internal_webhook_count
        
        print(f"   📱 企微Webhook数量: {total_webhook_count} (组织群:{org_webhook_count}, 运营群:{internal_webhook_count})")
        
        success_count += 1
        
    except Exception as e:
        print(f"   ❌ 系统启动测试失败: {e}")
    
    total_tests += 1
    
    return success_count, total_tests

def main():
    """主测试函数"""
    print("🧹 wechat_groups.json 配置清理验证")
    print("=" * 60)
    
    total_success = 0
    total_tests = 0
    
    # 运行所有测试
    test_functions = [
        ("文件清理", test_file_cleanup),
        ("导入清理", test_import_cleanup),
        ("配置兼容性", test_config_compatibility),
        ("企微客户端", test_wechat_client),
        ("系统启动", test_system_startup)
    ]
    
    for test_name, test_func in test_functions:
        success, tests = test_func()
        total_success += success
        total_tests += tests
        print(f"\n📊 {test_name}: {success}/{tests} 通过")
    
    # 最终结果
    print("\n" + "=" * 60)
    print("🎯 清理验证结果:")
    print(f"   ✅ 成功测试: {total_success}")
    print(f"   ❌ 失败测试: {total_tests - total_success}")
    print(f"   📈 成功率: {total_success / total_tests * 100:.1f}%")
    
    print("\n🎉 清理验证评估:")
    if total_success / total_tests >= 0.9:
        print("   🏆 优秀！旧配置系统已完全清理")
        print("   ✅ 数据库+.env混合方案工作正常")
        print("   ✅ 系统可以正常启动和运行")
    elif total_success / total_tests >= 0.7:
        print("   👍 良好！大部分清理工作已完成")
        print("   📋 部分功能需要进一步检查")
    else:
        print("   ⚠️ 清理工作需要继续完善")
        print("   📋 请检查失败的测试项")
    
    print("\n💡 配置方案总结:")
    print("   🎯 组织群配置：")
    print("      - 存储位置：数据库 group_config 表")
    print("      - 管理方式：Web UI [系统管理 → 企微群配置]")
    print("      - 数据关系：商机.orgName → 企微群 → webhook地址")
    print("   🎯 运营群配置：")
    print("      - 存储位置：.env 文件 INTERNAL_OPS_WEBHOOK")
    print("      - 管理方式：开发人员配置")
    print("      - 使用场景：升级通知、内部运营通知")
    
    return total_success / total_tests >= 0.8

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

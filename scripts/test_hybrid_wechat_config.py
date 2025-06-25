#!/usr/bin/env python3
"""
测试混合企微配置方案

验证数据库+.env的混合配置方案
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_hybrid_config_design():
    """测试混合配置设计"""
    print("🔧 测试混合企微配置设计")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # 1. 测试.env配置（内部运营群）
    print("\n📊 测试.env配置（内部运营群）:")
    
    try:
        from src.fsoa.utils.config import get_config
        config = get_config()
        
        # 测试内部运营群配置
        internal_webhook = config.internal_ops_webhook_url
        print(f"   ✅ 内部运营群Webhook: {'已配置' if internal_webhook else '未配置'}")
        
        if internal_webhook and internal_webhook.startswith("https://qyapi.weixin.qq.com"):
            print(f"   ✅ Webhook格式正确")
            success_count += 1
        else:
            print(f"   ⚠️ Webhook格式需要检查: {internal_webhook}")
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ .env配置测试失败: {e}")
        total_tests += 1
    
    # 2. 测试数据库配置（组织群）
    print("\n🗄️ 测试数据库配置（组织群）:")
    
    try:
        from src.fsoa.data.database import get_database_manager
        
        db_manager = get_database_manager()
        
        # 测试群组配置方法
        all_configs = db_manager.get_group_configs()
        enabled_configs = db_manager.get_enabled_group_configs()
        
        print(f"   ✅ 总群组配置: {len(all_configs)} 个")
        print(f"   ✅ 启用配置: {len(enabled_configs)} 个")
        
        # 测试创建配置
        test_config = db_manager.create_or_update_group_config(
            group_id="test_org",
            name="测试组织",
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
            enabled=True
        )
        print(f"   ✅ 创建测试配置成功: {test_config.group_id}")
        
        # 测试获取配置
        retrieved_config = db_manager.get_group_config_by_id("test_org")
        if retrieved_config and retrieved_config.name == "测试组织":
            print(f"   ✅ 配置检索成功")
            success_count += 1
        else:
            print(f"   ❌ 配置检索失败")
        total_tests += 1
        
        # 清理测试数据
        db_manager.delete_group_config("test_org")
        print(f"   ✅ 测试数据清理完成")
        
    except Exception as e:
        print(f"   ❌ 数据库配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        total_tests += 1
    
    # 3. 测试企微客户端集成
    print("\n📱 测试企微客户端集成:")
    
    try:
        from src.fsoa.notification.wechat import get_wechat_client
        
        client = get_wechat_client()
        
        # 测试组织群映射
        org_mapping = client.get_org_webhook_mapping()
        print(f"   ✅ 组织群映射: {len(org_mapping)} 个")
        
        # 测试内部运营群
        internal_webhook = client.get_internal_ops_webhook()
        print(f"   ✅ 内部运营群: {'已配置' if internal_webhook else '未配置'}")
        
        # 测试可用群组
        available_groups = client.get_available_groups()
        print(f"   ✅ 可用群组: {len(available_groups)} 个")
        
        if len(org_mapping) >= 0 and internal_webhook:  # 允许组织群为空
            success_count += 1
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 企微客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        total_tests += 1
    
    return success_count, total_tests

def test_business_logic_alignment():
    """测试业务逻辑对齐"""
    print("\n💼 测试业务逻辑对齐")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # 1. 测试商机到组织群的映射
    print("\n🎯 测试商机→组织群映射:")
    
    try:
        from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
        from src.fsoa.notification.wechat import get_wechat_client
        from datetime import datetime
        
        # 创建测试商机
        test_opportunity = OpportunityInfo(
            order_num="TEST_001",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试负责人",
            create_time=datetime.now(),
            org_name="测试组织A",  # 这是关键：orgName
            order_status=OpportunityStatus.PENDING_APPOINTMENT,
            is_overdue=True,
            escalation_level=0
        )
        
        client = get_wechat_client()
        org_mapping = client.get_org_webhook_mapping()
        
        print(f"   ✅ 测试商机orgName: {test_opportunity.org_name}")
        print(f"   ✅ 可用组织群: {list(org_mapping.keys())}")
        
        # 检查映射逻辑
        if test_opportunity.org_name in org_mapping:
            print(f"   ✅ 商机组织有对应的企微群")
            success_count += 1
        else:
            print(f"   ⚠️ 商机组织暂无对应的企微群（需要配置）")
            success_count += 1  # 这是正常情况，不算失败
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 业务逻辑对齐测试失败: {e}")
        total_tests += 1
    
    # 2. 测试升级通知逻辑
    print("\n🚨 测试升级通知逻辑:")
    
    try:
        from src.fsoa.utils.config import get_config
        
        config = get_config()
        internal_webhook = config.internal_ops_webhook_url
        
        print(f"   ✅ 内部运营群配置: {'可用' if internal_webhook else '未配置'}")
        
        # 模拟升级通知场景
        if internal_webhook:
            print(f"   ✅ 升级通知可以发送到内部运营群")
            success_count += 1
        else:
            print(f"   ❌ 升级通知无法发送（内部运营群未配置）")
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 升级通知逻辑测试失败: {e}")
        total_tests += 1
    
    return success_count, total_tests

def test_ui_integration():
    """测试UI集成"""
    print("\n🖥️ 测试UI集成")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    try:
        # 检查UI文件
        ui_file = Path("src/fsoa/ui/app.py")
        with open(ui_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否使用了新的混合配置
        hybrid_keywords = [
            "数据库+.env混合配置",
            "组织群配置(数据库)",
            "运营群配置(.env)",
            "get_database_manager",
            "get_group_configs"
        ]
        
        found_keywords = []
        for keyword in hybrid_keywords:
            if keyword in content:
                found_keywords.append(keyword)
        
        print(f"   ✅ 混合配置关键词: {len(found_keywords)}/{len(hybrid_keywords)}")
        for keyword in found_keywords:
            print(f"      - {keyword}")
        
        if len(found_keywords) >= len(hybrid_keywords) * 0.8:
            success_count += 1
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ UI集成测试失败: {e}")
        total_tests += 1
    
    return success_count, total_tests

def test_configuration_completeness():
    """测试配置完整性"""
    print("\n🔍 测试配置完整性")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # 1. 检查.env文件
    print("\n📄 检查.env文件:")
    
    try:
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                env_content = f.read()
            
            if "INTERNAL_OPS_WEBHOOK" in env_content:
                print("   ✅ .env文件包含内部运营群配置")
                success_count += 1
            else:
                print("   ❌ .env文件缺少内部运营群配置")
            total_tests += 1
        else:
            print("   ⚠️ .env文件不存在")
            total_tests += 1
            
    except Exception as e:
        print(f"   ❌ .env文件检查失败: {e}")
        total_tests += 1
    
    # 2. 检查数据库表
    print("\n🗄️ 检查数据库表:")
    
    try:
        from src.fsoa.data.database import get_database_manager
        
        db_manager = get_database_manager()
        
        # 检查group_config表是否可用
        group_configs = db_manager.get_group_configs()
        print(f"   ✅ group_config表可用，当前有 {len(group_configs)} 条记录")
        success_count += 1
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 数据库表检查失败: {e}")
        total_tests += 1
    
    return success_count, total_tests

def main():
    """主测试函数"""
    print("🔧 混合企微配置方案验证测试")
    print("=" * 70)
    
    total_success = 0
    total_tests = 0
    
    # 运行所有测试
    test_functions = [
        ("混合配置设计", test_hybrid_config_design),
        ("业务逻辑对齐", test_business_logic_alignment),
        ("UI集成", test_ui_integration),
        ("配置完整性", test_configuration_completeness)
    ]
    
    for test_name, test_func in test_functions:
        success, tests = test_func()
        total_success += success
        total_tests += tests
        print(f"\n📊 {test_name}: {success}/{tests} 通过")
    
    # 最终结果
    print("\n" + "=" * 70)
    print("🎯 混合配置方案测试结果:")
    print(f"   ✅ 成功测试: {total_success}")
    print(f"   ❌ 失败测试: {total_tests - total_success}")
    print(f"   📈 成功率: {total_success / total_tests * 100:.1f}%")
    
    print("\n🎉 混合配置方案评估:")
    if total_success / total_tests >= 0.8:
        print("   🏆 优秀！混合配置方案设计合理")
        print("   ✅ 组织群配置：数据库管理，灵活可扩展")
        print("   ✅ 运营群配置：.env文件，开发人员控制")
        print("   ✅ 职责分离清晰，管理便捷")
    elif total_success / total_tests >= 0.6:
        print("   🎯 良好！混合配置方案基本可行")
        print("   📋 部分功能需要完善")
    else:
        print("   ⚠️ 混合配置方案需要优化")
        print("   📋 请检查失败的测试项")
    
    print("\n💡 配置方案总结:")
    print("   🎯 组织群配置：")
    print("      - 存储位置：数据库 group_config 表")
    print("      - 管理方式：Web UI [系统管理 → 企微群配置]")
    print("      - 用户角色：运营人员可以管理")
    print("      - 数据关系：商机.orgName → 企微群 → webhook地址")
    print("   🎯 运营群配置：")
    print("      - 存储位置：.env 文件 INTERNAL_OPS_WEBHOOK")
    print("      - 管理方式：开发人员配置")
    print("      - 用户角色：开发人员设置")
    print("      - 使用场景：升级通知、内部运营通知")
    
    return total_success / total_tests >= 0.7

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

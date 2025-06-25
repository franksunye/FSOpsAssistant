#!/usr/bin/env python3
"""
企微配置重复问题分析和优化方案

全面检查系统中企微配置的重复情况，制定统一的优化方案
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def analyze_duplication_issues():
    """分析企微配置重复问题"""
    print("🔍 企微配置重复问题分析")
    print("=" * 60)
    
    issues = []
    
    # 1. UI层面的重复
    print("\n🖥️ UI层面重复分析:")
    
    ui_duplications = [
        {
            "位置": "系统管理 → 系统设置 → 群组管理",
            "函数": "show_system_settings() tab3",
            "功能": "群组列表、添加新群组、Webhook URL配置",
            "问题": "使用示例数据，没有与实际配置系统集成",
            "状态": "❌ 需要移除或重构"
        },
        {
            "位置": "系统管理 → 企微群配置", 
            "函数": "show_wechat_config()",
            "功能": "完整的企微配置管理，组织映射、内部运营群、@用户",
            "问题": "功能完整，与配置系统集成",
            "状态": "✅ 保留并优化"
        }
    ]
    
    for dup in ui_duplications:
        print(f"   📍 {dup['位置']}")
        print(f"      - 函数: {dup['函数']}")
        print(f"      - 功能: {dup['功能']}")
        print(f"      - 问题: {dup['问题']}")
        print(f"      - 状态: {dup['状态']}")
        print()
    
    issues.extend(ui_duplications)
    
    # 2. 配置系统层面的重复
    print("⚙️ 配置系统重复分析:")
    
    config_duplications = [
        {
            "位置": ".env文件 → WECHAT_WEBHOOK_URLS",
            "类型": "简单配置",
            "功能": "逗号分隔的Webhook URL列表",
            "问题": "只支持简单列表，无法支持组织映射",
            "状态": "❌ 功能有限，需要升级"
        },
        {
            "位置": "config/wechat_groups.json",
            "类型": "完整配置",
            "功能": "组织映射、内部运营群、@用户、通知设置",
            "问题": "功能完整，支持复杂配置",
            "状态": "✅ 保留并作为主配置"
        },
        {
            "位置": "src.fsoa.utils.config.Config",
            "类型": "配置类",
            "功能": "wechat_webhook_list属性",
            "问题": "与新配置系统不兼容",
            "状态": "❌ 需要重构集成"
        }
    ]
    
    for dup in config_duplications:
        print(f"   📍 {dup['位置']}")
        print(f"      - 类型: {dup['类型']}")
        print(f"      - 功能: {dup['功能']}")
        print(f"      - 问题: {dup['问题']}")
        print(f"      - 状态: {dup['状态']}")
        print()
    
    issues.extend(config_duplications)
    
    # 3. 代码层面的重复
    print("💻 代码层面重复分析:")
    
    code_duplications = [
        {
            "位置": "src.fsoa.notification.wechat",
            "功能": "企微客户端，使用旧配置系统",
            "问题": "可能与新配置管理器不兼容",
            "状态": "⚠️ 需要检查兼容性"
        },
        {
            "位置": "src.fsoa.config.wechat_config",
            "功能": "新的配置管理器",
            "问题": "功能完整，但可能与旧系统冲突",
            "状态": "✅ 作为主配置系统"
        }
    ]
    
    for dup in code_duplications:
        print(f"   📍 {dup['位置']}")
        print(f"      - 功能: {dup['功能']}")
        print(f"      - 问题: {dup['问题']}")
        print(f"      - 状态: {dup['状态']}")
        print()
    
    issues.extend(code_duplications)
    
    return issues

def generate_optimization_plan():
    """生成优化方案"""
    print("\n💡 企微配置统一优化方案")
    print("=" * 60)
    
    plan = {
        "Phase 1: 清理重复UI": [
            "移除系统设置中的群组管理tab",
            "保留并优化企微群配置页面",
            "统一所有企微配置入口到一个页面"
        ],
        "Phase 2: 配置系统统一": [
            "以wechat_config.py为主配置系统",
            "重构Config类集成新配置管理器",
            "保持.env文件兼容性（向后兼容）"
        ],
        "Phase 3: 代码集成优化": [
            "更新企微客户端使用新配置管理器",
            "统一所有企微相关代码的配置来源",
            "添加配置迁移和兼容性处理"
        ],
        "Phase 4: 测试和验证": [
            "验证配置系统统一后的功能完整性",
            "测试向后兼容性",
            "更新文档和用户指南"
        ]
    }
    
    for phase, tasks in plan.items():
        print(f"\n🎯 {phase}:")
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task}")
    
    return plan

def test_current_config_systems():
    """测试当前配置系统的状态"""
    print("\n🧪 当前配置系统测试")
    print("=" * 60)
    
    results = {}
    
    # 1. 测试旧配置系统
    print("\n📊 测试旧配置系统:")
    try:
        from src.fsoa.utils.config import get_config
        config = get_config()
        webhook_list = config.wechat_webhook_list
        print(f"   ✅ 旧配置系统可用: {len(webhook_list)} 个Webhook")
        results["old_config"] = {"status": "working", "count": len(webhook_list)}
    except Exception as e:
        print(f"   ❌ 旧配置系统失败: {e}")
        results["old_config"] = {"status": "failed", "error": str(e)}
    
    # 2. 测试新配置系统
    print("\n🔧 测试新配置系统:")
    try:
        from src.fsoa.config.wechat_config import get_wechat_config_manager
        config_manager = get_wechat_config_manager()
        org_mapping = config_manager.get_org_webhook_mapping()
        print(f"   ✅ 新配置系统可用: {len(org_mapping)} 个组织映射")
        results["new_config"] = {"status": "working", "count": len(org_mapping)}
    except Exception as e:
        print(f"   ❌ 新配置系统失败: {e}")
        results["new_config"] = {"status": "failed", "error": str(e)}
    
    # 3. 测试企微客户端
    print("\n📱 测试企微客户端:")
    try:
        from src.fsoa.notification.wechat import get_wechat_client
        client = get_wechat_client()
        available_groups = client.get_available_groups()
        print(f"   ✅ 企微客户端可用: {len(available_groups)} 个可用群组")
        results["wechat_client"] = {"status": "working", "count": len(available_groups)}
    except Exception as e:
        print(f"   ❌ 企微客户端失败: {e}")
        results["wechat_client"] = {"status": "failed", "error": str(e)}
    
    return results

def main():
    """主函数"""
    print("🔧 企微配置重复问题全面分析")
    print("=" * 80)
    
    # 分析重复问题
    issues = analyze_duplication_issues()
    
    # 测试当前系统状态
    test_results = test_current_config_systems()
    
    # 生成优化方案
    optimization_plan = generate_optimization_plan()
    
    # 总结和建议
    print("\n" + "=" * 80)
    print("📋 问题总结和建议")
    print("=" * 80)
    
    print(f"\n🚨 发现的问题:")
    print(f"   - UI层面重复: 2个企微配置入口")
    print(f"   - 配置系统重复: 3套配置机制")
    print(f"   - 代码层面重复: 可能的兼容性问题")
    
    print(f"\n💡 核心建议:")
    print(f"   1. 🎯 统一配置入口 - 只保留一个企微配置页面")
    print(f"   2. 🔧 统一配置系统 - 以新配置管理器为主")
    print(f"   3. 🔗 保持向后兼容 - 渐进式迁移，不破坏现有功能")
    print(f"   4. 📚 更新文档 - 明确配置方式和最佳实践")
    
    print(f"\n⚡ 立即行动项:")
    print(f"   1. 移除系统设置中的群组管理tab")
    print(f"   2. 重构Config类集成新配置管理器")
    print(f"   3. 测试配置系统统一后的功能")
    
    # 检查系统状态
    working_systems = sum(1 for result in test_results.values() if result.get("status") == "working")
    total_systems = len(test_results)
    
    print(f"\n📊 当前系统状态: {working_systems}/{total_systems} 个系统正常工作")
    
    if working_systems == total_systems:
        print("✅ 所有配置系统都在工作，可以安全进行重构")
    else:
        print("⚠️ 部分配置系统有问题，需要先修复再重构")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

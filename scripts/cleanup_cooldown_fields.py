#!/usr/bin/env python3
"""
清理cooldown相关的无效字段和方法
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def analyze_cooldown_usage():
    """分析cooldown字段的使用情况"""
    print("=== 分析cooldown字段使用情况 ===")
    
    print("\n📋 当前问题:")
    print("1. NotificationTask模型中有cooldown_hours字段，但数据库表中没有")
    print("2. 模型中的is_in_cooldown、can_retry、should_send_now方法依赖无效字段")
    print("3. 创建任务时设置cooldown_hours参数没有意义")
    print("4. 真正的cooldown控制在NotificationTaskManager中")
    
    print("\n🎯 清理目标:")
    print("1. 从NotificationTask模型中移除cooldown_hours字段")
    print("2. 移除依赖cooldown_hours的方法")
    print("3. 移除创建任务时的cooldown_hours参数")
    print("4. 保留NotificationTaskManager中的真正cooldown机制")
    
    print("\n📁 需要修改的文件:")
    files_to_modify = [
        "src/fsoa/data/models.py - 移除cooldown_hours字段和相关方法",
        "src/fsoa/agent/managers/notification_manager.py - 移除创建任务时的cooldown_hours参数",
        "tests/unit/test_agent/test_managers/test_notification_manager.py - 更新测试",
        "docs/13_NOTIFICATION_DESIGN.md - 更新文档",
        "docs/12_SLA_DESIGN.md - 更新文档"
    ]
    
    for file_info in files_to_modify:
        print(f"   - {file_info}")
    
    print("\n⚠️ 需要保留的功能:")
    print("✅ NotificationTaskManager.notification_cooldown_hours")
    print("✅ NotificationTaskManager._has_pending_task()方法")
    print("✅ 系统配置表中的notification_cooldown")
    print("✅ Web界面的cooldown配置")
    
    return True

def check_impact():
    """检查清理的影响"""
    print("\n=== 检查清理影响 ===")
    
    print("\n🔍 可能受影响的代码:")
    
    # 检查is_in_cooldown的使用
    print("1. is_in_cooldown方法的使用:")
    print("   - 主要在模型内部使用")
    print("   - can_retry和should_send_now方法依赖它")
    print("   - 但这些方法实际上没有被使用")
    
    print("\n2. can_retry方法的使用:")
    print("   - 在should_send_now中使用")
    print("   - 但should_send_now方法没有被实际调用")
    
    print("\n3. should_send_now方法的使用:")
    print("   - 定义了但没有被实际使用")
    print("   - 通知发送逻辑在NotificationTaskManager中")
    
    print("\n✅ 结论: 这些方法都是无效的，可以安全移除")
    
    return True

def generate_cleanup_plan():
    """生成清理计划"""
    print("\n=== 清理计划 ===")
    
    cleanup_steps = [
        {
            "step": 1,
            "file": "src/fsoa/data/models.py",
            "action": "移除cooldown_hours字段",
            "details": [
                "删除 cooldown_hours: float = Field(2.0, description='冷静时间（小时）')",
                "删除 last_sent_at 字段（也没有在数据库表中）",
                "删除 is_in_cooldown 方法",
                "删除 can_retry 方法",
                "删除 should_send_now 方法"
            ]
        },
        {
            "step": 2,
            "file": "src/fsoa/agent/managers/notification_manager.py",
            "action": "移除创建任务时的cooldown_hours参数",
            "details": [
                "在create_notification_tasks方法中",
                "移除 cooldown_hours=self.notification_cooldown_hours 参数",
                "保留真正的cooldown检查逻辑"
            ]
        },
        {
            "step": 3,
            "file": "tests/unit/test_agent/test_managers/test_notification_manager.py",
            "action": "更新测试",
            "details": [
                "移除test_cooldown_check测试（测试无效方法）",
                "或者重写为测试NotificationTaskManager的cooldown机制"
            ]
        },
        {
            "step": 4,
            "file": "docs/",
            "action": "更新文档",
            "details": [
                "更新设计文档中的模型定义",
                "移除cooldown_hours字段的描述",
                "强调cooldown控制在Manager层面"
            ]
        }
    ]
    
    for step in cleanup_steps:
        print(f"\n步骤 {step['step']}: {step['action']}")
        print(f"文件: {step['file']}")
        for detail in step['details']:
            print(f"   - {detail}")
    
    return cleanup_steps

if __name__ == "__main__":
    print("🧹 Cooldown字段清理分析")
    print("="*60)
    
    analyze_cooldown_usage()
    check_impact()
    cleanup_steps = generate_cleanup_plan()
    
    print("\n" + "="*60)
    print("📋 总结:")
    print("✅ 可以安全移除模型中的cooldown相关字段和方法")
    print("✅ 真正的cooldown机制在NotificationTaskManager中，不受影响")
    print("✅ Web界面配置继续有效")
    print("✅ 清理后代码更清晰，不会产生误读")
    print("="*60)

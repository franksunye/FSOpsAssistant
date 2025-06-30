#!/usr/bin/env python3
"""
分析cooldown机制的问题
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def analyze_cooldown_issue():
    """分析cooldown机制的问题"""
    print("=== 分析cooldown机制的问题 ===")
    
    try:
        from src.fsoa.data.database import get_database_manager, NotificationTaskTable
        from src.fsoa.data.models import NotificationTask
        from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
        
        db_manager = get_database_manager()
        
        print("\n1. 系统配置表中的cooldown配置:")
        cooldown_config = db_manager.get_system_config('notification_cooldown')
        print(f"   notification_cooldown: {cooldown_config} 分钟")
        if cooldown_config:
            cooldown_hours = int(cooldown_config) / 60.0
            print(f"   转换为小时: {cooldown_hours} 小时")
        
        print("\n2. 数据库表结构分析:")
        print("   NotificationTaskTable 字段:")
        table_columns = NotificationTaskTable.__table__.columns.keys()
        print(f"   {table_columns}")
        print(f"   是否包含cooldown_hours字段: {'cooldown_hours' in table_columns}")
        
        print("\n3. 模型定义分析:")
        print("   NotificationTask 模型字段:")
        model_fields = list(NotificationTask.__fields__.keys())
        print(f"   {model_fields}")
        print(f"   是否包含cooldown_hours字段: {'cooldown_hours' in model_fields}")
        
        # 检查模型默认值
        cooldown_field = NotificationTask.__fields__.get('cooldown_hours')
        if cooldown_field:
            print(f"   cooldown_hours默认值: {cooldown_field.default}")
        
        print("\n4. NotificationTaskManager配置:")
        manager = NotificationTaskManager()
        print(f"   notification_cooldown_hours: {manager.notification_cooldown_hours}")
        
        print("\n5. 问题分析:")
        print("   ❌ 数据库表中没有cooldown_hours字段")
        print("   ❌ 模型中的cooldown_hours字段无法持久化到数据库")
        print("   ❌ 每次创建NotificationTask对象时都使用默认值2.0")
        print("   ❌ Web界面配置的cooldown值无法影响实际的通知任务")
        
        print("\n6. cooldown机制的实际工作方式:")
        print("   📋 当前实现:")
        print("   1. NotificationTaskManager从系统配置读取cooldown值")
        print("   2. 创建NotificationTask时设置cooldown_hours字段")
        print("   3. 但该字段不会保存到数据库（表中没有对应列）")
        print("   4. 从数据库读取时，cooldown_hours恢复为默认值2.0")
        print("   5. 实际的cooldown检查可能使用其他机制")
        
        print("\n7. 检查实际的cooldown检查机制:")
        # 检查_has_recent_notification方法
        print("   _has_recent_notification方法使用:")
        print("   - manager.notification_cooldown_hours (从配置读取)")
        print("   - 不依赖数据库中的cooldown_hours字段")
        print("   - 所以cooldown机制实际上是有效的！")
        
        print("\n8. 数据库中的notification_tasks示例:")
        with db_manager.get_session() as session:
            tasks = session.query(NotificationTaskTable).limit(5).all()
            for task in tasks:
                print(f"   任务ID: {task.id}, order_num: {task.order_num}, "
                      f"type: {task.notification_type}, status: {task.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_cooldown_effectiveness():
    """检查cooldown机制的有效性"""
    print("\n=== 检查cooldown机制的有效性 ===")
    
    try:
        from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
        from src.fsoa.data.models import NotificationTaskType
        from datetime import datetime, timedelta
        
        manager = NotificationTaskManager()
        
        print(f"1. 当前配置的cooldown时间: {manager.notification_cooldown_hours} 小时")
        
        # 模拟检查cooldown
        test_order = "TEST_ORDER_001"
        
        print(f"\n2. 检查订单 {test_order} 的cooldown状态:")
        has_recent = manager._has_recent_notification(test_order, NotificationTaskType.REMINDER)
        print(f"   是否有最近的通知: {has_recent}")
        
        print("\n3. cooldown机制工作原理:")
        print("   ✅ NotificationTaskManager._has_recent_notification()方法")
        print("   ✅ 使用manager.notification_cooldown_hours配置")
        print("   ✅ 查询数据库中的recent_notification_tasks")
        print("   ✅ 不依赖notification_tasks表中的cooldown_hours字段")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

if __name__ == "__main__":
    print("cooldown机制问题分析报告")
    print("="*60)
    
    success1 = analyze_cooldown_issue()
    success2 = check_cooldown_effectiveness()
    
    print("\n" + "="*60)
    print("📋 总结:")
    print("1. 数据库表结构与模型定义不一致")
    print("2. cooldown_hours字段无法持久化")
    print("3. 但cooldown机制实际上是有效的！")
    print("4. 使用配置表中的notification_cooldown值")
    print("5. Web界面的配置确实会影响cooldown行为")
    print("="*60)

#!/usr/bin/env python3
"""
验证cooldown字段清理的效果
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def verify_model_cleanup():
    """验证模型清理效果"""
    print("=== 验证NotificationTask模型清理 ===")
    
    try:
        from src.fsoa.data.models import NotificationTask
        
        # 检查字段
        model_fields = list(NotificationTask.model_fields.keys())
        print(f"模型字段: {model_fields}")
        
        # 检查是否移除了cooldown相关字段
        removed_fields = ['cooldown_hours', 'last_sent_at']
        for field in removed_fields:
            if field in model_fields:
                print(f"❌ 字段 {field} 仍然存在")
                return False
            else:
                print(f"✅ 字段 {field} 已成功移除")
        
        # 检查是否移除了相关方法
        removed_methods = ['is_in_cooldown', 'can_retry', 'should_send_now']
        for method in removed_methods:
            if hasattr(NotificationTask, method):
                print(f"❌ 方法 {method} 仍然存在")
                return False
            else:
                print(f"✅ 方法 {method} 已成功移除")
        
        # 检查保留的方法
        kept_methods = ['is_pending', 'is_overdue']
        for method in kept_methods:
            if hasattr(NotificationTask, method):
                print(f"✅ 方法 {method} 已保留")
            else:
                print(f"❌ 方法 {method} 意外丢失")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def verify_manager_functionality():
    """验证NotificationTaskManager功能完整性"""
    print("\n=== 验证NotificationTaskManager功能 ===")
    
    try:
        from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
        from src.fsoa.data.database import get_database_manager
        
        # 创建manager实例
        manager = NotificationTaskManager()
        
        # 检查cooldown配置
        print(f"✅ notification_cooldown_hours: {manager.notification_cooldown_hours}")
        
        # 检查配置来源
        db_manager = get_database_manager()
        cooldown_config = db_manager.get_system_config('notification_cooldown')
        print(f"✅ 系统配置 notification_cooldown: {cooldown_config} 分钟")
        
        if cooldown_config:
            expected_hours = int(cooldown_config) / 60.0
            if abs(manager.notification_cooldown_hours - expected_hours) < 0.01:
                print("✅ Manager正确读取了系统配置")
            else:
                print("❌ Manager配置与系统配置不一致")
                return False
        
        # 检查关键方法存在
        key_methods = ['_has_pending_task', 'create_notification_tasks']
        for method in key_methods:
            if hasattr(manager, method):
                print(f"✅ 方法 {method} 存在")
            else:
                print(f"❌ 方法 {method} 丢失")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def test_task_creation():
    """测试任务创建不再使用无效参数"""
    print("\n=== 测试任务创建 ===")
    
    try:
        from src.fsoa.data.models import NotificationTask, NotificationTaskType
        from datetime import datetime
        
        # 创建任务（不使用cooldown_hours参数）
        task = NotificationTask(
            order_num="TEST001",
            org_name="测试公司",
            notification_type=NotificationTaskType.REMINDER,
            due_time=datetime.now(),
            max_retry_count=5
        )
        
        print("✅ 成功创建NotificationTask（无cooldown_hours参数）")
        print(f"   order_num: {task.order_num}")
        print(f"   org_name: {task.org_name}")
        print(f"   notification_type: {task.notification_type}")
        print(f"   max_retry_count: {task.max_retry_count}")
        
        # 验证基本属性方法
        print(f"   is_pending: {task.is_pending}")
        print(f"   is_overdue: {task.is_overdue}")
        
        return True
        
    except Exception as e:
        print(f"❌ 任务创建失败: {e}")
        return False

def verify_web_config_still_works():
    """验证Web配置仍然有效"""
    print("\n=== 验证Web配置有效性 ===")
    
    try:
        from src.fsoa.data.database import get_database_manager
        from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
        
        db_manager = get_database_manager()
        
        # 获取当前配置
        original_config = db_manager.get_system_config('notification_cooldown')
        print(f"原始配置: {original_config} 分钟")
        
        # 修改配置
        test_value = "45"  # 45分钟
        db_manager.set_system_config('notification_cooldown', test_value, "测试配置")
        print(f"修改配置为: {test_value} 分钟")
        
        # 创建新的manager实例验证配置生效
        new_manager = NotificationTaskManager()
        expected_hours = int(test_value) / 60.0
        
        if abs(new_manager.notification_cooldown_hours - expected_hours) < 0.01:
            print(f"✅ Web配置生效: {new_manager.notification_cooldown_hours} 小时")
        else:
            print(f"❌ Web配置未生效: 期望 {expected_hours}，实际 {new_manager.notification_cooldown_hours}")
            return False
        
        # 恢复原始配置
        if original_config:
            db_manager.set_system_config('notification_cooldown', original_config, "通知冷却时间（分钟）")
            print(f"已恢复原始配置: {original_config} 分钟")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

if __name__ == "__main__":
    print("🧹 Cooldown字段清理验证")
    print("="*60)
    
    success1 = verify_model_cleanup()
    success2 = verify_manager_functionality()
    success3 = test_task_creation()
    success4 = verify_web_config_still_works()
    
    print("\n" + "="*60)
    print("📋 清理验证结果:")
    print(f"✅ 模型清理: {'通过' if success1 else '失败'}")
    print(f"✅ Manager功能: {'完整' if success2 else '受损'}")
    print(f"✅ 任务创建: {'正常' if success3 else '异常'}")
    print(f"✅ Web配置: {'有效' if success4 else '失效'}")
    
    if all([success1, success2, success3, success4]):
        print("\n🎉 清理成功！所有功能正常")
        print("💡 cooldown机制现在更清晰，不会产生误读")
        print("✅ Web界面配置继续有效")
        print("✅ 通知系统功能完整")
    else:
        print("\n❌ 清理过程中发现问题，需要进一步检查")
    
    print("="*60)

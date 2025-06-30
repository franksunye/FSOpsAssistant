#!/usr/bin/env python3
"""
测试可配置通知功能

验证通知开关配置是否正确工作
"""

import sys
import os
from datetime import datetime, timedelta

# 设置测试环境变量
os.environ['DEEPSEEK_API_KEY'] = 'test_key'
os.environ['METABASE_URL'] = 'http://test.metabase.com'
os.environ['METABASE_USERNAME'] = 'test_user'
os.environ['METABASE_PASSWORD'] = 'test_password'
os.environ['INTERNAL_OPS_WEBHOOK'] = 'https://test.webhook.com'
os.environ['DATABASE_URL'] = 'sqlite:///test_fsoa.db'
os.environ['LOG_LEVEL'] = 'INFO'

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.models import OpportunityInfo, OpportunityStatus, NotificationTaskType
from src.fsoa.data.database import get_database_manager
from src.fsoa.agent.managers.notification_manager import NotificationTaskManager


def test_database_config():
    """测试数据库配置项"""
    print("🗄️ 测试数据库配置项")
    print("-" * 50)
    
    db_manager = get_database_manager()
    
    # 检查配置项是否存在
    reminder_enabled = db_manager.get_system_config("notification_reminder_enabled")
    escalation_enabled = db_manager.get_system_config("notification_escalation_enabled")
    
    print(f"提醒通知开关: {reminder_enabled}")
    print(f"升级通知开关: {escalation_enabled}")
    
    # 如果配置不存在，初始化数据库
    if reminder_enabled is None or escalation_enabled is None:
        print("配置项不存在，初始化数据库...")
        db_manager.init_database()
        
        # 重新检查
        reminder_enabled = db_manager.get_system_config("notification_reminder_enabled")
        escalation_enabled = db_manager.get_system_config("notification_escalation_enabled")
        
        print(f"初始化后 - 提醒通知开关: {reminder_enabled}")
        print(f"初始化后 - 升级通知开关: {escalation_enabled}")
    
    assert reminder_enabled is not None, "提醒通知配置项应该存在"
    assert escalation_enabled is not None, "升级通知配置项应该存在"
    print("✅ 数据库配置项测试通过")


def test_notification_manager_config_loading():
    """测试NotificationManager配置加载"""
    print("\n📋 测试NotificationManager配置加载")
    print("-" * 50)
    
    # 创建NotificationManager实例
    manager = NotificationTaskManager()
    
    print(f"提醒通知开关: {manager.reminder_enabled}")
    print(f"升级通知开关: {manager.escalation_enabled}")
    
    # 验证默认配置
    assert hasattr(manager, 'reminder_enabled'), "应该有reminder_enabled属性"
    assert hasattr(manager, 'escalation_enabled'), "应该有escalation_enabled属性"
    assert isinstance(manager.reminder_enabled, bool), "reminder_enabled应该是布尔值"
    assert isinstance(manager.escalation_enabled, bool), "escalation_enabled应该是布尔值"
    
    print("✅ NotificationManager配置加载测试通过")


def create_test_opportunities(scenario_num):
    """创建测试商机"""
    from datetime import date
    today = date.today()
    # 找到最近的工作日
    weekday = today.weekday()  # 0=Monday, 6=Sunday
    if weekday >= 5:  # 周末
        days_back = weekday - 4  # 回到周五
        work_date = today - timedelta(days=days_back)
    else:
        work_date = today

    # 创建工作时间内的测试时间
    reminder_time = datetime.combine(work_date, datetime.min.time()) + timedelta(hours=10)  # 上午10点
    escalation_time = datetime.combine(work_date, datetime.min.time()) + timedelta(hours=9)   # 上午9点

    test_opportunities = [
        OpportunityInfo(
            order_num=f"TEST_REMINDER_{scenario_num:03d}",
            name=f"测试客户{scenario_num}_1",
            address=f"测试地址{scenario_num}_1",
            supervisor_name=f"测试销售{scenario_num}_1",
            create_time=reminder_time - timedelta(hours=6),  # 6小时前，应该触发提醒
            org_name=f"测试公司{scenario_num}_1",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        ),
        OpportunityInfo(
            order_num=f"TEST_ESCALATION_{scenario_num:03d}",
            name=f"测试客户{scenario_num}_2",
            address=f"测试地址{scenario_num}_2",
            supervisor_name=f"测试销售{scenario_num}_2",
            create_time=escalation_time - timedelta(hours=10),  # 10小时前，应该触发升级
            org_name=f"测试公司{scenario_num}_2",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
    ]

    # 手动设置SLA状态用于测试
    test_opportunities[0].elapsed_hours = 6.0
    test_opportunities[0].is_violation = True
    test_opportunities[0].is_overdue = False
    test_opportunities[0].escalation_level = 0

    test_opportunities[1].elapsed_hours = 10.0
    test_opportunities[1].is_violation = True
    test_opportunities[1].is_overdue = True
    test_opportunities[1].escalation_level = 1

    return test_opportunities


def test_notification_creation_with_config():
    """测试不同配置下的通知创建"""
    print("\n🔔 测试不同配置下的通知创建")
    print("-" * 50)

    db_manager = get_database_manager()

    # 清理之前的测试数据
    try:
        from sqlalchemy import text
        with db_manager.get_session() as session:
            # 删除测试通知任务
            session.execute(text("DELETE FROM notification_tasks WHERE order_num LIKE 'TEST_%'"))
            session.commit()
            print("清理了之前的测试数据")
    except Exception as e:
        print(f"清理测试数据时出错: {e}")

    # 测试场景1：只启用提醒通知
    print("\n场景1：只启用提醒通知")
    db_manager.set_system_config("notification_reminder_enabled", "true", "测试")
    db_manager.set_system_config("notification_escalation_enabled", "false", "测试")

    test_opportunities1 = create_test_opportunities(1)
    print(f"  测试商机订单号: {[opp.order_num for opp in test_opportunities1]}")
    manager1 = NotificationTaskManager()
    tasks1 = manager1.create_notification_tasks(test_opportunities1, 1001)

    reminder_tasks1 = [t for t in tasks1 if t.notification_type == NotificationTaskType.REMINDER]
    escalation_tasks1 = [t for t in tasks1 if t.notification_type == NotificationTaskType.ESCALATION]

    print(f"  创建的提醒任务: {len(reminder_tasks1)}")
    print(f"  创建的升级任务: {len(escalation_tasks1)}")
    assert len(reminder_tasks1) > 0, "应该创建提醒任务"
    assert len(escalation_tasks1) == 0, "不应该创建升级任务"

    # 测试场景2：只启用升级通知
    print("\n场景2：只启用升级通知")
    db_manager.set_system_config("notification_reminder_enabled", "false", "测试")
    db_manager.set_system_config("notification_escalation_enabled", "true", "测试")

    test_opportunities2 = create_test_opportunities(2)
    manager2 = NotificationTaskManager()
    tasks2 = manager2.create_notification_tasks(test_opportunities2, 1002)

    reminder_tasks2 = [t for t in tasks2 if t.notification_type == NotificationTaskType.REMINDER]
    escalation_tasks2 = [t for t in tasks2 if t.notification_type == NotificationTaskType.ESCALATION]

    print(f"  创建的提醒任务: {len(reminder_tasks2)}")
    print(f"  创建的升级任务: {len(escalation_tasks2)}")
    assert len(reminder_tasks2) == 0, "不应该创建提醒任务"
    assert len(escalation_tasks2) > 0, "应该创建升级任务"

    # 测试场景3：启用所有通知
    print("\n场景3：启用所有通知")
    db_manager.set_system_config("notification_reminder_enabled", "true", "测试")
    db_manager.set_system_config("notification_escalation_enabled", "true", "测试")

    test_opportunities3 = create_test_opportunities(3)
    manager3 = NotificationTaskManager()
    tasks3 = manager3.create_notification_tasks(test_opportunities3, 1003)

    reminder_tasks3 = [t for t in tasks3 if t.notification_type == NotificationTaskType.REMINDER]
    escalation_tasks3 = [t for t in tasks3 if t.notification_type == NotificationTaskType.ESCALATION]

    print(f"  创建的提醒任务: {len(reminder_tasks3)}")
    print(f"  创建的升级任务: {len(escalation_tasks3)}")
    assert len(reminder_tasks3) > 0, "应该创建提醒任务"
    assert len(escalation_tasks3) > 0, "应该创建升级任务"

    # 测试场景4：关闭所有通知
    print("\n场景4：关闭所有通知")
    db_manager.set_system_config("notification_reminder_enabled", "false", "测试")
    db_manager.set_system_config("notification_escalation_enabled", "false", "测试")

    test_opportunities4 = create_test_opportunities(4)
    manager4 = NotificationTaskManager()
    tasks4 = manager4.create_notification_tasks(test_opportunities4, 1004)

    reminder_tasks4 = [t for t in tasks4 if t.notification_type == NotificationTaskType.REMINDER]
    escalation_tasks4 = [t for t in tasks4 if t.notification_type == NotificationTaskType.ESCALATION]

    print(f"  创建的提醒任务: {len(reminder_tasks4)}")
    print(f"  创建的升级任务: {len(escalation_tasks4)}")
    assert len(reminder_tasks4) == 0, "不应该创建提醒任务"
    assert len(escalation_tasks4) == 0, "不应该创建升级任务"

    print("✅ 通知创建配置测试通过")


def test_config_persistence():
    """测试配置持久化"""
    print("\n💾 测试配置持久化")
    print("-" * 50)
    
    db_manager = get_database_manager()
    
    # 设置测试配置
    db_manager.set_system_config("notification_reminder_enabled", "false", "测试持久化")
    db_manager.set_system_config("notification_escalation_enabled", "true", "测试持久化")
    
    # 创建新的manager实例，验证配置是否正确加载
    manager = NotificationTaskManager()
    
    assert manager.reminder_enabled == False, "提醒通知应该被禁用"
    assert manager.escalation_enabled == True, "升级通知应该被启用"
    
    print(f"持久化测试 - 提醒通知: {manager.reminder_enabled}")
    print(f"持久化测试 - 升级通知: {manager.escalation_enabled}")
    
    # 恢复默认配置
    db_manager.set_system_config("notification_reminder_enabled", "true", "恢复默认")
    db_manager.set_system_config("notification_escalation_enabled", "false", "恢复默认")
    
    print("✅ 配置持久化测试通过")


def main():
    """主函数"""
    print("=" * 60)
    print("可配置通知功能测试")
    print("=" * 60)
    
    try:
        test_database_config()
        test_notification_manager_config_loading()
        test_notification_creation_with_config()
        test_config_persistence()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！可配置通知功能工作正常")
        print("=" * 60)
        
        # 显示当前配置状态
        db_manager = get_database_manager()
        reminder_enabled = db_manager.get_system_config("notification_reminder_enabled")
        escalation_enabled = db_manager.get_system_config("notification_escalation_enabled")
        
        print(f"\n当前配置状态:")
        print(f"  提醒通知: {'启用' if reminder_enabled == 'true' else '禁用'}")
        print(f"  升级通知: {'启用' if escalation_enabled == 'true' else '禁用'}")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

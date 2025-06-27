#!/usr/bin/env python3
"""
测试通知任务清理功能

这个脚本测试Web应用中"清理旧任务"功能的实际效果
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置环境变量
os.environ['DEEPSEEK_API_KEY'] = 'test'
os.environ['METABASE_URL'] = 'http://test'
os.environ['METABASE_USERNAME'] = 'test'
os.environ['METABASE_PASSWORD'] = 'test'
os.environ['INTERNAL_OPS_WEBHOOK'] = 'http://test'

def create_test_tasks():
    """创建测试用的通知任务"""
    print("=== 创建测试通知任务 ===")
    
    from src.fsoa.data.database import get_database_manager, NotificationTaskTable
    from src.fsoa.utils.timezone_utils import now_china_naive
    
    db_manager = get_database_manager()
    now = now_china_naive()
    
    # 创建不同时间的测试任务
    test_tasks = [
        # 新任务（不应该被清理）
        {
            "order_num": "TEST001",
            "org_name": "测试组织1",
            "notification_type": "standard",
            "status": "sent",
            "created_at": now - timedelta(days=1),  # 1天前
            "sent_at": now - timedelta(days=1)
        },
        {
            "order_num": "TEST002", 
            "org_name": "测试组织2",
            "notification_type": "violation",
            "status": "pending",
            "created_at": now - timedelta(days=10),  # 10天前，但是pending状态
            "sent_at": None
        },
        # 旧任务（应该被清理）
        {
            "order_num": "TEST003",
            "org_name": "测试组织3", 
            "notification_type": "standard",
            "status": "sent",
            "created_at": now - timedelta(days=10),  # 10天前
            "sent_at": now - timedelta(days=10)
        },
        {
            "order_num": "TEST004",
            "org_name": "测试组织4",
            "notification_type": "escalation", 
            "status": "failed",
            "created_at": now - timedelta(days=15),  # 15天前
            "sent_at": None
        },
        {
            "order_num": "TEST005",
            "org_name": "测试组织5",
            "notification_type": "standard",
            "status": "confirmed",
            "created_at": now - timedelta(days=8),  # 8天前
            "sent_at": now - timedelta(days=8)
        }
    ]
    
    created_count = 0
    with db_manager.get_session() as session:
        for task_data in test_tasks:
            # 检查是否已存在
            existing = session.query(NotificationTaskTable).filter_by(
                order_num=task_data["order_num"]
            ).first()
            
            if not existing:
                task = NotificationTaskTable(
                    order_num=task_data["order_num"],
                    org_name=task_data["org_name"],
                    notification_type=task_data["notification_type"],
                    status=task_data["status"],
                    due_time=task_data["created_at"],
                    message=f"测试消息 - {task_data['order_num']}",
                    created_at=task_data["created_at"],
                    updated_at=task_data["created_at"],
                    sent_at=task_data["sent_at"]
                )
                session.add(task)
                created_count += 1
        
        session.commit()
    
    print(f"✓ 创建了 {created_count} 个测试任务")
    return created_count


def show_current_tasks():
    """显示当前的通知任务"""
    print("\n=== 当前通知任务列表 ===")
    
    from src.fsoa.data.database import get_database_manager, NotificationTaskTable
    from src.fsoa.utils.timezone_utils import now_china_naive
    
    db_manager = get_database_manager()
    now = now_china_naive()
    
    with db_manager.get_session() as session:
        tasks = session.query(NotificationTaskTable).order_by(NotificationTaskTable.created_at.desc()).all()
        
        if not tasks:
            print("没有找到任务")
            return 0
        
        print(f"{'订单号':<12} {'状态':<10} {'类型':<12} {'创建时间':<20} {'天数':<6}")
        print("-" * 70)
        
        for task in tasks:
            days_ago = (now - task.created_at).days
            print(f"{task.order_num:<12} {task.status:<10} {task.notification_type:<12} "
                  f"{task.created_at.strftime('%Y-%m-%d %H:%M'):<20} {days_ago:<6}")
        
        return len(tasks)


def test_cleanup_function():
    """测试清理功能"""
    print("\n=== 测试清理功能 ===")
    
    from src.fsoa.agent.managers.notification_manager import NotificationTaskManager
    from src.fsoa.data.database import get_database_manager
    
    db_manager = get_database_manager()
    manager = NotificationTaskManager()
    
    # 显示清理前的任务数量
    before_count = show_current_tasks()
    print(f"\n清理前总任务数: {before_count}")
    
    # 执行清理（清理7天前的任务）
    print("\n执行清理操作（清理7天前的已完成任务）...")
    cleaned_count = manager.cleanup_old_tasks(days_back=7)
    
    print(f"清理结果: {cleaned_count} 个任务被清理")
    
    # 显示清理后的任务
    print("\n=== 清理后的任务列表 ===")
    after_count = show_current_tasks()
    print(f"\n清理后总任务数: {after_count}")
    
    # 验证清理结果
    expected_remaining = before_count - cleaned_count
    if after_count == expected_remaining:
        print(f"✓ 清理结果正确: {before_count} - {cleaned_count} = {after_count}")
        return True
    else:
        print(f"✗ 清理结果异常: 期望剩余 {expected_remaining}，实际剩余 {after_count}")
        return False


def verify_cleanup_logic():
    """验证清理逻辑的正确性"""
    print("\n=== 验证清理逻辑 ===")
    
    from src.fsoa.data.database import get_database_manager, NotificationTaskTable
    from src.fsoa.utils.timezone_utils import now_china_naive
    
    db_manager = get_database_manager()
    now = now_china_naive()
    
    with db_manager.get_session() as session:
        # 检查剩余任务
        remaining_tasks = session.query(NotificationTaskTable).all()
        
        print("剩余任务分析:")
        for task in remaining_tasks:
            days_ago = (now - task.created_at).days
            should_be_cleaned = (days_ago >= 7 and task.status in ['sent', 'confirmed', 'failed'])
            status_icon = "❌" if should_be_cleaned else "✓"
            
            print(f"{status_icon} {task.order_num}: {task.status}, {days_ago}天前 "
                  f"{'(应该被清理但未清理)' if should_be_cleaned else '(正确保留)'}")
        
        # 统计验证
        old_completed_tasks = session.query(NotificationTaskTable).filter(
            NotificationTaskTable.created_at < now - timedelta(days=7),
            NotificationTaskTable.status.in_(['sent', 'confirmed', 'failed'])
        ).count()
        
        if old_completed_tasks == 0:
            print("✓ 清理逻辑正确：没有遗留的旧已完成任务")
            return True
        else:
            print(f"✗ 清理逻辑有问题：还有 {old_completed_tasks} 个旧已完成任务未被清理")
            return False


def cleanup_test_data():
    """清理测试数据"""
    print("\n=== 清理测试数据 ===")
    
    from src.fsoa.data.database import get_database_manager, NotificationTaskTable
    
    db_manager = get_database_manager()
    
    with db_manager.get_session() as session:
        # 删除所有测试任务
        deleted = session.query(NotificationTaskTable).filter(
            NotificationTaskTable.order_num.like('TEST%')
        ).delete()
        
        session.commit()
        print(f"✓ 清理了 {deleted} 个测试任务")
        
        return deleted


def main():
    """主函数"""
    print("开始测试通知任务清理功能...")
    
    try:
        # 1. 创建测试数据
        create_test_tasks()
        
        # 2. 测试清理功能
        success = test_cleanup_function()
        
        # 3. 验证清理逻辑
        logic_correct = verify_cleanup_logic()
        
        # 4. 清理测试数据
        cleanup_test_data()
        
        # 总结
        if success and logic_correct:
            print("\n✅ 通知任务清理功能测试通过！")
            print("\n📋 清理规则总结:")
            print("- 清理对象: notification_tasks 表中的已完成任务")
            print("- 清理条件: 创建时间超过指定天数（默认7天）")
            print("- 清理状态: 'sent', 'confirmed', 'failed'")
            print("- 保留状态: 'pending' (待处理任务不会被清理)")
            print("- 保留时间: 7天内的任务不会被清理")
        else:
            print("\n❌ 测试失败")
        
        return success and logic_correct
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

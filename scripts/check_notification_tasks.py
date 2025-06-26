#!/usr/bin/env python3
"""
检查通知任务状态
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.database import get_database_manager
from src.fsoa.utils.logger import get_logger

logger = get_logger(__name__)


def check_notification_tasks():
    """检查通知任务状态"""
    print("=" * 60)
    print("检查通知任务状态")
    print("=" * 60)
    
    try:
        db_manager = get_database_manager()
        
        # 查询notification_tasks表
        with db_manager.get_session() as session:
            from src.fsoa.data.database import NotificationTaskTable
            
            # 获取所有任务
            all_tasks = session.query(NotificationTaskTable).all()
            print(f"总通知任务: {len(all_tasks)} 条")
            
            if all_tasks:
                # 检查表结构
                first_task = all_tasks[0]
                print(f"\n表结构检查:")
                print(f"  ID: {hasattr(first_task, 'id')}")
                print(f"  order_num: {hasattr(first_task, 'order_num')}")
                print(f"  org_name: {hasattr(first_task, 'org_name')}")
                print(f"  status: {hasattr(first_task, 'status')}")
                print(f"  created_at: {hasattr(first_task, 'created_at')}")
                print(f"  error_message: {hasattr(first_task, 'error_message')}")
                print(f"  run_id: {hasattr(first_task, 'run_id')}")
                
                # 显示前5条任务详情
                print(f"\n前5条任务详情:")
                for i, task in enumerate(all_tasks[:5], 1):
                    print(f"{i}. ID: {task.id}")
                    if hasattr(task, 'order_num'):
                        print(f"   工单号: {task.order_num}")
                    if hasattr(task, 'org_name'):
                        print(f"   组织: {task.org_name}")
                    if hasattr(task, 'status'):
                        print(f"   状态: {task.status}")
                    if hasattr(task, 'created_at'):
                        print(f"   创建时间: {task.created_at}")
                    if hasattr(task, 'error_message'):
                        print(f"   错误信息: {task.error_message}")
                    print()
            
            # 统计各状态的任务数量
            from sqlalchemy import func
            status_counts = session.query(
                NotificationTaskTable.status,
                func.count(NotificationTaskTable.id)
            ).group_by(NotificationTaskTable.status).all()
            
            print("任务状态统计:")
            for status, count in status_counts:
                print(f"  {status}: {count} 条")
                
            # 检查pending任务的详细信息
            pending_tasks = session.query(NotificationTaskTable).filter(
                NotificationTaskTable.status == 'pending'
            ).all()
            
            if pending_tasks:
                print(f"\nPending任务分析:")
                print(f"  数量: {len(pending_tasks)}")
                
                # 检查是否有错误信息
                tasks_with_errors = [t for t in pending_tasks if hasattr(t, 'error_message') and t.error_message]
                print(f"  有错误信息的任务: {len(tasks_with_errors)}")
                
                if tasks_with_errors:
                    print(f"\n错误信息示例:")
                    for i, task in enumerate(tasks_with_errors[:3], 1):
                        print(f"  {i}. 任务ID {task.id}: {task.error_message}")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        logger.error(f"Check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def fix_pending_tasks():
    """尝试修复pending任务"""
    print("\n" + "=" * 60)
    print("尝试修复Pending任务")
    print("=" * 60)
    
    try:
        from src.fsoa.agent.tools import execute_notification_tasks
        
        # 尝试执行pending任务
        print("正在执行pending通知任务...")

        # 创建一个临时的run_id
        from src.fsoa.agent.tools import get_execution_tracker
        execution_tracker = get_execution_tracker()
        run_id = execution_tracker.start_run({"temporary": True, "manual_notification": True})

        result = execute_notification_tasks(run_id)
        
        print(f"执行结果:")
        print(f"  发送成功: {result.get('sent_count', 0)}")
        print(f"  发送失败: {result.get('failed_count', 0)}")
        print(f"  总计处理: {result.get('total_count', 0)}")
        
        if result.get('failed_tasks'):
            print(f"\n失败任务详情:")
            for task in result['failed_tasks'][:3]:
                print(f"  - 工单号: {task.get('order_num', 'N/A')}")
                print(f"    错误: {task.get('error', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        logger.error(f"Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def clear_failed_tasks():
    """清理失败的任务"""
    print("\n" + "=" * 60)
    print("清理失败任务")
    print("=" * 60)
    
    try:
        db_manager = get_database_manager()
        
        with db_manager.get_session() as session:
            from src.fsoa.data.database import NotificationTaskTable
            
            # 删除所有pending任务
            deleted = session.query(NotificationTaskTable).filter(
                NotificationTaskTable.status == 'pending'
            ).delete()
            
            session.commit()
            print(f"✅ 已删除 {deleted} 个pending任务")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        logger.error(f"Clear failed: {e}")
        return False


def main():
    """主函数"""
    print("FSOA 通知任务诊断工具")
    
    # 1. 检查任务状态
    success = check_notification_tasks()
    
    if success:
        # 2. 尝试修复
        print("\n是否尝试修复pending任务? (y/n): ", end="")
        choice = input().strip().lower()
        
        if choice in ['y', 'yes']:
            fix_success = fix_pending_tasks()
            
            if not fix_success:
                print("\n修复失败，是否清理所有pending任务? (y/n): ", end="")
                clear_choice = input().strip().lower()
                
                if clear_choice in ['y', 'yes']:
                    clear_failed_tasks()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    main()

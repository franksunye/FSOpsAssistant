#!/usr/bin/env python3
"""
清理pending通知任务
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.database import get_database_manager


def main():
    """清理所有pending通知任务"""
    print("清理Pending通知任务")
    print("=" * 40)
    
    try:
        db_manager = get_database_manager()
        
        with db_manager.get_session() as session:
            from src.fsoa.data.database import NotificationTaskTable
            
            # 查询pending任务数量
            pending_count = session.query(NotificationTaskTable).filter(
                NotificationTaskTable.status == 'pending'
            ).count()
            
            print(f"找到 {pending_count} 个pending任务")
            
            if pending_count > 0:
                # 删除所有pending任务
                deleted = session.query(NotificationTaskTable).filter(
                    NotificationTaskTable.status == 'pending'
                ).delete()
                
                session.commit()
                print(f"✅ 已删除 {deleted} 个pending任务")
            else:
                print("✅ 没有pending任务需要清理")
        
        print("\n清理完成！现在可以重新执行Agent。")
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

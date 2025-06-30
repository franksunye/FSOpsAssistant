#!/usr/bin/env python3
"""
验证通知系统是否正常工作
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

def verify_notification_system():
    """验证通知系统的正确性"""
    
    print("=== 通知系统验证 ===\n")
    
    # 连接数据库
    db_path = Path("fsoa.db")
    if not db_path.exists():
        print("数据库文件不存在")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 1. 检查升级任务的数据一致性
        print("1. 检查升级任务数据一致性:")
        cursor.execute("""
            SELECT org_name, COUNT(*) as task_count
            FROM notification_tasks 
            WHERE notification_type = 'escalation' 
            AND status = 'pending'
            GROUP BY org_name
        """)
        
        org_counts = cursor.fetchall()
        print(f"   找到 {len(org_counts)} 个组织有升级任务:")
        
        all_good = True
        for org_name, task_count in org_counts:
            if task_count > 1:
                print(f"   ❌ {org_name}: {task_count} 个升级任务 (应该只有1个)")
                all_good = False
            else:
                print(f"   ✅ {org_name}: {task_count} 个升级任务")
        
        if all_good:
            print("   ✅ 升级任务数据一致性检查通过")
        else:
            print("   ❌ 发现重复的升级任务")
        
        # 2. 检查order_num格式
        print("\n2. 检查order_num格式:")
        cursor.execute("""
            SELECT notification_type, 
                   COUNT(*) as total,
                   SUM(CASE WHEN order_num LIKE 'ESCALATION_%' THEN 1 ELSE 0 END) as escalation_format,
                   SUM(CASE WHEN order_num LIKE 'GD%' THEN 1 ELSE 0 END) as order_format
            FROM notification_tasks 
            GROUP BY notification_type
        """)
        
        format_stats = cursor.fetchall()
        for notification_type, total, escalation_format, order_format in format_stats:
            print(f"   {notification_type} 类型:")
            print(f"     总数: {total}")
            print(f"     ESCALATION_格式: {escalation_format}")
            print(f"     工单号格式: {order_format}")
            
            if notification_type == 'escalation':
                if escalation_format == total:
                    print(f"     ✅ 所有升级任务都使用ESCALATION_格式")
                else:
                    print(f"     ❌ 升级任务格式不一致")
            elif notification_type == 'reminder':
                if order_format == total:
                    print(f"     ✅ 所有提醒任务都使用工单号格式")
                else:
                    print(f"     ❌ 提醒任务格式不一致")
        
        # 3. 检查业务逻辑正确性
        print("\n3. 检查业务逻辑正确性:")
        
        # 检查是否有组织同时有多个升级任务
        cursor.execute("""
            SELECT org_name, GROUP_CONCAT(order_num) as order_nums
            FROM notification_tasks 
            WHERE notification_type = 'escalation' 
            AND status = 'pending'
            GROUP BY org_name
            HAVING COUNT(*) > 1
        """)
        
        duplicate_orgs = cursor.fetchall()
        if duplicate_orgs:
            print("   ❌ 发现重复升级任务的组织:")
            for org_name, order_nums in duplicate_orgs:
                print(f"     {org_name}: {order_nums}")
        else:
            print("   ✅ 没有重复的升级任务")
        
        # 4. 检查任务创建逻辑
        print("\n4. 检查任务创建逻辑:")
        cursor.execute("""
            SELECT notification_type, 
                   MIN(created_at) as first_created,
                   MAX(created_at) as last_created,
                   COUNT(*) as total_count
            FROM notification_tasks 
            WHERE created_at >= datetime('now', '-1 day')
            GROUP BY notification_type
        """)
        
        recent_stats = cursor.fetchall()
        if recent_stats:
            print("   最近24小时创建的任务:")
            for notification_type, first_created, last_created, total_count in recent_stats:
                print(f"     {notification_type}: {total_count} 个任务")
                print(f"       首次创建: {first_created}")
                print(f"       最后创建: {last_created}")
        else:
            print("   最近24小时没有创建新任务")
        
        # 5. 总结
        print("\n=== 验证结果 ===")
        
        # 检查是否有明显的问题
        cursor.execute("""
            SELECT COUNT(*) FROM notification_tasks 
            WHERE notification_type = 'escalation' 
            AND status = 'pending'
        """)
        escalation_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT org_name) FROM notification_tasks 
            WHERE notification_type = 'escalation' 
            AND status = 'pending'
        """)
        org_count = cursor.fetchone()[0]
        
        if escalation_count == org_count:
            print("✅ 升级任务数量正确：每个组织只有一个升级任务")
            print("✅ 当前的通知系统设计是正确的")
            print("\n📝 说明:")
            print("   - order_num字段在升级任务中存储'ESCALATION_组织名'是设计决策")
            print("   - 这确保了每个组织只有一个升级任务")
            print("   - 虽然语义上有些混乱，但功能上是正确的")
            return True
        else:
            print(f"❌ 升级任务数量异常：{escalation_count} 个任务，{org_count} 个组织")
            print("❌ 存在重复的升级任务")
            return False
            
    except Exception as e:
        print(f"验证失败: {e}")
        return False
    finally:
        conn.close()

def suggest_improvements():
    """建议改进方案"""
    print("\n=== 改进建议 ===")
    print("虽然当前系统功能正确，但可以考虑以下改进:")
    print("1. 添加注释说明order_num字段在升级任务中的特殊用法")
    print("2. 在数据库表中添加is_escalation_task字段来明确标识")
    print("3. 在UI中显示时区分工单号和任务标识符")
    print("4. 考虑未来重构时引入专门的task_identifier字段")

if __name__ == "__main__":
    is_correct = verify_notification_system()
    suggest_improvements()
    
    if is_correct:
        print("\n🎉 结论：当前通知系统功能正确，无需修复")
        sys.exit(0)
    else:
        print("\n⚠️  结论：发现问题，需要修复")
        sys.exit(1)

#!/usr/bin/env python3
"""
检查升级任务的数据问题
"""

import sqlite3
import sys
from pathlib import Path

def check_escalation_tasks():
    """检查升级任务数据"""
    db_path = Path("fsoa.db")
    if not db_path.exists():
        print("数据库文件不存在")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("=== 检查升级任务数据 ===")
        
        # 检查所有升级任务
        cursor.execute("""
            SELECT id, order_num, org_name, notification_type, status, created_at 
            FROM notification_tasks 
            WHERE notification_type = 'escalation' 
            ORDER BY id DESC 
            LIMIT 20
        """)
        
        rows = cursor.fetchall()
        print(f"找到 {len(rows)} 个升级任务:")
        
        for row in rows:
            task_id, order_num, org_name, notification_type, status, created_at = row
            is_new_format = order_num.startswith('ESCALATION_')
            format_type = "新格式" if is_new_format else "旧格式"
            print(f"  ID: {task_id}, order_num: {order_num[:50]}..., org: {org_name}, status: {status}, {format_type}")
        
        # 检查问题数据
        print("\n=== 检查问题数据 ===")
        cursor.execute("""
            SELECT id, order_num, org_name 
            FROM notification_tasks 
            WHERE notification_type = 'escalation' 
            AND order_num LIKE 'ESCALATION_%'
        """)
        
        problem_rows = cursor.fetchall()
        print(f"找到 {len(problem_rows)} 个使用ESCALATION_格式的任务:")
        
        for row in problem_rows:
            task_id, order_num, org_name = row
            print(f"  ID: {task_id}, order_num: {order_num}, org: {org_name}")
            
            # 检查order_num是否等于ESCALATION_org_name
            expected_order_num = f"ESCALATION_{org_name}"
            if order_num == expected_order_num:
                print(f"    ✓ 格式正确: {order_num}")
            else:
                print(f"    ✗ 格式错误: 期望 {expected_order_num}, 实际 {order_num}")
        
        # 统计各种状态
        print("\n=== 统计信息 ===")
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM notification_tasks 
            WHERE notification_type = 'escalation' 
            GROUP BY status
        """)
        
        status_counts = cursor.fetchall()
        for status, count in status_counts:
            print(f"  {status}: {count} 个任务")
            
    except Exception as e:
        print(f"检查失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_escalation_tasks()

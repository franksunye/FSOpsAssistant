#!/usr/bin/env python3
"""
通知问题诊断脚本

用于诊断当前通知系统的具体问题
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any

def get_database_path() -> str:
    """获取数据库路径"""
    try:
        from fsoa.utils.config import get_config
        config = get_config()
        db_url = config.database_url
        if db_url.startswith('sqlite:///'):
            return db_url[10:]
        else:
            return 'fsoa.db'
    except:
        return 'fsoa.db'

def analyze_escalation_tasks_detailed(db_path: str) -> Dict[str, Any]:
    """详细分析升级任务"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("=== 升级任务详细分析 ===")
        
        # 查询所有升级任务
        cursor.execute("""
            SELECT id, order_num, org_name, status, created_at, sent_at, message
            FROM notification_tasks 
            WHERE notification_type = 'escalation'
            ORDER BY org_name, created_at DESC
        """)
        
        escalation_tasks = cursor.fetchall()
        
        print(f"总升级任务数: {len(escalation_tasks)}")
        
        # 按组织分组分析
        org_analysis = {}
        for task in escalation_tasks:
            task_id, order_num, org_name, status, created_at, sent_at, message = task
            
            if org_name not in org_analysis:
                org_analysis[org_name] = {
                    'tasks': [],
                    'pending_count': 0,
                    'sent_count': 0,
                    'old_format_count': 0,
                    'new_format_count': 0
                }
            
            task_info = {
                'id': task_id,
                'order_num': order_num,
                'status': status,
                'created_at': created_at,
                'sent_at': sent_at,
                'message_length': len(message) if message else 0,
                'is_new_format': order_num.startswith('ESCALATION_')
            }
            
            org_analysis[org_name]['tasks'].append(task_info)
            
            if status == 'pending':
                org_analysis[org_name]['pending_count'] += 1
            elif status == 'sent':
                org_analysis[org_name]['sent_count'] += 1
            
            if task_info['is_new_format']:
                org_analysis[org_name]['new_format_count'] += 1
            else:
                org_analysis[org_name]['old_format_count'] += 1
        
        # 输出分析结果
        for org_name, analysis in org_analysis.items():
            print(f"\n组织: {org_name}")
            print(f"  总任务数: {len(analysis['tasks'])}")
            print(f"  待处理: {analysis['pending_count']}")
            print(f"  已发送: {analysis['sent_count']}")
            print(f"  旧格式任务: {analysis['old_format_count']}")
            print(f"  新格式任务: {analysis['new_format_count']}")
            
            print("  任务详情:")
            for task in analysis['tasks']:
                format_type = "新格式" if task['is_new_format'] else "旧格式"
                print(f"    - ID={task['id']}, order_num={task['order_num'][:20]}..., "
                      f"status={task['status']}, {format_type}, "
                      f"消息长度={task['message_length']}")
        
        return org_analysis
        
    finally:
        conn.close()

def analyze_message_content(db_path: str, org_name: str = "北京虹象防水工程有限公司") -> None:
    """分析特定组织的消息内容"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print(f"\n=== 分析 {org_name} 的消息内容 ===")
        
        cursor.execute("""
            SELECT id, order_num, status, message, sent_at
            FROM notification_tasks 
            WHERE notification_type = 'escalation' AND org_name = ?
            ORDER BY created_at DESC
        """, (org_name,))
        
        tasks = cursor.fetchall()
        
        for i, task in enumerate(tasks, 1):
            task_id, order_num, status, message, sent_at = task
            
            print(f"\n任务 {i} (ID={task_id}):")
            print(f"  order_num: {order_num}")
            print(f"  status: {status}")
            print(f"  sent_at: {sent_at}")
            
            if message:
                lines = message.split('\n')
                print(f"  消息行数: {len(lines)}")
                
                # 查找工单数量行
                for line in lines:
                    if "需要升级处理的工单数" in line:
                        print(f"  工单数量行: {line}")
                        break
                
                # 查找截断行
                for line in lines:
                    if "还有" in line and "个工单需要处理" in line:
                        print(f"  截断行: {line}")
                        break
                
                # 统计实际显示的工单数
                order_count = 0
                for line in lines:
                    if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.')):
                        if "工单号：" in line:
                            order_count += 1
                
                print(f"  实际显示工单数: {order_count}")
            else:
                print("  消息内容为空")
        
    finally:
        conn.close()

def check_pending_tasks_execution_order(db_path: str) -> None:
    """检查待处理任务的执行顺序"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n=== 待处理任务执行顺序分析 ===")
        
        cursor.execute("""
            SELECT id, order_num, org_name, notification_type, created_at, due_time
            FROM notification_tasks 
            WHERE status = 'pending'
            ORDER BY due_time, created_at
        """)
        
        pending_tasks = cursor.fetchall()
        
        print(f"待处理任务总数: {len(pending_tasks)}")
        
        escalation_tasks = [t for t in pending_tasks if t[3] == 'escalation']
        print(f"待处理升级任务数: {len(escalation_tasks)}")
        
        if escalation_tasks:
            print("\n待处理升级任务:")
            for task in escalation_tasks:
                task_id, order_num, org_name, notification_type, created_at, due_time = task
                is_new_format = order_num.startswith('ESCALATION_')
                format_type = "新格式" if is_new_format else "旧格式"
                print(f"  ID={task_id}, org={org_name}, order_num={order_num[:30]}..., {format_type}")
        
        # 检查是否有同一组织的多个升级任务
        org_escalation_count = {}
        for task in escalation_tasks:
            org_name = task[2]
            org_escalation_count[org_name] = org_escalation_count.get(org_name, 0) + 1
        
        duplicate_orgs = {org: count for org, count in org_escalation_count.items() if count > 1}
        if duplicate_orgs:
            print(f"\n⚠️  有多个待处理升级任务的组织:")
            for org, count in duplicate_orgs.items():
                print(f"  {org}: {count} 个任务")
        else:
            print("\n✅ 没有组织有多个待处理升级任务")
        
    finally:
        conn.close()

def simulate_notification_execution(db_path: str) -> None:
    """模拟通知执行过程"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n=== 模拟通知执行过程 ===")
        
        # 获取待处理任务
        cursor.execute("""
            SELECT id, order_num, org_name, notification_type
            FROM notification_tasks 
            WHERE status = 'pending'
            ORDER BY due_time, created_at
        """)
        
        pending_tasks = cursor.fetchall()
        
        # 按组织分组
        org_tasks = {}
        for task in pending_tasks:
            task_id, order_num, org_name, notification_type = task
            if org_name not in org_tasks:
                org_tasks[org_name] = []
            org_tasks[org_name].append({
                'id': task_id,
                'order_num': order_num,
                'notification_type': notification_type
            })
        
        print("按组织分组的待处理任务:")
        for org_name, tasks in org_tasks.items():
            print(f"\n组织: {org_name}")
            
            escalation_tasks = [t for t in tasks if t['notification_type'] == 'escalation']
            other_tasks = [t for t in tasks if t['notification_type'] != 'escalation']
            
            print(f"  升级任务: {len(escalation_tasks)}")
            for task in escalation_tasks:
                is_new_format = task['order_num'].startswith('ESCALATION_')
                format_type = "新格式" if is_new_format else "旧格式"
                print(f"    - ID={task['id']}, {format_type}, order_num={task['order_num'][:30]}...")
            
            print(f"  其他任务: {len(other_tasks)}")
            
            # 预测执行结果
            if len(escalation_tasks) > 1:
                print(f"  ⚠️  预测: 将发送 {len(escalation_tasks)} 个升级通知")
            elif len(escalation_tasks) == 1:
                print(f"  ✅ 预测: 将发送 1 个升级通知")
        
    finally:
        conn.close()

def main():
    """主函数"""
    print("=== 通知问题诊断脚本 ===")
    print(f"执行时间: {datetime.now()}")
    
    db_path = get_database_path()
    print(f"数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        return
    
    try:
        # 1. 详细分析升级任务
        analyze_escalation_tasks_detailed(db_path)
        
        # 2. 分析特定组织的消息内容
        analyze_message_content(db_path)
        
        # 3. 检查待处理任务的执行顺序
        check_pending_tasks_execution_order(db_path)
        
        # 4. 模拟通知执行过程
        simulate_notification_execution(db_path)
        
    except Exception as e:
        print(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

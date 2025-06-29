#!/usr/bin/env python3
"""
清理重复升级任务脚本

用于清理修复前创建的重复升级任务，确保每个组织只有一个升级任务
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import sqlite3
from datetime import datetime
from typing import List, Dict, Any

def get_database_path() -> str:
    """获取数据库路径"""
    # 尝试从配置中获取数据库路径
    try:
        from fsoa.utils.config import get_config
        config = get_config()
        db_url = config.database_url
        if db_url.startswith('sqlite:///'):
            return db_url[10:]  # 移除 'sqlite:///' 前缀
        else:
            return 'fsoa.db'  # 默认路径
    except:
        return 'fsoa.db'  # 默认路径

def analyze_escalation_tasks(db_path: str) -> Dict[str, Any]:
    """分析当前的升级任务情况"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 查询所有升级任务
        cursor.execute("""
            SELECT id, order_num, org_name, status, created_at, sent_at
            FROM notification_tasks 
            WHERE notification_type = 'escalation'
            ORDER BY org_name, created_at
        """)
        
        escalation_tasks = cursor.fetchall()
        
        # 按组织分组
        org_tasks = {}
        for task in escalation_tasks:
            task_id, order_num, org_name, status, created_at, sent_at = task
            if org_name not in org_tasks:
                org_tasks[org_name] = []
            org_tasks[org_name].append({
                'id': task_id,
                'order_num': order_num,
                'org_name': org_name,
                'status': status,
                'created_at': created_at,
                'sent_at': sent_at
            })
        
        # 统计信息
        total_tasks = len(escalation_tasks)
        orgs_with_multiple = {org: tasks for org, tasks in org_tasks.items() if len(tasks) > 1}
        
        analysis = {
            'total_escalation_tasks': total_tasks,
            'total_orgs': len(org_tasks),
            'orgs_with_multiple_tasks': len(orgs_with_multiple),
            'org_tasks': org_tasks,
            'duplicate_orgs': orgs_with_multiple
        }
        
        return analysis
        
    finally:
        conn.close()

def cleanup_duplicate_escalation_tasks(db_path: str, dry_run: bool = True) -> Dict[str, Any]:
    """清理重复的升级任务"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 开始事务
        cursor.execute("BEGIN TRANSACTION")
        
        # 查找重复的升级任务
        cursor.execute("""
            SELECT org_name, COUNT(*) as task_count
            FROM notification_tasks 
            WHERE notification_type = 'escalation'
            GROUP BY org_name
            HAVING COUNT(*) > 1
        """)
        
        duplicate_orgs = cursor.fetchall()
        
        cleanup_stats = {
            'duplicate_orgs_found': len(duplicate_orgs),
            'tasks_to_delete': 0,
            'tasks_deleted': 0,
            'errors': []
        }
        
        for org_name, task_count in duplicate_orgs:
            print(f"处理组织: {org_name} (有 {task_count} 个升级任务)")
            
            # 获取该组织的所有升级任务，按创建时间排序
            cursor.execute("""
                SELECT id, order_num, status, created_at, sent_at
                FROM notification_tasks 
                WHERE notification_type = 'escalation' AND org_name = ?
                ORDER BY created_at DESC
            """, (org_name,))
            
            org_tasks = cursor.fetchall()
            
            # 保留最新的任务，删除其他的
            if len(org_tasks) > 1:
                keep_task = org_tasks[0]  # 最新的任务
                delete_tasks = org_tasks[1:]  # 其他任务
                
                print(f"  保留任务: ID={keep_task[0]}, order_num={keep_task[1]}")
                
                for task in delete_tasks:
                    task_id, order_num, status, created_at, sent_at = task
                    print(f"  {'[DRY RUN] ' if dry_run else ''}删除任务: ID={task_id}, order_num={order_num}, status={status}")
                    
                    cleanup_stats['tasks_to_delete'] += 1
                    
                    if not dry_run:
                        try:
                            cursor.execute("DELETE FROM notification_tasks WHERE id = ?", (task_id,))
                            cleanup_stats['tasks_deleted'] += 1
                        except Exception as e:
                            error_msg = f"删除任务 {task_id} 失败: {e}"
                            print(f"  错误: {error_msg}")
                            cleanup_stats['errors'].append(error_msg)
        
        if dry_run:
            print("\n=== DRY RUN 模式 - 未实际删除数据 ===")
            cursor.execute("ROLLBACK")
        else:
            print("\n=== 提交更改 ===")
            cursor.execute("COMMIT")
        
        return cleanup_stats
        
    except Exception as e:
        cursor.execute("ROLLBACK")
        raise e
    finally:
        conn.close()

def create_org_level_escalation_tasks(db_path: str, dry_run: bool = True) -> Dict[str, Any]:
    """为需要升级的组织创建新的组织级别升级任务"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN TRANSACTION")
        
        # 查找所有需要升级但没有升级任务的组织
        # 这里需要从实际的商机数据中分析，但由于我们没有直接访问Metabase，
        # 我们先创建一个占位符逻辑
        
        creation_stats = {
            'orgs_checked': 0,
            'tasks_to_create': 0,
            'tasks_created': 0,
            'errors': []
        }
        
        # 获取当前有升级任务的组织
        cursor.execute("""
            SELECT DISTINCT org_name 
            FROM notification_tasks 
            WHERE notification_type = 'escalation'
        """)
        
        existing_orgs = {row[0] for row in cursor.fetchall()}
        creation_stats['orgs_checked'] = len(existing_orgs)
        
        print(f"当前有升级任务的组织: {existing_orgs}")
        
        # 为现有的升级任务更新order_num格式
        for org_name in existing_orgs:
            new_order_num = f"ESCALATION_{org_name}"
            
            cursor.execute("""
                SELECT id, order_num FROM notification_tasks 
                WHERE notification_type = 'escalation' AND org_name = ?
                LIMIT 1
            """, (org_name,))
            
            task = cursor.fetchone()
            if task:
                task_id, current_order_num = task
                if not current_order_num.startswith("ESCALATION_"):
                    print(f"  {'[DRY RUN] ' if dry_run else ''}更新任务 {task_id}: {current_order_num} -> {new_order_num}")
                    creation_stats['tasks_to_create'] += 1
                    
                    if not dry_run:
                        try:
                            cursor.execute("""
                                UPDATE notification_tasks 
                                SET order_num = ? 
                                WHERE id = ?
                            """, (new_order_num, task_id))
                            creation_stats['tasks_created'] += 1
                        except Exception as e:
                            error_msg = f"更新任务 {task_id} 失败: {e}"
                            print(f"  错误: {error_msg}")
                            creation_stats['errors'].append(error_msg)
        
        if dry_run:
            print("\n=== DRY RUN 模式 - 未实际更新数据 ===")
            cursor.execute("ROLLBACK")
        else:
            print("\n=== 提交更改 ===")
            cursor.execute("COMMIT")
        
        return creation_stats
        
    except Exception as e:
        cursor.execute("ROLLBACK")
        raise e
    finally:
        conn.close()

def main():
    """主函数"""
    print("=== 升级任务清理脚本 ===")
    print(f"执行时间: {datetime.now()}")
    
    # 获取数据库路径
    db_path = get_database_path()
    print(f"数据库路径: {db_path}")
    
    # 检查数据库是否存在
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        return
    
    try:
        # 1. 分析当前情况
        print("\n=== 1. 分析当前升级任务情况 ===")
        analysis = analyze_escalation_tasks(db_path)
        
        print(f"总升级任务数: {analysis['total_escalation_tasks']}")
        print(f"涉及组织数: {analysis['total_orgs']}")
        print(f"有重复任务的组织数: {analysis['orgs_with_multiple_tasks']}")
        
        if analysis['duplicate_orgs']:
            print("\n重复任务的组织:")
            for org_name, tasks in analysis['duplicate_orgs'].items():
                print(f"  {org_name}: {len(tasks)} 个任务")
                for task in tasks:
                    print(f"    - ID={task['id']}, order_num={task['order_num']}, status={task['status']}")
        
        # 2. 清理重复任务 (DRY RUN)
        print("\n=== 2. 清理重复升级任务 (DRY RUN) ===")
        cleanup_stats = cleanup_duplicate_escalation_tasks(db_path, dry_run=True)
        
        print(f"发现重复组织: {cleanup_stats['duplicate_orgs_found']}")
        print(f"计划删除任务: {cleanup_stats['tasks_to_delete']}")
        
        # 3. 更新任务格式 (DRY RUN)
        print("\n=== 3. 更新任务格式 (DRY RUN) ===")
        creation_stats = create_org_level_escalation_tasks(db_path, dry_run=True)
        
        print(f"检查组织数: {creation_stats['orgs_checked']}")
        print(f"计划更新任务: {creation_stats['tasks_to_create']}")
        
        # 4. 询问是否执行实际清理
        if cleanup_stats['tasks_to_delete'] > 0 or creation_stats['tasks_to_create'] > 0:
            print("\n=== 确认执行 ===")
            response = input("是否执行实际的清理和更新操作? (yes/no): ")
            
            if response.lower() in ['yes', 'y']:
                print("\n=== 执行实际清理 ===")
                
                # 执行清理
                if cleanup_stats['tasks_to_delete'] > 0:
                    print("清理重复任务...")
                    cleanup_duplicate_escalation_tasks(db_path, dry_run=False)
                
                # 执行更新
                if creation_stats['tasks_to_create'] > 0:
                    print("更新任务格式...")
                    create_org_level_escalation_tasks(db_path, dry_run=False)
                
                print("✅ 清理完成!")
            else:
                print("❌ 取消执行")
        else:
            print("✅ 无需清理")
    
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

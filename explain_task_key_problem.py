#!/usr/bin/env python3
"""
演示task_key的必要性和当前数据模型的问题
"""

import sqlite3
from pathlib import Path

def demonstrate_problem():
    """演示当前数据模型的问题"""
    
    print("=== 当前数据模型问题演示 ===\n")
    
    # 连接数据库
    db_path = Path("fsoa.db")
    if not db_path.exists():
        print("数据库文件不存在")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 1. 查看当前升级任务的数据
        print("1. 当前升级任务的数据结构问题:")
        cursor.execute("""
            SELECT id, order_num, org_name, notification_type 
            FROM notification_tasks 
            WHERE notification_type = 'escalation' 
            LIMIT 5
        """)
        
        rows = cursor.fetchall()
        for row in rows:
            task_id, order_num, org_name, notification_type = row
            print(f"   ID: {task_id}")
            print(f"   order_num: {order_num}")
            print(f"   org_name: {org_name}")
            print(f"   notification_type: {notification_type}")
            print(f"   问题: order_num字段存储的是'ESCALATION_组织名'而不是真实工单号")
            print()
        
        # 2. 演示查询问题
        print("2. 查询问题演示:")
        print("   问题: 如何区分同一组织的不同升级任务？")
        print("   - 按notification_type='escalation'查询会返回所有升级任务")
        print("   - 按order_num查询需要知道'ESCALATION_组织名'的确切格式")
        print("   - 无法直接通过工单号查询升级任务")
        print()
        
        # 3. 演示语义混乱
        print("3. 语义混乱问题:")
        print("   order_num字段的含义不一致:")
        
        cursor.execute("""
            SELECT notification_type, order_num, 
                   CASE 
                       WHEN order_num LIKE 'ESCALATION_%' THEN '组织标识符'
                       ELSE '真实工单号'
                   END as order_num_type
            FROM notification_tasks 
            GROUP BY notification_type, order_num_type
        """)
        
        type_rows = cursor.fetchall()
        for row in type_rows:
            notification_type, example_order_num, order_num_type = row
            print(f"   {notification_type} 类型: order_num存储 {order_num_type}")
            print(f"     示例: {example_order_num[:50]}...")
        print()
        
        # 4. 演示task_key解决方案
        print("4. task_key解决方案:")
        print("   引入task_key字段后的数据结构:")
        print("   - task_key: 任务的唯一标识符")
        print("     * 提醒任务: task_key = 工单号 (如: 'GD2025064176')")
        print("     * 升级任务: task_key = 'ESCALATION_组织名'")
        print("   - order_num: 关联的工单号")
        print("     * 提醒任务: order_num = 工单号")
        print("     * 升级任务: order_num = NULL (因为升级任务聚合多个工单)")
        print()
        
        # 5. 演示查询优势
        print("5. task_key的查询优势:")
        print("   - 唯一标识: 每个任务都有唯一的task_key")
        print("   - 语义清晰: order_num只存储真实工单号或NULL")
        print("   - 查询简单: 直接通过task_key查询特定任务")
        print("   - 去重容易: 基于task_key + notification_type去重")
        print()
        
        # 6. 演示业务逻辑
        print("6. 业务逻辑示例:")
        print("   升级任务创建逻辑:")
        print("   ```python")
        print("   # 当前错误的方式")
        print("   order_num = f'ESCALATION_{org_name}'  # 污染了order_num字段")
        print("   ")
        print("   # 修复后的方式")
        print("   task_key = f'ESCALATION_{org_name}'   # 专门的任务标识")
        print("   order_num = None                      # 升级任务不关联具体工单")
        print("   ```")
        print()
        
        print("=== 总结 ===")
        print("task_key的作用:")
        print("1. 解决语义混乱: order_num字段保持纯净，只存储真实工单号")
        print("2. 统一标识: 所有任务都有唯一的task_key标识符")
        print("3. 简化查询: 基于task_key的查询更直观和可靠")
        print("4. 支持扩展: 未来可以支持更复杂的任务类型")
        print()
        print("notification_type vs task_key:")
        print("- notification_type: 任务类型分类 (reminder/escalation)")
        print("- task_key: 任务实例标识 (具体的某个任务)")
        print("- 两者配合使用才能精确定位和去重任务")
        
    except Exception as e:
        print(f"演示失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    demonstrate_problem()

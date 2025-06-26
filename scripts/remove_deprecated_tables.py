#!/usr/bin/env python3
"""
数据库清理脚本：删除废弃的表

删除以下废弃表：
- notifications_deprecated
- tasks_deprecated  
- agent_executions_deprecated

这些表已被新的系统替代：
- notifications_deprecated -> notification_tasks
- tasks_deprecated -> 直接使用商机数据
- agent_executions_deprecated -> agent_runs + agent_history
"""

import sys
import os
from pathlib import Path
import sqlite3
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def backup_deprecated_data():
    """备份废弃表的数据"""
    db_path = project_root / "fsoa.db"
    backup_path = project_root / f"deprecated_tables_backup_{int(datetime.now().timestamp())}.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        backup_conn = sqlite3.connect(str(backup_path))
        
        # 备份废弃表的数据
        deprecated_tables = [
            'notifications_deprecated',
            'tasks_deprecated', 
            'agent_executions_deprecated'
        ]
        
        backed_up_tables = []
        
        for table_name in deprecated_tables:
            try:
                # 检查表是否存在
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                
                if cursor.fetchone():
                    # 获取表结构
                    cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table_name}'")
                    create_sql = cursor.fetchone()[0]
                    
                    # 在备份数据库中创建表
                    backup_conn.execute(create_sql)
                    
                    # 复制数据
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    
                    if rows:
                        # 获取列数
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        placeholders = ','.join(['?' for _ in columns])
                        
                        backup_conn.executemany(
                            f"INSERT INTO {table_name} VALUES ({placeholders})", 
                            rows
                        )
                        
                        backed_up_tables.append(f"{table_name} ({len(rows)} 条记录)")
                        print(f"✅ 备份表 {table_name}: {len(rows)} 条记录")
                    else:
                        backed_up_tables.append(f"{table_name} (空表)")
                        print(f"ℹ️  备份表 {table_name}: 空表")
                        
            except Exception as e:
                print(f"⚠️  备份表 {table_name} 失败: {e}")
        
        backup_conn.commit()
        backup_conn.close()
        conn.close()
        
        if backed_up_tables:
            print(f"\n📦 数据备份完成: {backup_path}")
            print("备份内容:")
            for table_info in backed_up_tables:
                print(f"  - {table_info}")
            return backup_path
        else:
            # 如果没有数据需要备份，删除空的备份文件
            os.remove(backup_path)
            print("ℹ️  没有废弃表数据需要备份")
            return None
            
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return None


def drop_deprecated_tables():
    """删除废弃的表"""
    db_path = project_root / "fsoa.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 要删除的废弃表
        deprecated_tables = [
            'notifications_deprecated',
            'tasks_deprecated',
            'agent_executions_deprecated'
        ]
        
        dropped_tables = []
        
        for table_name in deprecated_tables:
            try:
                # 检查表是否存在
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                
                if cursor.fetchone():
                    # 删除表
                    cursor.execute(f"DROP TABLE {table_name}")
                    dropped_tables.append(table_name)
                    print(f"🗑️  删除表: {table_name}")
                else:
                    print(f"ℹ️  表不存在: {table_name}")
                    
            except Exception as e:
                print(f"❌ 删除表 {table_name} 失败: {e}")
        
        conn.commit()
        conn.close()
        
        return dropped_tables
        
    except Exception as e:
        print(f"❌ 删除表失败: {e}")
        return []


def verify_cleanup():
    """验证清理结果"""
    db_path = project_root / "fsoa.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查废弃表是否已删除
        deprecated_tables = [
            'notifications_deprecated',
            'tasks_deprecated',
            'agent_executions_deprecated'
        ]
        
        remaining_tables = []
        
        for table_name in deprecated_tables:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            
            if cursor.fetchone():
                remaining_tables.append(table_name)
        
        # 检查新表是否存在
        new_tables = [
            'notification_tasks',
            'agent_runs',
            'agent_history'
        ]
        
        existing_new_tables = []
        
        for table_name in new_tables:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            
            if cursor.fetchone():
                existing_new_tables.append(table_name)
        
        conn.close()
        
        print("\n🔍 清理验证结果:")
        
        if remaining_tables:
            print(f"⚠️  仍存在的废弃表: {', '.join(remaining_tables)}")
        else:
            print("✅ 所有废弃表已删除")
        
        print(f"✅ 新表系统: {', '.join(existing_new_tables)}")
        
        return len(remaining_tables) == 0
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def main():
    """主函数"""
    print("🧹 开始清理废弃的数据库表...")
    print("=" * 50)
    
    try:
        # 1. 备份废弃表数据
        print("\n📦 步骤 1: 备份废弃表数据")
        backup_path = backup_deprecated_data()
        
        # 2. 删除废弃表
        print("\n🗑️  步骤 2: 删除废弃表")
        dropped_tables = drop_deprecated_tables()
        
        # 3. 验证清理结果
        print("\n🔍 步骤 3: 验证清理结果")
        success = verify_cleanup()
        
        # 4. 总结
        print("\n" + "=" * 50)
        if success:
            print("🎉 废弃表清理完成！")
            print("\n✅ 清理内容:")
            for table in dropped_tables:
                print(f"  - {table}")
            
            if backup_path:
                print(f"\n💾 备份文件: {backup_path}")
            
            print("\n📌 系统现在使用:")
            print("  - notification_tasks (替代 notifications_deprecated)")
            print("  - 直接使用商机数据 (替代 tasks_deprecated)")
            print("  - agent_runs + agent_history (替代 agent_executions_deprecated)")
            
        else:
            print("⚠️  清理可能不完整，请检查上述错误信息")
            
    except Exception as e:
        print(f"\n❌ 清理过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

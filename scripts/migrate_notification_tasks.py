#!/usr/bin/env python3
"""
数据库迁移脚本：为notification_tasks表添加新字段

新增字段：
- max_retry_count: 最大重试次数
- cooldown_hours: 冷静时间（小时）
- last_sent_at: 最后发送时间
"""

import sys
import os
from pathlib import Path
import sqlite3

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def migrate_notification_tasks_table():
    """迁移notification_tasks表"""
    db_path = project_root / "fsoa.db"

    try:
        # 使用sqlite3直接连接数据库
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='notification_tasks'
        """)

        if not cursor.fetchone():
            print("notification_tasks table does not exist, skipping migration")
            conn.close()
            return True

        # 检查新字段是否已存在
        cursor.execute("PRAGMA table_info(notification_tasks)")
        columns = [row[1] for row in cursor.fetchall()]

        migrations_needed = []

        if 'max_retry_count' not in columns:
            migrations_needed.append("ALTER TABLE notification_tasks ADD COLUMN max_retry_count INTEGER DEFAULT 5")

        if 'cooldown_hours' not in columns:
            migrations_needed.append("ALTER TABLE notification_tasks ADD COLUMN cooldown_hours REAL DEFAULT 2.0")

        if 'last_sent_at' not in columns:
            migrations_needed.append("ALTER TABLE notification_tasks ADD COLUMN last_sent_at DATETIME")

        # 执行迁移
        if migrations_needed:
            print(f"Executing {len(migrations_needed)} migrations...")

            for migration_sql in migrations_needed:
                print(f"Executing: {migration_sql}")
                cursor.execute(migration_sql)

            conn.commit()
            print("Migration completed successfully")
        else:
            print("No migrations needed, all columns already exist")

        conn.close()
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False


def main():
    """主函数"""
    print("🔄 开始数据库迁移...")
    
    try:
        success = migrate_notification_tasks_table()
        
        if success:
            print("✅ 数据库迁移完成")
        else:
            print("❌ 数据库迁移失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 迁移过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

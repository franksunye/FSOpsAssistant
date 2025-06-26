#!/usr/bin/env python3
"""
时区迁移脚本

将现有数据库中的UTC时间转换为中国时区时间
注意：这个脚本假设现有数据是UTC时间，将其转换为中国时间
"""

import sys
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 中国时区 (UTC+8)
CHINA_TZ = timezone(timedelta(hours=8))


def convert_utc_to_china_string(utc_time_str):
    """
    将UTC时间字符串转换为中国时间字符串
    
    Args:
        utc_time_str: UTC时间字符串，格式如 "2025-06-26 10:00:00"
        
    Returns:
        中国时间字符串
    """
    if not utc_time_str:
        return utc_time_str
    
    try:
        # 解析UTC时间
        utc_dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        
        # 如果没有时区信息，假设是UTC
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        
        # 转换为中国时区
        china_dt = utc_dt.astimezone(CHINA_TZ)
        
        # 返回naive datetime字符串（不带时区信息）
        return china_dt.replace(tzinfo=None).isoformat(' ')
        
    except Exception as e:
        print(f"⚠️ 时间转换失败: {utc_time_str} -> {e}")
        return utc_time_str


def migrate_table_timestamps(cursor, table_name, time_columns):
    """
    迁移表中的时间戳字段
    
    Args:
        cursor: 数据库游标
        table_name: 表名
        time_columns: 时间字段列表
    """
    try:
        # 检查表是否存在
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            print(f"⚠️ 表 {table_name} 不存在，跳过")
            return 0
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        existing_columns = [col[1] for col in columns_info]
        
        # 过滤出实际存在的时间字段
        valid_time_columns = [col for col in time_columns if col in existing_columns]
        
        if not valid_time_columns:
            print(f"⚠️ 表 {table_name} 中没有找到时间字段，跳过")
            return 0
        
        # 获取所有记录
        cursor.execute(f"SELECT rowid, {', '.join(valid_time_columns)} FROM {table_name}")
        records = cursor.fetchall()
        
        if not records:
            print(f"✅ 表 {table_name} 为空，无需迁移")
            return 0
        
        updated_count = 0
        
        for record in records:
            rowid = record[0]
            time_values = record[1:]
            
            # 转换时间值
            converted_values = []
            has_changes = False
            
            for i, time_value in enumerate(time_values):
                if time_value:
                    converted_value = convert_utc_to_china_string(time_value)
                    if converted_value != time_value:
                        has_changes = True
                    converted_values.append(converted_value)
                else:
                    converted_values.append(time_value)
            
            # 如果有变化，更新记录
            if has_changes:
                set_clauses = []
                for i, col in enumerate(valid_time_columns):
                    set_clauses.append(f"{col} = ?")
                
                update_sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE rowid = ?"
                cursor.execute(update_sql, converted_values + [rowid])
                updated_count += 1
        
        print(f"✅ 表 {table_name}: 更新了 {updated_count} 条记录")
        return updated_count
        
    except Exception as e:
        print(f"❌ 迁移表 {table_name} 失败: {e}")
        return 0


def migrate_database_timezone():
    """迁移数据库时区"""
    db_path = project_root / "fsoa.db"
    
    if not db_path.exists():
        print("⚠️ 数据库文件不存在，无需迁移")
        return True
    
    try:
        # 备份数据库
        backup_path = project_root / f"fsoa_backup_before_timezone_migration_{int(datetime.now().timestamp())}.db"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"📦 已备份数据库到: {backup_path}")
        
        # 连接数据库
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("\n🔄 开始时区迁移...")
        
        # 定义需要迁移的表和字段
        tables_to_migrate = {
            'agent_runs': ['trigger_time', 'created_at', 'updated_at'],
            'agent_history': ['timestamp', 'created_at'],
            'notification_tasks': ['due_time', 'sent_at', 'last_sent_at', 'created_at', 'updated_at'],
            'opportunity_cache': ['create_time', 'last_updated', 'created_at', 'updated_at'],
            'system_config': ['created_at']
        }
        
        total_updated = 0
        
        for table_name, time_columns in tables_to_migrate.items():
            updated_count = migrate_table_timestamps(cursor, table_name, time_columns)
            total_updated += updated_count
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print(f"\n🎉 时区迁移完成！")
        print(f"📊 总计更新了 {total_updated} 条记录")
        print(f"💾 备份文件: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 时区迁移失败: {e}")
        return False


def verify_timezone_migration():
    """验证时区迁移结果"""
    db_path = project_root / "fsoa.db"
    
    if not db_path.exists():
        print("⚠️ 数据库文件不存在")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("\n🔍 验证时区迁移结果...")
        
        # 检查一些示例记录
        tables_to_check = [
            ('agent_runs', 'trigger_time'),
            ('notification_tasks', 'created_at'),
            ('opportunity_cache', 'create_time')
        ]
        
        for table_name, time_column in tables_to_check:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                continue
            
            cursor.execute(f"SELECT {time_column} FROM {table_name} WHERE {time_column} IS NOT NULL LIMIT 3")
            records = cursor.fetchall()
            
            if records:
                print(f"\n📋 表 {table_name}.{time_column} 示例:")
                for i, record in enumerate(records, 1):
                    time_str = record[0]
                    print(f"  {i}. {time_str}")
                    
                    # 尝试解析时间
                    try:
                        dt = datetime.fromisoformat(time_str)
                        print(f"     解析成功: {dt}")
                    except Exception as e:
                        print(f"     解析失败: {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def main():
    """主函数"""
    print("🕒 FSOA 时区迁移工具")
    print("=" * 50)
    print("将现有数据库中的UTC时间转换为中国时区时间")
    print("=" * 50)
    
    # 确认操作
    print("\n⚠️ 注意事项:")
    print("1. 此操作会修改数据库中的时间数据")
    print("2. 操作前会自动备份数据库")
    print("3. 假设现有时间数据是UTC时间")
    print("4. 转换后的时间将是中国时区时间")
    
    confirm = input("\n是否继续时区迁移? (输入 'yes' 确认): ")
    if confirm.lower() != 'yes':
        print("❌ 操作已取消")
        return
    
    try:
        # 执行迁移
        success = migrate_database_timezone()
        
        if success:
            # 验证迁移结果
            verify_timezone_migration()
            
            print("\n" + "=" * 50)
            print("🎉 时区迁移完成！")
            print("✅ 所有时间数据现在都是中国时区")
            print("✅ 新的时间记录将自动使用中国时区")
            print("=" * 50)
        else:
            print("\n❌ 时区迁移失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 迁移过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

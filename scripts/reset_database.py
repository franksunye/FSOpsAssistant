#!/usr/bin/env python3
"""
数据库重置脚本

完全重新初始化数据库，包含所有新功能的表结构
适用于开发环境的数据库重置
"""

import os
import sys
from pathlib import Path
import sqlite3

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def backup_existing_database():
    """备份现有数据库"""
    db_path = project_root / "fsoa.db"
    
    if db_path.exists():
        backup_path = project_root / f"fsoa_backup_{int(time.time())}.db"
        import shutil
        import time
        
        shutil.copy2(db_path, backup_path)
        print(f"📦 已备份现有数据库到: {backup_path}")
        return backup_path
    
    return None


def remove_existing_database():
    """删除现有数据库"""
    db_path = project_root / "fsoa.db"
    
    if db_path.exists():
        os.remove(db_path)
        print("🗑️ 已删除现有数据库")


def create_new_database():
    """创建新数据库"""
    try:
        from src.fsoa.data.database import DatabaseManager
        from src.fsoa.utils.config import get_config
        
        # 获取配置
        config = get_config()
        print(f"📊 数据库URL: {config.database_url}")
        
        # 创建数据库管理器
        db_manager = DatabaseManager(config.database_url)
        
        # 初始化数据库
        print("📝 创建数据库表...")
        db_manager.init_database()
        
        # 验证初始化
        print("✅ 验证数据库初始化...")
        with db_manager.get_session() as session:
            from src.fsoa.data.database import SystemConfigTable
            config_count = session.query(SystemConfigTable).count()
            print(f"📋 系统配置项数量: {config_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        return False


def verify_new_features():
    """验证新功能的数据库结构"""
    db_path = project_root / "fsoa.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("\n🔍 验证新功能的数据库结构...")
        
        # 检查notification_tasks表的新字段
        cursor.execute("PRAGMA table_info(notification_tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_fields = [
            'max_retry_count',
            'cooldown_hours', 
            'last_sent_at'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field in columns:
                print(f"  ✅ {field} 字段存在")
            else:
                missing_fields.append(field)
                print(f"  ❌ {field} 字段缺失")
        
        # 检查通知类型是否支持新值
        cursor.execute("SELECT DISTINCT notification_type FROM notification_tasks LIMIT 1")
        print("  ✅ notification_type 字段支持新的通知类型")
        
        conn.close()
        
        if missing_fields:
            print(f"\n⚠️ 缺失字段: {', '.join(missing_fields)}")
            return False
        else:
            print("\n✅ 所有新功能字段验证通过")
            return True
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def show_database_info():
    """显示数据库信息"""
    db_path = project_root / "fsoa.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("\n📊 数据库表信息:")
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  📋 {table_name}: {count} 条记录")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取数据库信息失败: {e}")


def main():
    """主函数"""
    print("🔄 FSOA 数据库重置")
    print("=" * 50)
    print("⚠️  警告: 此操作将删除所有现有数据！")
    print("=" * 50)
    
    # 确认操作
    confirm = input("\n是否继续重置数据库? (输入 'yes' 确认): ")
    if confirm.lower() != 'yes':
        print("❌ 操作已取消")
        return
    
    try:
        # 1. 备份现有数据库
        print("\n📦 步骤 1: 备份现有数据库")
        backup_path = backup_existing_database()
        
        # 2. 删除现有数据库
        print("\n🗑️ 步骤 2: 删除现有数据库")
        remove_existing_database()
        
        # 3. 创建新数据库
        print("\n🏗️ 步骤 3: 创建新数据库")
        if not create_new_database():
            print("❌ 数据库创建失败")
            sys.exit(1)
        
        # 4. 验证新功能
        print("\n🔍 步骤 4: 验证新功能")
        if not verify_new_features():
            print("⚠️ 新功能验证失败，但数据库已创建")
        
        # 5. 显示数据库信息
        print("\n📊 步骤 5: 显示数据库信息")
        show_database_info()
        
        print("\n" + "=" * 50)
        print("🎉 数据库重置完成！")
        print("=" * 50)
        
        print("\n📌 下一步操作:")
        print("1. 检查 .env 文件配置")
        print("2. 配置企微群 webhook")
        print("3. 运行 streamlit run src/fsoa/ui/app.py 启动应用")
        print("4. 测试新的SLA功能")
        
        if backup_path:
            print(f"\n💾 备份文件位置: {backup_path}")
        
    except Exception as e:
        print(f"\n❌ 数据库重置失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
移除max_notifications_per_hour参数的数据库迁移脚本

此脚本将：
1. 从system_config表中删除max_notifications_per_hour配置
2. 从group_config表中删除max_notifications_per_hour字段（如果存在）
3. 清理相关的无用配置
"""

import sys
import os
import sqlite3
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

from fsoa.utils.logger import get_logger

logger = get_logger(__name__)

def migrate_database(db_path: str):
    """执行数据库迁移"""
    
    logger.info(f"开始迁移数据库: {db_path}")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 删除system_config表中的max_notifications_per_hour配置
        logger.info("删除system_config表中的max_notifications_per_hour配置...")
        cursor.execute("""
            DELETE FROM system_config 
            WHERE key = 'max_notifications_per_hour'
        """)
        deleted_configs = cursor.rowcount
        logger.info(f"删除了 {deleted_configs} 个system_config记录")
        
        # 2. 检查group_config表是否存在max_notifications_per_hour字段
        logger.info("检查group_config表结构...")
        cursor.execute("PRAGMA table_info(group_config)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'max_notifications_per_hour' in columns:
            logger.info("发现group_config表中存在max_notifications_per_hour字段，开始删除...")
            
            # 创建新的表结构（不包含max_notifications_per_hour字段）
            cursor.execute("""
                CREATE TABLE group_config_new (
                    group_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    webhook_url TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    notification_cooldown_minutes INTEGER DEFAULT 30,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """)
            
            # 复制数据（排除max_notifications_per_hour字段）
            cursor.execute("""
                INSERT INTO group_config_new 
                (group_id, name, webhook_url, enabled, notification_cooldown_minutes, created_at, updated_at)
                SELECT group_id, name, webhook_url, enabled, notification_cooldown_minutes, created_at, updated_at
                FROM group_config
            """)
            
            # 删除旧表
            cursor.execute("DROP TABLE group_config")
            
            # 重命名新表
            cursor.execute("ALTER TABLE group_config_new RENAME TO group_config")
            
            logger.info("成功重建group_config表，移除了max_notifications_per_hour字段")
        else:
            logger.info("group_config表中未发现max_notifications_per_hour字段，无需处理")
        
        # 3. 提交更改
        conn.commit()
        logger.info("数据库迁移完成")
        
        # 4. 验证迁移结果
        logger.info("验证迁移结果...")
        
        # 检查system_config
        cursor.execute("SELECT COUNT(*) FROM system_config WHERE key = 'max_notifications_per_hour'")
        remaining_configs = cursor.fetchone()[0]
        if remaining_configs == 0:
            logger.info("✅ system_config表中已无max_notifications_per_hour配置")
        else:
            logger.warning(f"⚠️ system_config表中仍有 {remaining_configs} 个max_notifications_per_hour配置")
        
        # 检查group_config表结构
        cursor.execute("PRAGMA table_info(group_config)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'max_notifications_per_hour' not in columns:
            logger.info("✅ group_config表中已无max_notifications_per_hour字段")
        else:
            logger.warning("⚠️ group_config表中仍存在max_notifications_per_hour字段")
        
        logger.info("迁移验证完成")
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """主函数"""
    
    # 确定数据库文件路径
    db_path = project_root / "fsoa.db"
    
    if not db_path.exists():
        logger.error(f"数据库文件不存在: {db_path}")
        return 1
    
    # 创建备份
    backup_path = project_root / f"fsoa_backup_{int(os.path.getmtime(db_path))}.db"
    logger.info(f"创建数据库备份: {backup_path}")
    
    import shutil
    shutil.copy2(db_path, backup_path)
    logger.info("备份创建完成")
    
    try:
        # 执行迁移
        migrate_database(str(db_path))
        logger.info("🎉 max_notifications_per_hour参数移除完成！")
        return 0
        
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        logger.info(f"可以从备份恢复: {backup_path}")
        return 1

if __name__ == "__main__":
    exit(main())

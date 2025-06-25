#!/usr/bin/env python3
"""
数据库初始化脚本

创建数据库表和初始化数据
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.fsoa.data.database import DatabaseManager
from src.fsoa.utils.config import get_config
from src.fsoa.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    print("🚀 FSOA数据库初始化开始...")
    
    try:
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
            # 检查表是否创建成功
            from src.fsoa.data.database import SystemConfigTable
            config_count = session.query(SystemConfigTable).count()
            print(f"📋 系统配置项数量: {config_count}")
        
        print("🎉 数据库初始化完成！")
        
        # 显示下一步操作提示
        print("\n📌 下一步操作:")
        print("1. 复制 .env.example 到 .env")
        print("2. 编辑 .env 文件，填入实际配置")
        print("3. 运行 streamlit run src/fsoa/ui/app.py 启动应用")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

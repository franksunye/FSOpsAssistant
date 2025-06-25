#!/usr/bin/env python3
"""
应用启动脚本

启动FSOA应用的便捷脚本
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")

    # 检查.env文件
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  .env文件不存在")
        print("📝 请复制 .env.example 到 .env 并填入实际配置")
        return False
    
    # 检查必要的环境变量
    from src.fsoa.utils.config import get_config
    try:
        config = get_config()
        print(f"✅ 配置加载成功")
        print(f"📊 数据库: {config.database_url}")
        print(f"🔗 Metabase: {config.metabase_url}")
        print(f"📱 企微Webhook数量: {len(config.wechat_webhook_list)}")
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def check_database():
    """检查数据库"""
    print("🗄️  检查数据库...")
    
    try:
        from src.fsoa.data.database import get_db_manager
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            # 简单查询测试
            from src.fsoa.data.database import SystemConfigTable
            config_count = session.query(SystemConfigTable).count()
            print(f"✅ 数据库连接正常，配置项: {config_count}")
            return True
            
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("💡 请运行: python scripts/init_db.py")
        return False


def start_streamlit():
    """启动Streamlit应用"""
    print("🚀 启动Streamlit应用...")
    
    app_path = project_root / "src" / "fsoa" / "ui" / "app.py"
    
    try:
        # 设置环境变量
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        # 启动Streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
        subprocess.run(cmd, env=env, cwd=project_root)
        
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")


def main():
    """主函数"""
    print("🤖 FSOA - 现场服务运营助手")
    print("=" * 50)
    
    # 检查环境
    if not check_environment():
        sys.exit(1)
    
    # 检查数据库
    if not check_database():
        sys.exit(1)
    
    # 启动应用
    start_streamlit()


if __name__ == "__main__":
    main()

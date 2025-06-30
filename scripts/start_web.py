#!/usr/bin/env python3
"""
启动 FSOA Web 界面的便捷脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """主函数"""
    print("🚀 启动 FSOA Web 界面...")
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    
    # 检查 .env 文件
    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ .env 文件不存在")
        print("💡 请先复制 .env.example 到 .env 并配置相关参数")
        return False
    
    # 检查 Streamlit 是否安装
    try:
        import streamlit
        print(f"✅ Streamlit 版本: {streamlit.__version__}")
    except ImportError:
        print("❌ Streamlit 未安装")
        print("💡 请运行: pip install streamlit")
        return False
    
    # 启动 Streamlit 应用
    app_path = project_root / "src" / "fsoa" / "ui" / "app.py"
    
    print(f"📂 应用路径: {app_path}")
    print("🌐 启动 Web 界面...")
    print("📍 访问地址: http://localhost:8501")
    print("⏹️  按 Ctrl+C 停止服务")
    print("-" * 50)
    
    try:
        # 切换到项目根目录
        os.chdir(project_root)

        # 设置环境变量，确保Python能找到项目模块
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)

        # 启动 Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(app_path),
            "--server.address", "localhost",
            "--server.port", "8501"
        ], env=env)
        
    except KeyboardInterrupt:
        print("\n🛑 Web 界面已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()

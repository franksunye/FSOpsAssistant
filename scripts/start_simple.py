#!/usr/bin/env python3
"""
简化的FSOA启动脚本

跳过外部服务测试，直接启动核心功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_basic_config():
    """检查基本配置"""
    print("🔍 检查基本配置...")
    
    try:
        from src.fsoa.utils.config import get_config
        config = get_config()
        
        print("✅ 配置加载成功")
        print(f"📊 数据库: {config.database_url}")
        print(f"🧠 LLM消息格式化: {'启用' if config.use_llm_message_formatting else '禁用'}")
        print(f"🔧 调试模式: {'启用' if config.debug else '禁用'}")
        
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
            from src.fsoa.data.database import SystemConfigTable
            config_count = session.query(SystemConfigTable).count()
            print(f"✅ 数据库连接正常，配置项: {config_count}")
            return True
            
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("💡 请运行: python scripts/init_db.py")
        return False


def start_web_ui():
    """启动Web界面"""
    print("🌐 启动Web界面...")
    
    try:
        import subprocess
        import webbrowser
        import time
        
        # 启动Streamlit应用
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            "src/fsoa/ui/app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ]
        
        print("🚀 启动Streamlit服务器...")
        print(f"📝 命令: {' '.join(cmd)}")
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)

        # 启动进程
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 等待服务器启动
        print("⏳ 等待服务器启动...")
        time.sleep(3)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            print("✅ Web界面启动成功!")
            print("🌐 访问地址: http://localhost:8501")
            print("📱 移动端: http://your-ip:8501")
            print()
            print("💡 使用说明:")
            print("  - 商机管理: 查看和管理商机数据")
            print("  - 通知任务: 管理通知任务和发送状态")
            print("  - 系统管理: 配置企微群和系统参数")
            print("  - Agent执行: 手动触发或查看执行历史")
            print()
            print("🛑 按 Ctrl+C 停止服务")
            
            try:
                # 等待用户中断
                process.wait()
            except KeyboardInterrupt:
                print("\n🛑 收到停止信号...")
                process.terminate()
                process.wait()
                print("👋 Web界面已停止")
        else:
            print("❌ Web界面启动失败")
            # 读取错误输出
            output, _ = process.communicate()
            print(f"错误信息: {output}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Web界面启动失败: {e}")
        return False


def start_agent_scheduler():
    """启动Agent调度器"""
    print("🤖 启动Agent调度器...")

    try:
        from src.fsoa.utils.scheduler import get_scheduler
        from src.fsoa.agent.orchestrator import run_agent_cycle
        from src.fsoa.data.database import get_database_manager

        # 从数据库读取执行间隔
        db_manager = get_database_manager()
        interval_config = db_manager.get_system_config("agent_execution_interval")
        interval_minutes = int(interval_config) if interval_config else 60

        scheduler = get_scheduler()

        # 添加Agent执行任务
        scheduler.add_job(
            func=run_agent_cycle,
            trigger="interval",
            minutes=interval_minutes,
            id="agent_cycle",
            name="FSOA Agent Cycle",
            replace_existing=True
        )

        # 启动调度器
        scheduler.start()

        print(f"✅ Agent调度器启动成功")
        print(f"⏰ 执行间隔: {interval_minutes} 分钟")

        return scheduler

    except Exception as e:
        print(f"❌ Agent调度器启动失败: {e}")
        return None


def main():
    """主函数"""
    print("🚀 FSOA - 简化启动")
    print("=" * 50)
    
    try:
        # 1. 检查基本配置
        if not check_basic_config():
            sys.exit(1)
        print()
        
        # 2. 检查数据库
        if not check_database():
            sys.exit(1)
        print()
        
        # 3. 启动Agent调度器（后台）
        scheduler = start_agent_scheduler()
        print()
        
        # 4. 启动Web界面（前台）
        print("=" * 50)
        start_web_ui()
        
        # 5. 清理
        if scheduler:
            print("🛑 停止Agent调度器...")
            scheduler.shutdown()
        
        print("👋 FSOA已安全关闭")
        
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号...")
        if 'scheduler' in locals() and scheduler:
            scheduler.shutdown()
        print("👋 FSOA已安全关闭")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

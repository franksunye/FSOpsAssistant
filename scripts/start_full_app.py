#!/usr/bin/env python3
"""
完整应用启动脚本

启动包含定时任务的完整FSOA应用
"""

import os
import sys
import time
import signal
import threading
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def force_reload_config():
    """强制重新加载配置"""
    # 清除所有相关的环境变量
    for key in list(os.environ.keys()):
        if key.startswith(('DEEPSEEK_', 'METABASE_', 'WECHAT_', 'AGENT_', 'NOTIFICATION_', 'LLM_', 'DATABASE_', 'LOG_', 'DEBUG', 'TESTING')):
            del os.environ[key]
    
    # 重新加载 .env 文件
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # 清除模块缓存
    modules_to_clear = [
        'src.fsoa.utils.config',
        'src.fsoa.agent.orchestrator',
        'src.fsoa.utils.scheduler'
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]


def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")

    # 检查.env文件
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  .env文件不存在")
        print("📝 请复制 .env.example 到 .env 并填入实际配置")
        return False
    
    # 强制重新加载配置
    try:
        force_reload_config()
        
        # 重新导入配置
        from src.fsoa.utils.config import get_config
        config = get_config()
        
        print(f"✅ 配置加载成功")
        print(f"📊 数据库: {config.database_url}")
        print(f"🔗 Metabase: {config.metabase_url}")

        # 获取企微配置数量
        try:
            from src.fsoa.data.database import get_database_manager
            db_manager = get_database_manager()
            group_configs = db_manager.get_enabled_group_configs()
            org_webhook_count = len([gc for gc in group_configs if gc.webhook_url])
            internal_webhook_count = 1 if config.internal_ops_webhook else 0
            total_webhook_count = org_webhook_count + internal_webhook_count
            print(f"📱 企微Webhook数量: {total_webhook_count} (组织群:{org_webhook_count}, 运营群:{internal_webhook_count})")
        except Exception as e:
            print(f"📱 企微Webhook数量: 检查中... ({e})")

        # 从数据库读取Agent执行间隔
        try:
            interval_config = db_manager.get_system_config("agent_execution_interval")
            interval_minutes = int(interval_config) if interval_config else 60
            print(f"⏰ Agent执行间隔: {interval_minutes} 分钟")
        except Exception as e:
            print(f"⏰ Agent执行间隔: 60 分钟 (默认值，读取配置失败: {e})")
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


def test_services():
    """测试外部服务连接"""
    print("🔌 测试外部服务连接...")
    
    try:
        from src.fsoa.agent.tools import get_system_health
        
        health = get_system_health()
        
        print(f"📊 系统健康状态: {health.get('overall_status', 'unknown')}")
        print(f"   - Metabase: {'✅' if health.get('metabase_connection') else '❌'}")
        print(f"   - 企微: {'✅' if health.get('wechat_webhook') else '❌'}")
        print(f"   - DeepSeek: {'✅' if health.get('deepseek_connection') else '❌'}")
        print(f"   - 数据库: {'✅' if health.get('database_connection') else '❌'}")
        
        if health.get('overall_status') == 'healthy':
            print("✅ 所有外部服务连接正常")
            return True
        else:
            print("⚠️  部分服务连接异常，但应用仍可启动")
            return True
            
    except Exception as e:
        print(f"❌ 服务连接测试失败: {e}")
        return False


def start_scheduler():
    """启动定时任务调度器"""
    print("⏰ 启动定时任务调度器...")
    
    try:
        from src.fsoa.utils.scheduler import get_scheduler, setup_agent_scheduler, start_scheduler
        
        # 获取调度器
        scheduler = get_scheduler()
        
        # 设置Agent定时任务
        setup_agent_scheduler()
        
        # 启动调度器
        start_scheduler()
        
        print("✅ 定时任务调度器启动成功")
        return scheduler
        
    except Exception as e:
        print(f"❌ 定时任务调度器启动失败: {e}")
        return None


def run_agent_once():
    """手动执行一次Agent"""
    print("🤖 手动执行Agent...")

    try:
        from src.fsoa.agent.orchestrator import AgentOrchestrator

        agent = AgentOrchestrator()
        execution = agent.execute()

        print(f"✅ Agent执行完成")
        print(f"   - 执行ID: {execution.id}")
        print(f"   - 状态: {execution.status.value}")
        print(f"   - 处理任务数: {execution.tasks_processed}")
        print(f"   - 发送通知数: {execution.notifications_sent}")

        if execution.errors:
            print(f"   - 错误数: {len(execution.errors)}")
            for error in execution.errors[:3]:
                print(f"     • {error}")

        return True

    except Exception as e:
        print(f"❌ Agent执行失败: {e}")
        return False


def start_web_interface():
    """启动Web界面"""
    print("🌐 启动Web界面...")

    try:
        # 检查 Streamlit 是否安装
        import streamlit
        print(f"✅ Streamlit 版本: {streamlit.__version__}")
    except ImportError:
        print("❌ Streamlit 未安装")
        print("💡 请运行: pip install streamlit")
        return None

    # 启动 Streamlit 应用
    app_path = project_root / "src" / "fsoa" / "ui" / "app.py"

    print(f"📂 应用路径: {app_path}")
    print("🌐 启动 Web 界面...")
    print("📍 访问地址: http://localhost:8501")

    try:
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)

        # 启动 Streamlit 进程
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run",
            str(app_path),
            "--server.address", "localhost",
            "--server.port", "8501",
            "--server.headless", "true"
        ], cwd=str(project_root), env=env)

        print("✅ Web界面启动成功")
        return process

    except Exception as e:
        print(f"❌ Web界面启动失败: {e}")
        return None


# 全局变量用于优雅关闭
shutdown_event = threading.Event()
web_process = None


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n📡 收到信号 {signum}，准备关闭应用...")
    shutdown_event.set()


def main():
    """主函数"""
    global web_process

    print("🚀 FSOA - 完整应用启动")
    print("=" * 50)

    try:
        # 设置信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 检查环境
        if not check_environment():
            sys.exit(1)

        # 检查数据库
        if not check_database():
            sys.exit(1)

        # 测试服务连接
        if not test_services():
            print("⚠️  服务连接测试失败，但继续启动应用")

        # 启动Web界面
        print("\n🌐 启动Web界面...")
        web_process = start_web_interface()
        if not web_process:
            print("⚠️  Web界面启动失败，但继续启动Agent服务")

        # 启动定时任务调度器
        scheduler = start_scheduler()
        if not scheduler:
            print("⚠️  定时任务调度器启动失败，但继续启动应用")

        # 手动执行一次Agent
        print("\n🎯 执行初始Agent检查...")
        run_agent_once()

        print("\n🎉 FSOA完整应用启动完成！")
        print("📌 功能状态:")
        print("   - 🌐 Web界面: 运行中" if web_process else "   - 🌐 Web界面: 未启动")
        print("   - ⏰ 定时任务: 运行中" if scheduler else "   - ⏰ 定时任务: 未启动")
        print("   - 🤖 Agent: 就绪")
        print("   - 📊 监控: 激活")
        print("\n💡 提示:")
        print("   - 查看日志: tail -f logs/fsoa.log")
        print("   - Web界面: http://localhost:8501")
        print("   - 停止应用: Ctrl+C")
        print("\n" + "=" * 50)

        # 主循环 - 保持应用运行
        print("🔄 应用运行中，按 Ctrl+C 停止...")
        while not shutdown_event.is_set():
            # 检查Web进程是否还在运行
            if web_process and web_process.poll() is not None:
                print("⚠️  Web界面进程意外退出")
                web_process = None
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n📡 收到中断信号...")
    except Exception as e:
        print(f"\n❌ 应用运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 优雅关闭
        print("\n🛑 正在关闭应用...")

        # 停止Web界面
        try:
            if web_process and web_process.poll() is None:
                print("🌐 正在停止Web界面...")
                web_process.terminate()
                web_process.wait(timeout=5)
                print("✅ Web界面已停止")
        except Exception as e:
            print(f"⚠️  停止Web界面时出错: {e}")
            try:
                if web_process:
                    web_process.kill()
            except:
                pass

        # 停止调度器
        try:
            if 'scheduler' in locals() and scheduler:
                from src.fsoa.utils.scheduler import stop_scheduler
                stop_scheduler()
                print("✅ 定时任务调度器已停止")
        except Exception as e:
            print(f"⚠️  停止调度器时出错: {e}")

        print("👋 FSOA完整应用已安全关闭")


if __name__ == "__main__":
    main()

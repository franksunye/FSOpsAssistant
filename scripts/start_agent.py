#!/usr/bin/env python3
"""
Agent服务启动脚本

启动FSOA Agent后台服务
"""

import os
import sys
import signal
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n收到信号 {signum}，正在停止Agent服务...")
    from src.fsoa.utils.scheduler import stop_scheduler
    stop_scheduler()
    print("Agent服务已停止")
    sys.exit(0)


def main():
    """主函数"""
    print("🤖 FSOA Agent服务启动器")
    print("=" * 50)

    try:

        # 检查环境配置
        print("🔍 检查环境配置...")
        from src.fsoa.utils.config import get_config
        config = get_config()
        print(f"✅ 配置加载成功")
        print(f"📊 数据库: {config.database_url}")
        print(f"🔗 Metabase: {config.metabase_url}")
        print(f"🤖 DeepSeek: {config.deepseek_base_url}")
        
        # 检查数据库连接
        print("\n🗄️  检查数据库连接...")
        from src.fsoa.data.database import get_db_manager
        db_manager = get_db_manager()
        print("✅ 数据库连接正常")
        
        # 测试系统健康状态
        print("\n🏥 检查系统健康状态...")
        from src.fsoa.agent.tools import get_system_health
        health = get_system_health()
        
        print(f"📊 Metabase: {'✅' if health.get('metabase_connection') else '❌'}")
        print(f"📱 企微Webhook: {'✅' if health.get('wechat_webhook') else '❌'}")
        print(f"🤖 DeepSeek: {'✅' if health.get('deepseek_connection') else '❌'}")
        print(f"🗄️  数据库: {'✅' if health.get('database_connection') else '❌'}")
        print(f"🎯 整体状态: {health.get('overall_status', 'unknown')}")
        
        if health.get('overall_status') == 'unhealthy':
            print("⚠️  系统状态不健康，建议检查配置后再启动")
            response = input("是否继续启动？(y/N): ")
            if response.lower() != 'y':
                print("❌ 启动已取消")
                return
        
        # 启动调度器
        print("\n🚀 启动Agent调度器...")
        from src.fsoa.utils.scheduler import start_scheduler, setup_agent_scheduler
        
        scheduler = start_scheduler()
        job_id = setup_agent_scheduler()
        
        # 从数据库读取执行间隔用于显示
        from src.fsoa.data.database import get_database_manager
        db_manager = get_database_manager()
        interval_config = db_manager.get_system_config("agent_execution_interval")
        interval_minutes = int(interval_config) if interval_config else 60

        print(f"✅ 调度器启动成功")
        print(f"📋 任务ID: {job_id}")
        print(f"⏰ 执行间隔: {interval_minutes}分钟")
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("\n🎉 Agent服务启动完成！")
        print("📝 日志文件: logs/fsoa.log")
        print("🌐 Web界面: http://localhost:8501")
        print("⏹️  按 Ctrl+C 停止服务")
        print("-" * 50)
        
        # 保持服务运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)
            
    except Exception as e:
        print(f"❌ Agent服务启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

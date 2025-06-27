#!/usr/bin/env python3
"""
测试Web端修改执行频率后是否立即生效

这个脚本测试：
1. 当前调度器的执行间隔
2. 修改数据库中的执行间隔配置
3. 验证调度器是否自动更新
"""

import sys
import os
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置环境变量
os.environ['DEEPSEEK_API_KEY'] = 'test'
os.environ['METABASE_URL'] = 'http://test'
os.environ['METABASE_USERNAME'] = 'test'
os.environ['METABASE_PASSWORD'] = 'test'
os.environ['INTERNAL_OPS_WEBHOOK'] = 'http://test'

def get_current_scheduler_info():
    """获取当前调度器信息"""
    print("=== 获取当前调度器信息 ===")
    
    try:
        from src.fsoa.utils.scheduler import get_scheduler
        from src.fsoa.data.database import get_database_manager
        
        scheduler = get_scheduler()
        db_manager = get_database_manager()
        
        # 从数据库读取配置
        interval_config = db_manager.get_system_config("agent_execution_interval")
        db_interval = int(interval_config) if interval_config else 60
        
        print(f"数据库中的执行间隔: {db_interval} 分钟")
        
        # 检查调度器状态
        if hasattr(scheduler, 'scheduler') and scheduler.scheduler:
            is_running = scheduler.scheduler.running
            print(f"调度器运行状态: {'运行中' if is_running else '已停止'}")
            
            if is_running:
                # 获取Agent任务信息
                jobs = scheduler.scheduler.get_jobs()
                agent_job = None
                for job in jobs:
                    if job.id == "agent_execution":
                        agent_job = job
                        break
                
                if agent_job:
                    print(f"找到Agent任务: {agent_job.id}")
                    print(f"任务触发器: {agent_job.trigger}")
                    
                    # 尝试获取间隔信息
                    if hasattr(agent_job.trigger, 'interval'):
                        current_interval_seconds = agent_job.trigger.interval.total_seconds()
                        current_interval_minutes = current_interval_seconds / 60
                        print(f"调度器中的实际执行间隔: {current_interval_minutes} 分钟")
                        
                        # 检查是否一致
                        if abs(current_interval_minutes - db_interval) < 0.1:
                            print("✓ 数据库配置与调度器配置一致")
                            return True, db_interval, current_interval_minutes
                        else:
                            print("✗ 数据库配置与调度器配置不一致")
                            return False, db_interval, current_interval_minutes
                    else:
                        print("⚠️ 无法获取调度器间隔信息")
                        return None, db_interval, None
                else:
                    print("⚠️ 未找到Agent执行任务")
                    return None, db_interval, None
            else:
                print("⚠️ 调度器未运行")
                return None, db_interval, None
        else:
            print("⚠️ 调度器未初始化")
            return None, db_interval, None
            
    except Exception as e:
        print(f"❌ 获取调度器信息失败: {e}")
        return None, None, None


def update_execution_interval(new_interval: int):
    """更新执行间隔配置"""
    print(f"\n=== 更新执行间隔为 {new_interval} 分钟 ===")
    
    try:
        from src.fsoa.data.database import get_database_manager
        
        db_manager = get_database_manager()
        
        # 保存新的执行间隔
        success = db_manager.set_system_config(
            "agent_execution_interval", 
            str(new_interval), 
            "Agent执行间隔（分钟）"
        )
        
        if success:
            print(f"✓ 数据库配置已更新为 {new_interval} 分钟")
            return True
        else:
            print("✗ 数据库配置更新失败")
            return False
            
    except Exception as e:
        print(f"❌ 更新配置失败: {e}")
        return False


def test_scheduler_auto_update():
    """测试调度器是否自动更新"""
    print("\n=== 测试调度器自动更新 ===")
    
    # 1. 获取当前状态
    print("1. 获取当前状态...")
    consistent, db_interval, scheduler_interval = get_current_scheduler_info()
    
    if db_interval is None:
        print("❌ 无法获取当前配置，测试终止")
        return False
    
    # 2. 更新配置
    new_interval = 1 if db_interval != 1 else 2  # 选择一个不同的值
    print(f"\n2. 更新配置从 {db_interval} 分钟到 {new_interval} 分钟...")
    
    if not update_execution_interval(new_interval):
        print("❌ 配置更新失败，测试终止")
        return False
    
    # 3. 等待一段时间
    print("\n3. 等待5秒后检查调度器是否自动更新...")
    time.sleep(5)
    
    # 4. 再次检查调度器状态
    print("\n4. 检查调度器是否自动更新...")
    consistent_after, db_interval_after, scheduler_interval_after = get_current_scheduler_info()
    
    if scheduler_interval_after is not None:
        if abs(scheduler_interval_after - new_interval) < 0.1:
            print("✅ 调度器已自动更新到新的执行间隔")
            return True
        else:
            print(f"❌ 调度器未自动更新，仍为 {scheduler_interval_after} 分钟")
            return False
    else:
        print("⚠️ 无法确定调度器是否更新（调度器可能未运行）")
        return False


def test_manual_restart():
    """测试手动重启调度器"""
    print("\n=== 测试手动重启调度器 ===")
    
    try:
        from src.fsoa.utils.scheduler import stop_scheduler, start_scheduler, setup_agent_scheduler
        
        print("1. 停止调度器...")
        stop_scheduler()
        time.sleep(2)
        
        print("2. 启动调度器...")
        start_scheduler()
        
        print("3. 重新设置Agent任务...")
        job_id = setup_agent_scheduler()
        
        print(f"✓ 调度器重启完成，任务ID: {job_id}")
        
        # 4. 验证新配置
        print("\n4. 验证重启后的配置...")
        consistent, db_interval, scheduler_interval = get_current_scheduler_info()
        
        if scheduler_interval is not None and abs(scheduler_interval - db_interval) < 0.1:
            print("✅ 重启后调度器使用了最新的数据库配置")
            return True
        else:
            print("❌ 重启后调度器配置仍不正确")
            return False
            
    except Exception as e:
        print(f"❌ 手动重启失败: {e}")
        return False


def restore_original_config():
    """恢复原始配置"""
    print("\n=== 恢复原始配置 ===")
    
    # 恢复为默认的60分钟
    success = update_execution_interval(60)
    if success:
        print("✓ 已恢复为默认的60分钟执行间隔")
    else:
        print("✗ 恢复默认配置失败")
    
    return success


def main():
    """主函数"""
    print("开始测试Web端修改执行频率的生效机制...")
    
    try:
        # 1. 测试调度器自动更新
        auto_update_works = test_scheduler_auto_update()
        
        # 2. 测试手动重启
        manual_restart_works = test_manual_restart()
        
        # 3. 恢复原始配置
        restore_original_config()
        
        # 4. 总结结果
        print("\n" + "="*60)
        print("📋 测试结果总结:")
        print(f"  自动更新: {'✅ 支持' if auto_update_works else '❌ 不支持'}")
        print(f"  手动重启: {'✅ 有效' if manual_restart_works else '❌ 无效'}")
        
        if not auto_update_works:
            print("\n⚠️  重要发现:")
            print("   Web端修改执行频率后，调度器不会自动更新！")
            print("   需要手动重启调度器才能使新配置生效。")
            print("\n💡 解决方案:")
            print("   1. 在Web界面保存配置后，点击'🔄 重启调度器'按钮")
            print("   2. 或者重启整个Agent服务")
            print("   3. 或者修改代码实现自动重启功能")
        else:
            print("\n✅ 配置更新机制正常工作")
        
        return auto_update_works
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

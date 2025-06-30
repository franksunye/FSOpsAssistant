#!/usr/bin/env python3
"""
测试调度器运行时的重启功能
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_restart_running_scheduler():
    """测试调度器运行时的重启功能"""
    print("=== 测试调度器运行时的重启功能 ===")
    
    try:
        from src.fsoa.utils.scheduler import get_scheduler, stop_scheduler, start_scheduler, setup_agent_scheduler
        from src.fsoa.data.database import get_database_manager
        
        db_manager = get_database_manager()
        
        # 1. 启动调度器
        print("1. 启动调度器...")
        db_manager.set_system_config("agent_execution_interval", "10", "Agent执行间隔（分钟）")
        start_scheduler()
        job_id = setup_agent_scheduler()
        print(f"   ✓ 调度器已启动（间隔：10分钟，任务ID：{job_id}）")
        
        # 2. 验证调度器正在运行
        time.sleep(1)
        scheduler = get_scheduler()
        is_running = hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running
        print(f"   调度器运行状态: {'运行中' if is_running else '已停止'}")
        
        if not is_running:
            print("   ❌ 调度器启动失败")
            return False
        
        # 3. 修改配置并重启
        print("\n2. 修改配置并重启...")
        new_interval = 2
        db_manager.set_system_config("agent_execution_interval", str(new_interval), "Agent执行间隔（分钟）")
        
        # 执行重启逻辑
        scheduler = get_scheduler()
        is_running = hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running
        
        if is_running:
            print("   调度器正在运行，执行重启...")
            stop_scheduler()
            start_scheduler()
            job_id = setup_agent_scheduler()
            print(f"   ✅ 调度器已重启（新间隔：{new_interval}分钟，任务ID：{job_id}）")
        
        # 4. 验证结果
        print("\n3. 验证结果...")
        time.sleep(1)
        
        scheduler = get_scheduler()
        is_running = hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running
        print(f"   调度器运行状态: {'运行中' if is_running else '已停止'}")
        
        if is_running:
            jobs = scheduler.scheduler.get_jobs()
            agent_job = None
            for job in jobs:
                if job.id == "agent_execution":
                    agent_job = job
                    break
            
            if agent_job:
                trigger = agent_job.trigger
                if hasattr(trigger, 'interval'):
                    interval_seconds = trigger.interval.total_seconds()
                    interval_minutes = interval_seconds / 60
                    print(f"   调度器中的实际执行间隔: {interval_minutes} 分钟")
                    
                    if abs(interval_minutes - new_interval) < 0.1:
                        print("   ✅ 重启成功，配置已更新")
                        return True
                    else:
                        print(f"   ❌ 配置不一致：期望 {new_interval} 分钟，实际 {interval_minutes} 分钟")
                        return False
        
        return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    finally:
        # 清理
        try:
            from src.fsoa.utils.scheduler import stop_scheduler
            from src.fsoa.data.database import get_database_manager
            stop_scheduler()
            db_manager = get_database_manager()
            db_manager.set_system_config("agent_execution_interval", "60", "Agent执行间隔（分钟）")
            print("\n✓ 清理完成")
        except:
            pass

if __name__ == "__main__":
    success = test_restart_running_scheduler()
    
    print("\n" + "="*50)
    if success:
        print("🎉 重启功能测试通过！")
    else:
        print("❌ 重启功能测试失败！")
    print("="*50)

#!/usr/bin/env python3
"""
测试修复后的自动启动功能
验证Web界面修改执行间隔后能否自动启动调度器
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_auto_start_functionality():
    """测试自动启动功能"""
    print("=== 测试修复后的自动启动功能 ===")
    
    try:
        from src.fsoa.utils.scheduler import get_scheduler, stop_scheduler, start_scheduler, setup_agent_scheduler
        from src.fsoa.data.database import get_database_manager
        
        db_manager = get_database_manager()
        
        # 1. 确保调度器处于停止状态
        print("1. 确保调度器处于停止状态...")
        scheduler = get_scheduler()
        if hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running:
            stop_scheduler()
            print("   调度器已停止")
        else:
            print("   调度器已经是停止状态")
        
        # 2. 获取当前配置
        current_interval_config = db_manager.get_system_config("agent_execution_interval")
        current_interval = int(current_interval_config) if current_interval_config else 60
        print(f"   当前数据库配置: {current_interval} 分钟")
        
        # 3. 模拟Web界面的配置更新逻辑
        print("\n2. 模拟Web界面修改配置...")
        new_interval = 5  # 修改为5分钟
        
        # 检查是否有变化
        interval_changed = (new_interval != current_interval)
        print(f"   新间隔: {new_interval} 分钟")
        print(f"   配置是否变化: {interval_changed}")
        
        if not interval_changed:
            # 如果没有变化，先设置一个不同的值
            temp_interval = current_interval + 1
            db_manager.set_system_config("agent_execution_interval", str(temp_interval), "Agent执行间隔（分钟）")
            print(f"   为了测试，先设置为 {temp_interval} 分钟")
            interval_changed = True
        
        # 4. 保存新配置
        print(f"\n3. 保存新配置 {new_interval} 分钟...")
        success = db_manager.set_system_config("agent_execution_interval", str(new_interval), "Agent执行间隔（分钟）")
        if success:
            print("   ✓ 数据库配置已更新")
        else:
            print("   ✗ 数据库配置更新失败")
            return False
        
        # 5. 模拟修复后的自动启动逻辑
        print("\n4. 执行修复后的自动启动逻辑...")
        if interval_changed:
            try:
                scheduler = get_scheduler()
                is_running = hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running
                
                if is_running:
                    print("   调度器正在运行，执行重启...")
                    stop_scheduler()
                    start_scheduler()
                    setup_agent_scheduler()
                    print(f"   ✅ 调度器已重启（新间隔：{new_interval}分钟）")
                else:
                    print("   调度器未运行，执行启动...")
                    start_scheduler()
                    job_id = setup_agent_scheduler()
                    print(f"   ✅ 调度器已启动（执行间隔：{new_interval}分钟，任务ID：{job_id}）")
                    
            except Exception as restart_error:
                print(f"   ❌ 调度器启动失败: {restart_error}")
                return False
        
        # 6. 验证结果
        print("\n5. 验证结果...")
        time.sleep(1)  # 等待调度器完全启动
        
        scheduler = get_scheduler()
        is_running = hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running
        print(f"   调度器运行状态: {'运行中' if is_running else '已停止'}")
        
        if is_running:
            # 检查任务配置
            jobs = scheduler.scheduler.get_jobs()
            agent_job = None
            for job in jobs:
                if job.id == "agent_execution":
                    agent_job = job
                    break
            
            if agent_job:
                # 获取间隔信息
                trigger = agent_job.trigger
                if hasattr(trigger, 'interval'):
                    interval_seconds = trigger.interval.total_seconds()
                    interval_minutes = interval_seconds / 60
                    print(f"   调度器中的实际执行间隔: {interval_minutes} 分钟")
                    
                    # 验证配置一致性
                    if abs(interval_minutes - new_interval) < 0.1:
                        print("   ✅ 配置一致性验证通过")
                        return True
                    else:
                        print(f"   ❌ 配置不一致：期望 {new_interval} 分钟，实际 {interval_minutes} 分钟")
                        return False
                else:
                    print("   ❌ 无法获取任务间隔信息")
                    return False
            else:
                print("   ❌ 未找到Agent任务")
                return False
        else:
            print("   ❌ 调度器未成功启动")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def cleanup():
    """清理测试环境"""
    print("\n=== 清理测试环境 ===")
    try:
        from src.fsoa.utils.scheduler import stop_scheduler
        from src.fsoa.data.database import get_database_manager
        
        # 停止调度器
        stop_scheduler()
        print("✓ 调度器已停止")
        
        # 恢复默认配置
        db_manager = get_database_manager()
        db_manager.set_system_config("agent_execution_interval", "60", "Agent执行间隔（分钟）")
        print("✓ 已恢复默认配置（60分钟）")
        
    except Exception as e:
        print(f"⚠️ 清理过程中出现错误: {e}")

if __name__ == "__main__":
    try:
        success = test_auto_start_functionality()
        
        print("\n" + "="*60)
        if success:
            print("🎉 测试通过！修复后的自动启动功能工作正常")
            print("💡 现在Web界面修改执行间隔后会自动启动/重启调度器")
        else:
            print("❌ 测试失败！需要进一步检查问题")
        print("="*60)
        
    finally:
        cleanup()

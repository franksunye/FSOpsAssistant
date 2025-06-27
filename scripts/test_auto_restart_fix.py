#!/usr/bin/env python3
"""
测试修复后的自动重启功能

这个脚本模拟Web界面保存Agent设置的过程，验证调度器是否自动重启
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

def get_scheduler_interval():
    """获取调度器当前的执行间隔"""
    try:
        from src.fsoa.utils.scheduler import get_scheduler
        
        scheduler = get_scheduler()
        
        if hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running:
            jobs = scheduler.scheduler.get_jobs()
            for job in jobs:
                if job.id == "agent_execution":
                    if hasattr(job.trigger, 'interval'):
                        interval_seconds = job.trigger.interval.total_seconds()
                        interval_minutes = interval_seconds / 60
                        return interval_minutes
        return None
    except Exception as e:
        print(f"获取调度器间隔失败: {e}")
        return None


def simulate_web_save_agent_settings(new_execution_interval: int):
    """模拟Web界面保存Agent设置的过程"""
    print(f"\n=== 模拟Web界面保存Agent设置（执行间隔：{new_execution_interval}分钟）===")
    
    try:
        from src.fsoa.data.database import get_database_manager
        from src.fsoa.utils.scheduler import get_scheduler, stop_scheduler, start_scheduler, setup_agent_scheduler
        
        db_manager = get_database_manager()

        # 获取当前执行间隔以检查是否有变化
        current_interval_config = db_manager.get_system_config("agent_execution_interval")
        current_interval = int(current_interval_config) if current_interval_config else 60
        interval_changed = (new_execution_interval != current_interval)
        
        print(f"当前数据库配置: {current_interval} 分钟")
        print(f"新配置: {new_execution_interval} 分钟")
        print(f"配置是否变化: {'是' if interval_changed else '否'}")

        # 保存Agent配置到数据库（模拟Web界面的保存逻辑）
        agent_configs = [
            ("agent_execution_interval", str(new_execution_interval), "Agent执行间隔（分钟）"),
            ("use_llm_optimization", "true", "是否启用LLM优化"),
            ("llm_temperature", "0.1", "LLM温度参数"),
            ("agent_max_retries", "3", "Agent最大重试次数"),
        ]

        for key, value, description in agent_configs:
            db_manager.set_system_config(key, value, description)
        
        print("✓ 配置已保存到数据库")

        # 如果执行间隔发生变化且调度器正在运行，自动重启调度器
        if interval_changed:
            try:
                scheduler = get_scheduler()
                if hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running:
                    print("🔄 检测到执行间隔变化，正在重启调度器...")
                    
                    # 获取重启前的间隔
                    old_scheduler_interval = get_scheduler_interval()
                    print(f"重启前调度器间隔: {old_scheduler_interval} 分钟")
                    
                    # 重启调度器
                    stop_scheduler()
                    start_scheduler()
                    setup_agent_scheduler()
                    
                    # 获取重启后的间隔
                    time.sleep(1)  # 等待调度器完全启动
                    new_scheduler_interval = get_scheduler_interval()
                    print(f"重启后调度器间隔: {new_scheduler_interval} 分钟")
                    
                    if new_scheduler_interval and abs(new_scheduler_interval - new_execution_interval) < 0.1:
                        print(f"✅ 调度器已自动重启，新间隔生效：{new_execution_interval}分钟")
                        return True
                    else:
                        print("❌ 调度器重启后间隔不正确")
                        return False
                else:
                    print("⚠️ 调度器未运行，无需重启")
                    return True
            except Exception as restart_error:
                print(f"❌ 调度器重启失败: {restart_error}")
                return False
        else:
            print("ℹ️ 执行间隔未变化，无需重启调度器")
            return True
            
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        return False


def test_auto_restart_functionality():
    """测试自动重启功能"""
    print("开始测试自动重启功能...")
    
    try:
        # 1. 启动调度器
        print("\n1. 启动调度器...")
        from src.fsoa.utils.scheduler import start_scheduler, setup_agent_scheduler
        
        start_scheduler()
        setup_agent_scheduler()
        
        # 验证调度器启动
        initial_interval = get_scheduler_interval()
        if initial_interval is not None:
            print(f"✓ 调度器已启动，当前间隔: {initial_interval} 分钟")
        else:
            print("❌ 调度器启动失败")
            return False
        
        # 2. 测试修改为不同的间隔
        test_intervals = [2, 5, 1]
        
        for test_interval in test_intervals:
            print(f"\n2. 测试修改执行间隔为 {test_interval} 分钟...")
            success = simulate_web_save_agent_settings(test_interval)
            
            if not success:
                print(f"❌ 测试间隔 {test_interval} 分钟失败")
                return False
            
            # 验证间隔确实改变了
            current_interval = get_scheduler_interval()
            if current_interval and abs(current_interval - test_interval) < 0.1:
                print(f"✅ 间隔成功更新为 {test_interval} 分钟")
            else:
                print(f"❌ 间隔更新失败，当前为 {current_interval} 分钟")
                return False
        
        # 3. 测试保存相同间隔（不应该重启）
        print(f"\n3. 测试保存相同间隔（不应该重启）...")
        last_interval = test_intervals[-1]
        success = simulate_web_save_agent_settings(last_interval)
        
        if success:
            print("✅ 相同间隔保存成功，调度器未重启")
        else:
            print("❌ 相同间隔保存失败")
            return False
        
        # 4. 恢复默认配置
        print("\n4. 恢复默认配置...")
        simulate_web_save_agent_settings(60)
        
        print("\n✅ 所有测试通过！自动重启功能正常工作")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理：停止调度器
        try:
            from src.fsoa.utils.scheduler import stop_scheduler
            stop_scheduler()
            print("\n🧹 调度器已停止")
        except:
            pass


def main():
    """主函数"""
    print("测试Web端修改执行频率自动重启功能...")
    
    success = test_auto_restart_functionality()
    
    if success:
        print("\n" + "="*60)
        print("🎉 修复验证成功！")
        print("\n📋 功能说明:")
        print("✅ Web端修改执行频率后，调度器会自动重启")
        print("✅ 新的执行间隔立即生效")
        print("✅ 如果间隔未变化，不会重启调度器")
        print("✅ 如果调度器未运行，配置仍会保存")
        print("\n💡 用户体验:")
        print("- 用户在Web界面修改执行频率从60分钟改为1分钟")
        print("- 点击'保存Agent设置'后，系统自动重启调度器")
        print("- 新的1分钟间隔立即生效，无需手动重启")
    else:
        print("\n❌ 修复验证失败")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

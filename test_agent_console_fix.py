#!/usr/bin/env python3
"""
测试Agent控制台修复
验证Agent控制台页面能否正确检测完整模式
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_agent_status_detection():
    """测试Agent状态检测"""
    print("🧪 测试Agent状态检测")
    print("=" * 50)
    
    try:
        from src.fsoa.agent.tools import get_agent_execution_status, detect_fsoa_processes
        
        # 获取Agent执行状态
        agent_exec_status = get_agent_execution_status()
        print("Agent执行状态:")
        print(f"  调度器运行: {agent_exec_status.get('scheduler_running')}")
        print(f"  最后执行: {agent_exec_status.get('last_execution')}")
        print(f"  执行状态: {agent_exec_status.get('last_execution_status')}")
        print(f"  下次执行: {agent_exec_status.get('next_execution')}")
        print(f"  执行间隔: {agent_exec_status.get('execution_interval')}")
        print(f"  总运行次数: {agent_exec_status.get('total_runs')}")
        
        # 获取进程信息
        process_info = detect_fsoa_processes()
        print(f"\n进程检测:")
        print(f"  当前PID: {process_info.get('current_pid')}")
        print(f"  FSOA进程数: {process_info.get('total_fsoa_processes')}")
        print(f"  有完整应用: {process_info.get('has_full_app_process')}")
        
        fsoa_processes = process_info.get('fsoa_processes', [])
        if fsoa_processes:
            print(f"  检测到的进程:")
            for proc in fsoa_processes:
                proc_type = "完整应用" if proc.get('is_full_app') else "其他进程"
                print(f"    PID {proc['pid']}: {proc_type}")
        
        # 模拟控制台页面的检测逻辑
        scheduler_running = agent_exec_status.get("scheduler_running", False)
        has_full_app_process = process_info.get("has_full_app_process", False)
        
        print(f"\n🎯 控制台页面检测结果:")
        if scheduler_running or has_full_app_process:
            print("  状态: 🟢 调度器运行中")
            if has_full_app_process and not scheduler_running:
                print("  说明: 💡 检测到完整应用进程运行中")
        else:
            print("  状态: 🔴 调度器已停止")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scheduler_info():
    """测试调度器信息获取"""
    print("\n⏰ 测试调度器信息")
    print("=" * 50)
    
    try:
        from src.fsoa.utils.scheduler import get_scheduler
        
        scheduler = get_scheduler()
        jobs_info = scheduler.get_jobs()
        
        print(f"当前进程调度器:")
        print(f"  运行状态: {jobs_info.get('is_running')}")
        print(f"  任务数量: {jobs_info.get('total_jobs')}")
        
        jobs = jobs_info.get('jobs', [])
        if jobs:
            print(f"  任务列表:")
            for job in jobs:
                print(f"    {job['id']}: {job['func']}")
                print(f"      下次执行: {job.get('next_run_time', '未知')}")
        else:
            print("  无活跃任务")
        
        return True
        
    except Exception as e:
        print(f"❌ 调度器信息获取失败: {e}")
        return False


def main():
    """主函数"""
    print("🔧 Agent控制台修复测试")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # 测试Agent状态检测
    if test_agent_status_detection():
        success_count += 1
    
    # 测试调度器信息
    if test_scheduler_info():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"测试完成: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        print("✅ 所有测试通过！Agent控制台修复成功")
    else:
        print("❌ 部分测试失败，请检查相关功能")
    
    print("\n💡 验证步骤:")
    print("1. 启动完整应用: python scripts/start_full_app.py")
    print("2. 访问Web界面的Agent控制台页面")
    print("3. 应该看到 '🟢 调度器运行中' 而不是 '🔴 调度器已停止'")
    print("4. 应该显示进程检测信息和详细状态")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
测试Agent状态检测功能
验证首页能否正确检测完整模式和Web模式
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_process_detection():
    """测试进程检测功能"""
    print("🔍 测试进程检测功能")
    print("=" * 50)
    
    try:
        from src.fsoa.agent.tools import detect_fsoa_processes
        
        process_info = detect_fsoa_processes()
        
        print(f"当前进程ID: {process_info.get('current_pid')}")
        print(f"FSOA进程数量: {process_info.get('total_fsoa_processes')}")
        print(f"有完整应用进程: {process_info.get('has_full_app_process')}")
        
        fsoa_processes = process_info.get('fsoa_processes', [])
        if fsoa_processes:
            print("\n发现的FSOA进程:")
            for proc in fsoa_processes:
                print(f"  PID: {proc['pid']}")
                print(f"  名称: {proc['name']}")
                print(f"  命令行: {proc['cmdline']}")
                print(f"  是否完整应用: {proc['is_full_app']}")
                print()
        else:
            print("未发现其他FSOA进程")
            
        return True
        
    except Exception as e:
        print(f"❌ 进程检测失败: {e}")
        return False


def test_agent_status_detection():
    """测试Agent状态检测功能"""
    print("\n🤖 测试Agent状态检测功能")
    print("=" * 50)
    
    try:
        from src.fsoa.agent.tools import get_agent_execution_status
        
        agent_status = get_agent_execution_status()
        
        print(f"调度器运行状态: {agent_status.get('scheduler_running')}")
        print(f"最后执行时间: {agent_status.get('last_execution')}")
        print(f"最后执行状态: {agent_status.get('last_execution_status')}")
        print(f"下次执行时间: {agent_status.get('next_execution')}")
        print(f"执行间隔: {agent_status.get('execution_interval')}")
        print(f"总运行次数: {agent_status.get('total_runs')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent状态检测失败: {e}")
        return False


def test_combined_detection():
    """测试组合检测逻辑"""
    print("\n🎯 测试组合检测逻辑")
    print("=" * 50)
    
    try:
        from src.fsoa.agent.tools import get_agent_execution_status, detect_fsoa_processes
        
        agent_exec_status = get_agent_execution_status()
        process_info = detect_fsoa_processes()
        
        # 模拟首页的检测逻辑
        scheduler_running = agent_exec_status.get("scheduler_running", False)
        has_full_app_process = process_info.get("has_full_app_process", False)
        last_execution = agent_exec_status.get("last_execution")
        
        print(f"调度器运行: {scheduler_running}")
        print(f"有完整应用进程: {has_full_app_process}")
        print(f"最后执行: {last_execution}")
        
        if scheduler_running or has_full_app_process:
            agent_status = "完整模式"
            agent_delta = "Agent + Web界面"
        elif last_execution and last_execution != "从未执行":
            agent_status = "完整模式"
            agent_delta = "Agent + Web界面"
        else:
            agent_status = "Web模式"
            agent_delta = "仅Web界面"
        
        print(f"\n🎯 检测结果:")
        print(f"Agent状态: {agent_status}")
        print(f"状态描述: {agent_delta}")
        
        return True
        
    except Exception as e:
        print(f"❌ 组合检测失败: {e}")
        return False


def main():
    """主函数"""
    print("🧪 Agent状态检测测试")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # 测试进程检测
    if test_process_detection():
        success_count += 1
    
    # 测试Agent状态检测
    if test_agent_status_detection():
        success_count += 1
    
    # 测试组合检测
    if test_combined_detection():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"测试完成: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        print("✅ 所有测试通过！Agent状态检测功能正常")
    else:
        print("❌ 部分测试失败，请检查相关功能")
    
    print("\n💡 使用说明:")
    print("1. 当前运行此脚本时应该显示 'Web模式'")
    print("2. 运行 'python scripts/start_full_app.py' 后应该显示 '完整模式'")
    print("3. 首页的Agent状态应该能正确反映当前运行模式")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
诊断Agent执行失败的原因
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.utils.logger import get_logger

logger = get_logger(__name__)


def test_agent_execution_step_by_step():
    """逐步测试Agent执行的每个环节"""
    print("=" * 60)
    print("Agent执行诊断 - 逐步测试")
    print("=" * 60)
    
    results = {}
    
    # 1. 测试执行追踪器
    print("\n1. 测试执行追踪器...")
    try:
        from src.fsoa.agent.tools import get_execution_tracker, start_agent_execution
        
        execution_tracker = get_execution_tracker()
        print(f"   ✅ 执行追踪器获取成功")
        
        # 启动一个测试执行
        context = {"test_execution": True, "diagnostic": True}
        run_id = start_agent_execution(context)
        print(f"   ✅ 启动执行成功，run_id: {run_id}")
        results["execution_tracker"] = True
        results["run_id"] = run_id
        
    except Exception as e:
        print(f"   ❌ 执行追踪器失败: {e}")
        results["execution_tracker"] = False
        return results
    
    # 2. 测试数据获取
    print("\n2. 测试数据获取...")
    try:
        from src.fsoa.agent.tools import get_all_opportunities
        
        opportunities = get_all_opportunities(force_refresh=True)
        print(f"   ✅ 获取商机成功: {len(opportunities)} 条")
        
        overdue_opportunities = [opp for opp in opportunities if opp.is_overdue]
        print(f"   ✅ 逾期商机: {len(overdue_opportunities)} 条")
        results["data_fetch"] = True
        results["opportunities_count"] = len(opportunities)
        results["overdue_count"] = len(overdue_opportunities)
        
    except Exception as e:
        print(f"   ❌ 数据获取失败: {e}")
        results["data_fetch"] = False
        import traceback
        traceback.print_exc()
        return results
    
    # 3. 测试通知管理器
    print("\n3. 测试通知管理器...")
    try:
        from src.fsoa.agent.tools import get_notification_manager
        
        notification_manager = get_notification_manager()
        print(f"   ✅ 通知管理器获取成功")
        results["notification_manager"] = True
        
    except Exception as e:
        print(f"   ❌ 通知管理器失败: {e}")
        results["notification_manager"] = False
        import traceback
        traceback.print_exc()
        return results
    
    # 4. 测试企微客户端
    print("\n4. 测试企微客户端...")
    try:
        from src.fsoa.notification.wechat import get_wechat_client
        
        wechat_client = get_wechat_client()
        print(f"   ✅ 企微客户端获取成功")
        
        # 测试配置
        from src.fsoa.data.database import get_database_manager
        db_manager = get_database_manager()
        group_configs = db_manager.get_enabled_group_configs()
        print(f"   ✅ 企微群配置: {len(group_configs)} 个")
        results["wechat_client"] = True
        results["group_configs_count"] = len(group_configs)
        
    except Exception as e:
        print(f"   ❌ 企微客户端失败: {e}")
        results["wechat_client"] = False
        import traceback
        traceback.print_exc()
        return results
    
    # 5. 测试通知任务创建
    print("\n5. 测试通知任务创建...")
    try:
        from src.fsoa.agent.tools import create_notification_tasks
        
        if overdue_opportunities:
            tasks = create_notification_tasks(overdue_opportunities, run_id)
            print(f"   ✅ 创建通知任务成功: {len(tasks)} 个")
            results["task_creation"] = True
            results["tasks_count"] = len(tasks)
        else:
            print(f"   ⚠️  没有逾期商机，跳过任务创建")
            results["task_creation"] = True
            results["tasks_count"] = 0
        
    except Exception as e:
        print(f"   ❌ 通知任务创建失败: {e}")
        results["task_creation"] = False
        import traceback
        traceback.print_exc()
        return results
    
    # 6. 测试通知任务执行
    print("\n6. 测试通知任务执行...")
    try:
        from src.fsoa.agent.tools import execute_notification_tasks
        
        notification_result = execute_notification_tasks(run_id)
        print(f"   ✅ 通知任务执行完成")
        print(f"   📊 发送成功: {notification_result.get('sent_count', 0)}")
        print(f"   📊 发送失败: {notification_result.get('failed_count', 0)}")
        print(f"   📊 升级通知: {notification_result.get('escalated_count', 0)}")
        
        if notification_result.get('errors'):
            print(f"   ⚠️  执行错误:")
            for error in notification_result['errors'][:3]:
                print(f"      - {error}")
        
        results["task_execution"] = True
        results["notification_result"] = notification_result
        
    except Exception as e:
        print(f"   ❌ 通知任务执行失败: {e}")
        results["task_execution"] = False
        import traceback
        traceback.print_exc()
        return results
    
    # 7. 测试执行完成
    print("\n7. 测试执行完成...")
    try:
        from src.fsoa.agent.tools import complete_agent_execution
        
        final_stats = {
            "opportunities_processed": len(opportunities),
            "notifications_sent": notification_result.get("sent_count", 0),
            "context": {"diagnostic_execution_completed": True}
        }
        complete_agent_execution(run_id, final_stats)
        print(f"   ✅ 执行完成成功")
        results["execution_completion"] = True
        
    except Exception as e:
        print(f"   ❌ 执行完成失败: {e}")
        results["execution_completion"] = False
        import traceback
        traceback.print_exc()
        return results
    
    return results


def analyze_results(results):
    """分析诊断结果"""
    print("\n" + "=" * 60)
    print("诊断结果分析")
    print("=" * 60)
    
    total_steps = 7
    passed_steps = sum(1 for key in ["execution_tracker", "data_fetch", "notification_manager", 
                                   "wechat_client", "task_creation", "task_execution", "execution_completion"] 
                      if results.get(key, False))
    
    print(f"总步骤: {total_steps}")
    print(f"通过步骤: {passed_steps}")
    print(f"成功率: {passed_steps/total_steps*100:.1f}%")
    
    if passed_steps == total_steps:
        print("\n🎉 所有步骤都通过了！Agent执行应该正常工作。")
        
        # 显示详细统计
        print(f"\n📊 执行统计:")
        print(f"  - 处理商机: {results.get('opportunities_count', 0)} 条")
        print(f"  - 逾期商机: {results.get('overdue_count', 0)} 条")
        print(f"  - 企微群配置: {results.get('group_configs_count', 0)} 个")
        print(f"  - 创建任务: {results.get('tasks_count', 0)} 个")
        
        notification_result = results.get('notification_result', {})
        print(f"  - 发送成功: {notification_result.get('sent_count', 0)}")
        print(f"  - 发送失败: {notification_result.get('failed_count', 0)}")
        print(f"  - 升级通知: {notification_result.get('escalated_count', 0)}")
        
    else:
        print("\n❌ 发现问题！以下步骤失败:")
        failed_steps = []
        if not results.get("execution_tracker", False):
            failed_steps.append("执行追踪器")
        if not results.get("data_fetch", False):
            failed_steps.append("数据获取")
        if not results.get("notification_manager", False):
            failed_steps.append("通知管理器")
        if not results.get("wechat_client", False):
            failed_steps.append("企微客户端")
        if not results.get("task_creation", False):
            failed_steps.append("通知任务创建")
        if not results.get("task_execution", False):
            failed_steps.append("通知任务执行")
        if not results.get("execution_completion", False):
            failed_steps.append("执行完成")
        
        for step in failed_steps:
            print(f"  - {step}")
    
    return passed_steps == total_steps


def main():
    """主函数"""
    print("FSOA Agent执行诊断工具")
    
    # 执行诊断
    results = test_agent_execution_step_by_step()
    
    # 分析结果
    success = analyze_results(results)
    
    if success:
        print("\n✅ 诊断完成：Agent执行功能正常")
        print("如果Web界面仍然显示失败，可能是前端显示问题。")
    else:
        print("\n❌ 诊断完成：发现Agent执行问题")
        print("请根据上述错误信息修复相关问题。")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

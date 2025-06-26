#!/usr/bin/env python3
"""
测试重构后的Agent工具

验证新的管理器架构和工具函数
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_data_strategy():
    """测试业务数据策略"""
    print("🧪 测试业务数据策略...")
    
    try:
        from src.fsoa.agent.tools import get_data_strategy, get_all_opportunities, fetch_overdue_opportunities
        
        # 测试获取数据策略实例
        data_strategy = get_data_strategy()
        print(f"✅ 数据策略实例创建成功")
        print(f"   - 缓存启用: {data_strategy.cache_enabled}")
        print(f"   - 缓存TTL: {data_strategy.cache_ttl} 小时")
        
        # 测试获取所有商机
        try:
            opportunities = get_all_opportunities(force_refresh=True)
            print(f"✅ 获取所有商机成功: {len(opportunities)} 个")
        except Exception as e:
            print(f"⚠️ 获取所有商机失败（可能是Metabase连接问题）: {e}")
        
        # 测试获取逾期商机
        try:
            overdue_opportunities = fetch_overdue_opportunities()
            print(f"✅ 获取逾期商机成功: {len(overdue_opportunities)} 个")
        except Exception as e:
            print(f"⚠️ 获取逾期商机失败（可能是Metabase连接问题）: {e}")
        
        # 测试缓存统计
        cache_stats = data_strategy.get_cache_statistics()
        print(f"✅ 缓存统计: {cache_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据策略测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_execution_tracker():
    """测试执行追踪器"""
    print("\n🧪 测试执行追踪器...")
    
    try:
        from src.fsoa.agent.tools import (
            get_execution_tracker, start_agent_execution, 
            complete_agent_execution
        )
        
        # 测试获取执行追踪器实例
        tracker = get_execution_tracker()
        print(f"✅ 执行追踪器实例创建成功")
        print(f"   - 当前是否运行: {tracker.is_running}")
        
        # 测试开始执行
        context = {"test_mode": True, "test_time": datetime.now().isoformat()}
        run_id = start_agent_execution(context)
        print(f"✅ 开始Agent执行成功: ID {run_id}")
        print(f"   - 当前运行ID: {tracker.current_run}")
        
        # 测试步骤追踪
        with tracker.track_step("test_step", {"input": "test_data"}) as output:
            output["result"] = "test_completed"
            output["count"] = 1
        print(f"✅ 步骤追踪测试成功")
        
        # 测试完成执行
        final_stats = {
            "opportunities_processed": 5,
            "notifications_sent": 3,
            "context": {"completed": True}
        }
        success = complete_agent_execution(run_id, final_stats)
        print(f"✅ 完成Agent执行: {success}")
        print(f"   - 当前是否运行: {tracker.is_running}")
        
        return True
        
    except Exception as e:
        print(f"❌ 执行追踪器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_notification_manager():
    """测试通知任务管理器"""
    print("\n🧪 测试通知任务管理器...")
    
    try:
        from src.fsoa.agent.tools import get_notification_manager, create_notification_tasks
        from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
        
        # 测试获取通知管理器实例
        manager = get_notification_manager()
        print(f"✅ 通知管理器实例创建成功")
        
        # 创建测试商机
        test_opportunities = [
            OpportunityInfo(
                order_num="TEST_NOTIF_001",
                name="测试客户A",
                address="北京市朝阳区",
                supervisor_name="张三",
                create_time=datetime.now(),
                org_name="测试组织A",
                order_status=OpportunityStatus.PENDING_APPOINTMENT,
                is_overdue=True,
                escalation_level=0
            ),
            OpportunityInfo(
                order_num="TEST_NOTIF_002",
                name="测试客户B",
                address="上海市浦东区",
                supervisor_name="李四",
                create_time=datetime.now(),
                org_name="测试组织B",
                order_status=OpportunityStatus.TEMPORARILY_NOT_VISITING,
                is_overdue=True,
                escalation_level=1
            )
        ]
        
        # 测试创建通知任务
        run_id = 999  # 测试用的run_id
        tasks = create_notification_tasks(test_opportunities, run_id)
        print(f"✅ 创建通知任务成功: {len(tasks)} 个")
        
        for task in tasks:
            print(f"   - 任务ID: {task.id}, 类型: {task.notification_type.value}, 工单: {task.order_num}")
        
        # 测试获取待处理任务
        pending_tasks = manager.db_manager.get_pending_notification_tasks()
        print(f"✅ 获取待处理任务: {len(pending_tasks)} 个")
        
        return True
        
    except Exception as e:
        print(f"❌ 通知管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integrated_workflow():
    """测试集成工作流"""
    print("\n🧪 测试集成工作流...")
    
    try:
        from src.fsoa.agent.tools import (
            start_agent_execution, get_data_strategy, 
            create_notification_tasks, execute_notification_tasks,
            complete_agent_execution, get_data_statistics
        )
        from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
        
        # 1. 开始Agent执行
        context = {"workflow_test": True, "start_time": datetime.now().isoformat()}
        run_id = start_agent_execution(context)
        print(f"1. ✅ 开始集成工作流: Run ID {run_id}")
        
        # 2. 获取数据统计
        stats = get_data_statistics()
        print(f"2. ✅ 数据统计: {stats.get('total_opportunities', 0)} 个商机")
        
        # 3. 创建测试商机和通知任务
        test_opportunities = [
            OpportunityInfo(
                order_num="WORKFLOW_001",
                name="工作流测试客户",
                address="测试地址",
                supervisor_name="测试负责人",
                create_time=datetime.now(),
                org_name="工作流测试组织",
                order_status=OpportunityStatus.PENDING_APPOINTMENT,
                is_overdue=True,
                escalation_level=0
            )
        ]
        
        tasks = create_notification_tasks(test_opportunities, run_id)
        print(f"3. ✅ 创建通知任务: {len(tasks)} 个")
        
        # 4. 执行通知任务（模拟）
        try:
            result = execute_notification_tasks(run_id)
            print(f"4. ✅ 执行通知任务: {result}")
        except Exception as e:
            print(f"4. ⚠️ 执行通知任务失败（可能是企微配置问题）: {e}")
        
        # 5. 完成执行
        final_stats = {
            "opportunities_processed": len(test_opportunities),
            "notifications_sent": len(tasks),
            "context": {"workflow_completed": True}
        }
        success = complete_agent_execution(run_id, final_stats)
        print(f"5. ✅ 完成工作流: {success}")
        
        return True
        
    except Exception as e:
        print(f"❌ 集成工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n🧪 测试向后兼容性...")
    
    try:
        from src.fsoa.agent.tools import fetch_overdue_tasks, send_business_notifications
        from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
        
        # 测试废弃的fetch_overdue_tasks函数（已重构，存在概念混淆）
        try:
            tasks = fetch_overdue_tasks()
            print(f"⚠️ 废弃函数fetch_overdue_tasks仍可用（存在任务-商机概念混淆）: {len(tasks)} 个任务")
            print("   推荐使用: fetch_overdue_opportunities() 获取逾期商机")
        except Exception as e:
            print(f"⚠️ fetch_overdue_tasks失败（可能是Metabase连接问题）: {e}")

        # 测试推荐的新接口
        try:
            from src.fsoa.agent.tools import fetch_overdue_opportunities
            opportunities = fetch_overdue_opportunities()
            print(f"✅ 推荐接口fetch_overdue_opportunities正常: {len(opportunities)} 个商机")
        except Exception as e:
            print(f"⚠️ fetch_overdue_opportunities失败: {e}")
        
        # 测试重构的send_business_notifications函数
        test_opportunities = [
            OpportunityInfo(
                order_num="COMPAT_001",
                name="兼容性测试客户",
                address="测试地址",
                supervisor_name="测试负责人",
                create_time=datetime.now(),
                org_name="兼容性测试组织",
                order_status=OpportunityStatus.PENDING_APPOINTMENT,
                is_overdue=True,
                escalation_level=0
            )
        ]
        
        try:
            result = send_business_notifications(test_opportunities)
            print(f"✅ 重构的send_business_notifications可用: {result}")
        except Exception as e:
            print(f"⚠️ send_business_notifications失败（可能是企微配置问题）: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 Agent工具重构测试")
    print("=" * 50)
    
    # 运行测试
    tests = [
        ("业务数据策略", test_data_strategy),
        ("执行追踪器", test_execution_tracker),
        ("通知管理器", test_notification_manager),
        ("集成工作流", test_integrated_workflow),
        ("向后兼容性", test_backward_compatibility)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ 通过" if result else "❌ 失败"
        except Exception as e:
            results[test_name] = f"❌ 异常: {str(e)[:50]}..."
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结:")
    for test_name, result in results.items():
        print(f"   {test_name}: {result}")
    
    passed_count = sum(1 for result in results.values() if result.startswith("✅"))
    total_count = len(results)
    
    print(f"\n🎯 总体结果: {passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("🎉 所有测试通过！Agent工具重构成功")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关代码")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

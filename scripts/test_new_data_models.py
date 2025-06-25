#!/usr/bin/env python3
"""
测试新的数据模型

验证重构后的数据模型功能
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_agent_run_model():
    """测试AgentRun模型"""
    print("🧪 测试AgentRun模型...")
    
    try:
        from src.fsoa.data.models import AgentRun, AgentRunStatus
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        # 创建测试数据
        agent_run = AgentRun(
            trigger_time=datetime.now(),
            status=AgentRunStatus.RUNNING,
            context={"test_mode": True, "opportunities_count": 5},
            opportunities_processed=0,
            notifications_sent=0
        )
        
        # 保存到数据库
        run_id = db_manager.save_agent_run(agent_run)
        print(f"✅ AgentRun保存成功，ID: {run_id}")
        
        # 测试属性
        print(f"   - 是否运行中: {agent_run.is_running}")
        print(f"   - 触发时间: {agent_run.trigger_time}")
        
        # 更新状态
        updates = {
            "end_time": datetime.now(),
            "status": AgentRunStatus.COMPLETED.value,
            "opportunities_processed": 5,
            "notifications_sent": 3
        }
        
        success = db_manager.update_agent_run(run_id, updates)
        print(f"✅ AgentRun更新成功: {success}")
        
        return run_id
        
    except Exception as e:
        print(f"❌ AgentRun模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_agent_history_model(run_id):
    """测试AgentHistory模型"""
    print("\n🧪 测试AgentHistory模型...")
    
    try:
        from src.fsoa.data.models import AgentHistory
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        # 创建测试历史记录
        histories = [
            AgentHistory(
                run_id=run_id,
                step_name="fetch_opportunities",
                timestamp=datetime.now(),
                input_data={"source": "metabase"},
                output_data={"count": 5, "overdue": 3},
                duration_seconds=2.5
            ),
            AgentHistory(
                run_id=run_id,
                step_name="send_notifications",
                timestamp=datetime.now(),
                input_data={"opportunities": 3},
                output_data={"sent": 3, "failed": 0},
                duration_seconds=1.2
            )
        ]
        
        # 保存历史记录
        for history in histories:
            success = db_manager.save_agent_history(history)
            print(f"✅ AgentHistory保存成功: {history.step_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ AgentHistory模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_notification_task_model():
    """测试NotificationTask模型"""
    print("\n🧪 测试NotificationTask模型...")
    
    try:
        from src.fsoa.data.models import NotificationTask, NotificationTaskType, NotificationTaskStatus
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        # 创建测试通知任务
        tasks = [
            NotificationTask(
                order_num="TEST001",
                org_name="测试组织A",
                notification_type=NotificationTaskType.STANDARD,
                due_time=datetime.now(),
                message="标准通知测试消息"
            ),
            NotificationTask(
                order_num="TEST002",
                org_name="测试组织B",
                notification_type=NotificationTaskType.ESCALATION,
                due_time=datetime.now() - timedelta(hours=1),  # 逾期任务
                message="升级通知测试消息"
            )
        ]
        
        task_ids = []
        for task in tasks:
            task_id = db_manager.save_notification_task(task)
            task_ids.append(task_id)
            print(f"✅ NotificationTask保存成功: {task.notification_type.value}, ID: {task_id}")
            print(f"   - 是否待发送: {task.is_pending}")
            print(f"   - 是否逾期: {task.is_overdue}")
        
        # 测试获取待处理任务
        pending_tasks = db_manager.get_pending_notification_tasks()
        print(f"✅ 获取到 {len(pending_tasks)} 个待处理任务")
        
        # 测试更新任务状态
        if task_ids:
            success = db_manager.update_notification_task_status(
                task_ids[0], 
                NotificationTaskStatus.SENT
            )
            print(f"✅ 任务状态更新成功: {success}")
        
        return True
        
    except Exception as e:
        print(f"❌ NotificationTask模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_opportunity_cache_model():
    """测试OpportunityInfo缓存模型"""
    print("\n🧪 测试OpportunityInfo缓存模型...")
    
    try:
        from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        # 创建测试商机
        opportunities = [
            OpportunityInfo(
                order_num="CACHE001",
                name="缓存测试客户A",
                address="北京市朝阳区",
                supervisor_name="张三",
                create_time=datetime.now() - timedelta(hours=30),
                org_name="测试组织A",
                order_status=OpportunityStatus.PENDING_APPOINTMENT
            ),
            OpportunityInfo(
                order_num="CACHE002",
                name="缓存测试客户B",
                address="上海市浦东区",
                supervisor_name="李四",
                create_time=datetime.now() - timedelta(hours=50),
                org_name="测试组织B",
                order_status=OpportunityStatus.TEMPORARILY_NOT_VISITING
            )
        ]
        
        # 更新逾期信息并保存缓存
        for opp in opportunities:
            opp.update_overdue_info()
            print(f"✅ 商机 {opp.order_num}:")
            print(f"   - 已过时长: {opp.elapsed_hours:.1f} 小时")
            print(f"   - 是否逾期: {opp.is_overdue}")
            print(f"   - 升级级别: {opp.escalation_level}")
            print(f"   - 应该缓存: {opp.should_cache()}")
            
            # 保存到缓存
            success = db_manager.save_opportunity_cache(opp)
            print(f"   - 缓存保存: {'成功' if success else '失败'}")
            
            # 测试缓存有效性
            print(f"   - 缓存有效: {opp.is_cache_valid()}")
            print(f"   - 数据哈希: {opp.source_hash[:8]}...")
        
        # 测试从缓存获取
        cached_opp = db_manager.get_opportunity_cache("CACHE001")
        if cached_opp:
            print(f"✅ 从缓存获取商机成功: {cached_opp.order_num}")
        
        # 测试获取所有缓存
        cached_opportunities = db_manager.get_cached_opportunities()
        print(f"✅ 获取到 {len(cached_opportunities)} 个缓存商机")
        
        return True
        
    except Exception as e:
        print(f"❌ OpportunityInfo缓存测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_relationships():
    """测试数据关系"""
    print("\n🧪 测试数据关系...")
    
    try:
        from src.fsoa.data.models import (
            AgentRun, AgentHistory, NotificationTask, OpportunityInfo,
            AgentRunStatus, NotificationTaskType, OpportunityStatus,
            NotificationTaskStatus
        )
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        # 创建一个完整的执行流程
        print("📋 模拟完整的Agent执行流程...")
        
        # 1. 创建Agent运行记录
        agent_run = AgentRun(
            trigger_time=datetime.now(),
            status=AgentRunStatus.RUNNING,
            context={"test_flow": True}
        )
        run_id = db_manager.save_agent_run(agent_run)
        print(f"1. Agent运行开始，ID: {run_id}")
        
        # 2. 记录获取数据步骤
        fetch_history = AgentHistory(
            run_id=run_id,
            step_name="fetch_opportunities",
            timestamp=datetime.now(),
            input_data={"source": "metabase"},
            output_data={"opportunities_found": 2}
        )
        db_manager.save_agent_history(fetch_history)
        print("2. 记录数据获取步骤")
        
        # 3. 创建通知任务
        notification_task = NotificationTask(
            order_num="FLOW001",
            org_name="流程测试组织",
            notification_type=NotificationTaskType.STANDARD,
            due_time=datetime.now(),
            created_run_id=run_id
        )
        task_id = db_manager.save_notification_task(notification_task)
        print(f"3. 创建通知任务，ID: {task_id}")
        
        # 4. 记录发送通知步骤
        send_history = AgentHistory(
            run_id=run_id,
            step_name="send_notifications",
            timestamp=datetime.now(),
            input_data={"tasks": 1},
            output_data={"sent": 1, "failed": 0}
        )
        db_manager.save_agent_history(send_history)
        print("4. 记录通知发送步骤")
        
        # 5. 更新Agent运行状态
        db_manager.update_agent_run(run_id, {
            "end_time": datetime.now(),
            "status": AgentRunStatus.COMPLETED.value,
            "opportunities_processed": 2,
            "notifications_sent": 1
        })
        print("5. 完成Agent运行")
        
        # 6. 更新通知任务状态
        db_manager.update_notification_task_status(
            task_id, 
            NotificationTaskStatus.SENT,
            sent_run_id=run_id
        )
        print("6. 更新通知任务状态")
        
        print("✅ 完整流程测试成功")
        return True
        
    except Exception as e:
        print(f"❌ 数据关系测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 新数据模型功能测试")
    print("=" * 50)
    
    # 运行测试
    tests = [
        ("AgentRun模型", test_agent_run_model),
        ("NotificationTask模型", test_notification_task_model),
        ("OpportunityInfo缓存", test_opportunity_cache_model),
        ("数据关系", test_data_relationships)
    ]
    
    results = {}
    run_id = None
    
    for test_name, test_func in tests:
        try:
            if test_name == "AgentRun模型":
                result = test_func()
                run_id = result
                results[test_name] = "✅ 通过" if result else "❌ 失败"
            elif test_name == "AgentHistory模型" and run_id:
                result = test_func(run_id)
                results[test_name] = "✅ 通过" if result else "❌ 失败"
            else:
                result = test_func()
                results[test_name] = "✅ 通过" if result else "❌ 失败"
        except Exception as e:
            results[test_name] = f"❌ 异常: {str(e)[:50]}..."
    
    # 如果有run_id，测试AgentHistory
    if run_id:
        try:
            result = test_agent_history_model(run_id)
            results["AgentHistory模型"] = "✅ 通过" if result else "❌ 失败"
        except Exception as e:
            results["AgentHistory模型"] = f"❌ 异常: {str(e)[:50]}..."
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结:")
    for test_name, result in results.items():
        print(f"   {test_name}: {result}")
    
    passed_count = sum(1 for result in results.values() if result.startswith("✅"))
    total_count = len(results)
    
    print(f"\n🎯 总体结果: {passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("🎉 所有测试通过！新数据模型功能正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关代码")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

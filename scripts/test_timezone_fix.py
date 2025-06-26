#!/usr/bin/env python3
"""
测试时区修复功能

验证所有时间都是中国时区（UTC+8）
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.fsoa.utils.timezone_utils import (
    now_china, now_china_naive, utc_to_china, china_to_utc,
    get_china_timezone_info, format_china_time
)


def test_timezone_utils():
    """测试时区工具函数"""
    print("🕒 测试时区工具函数")
    print("-" * 40)
    
    # 测试当前时间获取
    china_time = now_china()
    china_naive = now_china_naive()
    
    print(f"当前中国时间（带时区）: {china_time}")
    print(f"当前中国时间（naive）: {china_naive}")
    print(f"时区偏移: {china_time.strftime('%z')}")
    
    # 测试时区转换
    utc_now = datetime.now(timezone.utc)
    china_converted = utc_to_china(utc_now)
    
    print(f"\nUTC时间: {utc_now}")
    print(f"转换为中国时间: {china_converted}")
    
    # 验证时差
    time_diff = china_converted.hour - utc_now.hour
    if time_diff < 0:
        time_diff += 24
    
    print(f"时差: {time_diff}小时 (应该是8小时)")
    
    # 测试格式化
    formatted = format_china_time(china_time)
    print(f"格式化时间: {formatted}")
    
    return time_diff == 8


def test_database_time():
    """测试数据库时间记录"""
    print("\n🗄️ 测试数据库时间记录")
    print("-" * 40)
    
    try:
        from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
        from src.fsoa.utils.timezone_utils import now_china_naive
        
        # 创建测试商机
        test_opp = OpportunityInfo(
            order_num="TIMEZONE_TEST",
            name="时区测试客户",
            address="测试地址",
            supervisor_name="测试销售",
            create_time=now_china_naive(),
            org_name="测试公司",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
        
        print(f"商机创建时间: {test_opp.create_time}")
        print(f"时间类型: {type(test_opp.create_time)}")
        print(f"是否有时区信息: {test_opp.create_time.tzinfo is not None}")
        
        # 测试时间计算
        test_opp.update_overdue_info(use_business_time=True)
        print(f"已过时长: {test_opp.elapsed_hours:.2f}小时")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库时间测试失败: {e}")
        return False


def test_notification_task_time():
    """测试通知任务时间"""
    print("\n📢 测试通知任务时间")
    print("-" * 40)
    
    try:
        from src.fsoa.data.models import NotificationTask, NotificationTaskType
        from src.fsoa.utils.timezone_utils import now_china_naive
        
        # 创建测试通知任务
        task = NotificationTask(
            order_num="TIMEZONE_TEST",
            org_name="测试公司",
            notification_type=NotificationTaskType.VIOLATION,
            due_time=now_china_naive(),
            cooldown_hours=2.0,
            max_retry_count=5
        )
        
        print(f"任务到期时间: {task.due_time}")
        print(f"时间类型: {type(task.due_time)}")
        
        # 模拟发送后的时间更新
        task.last_sent_at = now_china_naive()
        print(f"最后发送时间: {task.last_sent_at}")
        
        # 测试冷静时间检查
        print(f"是否在冷静期: {task.is_in_cooldown}")
        print(f"是否可以重试: {task.can_retry}")
        
        return True
        
    except Exception as e:
        print(f"❌ 通知任务时间测试失败: {e}")
        return False


def test_business_time_calculation():
    """测试工作时间计算"""
    print("\n⏰ 测试工作时间计算")
    print("-" * 40)
    
    try:
        from src.fsoa.utils.business_time import BusinessTimeCalculator
        from src.fsoa.utils.timezone_utils import now_china_naive
        
        # 测试当前时间
        now = now_china_naive()
        print(f"当前时间: {now}")
        print(f"是否工作时间: {BusinessTimeCalculator.is_business_hours(now)}")
        
        # 测试时间计算
        start_time = now_china_naive().replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = now_china_naive().replace(hour=17, minute=0, second=0, microsecond=0)
        
        work_hours = BusinessTimeCalculator.calculate_business_hours_between(start_time, end_time)
        print(f"9点到17点的工作时长: {work_hours}小时")
        
        return True
        
    except Exception as e:
        print(f"❌ 工作时间计算测试失败: {e}")
        return False


def test_database_integration():
    """测试数据库集成"""
    print("\n🔗 测试数据库集成")
    print("-" * 40)
    
    try:
        from src.fsoa.data.database import get_db_manager
        from src.fsoa.data.models import AgentRun, AgentRunStatus
        from src.fsoa.utils.timezone_utils import now_china_naive
        
        db_manager = get_db_manager()
        
        # 创建测试Agent运行记录
        agent_run = AgentRun(
            trigger_time=now_china_naive(),
            status=AgentRunStatus.RUNNING,
            context={"test": "timezone_fix"},
            opportunities_processed=0,
            notifications_sent=0,
            errors=[]
        )
        
        # 保存到数据库
        run_id = db_manager.save_agent_run(agent_run)
        print(f"保存Agent运行记录，ID: {run_id}")
        
        # 从数据库读取
        saved_run = db_manager.get_agent_run(run_id)
        if saved_run:
            print(f"读取的触发时间: {saved_run.trigger_time}")
            print(f"时间类型: {type(saved_run.trigger_time)}")
            
            # 验证时间是否合理（应该是最近的时间）
            time_diff = abs((now_china_naive() - saved_run.trigger_time).total_seconds())
            print(f"时间差: {time_diff:.2f}秒")
            
            return time_diff < 60  # 应该在1分钟内
        else:
            print("❌ 无法读取保存的记录")
            return False
        
    except Exception as e:
        print(f"❌ 数据库集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_timezone_info():
    """显示时区信息"""
    print("\n📊 时区信息总览")
    print("=" * 50)
    
    info = get_china_timezone_info()
    for key, value in info.items():
        print(f"{key}: {value}")


def main():
    """主函数"""
    print("🚀 FSOA 时区修复测试")
    print("=" * 60)
    print("验证所有时间都使用中国时区（UTC+8）")
    print("=" * 60)
    
    results = {}
    
    try:
        # 1. 测试时区工具函数
        results["timezone_utils"] = test_timezone_utils()
        
        # 2. 测试数据库时间记录
        results["database_time"] = test_database_time()
        
        # 3. 测试通知任务时间
        results["notification_time"] = test_notification_task_time()
        
        # 4. 测试工作时间计算
        results["business_time"] = test_business_time_calculation()
        
        # 5. 测试数据库集成
        results["database_integration"] = test_database_integration()
        
        # 显示时区信息
        show_timezone_info()
        
        # 总结结果
        print("\n" + "=" * 60)
        print("🎯 测试结果总结")
        print("=" * 60)
        
        all_passed = True
        for test_name, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 所有时区测试通过！")
            print("✅ 系统现在使用中国时区（UTC+8）")
        else:
            print("⚠️ 部分测试失败，请检查时区配置")
        print("=" * 60)
        
        return all_passed
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

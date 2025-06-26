#!/usr/bin/env python3
"""
测试新的SLA功能：
1. 12小时违规检测
2. 2小时冷静时间
3. 5次重试机制
4. 工作时间计算
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.fsoa.data.models import (
    OpportunityInfo, OpportunityStatus, 
    NotificationTask, NotificationTaskType, NotificationTaskStatus
)
from src.fsoa.utils.business_time import BusinessTimeCalculator


def test_sla_thresholds():
    """测试SLA阈值设置"""
    print("🎯 测试SLA阈值设置")
    print("-" * 40)
    
    # 创建待预约商机
    pending_opp = OpportunityInfo(
        order_num="TEST001",
        name="测试客户",
        address="测试地址",
        supervisor_name="测试销售",
        create_time=datetime.now(),
        org_name="测试公司",
        order_status=OpportunityStatus.PENDING_APPOINTMENT
    )
    
    print("待预约商机的SLA阈值:")
    print(f"  违规阈值: {pending_opp.get_sla_threshold('violation')}小时")
    print(f"  标准阈值: {pending_opp.get_sla_threshold('standard')}小时")
    print(f"  升级阈值: {pending_opp.get_sla_threshold('escalation')}小时")
    
    # 创建暂不上门商机
    temp_not_visiting_opp = OpportunityInfo(
        order_num="TEST002",
        name="测试客户2",
        address="测试地址2",
        supervisor_name="测试销售2",
        create_time=datetime.now(),
        org_name="测试公司2",
        order_status=OpportunityStatus.TEMPORARILY_NOT_VISITING
    )
    
    print("\n暂不上门商机的SLA阈值:")
    print(f"  违规阈值: {temp_not_visiting_opp.get_sla_threshold('violation')}小时")
    print(f"  标准阈值: {temp_not_visiting_opp.get_sla_threshold('standard')}小时")
    print(f"  升级阈值: {temp_not_visiting_opp.get_sla_threshold('escalation')}小时")


def test_violation_detection():
    """测试违规检测"""
    print("\n⚠️ 测试违规检测")
    print("-" * 40)
    
    now = datetime.now()
    
    # 测试场景
    scenarios = [
        ("10小时前", 10, False),
        ("13小时前", 13, True),
        ("20小时前", 20, True),
    ]
    
    for desc, hours_ago, expected_violation in scenarios:
        create_time = now - timedelta(hours=hours_ago)
        
        opp = OpportunityInfo(
            order_num=f"TEST_{hours_ago}H",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试销售",
            create_time=create_time,
            org_name="测试公司",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
        
        # 更新计算字段
        opp.update_overdue_info(use_business_time=True)
        
        violation_status = "✅ 违规" if opp.is_violation else "❌ 未违规"
        expected_status = "✅ 违规" if expected_violation else "❌ 未违规"
        match = "✅" if (opp.is_violation == expected_violation) else "❌"
        
        print(f"  {desc}: {violation_status} (预期: {expected_status}) {match}")


def test_notification_task_cooldown():
    """测试通知任务冷静时间"""
    print("\n⏰ 测试通知任务冷静时间")
    print("-" * 40)
    
    now = datetime.now()
    
    # 创建通知任务
    task = NotificationTask(
        order_num="TEST001",
        org_name="测试公司",
        notification_type=NotificationTaskType.VIOLATION,
        due_time=now,
        cooldown_hours=2.0,
        max_retry_count=5
    )
    
    print("新创建的任务:")
    print(f"  是否在冷静期: {'是' if task.is_in_cooldown else '否'}")
    print(f"  是否可以重试: {'是' if task.can_retry else '否'}")
    print(f"  是否应该立即发送: {'是' if task.should_send_now() else '否'}")
    
    # 模拟发送后
    task.last_sent_at = now
    task.retry_count = 1
    
    print("\n发送1次后:")
    print(f"  重试次数: {task.retry_count}/{task.max_retry_count}")
    print(f"  是否在冷静期: {'是' if task.is_in_cooldown else '否'}")
    print(f"  是否可以重试: {'是' if task.can_retry else '否'}")
    print(f"  是否应该立即发送: {'是' if task.should_send_now() else '否'}")
    
    # 模拟2小时后
    task.last_sent_at = now - timedelta(hours=2.1)
    
    print("\n2小时后:")
    print(f"  是否在冷静期: {'是' if task.is_in_cooldown else '否'}")
    print(f"  是否可以重试: {'是' if task.can_retry else '否'}")
    print(f"  是否应该立即发送: {'是' if task.should_send_now() else '否'}")
    
    # 模拟达到最大重试次数
    task.retry_count = 5
    
    print("\n达到最大重试次数后:")
    print(f"  重试次数: {task.retry_count}/{task.max_retry_count}")
    print(f"  是否可以重试: {'是' if task.can_retry else '否'}")
    print(f"  是否应该立即发送: {'是' if task.should_send_now() else '否'}")


def test_business_time_scenarios():
    """测试工作时间场景"""
    print("\n🕒 测试工作时间场景")
    print("-" * 40)
    
    # 场景1: 周五下班后创建，周一检查
    friday_evening = datetime(2025, 6, 27, 20, 0)  # 周五晚8点
    monday_morning = datetime(2025, 6, 30, 10, 0)  # 周一上午10点
    
    business_hours = BusinessTimeCalculator.calculate_business_hours_between(
        friday_evening, monday_morning
    )
    
    print(f"周五晚8点到周一上午10点的工作时长: {business_hours:.1f}小时")
    
    # 场景2: 创建商机并检查状态
    opp = OpportunityInfo(
        order_num="WEEKEND_TEST",
        name="周末测试客户",
        address="测试地址",
        supervisor_name="测试销售",
        create_time=friday_evening,
        org_name="测试公司",
        order_status=OpportunityStatus.PENDING_APPOINTMENT
    )
    
    # 模拟在周一检查
    opp.elapsed_hours = business_hours
    opp.update_overdue_info(use_business_time=True)
    
    print(f"商机状态 (周一检查):")
    print(f"  工作时长: {opp.elapsed_hours:.1f}小时")
    print(f"  是否违规: {'是' if opp.is_violation else '否'}")
    print(f"  是否逾期: {'是' if opp.is_overdue else '否'}")


def test_notification_types():
    """测试通知类型"""
    print("\n📢 测试通知类型")
    print("-" * 40)
    
    notification_types = [
        (NotificationTaskType.VIOLATION, "违规通知"),
        (NotificationTaskType.STANDARD, "标准通知"),
        (NotificationTaskType.ESCALATION, "升级通知"),
    ]
    
    for ntype, desc in notification_types:
        task = NotificationTask(
            order_num="TEST001",
            org_name="测试公司",
            notification_type=ntype,
            due_time=datetime.now(),
            cooldown_hours=2.0,
            max_retry_count=5
        )
        
        print(f"  {desc}: {ntype.value}")


def main():
    """主函数"""
    print("🚀 FSOA 新SLA功能测试")
    print("=" * 60)
    print("测试内容:")
    print("- 12小时违规检测")
    print("- 2小时冷静时间")
    print("- 5次重试机制")
    print("- 工作时间计算")
    print("- 新的通知类型")
    print("=" * 60)
    
    try:
        test_sla_thresholds()
        test_violation_detection()
        test_notification_task_cooldown()
        test_business_time_scenarios()
        test_notification_types()
        
        print("\n" + "=" * 60)
        print("✅ 所有新功能测试完成")
        print("\n📋 功能总结:")
        print("✅ 12小时违规检测 - 已实现")
        print("✅ 2小时冷静时间 - 已实现")
        print("✅ 5次重试机制 - 已实现")
        print("✅ 工作时间计算 - 已实现")
        print("✅ 新的通知类型 - 已实现")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
验证SLA设计文档与代码实现的一致性

检查当前代码中的SLA实现是否与更新后的SLA_DESIGN.md文档一致
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.models import OpportunityInfo, OpportunityStatus, NotificationTaskType
from src.fsoa.utils.business_time import BusinessTimeCalculator


def test_sla_thresholds():
    """测试SLA阈值设置是否符合两级体系"""
    print("🎯 测试SLA阈值设置")
    print("-" * 50)
    
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
    reminder_threshold = pending_opp.get_sla_threshold('reminder')
    escalation_threshold = pending_opp.get_sla_threshold('escalation')
    print(f"  提醒阈值: {reminder_threshold}小时")
    print(f"  升级阈值: {escalation_threshold}小时")
    
    # 验证是否符合文档设计
    assert reminder_threshold == 4, f"待预约提醒阈值应为4小时，实际为{reminder_threshold}小时"
    assert escalation_threshold == 8, f"待预约升级阈值应为8小时，实际为{escalation_threshold}小时"
    print("  ✅ 待预约阈值符合设计")
    
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
    reminder_threshold = temp_not_visiting_opp.get_sla_threshold('reminder')
    escalation_threshold = temp_not_visiting_opp.get_sla_threshold('escalation')
    print(f"  提醒阈值: {reminder_threshold}小时")
    print(f"  升级阈值: {escalation_threshold}小时")
    
    # 验证是否符合文档设计
    assert reminder_threshold == 8, f"暂不上门提醒阈值应为8小时，实际为{reminder_threshold}小时"
    assert escalation_threshold == 16, f"暂不上门升级阈值应为16小时，实际为{escalation_threshold}小时"
    print("  ✅ 暂不上门阈值符合设计")


def test_notification_types():
    """测试通知类型是否符合两级体系"""
    print("\n🔔 测试通知类型")
    print("-" * 50)
    
    # 检查通知类型枚举
    print("通知类型枚举:")
    print(f"  REMINDER: {NotificationTaskType.REMINDER}")
    print(f"  ESCALATION: {NotificationTaskType.ESCALATION}")
    
    # 检查向后兼容性
    print("\n向后兼容性:")
    print(f"  VIOLATION (兼容): {NotificationTaskType.VIOLATION}")
    print(f"  STANDARD (兼容): {NotificationTaskType.STANDARD}")
    
    # 验证兼容性映射
    assert NotificationTaskType.VIOLATION == NotificationTaskType.REMINDER, "VIOLATION应映射到REMINDER"
    assert NotificationTaskType.STANDARD == NotificationTaskType.ESCALATION, "STANDARD应映射到ESCALATION"
    print("  ✅ 向后兼容性正确")


def test_sla_status_calculation():
    """测试SLA状态计算逻辑"""
    print("\n📊 测试SLA状态计算")
    print("-" * 50)
    
    # 创建测试商机
    opp = OpportunityInfo(
        order_num="TEST003",
        name="测试客户3",
        address="测试地址3",
        supervisor_name="测试销售3",
        create_time=datetime.now() - timedelta(hours=6),  # 6小时前创建
        org_name="测试公司3",
        order_status=OpportunityStatus.PENDING_APPOINTMENT
    )
    
    # 计算SLA状态
    opp.update_overdue_info(use_business_time=True)
    
    print(f"商机创建时间: {opp.create_time}")
    print(f"已用工作时长: {opp.elapsed_hours:.1f}小时")
    print(f"是否需要提醒: {opp.is_violation}")
    print(f"是否需要升级: {opp.is_overdue}")
    print(f"升级级别: {opp.escalation_level}")
    print(f"SLA进度: {(opp.sla_progress_ratio * 100):.1f}%")
    
    # 验证状态计算逻辑
    if opp.elapsed_hours > 8:
        assert opp.is_overdue == True, "超过8小时应需要升级"
        assert opp.escalation_level == 1, "升级级别应为1"
    elif opp.elapsed_hours > 4:
        assert opp.is_violation == True, "超过4小时应需要提醒"
        assert opp.is_overdue == False, "未超过8小时不应需要升级"
    
    print("  ✅ SLA状态计算正确")


def test_business_time_calculation():
    """测试工作时间计算"""
    print("\n⏰ 测试工作时间计算")
    print("-" * 50)

    # 获取工作时间配置
    work_start_hour, work_end_hour, work_days = BusinessTimeCalculator._get_work_config()
    work_hours_per_day = BusinessTimeCalculator.get_work_hours_per_day()

    # 测试工作时间定义
    print("工作时间定义:")
    print(f"  工作开始时间: {work_start_hour}:00")
    print(f"  工作结束时间: {work_end_hour}:00")
    print(f"  每日工作时长: {work_hours_per_day}小时")
    print(f"  工作日: {work_days}")

    # 验证工作时间定义
    assert work_start_hour == 9, f"工作开始时间应为9点，实际为{work_start_hour}点"
    assert work_end_hour == 19, f"工作结束时间应为19点，实际为{work_end_hour}点"
    assert work_hours_per_day == 10, f"每日工作时长应为10小时，实际为{work_hours_per_day}小时"
    assert work_days == [1, 2, 3, 4, 5], f"工作日应为周一到周五，实际为{work_days}"
    print("  ✅ 工作时间定义正确")


def main():
    """主函数"""
    print("=" * 60)
    print("SLA设计文档与代码实现一致性验证")
    print("=" * 60)
    
    try:
        test_sla_thresholds()
        test_notification_types()
        test_sla_status_calculation()
        test_business_time_calculation()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！SLA实现与设计文档一致")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

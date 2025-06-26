#!/usr/bin/env python3
"""
测试工作时间计算功能
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.fsoa.utils.business_time import BusinessTimeCalculator, calculate_business_elapsed_hours
from src.fsoa.data.models import OpportunityInfo, OpportunityStatus


def test_business_time_calculation():
    """测试工作时间计算"""
    print("🧪 测试工作时间计算功能")
    print("=" * 50)
    
    # 测试1: 工作时间判断
    print("\n1. 工作时间判断测试:")
    test_times = [
        datetime(2025, 6, 26, 9, 0),   # 周三 9:00 - 工作时间
        datetime(2025, 6, 26, 18, 30), # 周三 18:30 - 非工作时间
        datetime(2025, 6, 28, 10, 0),  # 周五 10:00 - 工作时间
        datetime(2025, 6, 29, 10, 0),  # 周六 10:00 - 非工作时间
    ]
    
    for dt in test_times:
        is_business = BusinessTimeCalculator.is_business_hours(dt)
        weekday = dt.strftime("%A")
        print(f"   {dt.strftime('%Y-%m-%d %H:%M')} ({weekday}): {'✅ 工作时间' if is_business else '❌ 非工作时间'}")
    
    # 测试2: 工作时长计算
    print("\n2. 工作时长计算测试:")
    
    # 场景1: 同一工作日内
    start1 = datetime(2025, 6, 26, 9, 0)   # 周三 9:00
    end1 = datetime(2025, 6, 26, 17, 0)    # 周三 17:00
    hours1 = BusinessTimeCalculator.calculate_business_hours_between(start1, end1)
    print(f"   同一工作日 {start1.strftime('%m-%d %H:%M')} 到 {end1.strftime('%m-%d %H:%M')}: {hours1:.1f}小时")
    
    # 场景2: 跨工作日
    start2 = datetime(2025, 6, 26, 15, 0)  # 周三 15:00
    end2 = datetime(2025, 6, 27, 11, 0)    # 周四 11:00
    hours2 = BusinessTimeCalculator.calculate_business_hours_between(start2, end2)
    print(f"   跨工作日 {start2.strftime('%m-%d %H:%M')} 到 {end2.strftime('%m-%d %H:%M')}: {hours2:.1f}小时")
    
    # 场景3: 跨周末
    start3 = datetime(2025, 6, 27, 16, 0)  # 周五 16:00
    end3 = datetime(2025, 6, 30, 10, 0)    # 周一 10:00
    hours3 = BusinessTimeCalculator.calculate_business_hours_between(start3, end3)
    print(f"   跨周末 {start3.strftime('%m-%d %H:%M')} 到 {end3.strftime('%m-%d %H:%M')}: {hours3:.1f}小时")


def test_opportunity_sla_rules():
    """测试商机SLA规则"""
    print("\n🎯 测试新的SLA规则")
    print("=" * 50)
    
    # 创建测试商机
    now = datetime.now()
    
    # 测试场景
    test_scenarios = [
        {
            "name": "8小时前创建的待预约",
            "create_time": now - timedelta(hours=8),
            "status": OpportunityStatus.PENDING_APPOINTMENT,
            "expected": "未违规，未逾期"
        },
        {
            "name": "15小时前创建的待预约",
            "create_time": now - timedelta(hours=15),
            "status": OpportunityStatus.PENDING_APPOINTMENT,
            "expected": "已违规，未逾期"
        },
        {
            "name": "30小时前创建的待预约",
            "create_time": now - timedelta(hours=30),
            "status": OpportunityStatus.PENDING_APPOINTMENT,
            "expected": "已违规，已逾期，需升级"
        },
        {
            "name": "60小时前创建的暂不上门",
            "create_time": now - timedelta(hours=60),
            "status": OpportunityStatus.TEMPORARILY_NOT_VISITING,
            "expected": "已违规，已逾期，需升级"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📋 {scenario['name']}:")
        
        # 创建商机对象
        opp = OpportunityInfo(
            order_num=f"TEST{scenario['name'][:3]}",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试销售",
            create_time=scenario['create_time'],
            org_name="测试公司",
            order_status=scenario['status']
        )
        
        # 更新计算字段
        opp.update_overdue_info(use_business_time=True)
        
        # 显示结果
        print(f"   创建时间: {opp.create_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   工作时长: {opp.elapsed_hours:.1f}小时")
        print(f"   违规阈值: {opp.get_sla_threshold('violation')}小时")
        print(f"   标准阈值: {opp.get_sla_threshold('standard')}小时")
        print(f"   升级阈值: {opp.get_sla_threshold('escalation')}小时")
        print(f"   是否违规: {'✅' if opp.is_violation else '❌'}")
        print(f"   是否逾期: {'✅' if opp.is_overdue else '❌'}")
        print(f"   升级级别: {opp.escalation_level}")
        print(f"   预期结果: {scenario['expected']}")


def main():
    """主函数"""
    print("🚀 FSOA 新功能测试")
    print("测试工作时间计算和新的SLA规则")
    print("=" * 60)
    
    try:
        test_business_time_calculation()
        test_opportunity_sla_rules()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

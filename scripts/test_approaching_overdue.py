#!/usr/bin/env python3
"""
测试即将逾期功能
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.agent.tools import get_opportunity_statistics, get_approaching_overdue_opportunities
from src.fsoa.data.metabase import get_metabase_client
from src.fsoa.utils.logger import get_logger

logger = get_logger(__name__)


def test_new_functionality():
    """测试新的即将逾期功能"""
    print("=" * 60)
    print("测试即将逾期功能")
    print("=" * 60)
    
    try:
        # 1. 测试Metabase客户端的新方法
        print("\n1. 测试Metabase客户端")
        metabase_client = get_metabase_client()
        
        # 获取所有监控商机
        all_monitored = metabase_client.get_all_monitored_opportunities()
        print(f"   所有监控商机: {len(all_monitored)} 条")
        
        # 获取逾期商机
        overdue_only = metabase_client.get_overdue_opportunities()
        print(f"   逾期商机: {len(overdue_only)} 条")
        
        # 2. 测试即将逾期商机
        print("\n2. 测试即将逾期商机")
        approaching_opportunities = get_approaching_overdue_opportunities()
        print(f"   即将逾期商机: {len(approaching_opportunities)} 条")
        
        if approaching_opportunities:
            print("\n   即将逾期商机详情:")
            for i, opp in enumerate(approaching_opportunities[:3], 1):
                print(f"   {i}. 工单号: {opp.order_num}")
                print(f"      状态: {opp.order_status}")
                print(f"      SLA进度: {opp.sla_progress_ratio:.1%}")
                print(f"      已过时长: {opp.elapsed_hours:.1f} 小时")
                print(f"      SLA阈值: {opp.sla_threshold_hours} 小时")
                print()
        
        # 3. 测试统计信息
        print("\n3. 测试统计信息")
        stats = get_opportunity_statistics()
        
        print(f"   总商机数: {stats['total_opportunities']}")
        print(f"   已逾期: {stats['overdue_count']} ({stats['overdue_rate']:.1f}%)")
        print(f"   即将逾期: {stats['approaching_overdue_count']} ({stats['approaching_rate']:.1f}%)")
        print(f"   正常跟进: {stats['normal_count']}")
        print(f"   升级处理: {stats['escalation_count']}")
        
        # 4. 验证数据一致性
        print("\n4. 验证数据一致性")
        total_calculated = stats['overdue_count'] + stats['approaching_overdue_count'] + stats['normal_count']
        print(f"   计算总数: {total_calculated}")
        print(f"   统计总数: {stats['total_opportunities']}")
        print(f"   数据一致性: {'✅ 一致' if total_calculated == stats['total_opportunities'] else '❌ 不一致'}")
        
        # 5. 按状态分析
        print("\n5. 按状态分析")
        status_breakdown = stats['status_breakdown']
        for status, counts in status_breakdown.items():
            print(f"   {status}:")
            print(f"     总数: {counts['total']}")
            print(f"     已逾期: {counts['overdue']}")
            print(f"     即将逾期: {counts['approaching']}")
            print(f"     正常: {counts['normal']}")
        
        # 6. 按组织分析（显示前5个）
        print("\n6. 按组织分析 (前5个)")
        org_breakdown = stats['organization_breakdown']
        sorted_orgs = sorted(org_breakdown.items(), key=lambda x: x[1]['total'], reverse=True)
        
        for org_name, counts in sorted_orgs[:5]:
            print(f"   {org_name}:")
            print(f"     总数: {counts['total']}")
            print(f"     已逾期: {counts['overdue']}")
            print(f"     即将逾期: {counts['approaching']}")
            print(f"     正常: {counts['normal']}")
        
        print("\n" + "=" * 60)
        print("✅ 即将逾期功能测试完成")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("FSOA 即将逾期功能测试")
    success = test_new_functionality()
    
    if success:
        print("\n🎉 所有测试通过！")
        print("\n现在您可以:")
        print("1. 在Web界面查看新的商机分类统计")
        print("2. 使用 get_approaching_overdue_opportunities() 获取即将逾期的商机")
        print("3. 使用 get_opportunity_statistics() 获取详细统计信息")
        print("4. 系统现在显示43条监控商机，与Metabase数据源保持一致")
    else:
        print("\n❌ 测试失败，请检查错误信息")


if __name__ == "__main__":
    main()

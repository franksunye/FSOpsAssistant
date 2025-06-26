#!/usr/bin/env python3
"""
检查Metabase数据源和逾期商机处理逻辑
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.metabase import get_metabase_client
from src.fsoa.agent.tools import get_data_strategy, fetch_overdue_opportunities
from src.fsoa.utils.logger import get_logger

logger = get_logger(__name__)


def check_metabase_raw_data():
    """检查Metabase原始数据"""
    print("=" * 60)
    print("检查Metabase原始数据")
    print("=" * 60)
    
    try:
        metabase_client = get_metabase_client()
        
        # 测试认证
        auth_success = metabase_client.authenticate()
        print(f"Metabase认证: {'成功' if auth_success else '失败'}")
        
        if not auth_success:
            print("❌ Metabase认证失败，无法继续检查")
            return None
        
        # 获取原始数据
        raw_data = metabase_client.get_field_service_opportunities()
        print(f"Card 1712 原始数据: {len(raw_data)} 条")
        
        if not raw_data:
            print("❌ 没有获取到原始数据")
            return None
        
        # 分析状态分布
        status_count = {}
        for item in raw_data:
            status = item.get('orderstatus', '未知')
            status_count[status] = status_count.get(status, 0) + 1
        
        print("\n状态分布:")
        for status, count in sorted(status_count.items()):
            print(f"  {status}: {count} 条")
        
        # 检查监控状态的数据
        monitored_statuses = ['待预约', '暂不上门']
        monitored_data = [item for item in raw_data if item.get('orderstatus') in monitored_statuses]
        print(f"\n符合监控条件的数据: {len(monitored_data)} 条")
        
        # 显示前3条监控数据的详情
        if monitored_data:
            print("\n前3条监控数据详情:")
            for i, item in enumerate(monitored_data[:3], 1):
                print(f"{i}. 工单号: {item.get('orderNum', 'N/A')}")
                print(f"   状态: {item.get('orderstatus', 'N/A')}")
                print(f"   创建时间: {item.get('createTime', 'N/A')}")
                print(f"   组织: {item.get('orgName', 'N/A')}")
                print()
        
        return raw_data
        
    except Exception as e:
        print(f"❌ 检查Metabase原始数据失败: {e}")
        logger.error(f"Failed to check Metabase raw data: {e}")
        return None


def check_overdue_processing():
    """检查逾期商机处理逻辑"""
    print("=" * 60)
    print("检查逾期商机处理逻辑")
    print("=" * 60)
    
    try:
        metabase_client = get_metabase_client()
        
        # 1. 使用Metabase客户端的逾期商机方法
        overdue_from_metabase = metabase_client.get_overdue_opportunities()
        print(f"Metabase客户端逾期商机: {len(overdue_from_metabase)} 条")
        
        # 2. 使用数据策略的逾期商机方法
        data_strategy = get_data_strategy()
        overdue_from_strategy = data_strategy.get_overdue_opportunities(force_refresh=True)
        print(f"数据策略逾期商机: {len(overdue_from_strategy)} 条")
        
        # 3. 使用工具函数的逾期商机方法
        overdue_from_tools = fetch_overdue_opportunities(force_refresh=True)
        print(f"工具函数逾期商机: {len(overdue_from_tools)} 条")
        
        # 分析第一个逾期商机的详细信息
        if overdue_from_tools:
            print(f"\n第一个逾期商机详情:")
            first_opp = overdue_from_tools[0]
            print(f"  工单号: {first_opp.order_num}")
            print(f"  状态: {first_opp.order_status}")
            print(f"  创建时间: {first_opp.create_time}")
            print(f"  已过时长: {first_opp.elapsed_hours:.1f} 小时")
            print(f"  SLA阈值: {first_opp.sla_threshold_hours} 小时")
            print(f"  是否逾期: {first_opp.is_overdue}")
            print(f"  逾期时长: {first_opp.overdue_hours:.1f} 小时")
            print(f"  升级级别: {first_opp.escalation_level}")
        
        # 分析逾期商机的状态分布
        if overdue_from_tools:
            print(f"\n逾期商机状态分布:")
            overdue_status_count = {}
            for opp in overdue_from_tools:
                status = str(opp.order_status)
                overdue_status_count[status] = overdue_status_count.get(status, 0) + 1
            
            for status, count in sorted(overdue_status_count.items()):
                print(f"  {status}: {count} 条")
        
        return overdue_from_tools
        
    except Exception as e:
        print(f"❌ 检查逾期商机处理失败: {e}")
        logger.error(f"Failed to check overdue processing: {e}")
        return None


def analyze_discrepancy(raw_data, overdue_data):
    """分析数据差异"""
    print("=" * 60)
    print("分析数据差异")
    print("=" * 60)
    
    if not raw_data or not overdue_data:
        print("❌ 缺少数据，无法进行差异分析")
        return
    
    # 统计原始数据中符合监控条件的数量
    monitored_statuses = ['待预约', '暂不上门']
    monitored_raw = [item for item in raw_data if item.get('orderstatus') in monitored_statuses]
    
    print(f"原始数据总数: {len(raw_data)} 条")
    print(f"符合监控条件的原始数据: {len(monitored_raw)} 条")
    print(f"处理后的逾期商机: {len(overdue_data)} 条")
    print(f"数据差异: {len(monitored_raw) - len(overdue_data)} 条")
    
    if len(monitored_raw) != len(overdue_data):
        print(f"\n⚠️  发现数据差异！")
        print(f"预期逾期商机数量: {len(monitored_raw)}")
        print(f"实际逾期商机数量: {len(overdue_data)}")
        
        # 分析可能的原因
        print(f"\n可能的原因分析:")
        
        # 检查时间解析问题
        time_parse_errors = 0
        for item in monitored_raw:
            try:
                create_time = item.get('createTime')
                if create_time:
                    if isinstance(create_time, str):
                        datetime.fromisoformat(create_time.replace('Z', '+00:00'))
            except Exception:
                time_parse_errors += 1
        
        if time_parse_errors > 0:
            print(f"  - 时间解析错误: {time_parse_errors} 条")
        
        # 检查状态映射问题
        status_mapping_errors = 0
        for item in monitored_raw:
            status = item.get('orderstatus')
            if status not in ['待预约', '暂不上门']:
                status_mapping_errors += 1
        
        if status_mapping_errors > 0:
            print(f"  - 状态映射错误: {status_mapping_errors} 条")
        
        # 显示一些未被处理的数据示例
        processed_order_nums = {opp.order_num for opp in overdue_data}
        unprocessed = [item for item in monitored_raw if item.get('orderNum') not in processed_order_nums]
        
        if unprocessed:
            print(f"\n未被处理的数据示例 (前3条):")
            for i, item in enumerate(unprocessed[:3], 1):
                print(f"{i}. 工单号: {item.get('orderNum', 'N/A')}")
                print(f"   状态: {item.get('orderstatus', 'N/A')}")
                print(f"   创建时间: {item.get('createTime', 'N/A')}")
                print()
    else:
        print(f"\n✅ 数据一致，逾期商机处理逻辑正常")


def main():
    """主函数"""
    print("FSOA 逾期商机数据检查工具")
    print("=" * 60)
    
    # 1. 检查Metabase原始数据
    raw_data = check_metabase_raw_data()
    
    # 2. 检查逾期商机处理逻辑
    overdue_data = check_overdue_processing()
    
    # 3. 分析数据差异
    analyze_discrepancy(raw_data, overdue_data)
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)


if __name__ == "__main__":
    main()

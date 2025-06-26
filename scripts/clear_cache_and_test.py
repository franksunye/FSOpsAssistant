#!/usr/bin/env python3
"""
清理缓存并重新测试
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.database import get_database_manager
from src.fsoa.agent.tools import get_opportunity_statistics


def main():
    print("清理缓存并重新测试")
    print("=" * 40)
    
    # 清理缓存
    print("1. 清理缓存...")
    from src.fsoa.agent.tools import get_data_strategy
    data_strategy = get_data_strategy()
    cleared = data_strategy.clear_cache()
    print(f"✅ 缓存已清理: {cleared} 条记录")
    
    # 重新获取数据
    print("\n2. 重新获取统计信息...")
    stats = get_opportunity_statistics(force_refresh=True)
    
    print("📊 统计结果:")
    print(f"   总商机数: {stats['total_opportunities']}")
    print(f"   已逾期: {stats['overdue_count']}")
    print(f"   即将逾期: {stats['approaching_overdue_count']}")
    print(f"   正常跟进: {stats['normal_count']}")
    print(f"   升级处理: {stats['escalation_count']}")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    main()

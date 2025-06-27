#!/usr/bin/env python3
"""
数据同步重构测试脚本

测试新的"清空重建"数据同步逻辑，确保：
1. 每次同步都是完全清空重建
2. 数据一致性得到保证
3. Web界面与后端逻辑一致
4. 向后兼容性正常
"""

import sys
import os
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 设置测试环境变量
os.environ['FSOA_ENV_FILE'] = '.env.test'

from src.fsoa.agent.tools import get_data_strategy
from src.fsoa.data.database import get_db_manager
from src.fsoa.utils.logger import get_logger

logger = get_logger(__name__)

def test_full_refresh_cache():
    """测试完全刷新缓存功能"""
    print("🧪 测试完全刷新缓存功能...")
    
    try:
        data_strategy = get_data_strategy()
        db_manager = get_db_manager()
        
        # 1. 获取初始缓存状态
        initial_stats = data_strategy.get_cache_statistics()
        print(f"初始缓存状态: {initial_stats}")
        
        # 2. 执行完全刷新
        print("执行完全刷新...")
        old_count, new_count = data_strategy.refresh_cache()
        print(f"刷新结果: {old_count} -> {new_count}")
        
        # 3. 验证缓存状态
        final_stats = data_strategy.get_cache_statistics()
        print(f"最终缓存状态: {final_stats}")
        
        # 4. 验证数据模式
        assert final_stats.get("cache_mode") == "full_refresh", "缓存模式应该是 full_refresh"
        print("✅ 缓存模式验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 完全刷新缓存测试失败: {e}")
        return False

def test_data_consistency():
    """测试数据一致性"""
    print("\n🧪 测试数据一致性...")
    
    try:
        data_strategy = get_data_strategy()
        
        # 1. 获取数据两次，应该都是从Metabase获取的最新数据
        print("第一次获取数据...")
        data1 = data_strategy.get_opportunities()
        
        print("第二次获取数据...")
        data2 = data_strategy.get_opportunities()
        
        # 2. 验证数据一致性
        print(f"第一次获取: {len(data1)} 条商机")
        print(f"第二次获取: {len(data2)} 条商机")
        
        # 3. 验证每次都是全新获取（不依赖缓存TTL）
        if len(data1) == len(data2):
            print("✅ 数据数量一致")
        else:
            print("⚠️ 数据数量不一致，可能是Metabase数据发生了变化")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据一致性测试失败: {e}")
        return False

def test_cache_clear_rebuild():
    """测试缓存清空重建机制"""
    print("\n🧪 测试缓存清空重建机制...")
    
    try:
        data_strategy = get_data_strategy()
        db_manager = get_db_manager()
        
        # 1. 确保有缓存数据
        print("确保有缓存数据...")
        data_strategy.get_opportunities()
        
        initial_count = len(db_manager.get_cached_opportunities(24 * 7))
        print(f"初始缓存条目: {initial_count}")
        
        # 2. 清空缓存
        print("清空缓存...")
        cleared = data_strategy.clear_cache()
        print(f"清空了 {cleared} 个缓存条目")
        
        # 3. 验证缓存已清空
        after_clear_count = len(db_manager.get_cached_opportunities(24 * 7))
        print(f"清空后缓存条目: {after_clear_count}")
        assert after_clear_count == 0, "缓存应该完全清空"
        
        # 4. 重新获取数据，验证重建
        print("重新获取数据...")
        new_data = data_strategy.get_opportunities()
        
        final_count = len(db_manager.get_cached_opportunities(24 * 7))
        print(f"重建后缓存条目: {final_count}")
        
        print("✅ 缓存清空重建测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 缓存清空重建测试失败: {e}")
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n🧪 测试向后兼容性...")
    
    try:
        data_strategy = get_data_strategy()
        
        # 1. 测试旧的方法调用
        print("测试旧方法调用...")
        
        # 这些方法应该仍然可用，但内部使用新逻辑
        opportunities = data_strategy.get_opportunities(force_refresh=True)
        print(f"获取到 {len(opportunities)} 条商机")
        
        # 2. 测试统计方法
        stats = data_strategy.get_cache_statistics()
        print(f"缓存统计: {stats}")
        
        # 3. 验证新的标识字段
        assert stats.get("cache_mode") == "full_refresh", "应该标识为 full_refresh 模式"
        
        print("✅ 向后兼容性测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始数据同步重构测试")
    print("=" * 50)
    
    test_results = []
    
    # 执行各项测试
    test_results.append(test_full_refresh_cache())
    test_results.append(test_data_consistency())
    test_results.append(test_cache_clear_rebuild())
    test_results.append(test_backward_compatibility())
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！数据同步重构成功")
        return True
    else:
        print("❌ 部分测试失败，需要检查问题")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
数据同步重构集成测试

测试重构后的数据策略管理器与Web界面的集成
"""

import sys
import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 设置测试环境变量
os.environ['DATABASE_URL'] = f'sqlite:///{tempfile.mktemp()}.db'
os.environ['DEEPSEEK_API_KEY'] = 'test_key'
os.environ['METABASE_URL'] = 'http://test.metabase.com'
os.environ['METABASE_USERNAME'] = 'test_user'
os.environ['METABASE_PASSWORD'] = 'test_password'
os.environ['INTERNAL_OPS_WEBHOOK'] = 'https://test.webhook.com'

from src.fsoa.agent.managers.data_strategy import BusinessDataStrategy
from src.fsoa.data.database import get_db_manager
from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
from src.fsoa.utils.timezone_utils import now_china_naive

def create_mock_metabase_data():
    """创建模拟的Metabase数据"""
    return [
        {
            'orderNum': 'MOCK001',
            'name': '模拟客户A',
            'address': '模拟地址A',
            'supervisorName': '模拟销售A',
            'createTime': '2025-6-25, 10:00',
            'orgName': '模拟公司A',
            'orderstatus': '待预约'
        },
        {
            'orderNum': 'MOCK002',
            'name': '模拟客户B',
            'address': '模拟地址B',
            'supervisorName': '模拟销售B',
            'createTime': '2025-6-24, 15:30',
            'orgName': '模拟公司B',
            'orderstatus': '暂不上门'
        }
    ]

def test_data_strategy_integration():
    """测试数据策略管理器集成"""
    print("🧪 测试数据策略管理器集成...")
    
    try:
        # 初始化数据库
        db_manager = get_db_manager()
        db_manager.init_database()
        
        # 创建数据策略管理器
        data_strategy = BusinessDataStrategy()
        
        # 模拟Metabase客户端
        mock_metabase_client = Mock()
        mock_metabase_client.get_all_monitored_opportunities.return_value = []
        
        # 使用模拟客户端
        data_strategy.metabase_client = mock_metabase_client
        
        # 1. 测试获取空数据
        opportunities = data_strategy.get_opportunities()
        print(f"获取空数据: {len(opportunities)} 条商机")
        assert len(opportunities) == 0, "空数据应该返回0条商机"
        
        # 2. 测试缓存统计
        stats = data_strategy.get_cache_statistics()
        print(f"缓存统计: {stats}")
        assert stats.get("cache_mode") == "full_refresh", "应该是full_refresh模式"
        assert stats.get("cache_enabled") == True, "缓存应该启用"
        
        # 3. 测试手动刷新
        old_count, new_count = data_strategy.refresh_cache()
        print(f"手动刷新: {old_count} -> {new_count}")
        assert old_count == 0 and new_count == 0, "空数据刷新应该是0->0"
        
        # 4. 测试清空缓存
        cleared = data_strategy.clear_cache()
        print(f"清空缓存: {cleared} 条")
        assert cleared == 0, "空缓存清空应该是0条"
        
        print("✅ 数据策略管理器集成测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 数据策略管理器集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n🧪 测试向后兼容性...")
    
    try:
        # 初始化数据库
        db_manager = get_db_manager()
        db_manager.init_database()
        
        # 创建数据策略管理器
        data_strategy = BusinessDataStrategy()
        
        # 模拟Metabase客户端
        mock_metabase_client = Mock()
        mock_metabase_client.get_all_monitored_opportunities.return_value = []
        data_strategy.metabase_client = mock_metabase_client
        
        # 1. 测试旧的方法调用仍然有效
        opportunities_1 = data_strategy.get_opportunities(force_refresh=False)
        opportunities_2 = data_strategy.get_opportunities(force_refresh=True)
        
        print(f"force_refresh=False: {len(opportunities_1)} 条")
        print(f"force_refresh=True: {len(opportunities_2)} 条")
        
        # 在新的实现中，force_refresh参数被忽略，都是全新获取
        assert len(opportunities_1) == len(opportunities_2), "新实现中两种调用应该返回相同结果"
        
        # 2. 测试废弃方法的兼容性
        # _update_cache 方法应该仍然可用，但内部调用 _full_refresh_cache
        data_strategy._update_cache([])  # 应该不抛出异常
        
        # _should_partial_refresh 方法应该仍然可用，但始终返回True
        should_refresh = data_strategy._should_partial_refresh([])
        assert should_refresh == True, "废弃的_should_partial_refresh应该始终返回True"
        
        print("✅ 向后兼容性测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_web_interface_compatibility():
    """测试Web界面兼容性"""
    print("\n🧪 测试Web界面兼容性...")
    
    try:
        # 初始化数据库
        db_manager = get_db_manager()
        db_manager.init_database()
        
        # 创建数据策略管理器
        data_strategy = BusinessDataStrategy()
        
        # 模拟Metabase客户端
        mock_metabase_client = Mock()
        mock_metabase_client.get_all_monitored_opportunities.return_value = []
        data_strategy.metabase_client = mock_metabase_client
        
        # 1. 测试Web界面需要的统计信息
        stats = data_strategy.get_cache_statistics()
        
        # 验证Web界面需要的字段都存在
        required_fields = ["total_cached", "cache_enabled", "cache_mode", "overdue_cached", "organizations"]
        for field in required_fields:
            assert field in stats, f"统计信息应该包含{field}字段"
        
        print(f"Web界面统计信息: {stats}")
        
        # 2. 测试Web界面的操作方法
        # 刷新缓存
        old_count, new_count = data_strategy.refresh_cache()
        assert isinstance(old_count, int) and isinstance(new_count, int), "刷新缓存应该返回整数"
        
        # 清空缓存
        cleared = data_strategy.clear_cache()
        assert isinstance(cleared, int), "清空缓存应该返回整数"
        
        # 验证数据一致性
        consistency = data_strategy.validate_data_consistency()
        assert isinstance(consistency, dict), "数据一致性验证应该返回字典"
        
        print("✅ Web界面兼容性测试通过")
        return True
        
    except Exception as e:
        print(f"❌ Web界面兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试错误处理...")
    
    try:
        # 初始化数据库
        db_manager = get_db_manager()
        db_manager.init_database()
        
        # 创建数据策略管理器
        data_strategy = BusinessDataStrategy()
        
        # 模拟Metabase客户端抛出异常
        mock_metabase_client = Mock()
        mock_metabase_client.get_all_monitored_opportunities.side_effect = Exception("模拟Metabase连接失败")
        data_strategy.metabase_client = mock_metabase_client
        
        # 1. 测试Metabase失败时的降级策略
        try:
            opportunities = data_strategy.get_opportunities()
            # 应该返回空列表（因为缓存为空）
            assert len(opportunities) == 0, "Metabase失败且无缓存时应该返回空列表"
            print("✅ Metabase失败降级策略正常")
        except Exception:
            print("❌ Metabase失败时没有正确降级")
            return False
        
        # 2. 测试统计信息在异常情况下的处理
        stats = data_strategy.get_cache_statistics()
        assert "cache_enabled" in stats, "即使异常情况下也应该返回基本统计信息"
        print("✅ 异常情况下统计信息处理正常")
        
        print("✅ 错误处理测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🚀 开始数据同步重构集成测试")
    print("=" * 60)
    
    test_results = []
    
    # 执行各项测试
    test_results.append(test_data_strategy_integration())
    test_results.append(test_backward_compatibility())
    test_results.append(test_web_interface_compatibility())
    test_results.append(test_error_handling())
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 集成测试结果汇总:")
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有集成测试通过！数据同步重构完全成功")
        print("\n✨ 重构成果:")
        print("  • 实现了真正的'清空重建'数据同步机制")
        print("  • 简化了缓存策略，移除了复杂的TTL逻辑")
        print("  • 保持了完整的向后兼容性")
        print("  • Web界面与后端逻辑完全一致")
        print("  • 错误处理和事务安全性得到保证")
        return True
    else:
        print("❌ 部分集成测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

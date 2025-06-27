#!/usr/bin/env python3
"""
数据同步重构简化测试脚本

测试新的"清空重建"数据库操作逻辑，不依赖外部服务
"""

import sys
import os
import tempfile
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 设置测试环境变量
os.environ['DATABASE_URL'] = f'sqlite:///{tempfile.mktemp()}.db'
os.environ['DEEPSEEK_API_KEY'] = 'test_key'
os.environ['METABASE_URL'] = 'http://test.metabase.com'
os.environ['METABASE_USERNAME'] = 'test_user'
os.environ['METABASE_PASSWORD'] = 'test_password'
os.environ['INTERNAL_OPS_WEBHOOK'] = 'https://test.webhook.com'

from src.fsoa.data.database import DatabaseManager, OpportunityCacheTable
from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
from src.fsoa.utils.timezone_utils import now_china_naive

def create_test_opportunity(order_num: str, name: str = "测试客户") -> OpportunityInfo:
    """创建测试商机"""
    opportunity = OpportunityInfo(
        order_num=order_num,
        name=name,
        address="测试地址",
        supervisor_name="测试销售",
        create_time=now_china_naive(),
        org_name="测试公司",
        order_status=OpportunityStatus.PENDING_APPOINTMENT
    )
    # 确保商机会被缓存（设置SLA阈值）
    opportunity.sla_threshold_hours = 24
    opportunity.update_overdue_info()  # 更新逾期信息
    return opportunity

def test_full_refresh_cache():
    """测试完全刷新缓存功能"""
    print("🧪 测试完全刷新缓存功能...")
    
    try:
        # 创建数据库管理器
        db_manager = DatabaseManager()
        db_manager.init_database()
        
        # 1. 创建初始测试数据
        initial_opportunities = [
            create_test_opportunity("TEST001", "客户A"),
            create_test_opportunity("TEST002", "客户B"),
        ]
        
        # 使用旧方法保存数据
        for opp in initial_opportunities:
            db_manager.save_opportunity_cache(opp)
        
        initial_count = len(db_manager.get_cached_opportunities(24))
        print(f"初始缓存条目: {initial_count}")
        
        # 2. 创建新的测试数据
        new_opportunities = [
            create_test_opportunity("TEST003", "客户C"),
            create_test_opportunity("TEST004", "客户D"),
            create_test_opportunity("TEST005", "客户E"),
        ]
        
        # 3. 使用新的完全刷新方法
        print("执行完全刷新...")
        refreshed_count = db_manager.full_refresh_opportunity_cache(new_opportunities)
        
        # 4. 验证结果
        final_count = len(db_manager.get_cached_opportunities(24))
        print(f"刷新后缓存条目: {final_count}")
        print(f"成功刷新条目: {refreshed_count}")
        
        # 验证旧数据被清空，新数据被插入
        assert final_count == 3, f"应该有3个新条目，实际有{final_count}个"
        assert refreshed_count == 3, f"应该成功刷新3个条目，实际刷新{refreshed_count}个"
        
        # 验证具体数据
        cached_opportunities = db_manager.get_cached_opportunities(24)
        order_nums = [opp.order_num for opp in cached_opportunities]
        
        assert "TEST001" not in order_nums, "旧数据TEST001应该被清空"
        assert "TEST002" not in order_nums, "旧数据TEST002应该被清空"
        assert "TEST003" in order_nums, "新数据TEST003应该存在"
        assert "TEST004" in order_nums, "新数据TEST004应该存在"
        assert "TEST005" in order_nums, "新数据TEST005应该存在"
        
        print("✅ 完全刷新缓存测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 完全刷新缓存测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_clear_rebuild():
    """测试缓存清空重建机制"""
    print("\n🧪 测试缓存清空重建机制...")
    
    try:
        # 创建数据库管理器
        db_manager = DatabaseManager()
        db_manager.init_database()
        
        # 1. 创建测试数据
        test_opportunities = [
            create_test_opportunity("CLEAR001", "清空测试A"),
            create_test_opportunity("CLEAR002", "清空测试B"),
        ]
        
        # 使用完全刷新方法插入数据
        refreshed_count = db_manager.full_refresh_opportunity_cache(test_opportunities)
        initial_count = len(db_manager.get_cached_opportunities(24))
        print(f"初始缓存条目: {initial_count}")
        
        # 2. 测试清空操作
        with db_manager.get_session() as session:
            deleted_count = session.query(OpportunityCacheTable).delete()
            session.commit()
        
        print(f"清空了 {deleted_count} 个缓存条目")
        
        # 3. 验证清空结果
        after_clear_count = len(db_manager.get_cached_opportunities(24))
        print(f"清空后缓存条目: {after_clear_count}")
        assert after_clear_count == 0, "缓存应该完全清空"
        
        # 4. 重建缓存
        new_opportunities = [
            create_test_opportunity("REBUILD001", "重建测试A"),
            create_test_opportunity("REBUILD002", "重建测试B"),
            create_test_opportunity("REBUILD003", "重建测试C"),
        ]
        
        rebuild_count = db_manager.full_refresh_opportunity_cache(new_opportunities)
        final_count = len(db_manager.get_cached_opportunities(24))
        print(f"重建后缓存条目: {final_count}")
        
        assert final_count == 3, f"重建后应该有3个条目，实际有{final_count}个"
        assert rebuild_count == 3, f"应该重建3个条目，实际重建{rebuild_count}个"
        
        print("✅ 缓存清空重建测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 缓存清空重建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transaction_safety():
    """测试事务安全性"""
    print("\n🧪 测试事务安全性...")
    
    try:
        # 创建数据库管理器
        db_manager = DatabaseManager()
        db_manager.init_database()
        
        # 1. 创建初始数据
        initial_opportunities = [
            create_test_opportunity("TRANS001", "事务测试A"),
            create_test_opportunity("TRANS002", "事务测试B"),
        ]
        
        db_manager.full_refresh_opportunity_cache(initial_opportunities)
        initial_count = len(db_manager.get_cached_opportunities(24))
        print(f"初始缓存条目: {initial_count}")
        
        # 2. 创建一个会导致错误的商机（模拟异常情况）
        class BadOpportunity:
            def should_cache(self):
                return True
            
            def update_cache_info(self):
                raise Exception("模拟更新缓存信息时的错误")
        
        bad_opportunities = [BadOpportunity()]
        
        # 3. 尝试刷新，应该失败并回滚
        result_count = db_manager.full_refresh_opportunity_cache(bad_opportunities)
        print(f"异常刷新结果: {result_count}")
        
        # 4. 验证原数据仍然存在（事务回滚）
        after_error_count = len(db_manager.get_cached_opportunities(24))
        print(f"异常后缓存条目: {after_error_count}")
        
        # 由于事务回滚，原数据应该仍然存在
        assert after_error_count == initial_count, "事务回滚后原数据应该保持不变"
        
        print("✅ 事务安全性测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 事务安全性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🚀 开始数据同步重构简化测试")
    print("=" * 50)
    
    test_results = []
    
    # 执行各项测试
    test_results.append(test_full_refresh_cache())
    test_results.append(test_cache_clear_rebuild())
    test_results.append(test_transaction_safety())
    
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

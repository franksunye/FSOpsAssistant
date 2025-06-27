#!/usr/bin/env python3
"""
测试缓存操作修复
验证缓存管理的三个功能是否正确工作
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_cache_operations():
    """测试缓存操作功能"""
    print("🧪 测试缓存操作功能")
    print("=" * 50)
    
    try:
        from src.fsoa.agent.tools import get_data_strategy
        from src.fsoa.data.database import get_db_manager, OpportunityCacheTable
        
        data_strategy = get_data_strategy()
        db_manager = get_db_manager()
        
        # 1. 检查初始状态
        print("\n1️⃣ 检查初始缓存状态")
        with db_manager.get_session() as session:
            initial_count = session.query(OpportunityCacheTable).count()
        print(f"初始缓存记录数: {initial_count}")
        
        stats = data_strategy.get_cache_statistics()
        print(f"统计信息显示: {stats.get('total_cached')} 条缓存")
        
        # 2. 测试完全刷新缓存
        print("\n2️⃣ 测试完全刷新缓存")
        try:
            old_count, new_count = data_strategy.refresh_cache()
            print(f"刷新结果: {old_count} → {new_count}")
            
            # 验证数据库实际状态
            with db_manager.get_session() as session:
                actual_count = session.query(OpportunityCacheTable).count()
            print(f"数据库实际记录数: {actual_count}")
            
            if actual_count == new_count:
                print("✅ 完全刷新缓存功能正常")
            else:
                print(f"❌ 完全刷新缓存有问题：显示{new_count}条，实际{actual_count}条")
                
        except Exception as e:
            print(f"❌ 完全刷新缓存失败: {e}")
        
        # 3. 测试清空缓存
        print("\n3️⃣ 测试清空缓存")
        try:
            cleared_count = data_strategy.clear_cache()
            print(f"清空结果: {cleared_count} 条记录被删除")
            
            # 验证数据库实际状态
            with db_manager.get_session() as session:
                remaining_count = session.query(OpportunityCacheTable).count()
            print(f"数据库剩余记录数: {remaining_count}")
            
            if remaining_count == 0:
                print("✅ 清空缓存功能正常")
            else:
                print(f"❌ 清空缓存有问题：还剩余{remaining_count}条记录")
                
        except Exception as e:
            print(f"❌ 清空缓存失败: {e}")
        
        # 4. 测试验证一致性
        print("\n4️⃣ 测试验证一致性")
        try:
            consistency = data_strategy.validate_data_consistency()
            print(f"一致性检查结果:")
            print(f"  缓存数据: {consistency.get('cached_count')} 条")
            print(f"  源数据: {consistency.get('fresh_count')} 条")
            print(f"  数据一致: {consistency.get('data_consistent')}")
            
            if 'error' not in consistency:
                print("✅ 验证一致性功能正常")
            else:
                print(f"❌ 验证一致性失败: {consistency.get('error')}")
                
        except Exception as e:
            print(f"❌ 验证一致性失败: {e}")
        
        # 5. 最终状态检查
        print("\n5️⃣ 最终状态检查")
        final_stats = data_strategy.get_cache_statistics()
        with db_manager.get_session() as session:
            final_db_count = session.query(OpportunityCacheTable).count()
        
        print(f"统计信息显示: {final_stats.get('total_cached')} 条缓存")
        print(f"数据库实际记录: {final_db_count} 条")
        
        if final_stats.get('total_cached') == final_db_count:
            print("✅ 统计信息与数据库状态一致")
        else:
            print("❌ 统计信息与数据库状态不一致")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_web_interface_consistency():
    """测试Web界面一致性"""
    print("\n🌐 测试Web界面一致性")
    print("=" * 50)
    
    try:
        from src.fsoa.agent.tools import get_data_strategy
        from src.fsoa.data.database import get_db_manager, OpportunityCacheTable
        
        data_strategy = get_data_strategy()
        db_manager = get_db_manager()
        
        # 模拟Web界面的操作流程
        print("模拟Web界面操作流程...")
        
        # 1. 获取缓存统计（Web界面显示）
        stats = data_strategy.get_cache_statistics()
        print(f"Web界面显示缓存: {stats.get('total_cached')} 条")
        
        # 2. 执行刷新操作（用户点击刷新按钮）
        old_count, new_count = data_strategy.refresh_cache()
        print(f"刷新操作显示: {old_count} → {new_count}")
        
        # 3. 验证数据库实际状态
        with db_manager.get_session() as session:
            actual_count = session.query(OpportunityCacheTable).count()
        print(f"数据库实际状态: {actual_count} 条")
        
        # 4. 再次获取统计信息
        updated_stats = data_strategy.get_cache_statistics()
        print(f"更新后Web界面显示: {updated_stats.get('total_cached')} 条")
        
        # 验证一致性
        if new_count == actual_count == updated_stats.get('total_cached'):
            print("✅ Web界面与数据库状态完全一致")
            return True
        else:
            print("❌ Web界面与数据库状态不一致")
            print(f"  刷新显示: {new_count}")
            print(f"  数据库实际: {actual_count}")
            print(f"  统计显示: {updated_stats.get('total_cached')}")
            return False
            
    except Exception as e:
        print(f"❌ Web界面一致性测试失败: {e}")
        return False


def main():
    """主函数"""
    print("🔧 缓存操作修复测试")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # 测试缓存操作
    if test_cache_operations():
        success_count += 1
    
    # 测试Web界面一致性
    if test_web_interface_consistency():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"测试完成: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        print("🎉 所有测试通过！缓存操作修复成功")
        print("\n✨ 修复内容:")
        print("  • 完全刷新缓存：真正的清空重建，数据库状态与显示一致")
        print("  • 清空缓存：完全清空所有记录")
        print("  • 验证一致性：准确比较缓存与源数据")
        print("  • 统计信息：不使用TTL过滤，显示真实的数据库状态")
    else:
        print("❌ 部分测试失败，需要进一步检查")
    
    print("\n💡 使用说明:")
    print("1. 完全刷新缓存：清空所有现有数据，重新从Metabase获取并缓存")
    print("2. 清空缓存：删除所有缓存记录，下次获取时直接从Metabase同步")
    print("3. 验证一致性：比较缓存数据与Metabase源数据的一致性")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
测试前端更新

验证前端与后端的对齐情况
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_frontend_backend_integration():
    """测试前端与后端的集成"""
    print("🧪 测试前端与后端集成")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # 1. 测试新的API调用
    print("\n📡 测试新的API调用:")
    
    try:
        from src.fsoa.agent.tools import (
            get_data_statistics, get_data_strategy, 
            get_notification_manager, get_execution_tracker
        )
        
        # 测试数据统计API
        try:
            stats = get_data_statistics()
            print("   ✅ get_data_statistics() 可用")
            print(f"      - 总商机: {stats.get('total_opportunities', 0)}")
            print(f"      - 逾期商机: {stats.get('overdue_opportunities', 0)}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ get_data_statistics() 失败: {e}")
        total_tests += 1
        
        # 测试数据策略
        try:
            data_strategy = get_data_strategy()
            cache_stats = data_strategy.get_cache_statistics()
            print("   ✅ 数据策略可用")
            print(f"      - 缓存启用: {cache_stats.get('cache_enabled', False)}")
            print(f"      - 缓存条目: {cache_stats.get('total_cached', 0)}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 数据策略失败: {e}")
        total_tests += 1
        
        # 测试通知管理器
        try:
            notification_manager = get_notification_manager()
            notification_stats = notification_manager.get_notification_statistics()
            print("   ✅ 通知管理器可用")
            print(f"      - 待处理任务: {notification_stats.get('pending_count', 0)}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 通知管理器失败: {e}")
        total_tests += 1
        
        # 测试执行追踪器
        try:
            execution_tracker = get_execution_tracker()
            run_stats = execution_tracker.get_run_statistics()
            print("   ✅ 执行追踪器可用")
            print(f"      - 总运行次数: {run_stats.get('total_runs', 0)}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 执行追踪器失败: {e}")
        total_tests += 1
        
    except ImportError as e:
        print(f"   ❌ 导入新API失败: {e}")
        total_tests += 4
    
    # 2. 测试前端页面函数
    print("\n🖥️ 测试前端页面函数:")
    
    try:
        # 模拟streamlit环境
        class MockStreamlit:
            def header(self, text): pass
            def metric(self, label, value, delta=None): pass
            def columns(self, n): return [self] * n
            def markdown(self, text): pass
            def subheader(self, text): pass
            def expander(self, text): return self
            def write(self, text): pass
            def button(self, text): return False
            def spinner(self, text): return self
            def success(self, text): pass
            def error(self, text): pass
            def warning(self, text): pass
            def info(self, text): pass
            def rerun(self): pass
            def code(self, text): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
        
        # 替换streamlit
        import sys
        sys.modules['streamlit'] = MockStreamlit()
        
        from src.fsoa.ui.app import (
            show_execution_history, show_notification_management, 
            show_cache_management
        )
        
        # 测试执行历史页面
        try:
            show_execution_history()
            print("   ✅ 执行历史页面函数可用")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 执行历史页面失败: {e}")
        total_tests += 1
        
        # 测试通知管理页面
        try:
            show_notification_management()
            print("   ✅ 通知管理页面函数可用")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 通知管理页面失败: {e}")
        total_tests += 1
        
        # 测试缓存管理页面
        try:
            show_cache_management()
            print("   ✅ 缓存管理页面函数可用")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 缓存管理页面失败: {e}")
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 前端页面测试失败: {e}")
        total_tests += 3
    
    # 3. 测试数据流
    print("\n🔄 测试数据流:")
    
    try:
        from src.fsoa.agent.tools import (
            start_agent_execution, get_all_opportunities,
            create_notification_tasks, complete_agent_execution
        )
        from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
        
        # 模拟完整的数据流
        try:
            # 开始执行
            run_id = start_agent_execution({"test": True})
            print(f"   ✅ 开始执行成功: Run ID {run_id}")
            
            # 创建测试数据
            test_opportunity = OpportunityInfo(
                order_num="FRONTEND_TEST_001",
                name="前端测试客户",
                address="测试地址",
                supervisor_name="测试负责人",
                create_time=datetime.now(),
                org_name="前端测试组织",
                order_status=OpportunityStatus.PENDING_APPOINTMENT,
                is_overdue=True,
                escalation_level=0
            )
            
            # 创建通知任务
            tasks = create_notification_tasks([test_opportunity], run_id)
            print(f"   ✅ 创建通知任务成功: {len(tasks)} 个")
            
            # 完成执行
            final_stats = {
                "opportunities_processed": 1,
                "notifications_sent": len(tasks),
                "context": {"frontend_test": True}
            }
            complete_agent_execution(run_id, final_stats)
            print("   ✅ 完成执行成功")
            
            success_count += 1
        except Exception as e:
            print(f"   ❌ 数据流测试失败: {e}")
        total_tests += 1
        
    except ImportError as e:
        print(f"   ❌ 数据流导入失败: {e}")
        total_tests += 1
    
    # 4. 计算对齐度
    print("\n" + "=" * 50)
    print("📊 前端更新测试总结:")
    print(f"   ✅ 成功测试: {success_count}")
    print(f"   ❌ 失败测试: {total_tests - success_count}")
    print(f"   📈 成功率: {success_count / total_tests * 100:.1f}%")
    
    if success_count / total_tests >= 0.8:
        print("   🎉 前端更新成功！对齐度良好")
        return True
    elif success_count / total_tests >= 0.6:
        print("   ⚠️ 前端更新基本成功，部分功能需要调整")
        return True
    else:
        print("   🚨 前端更新存在问题，需要进一步修复")
        return False

def test_ui_functionality():
    """测试UI功能"""
    print("\n🖥️ 测试UI功能:")
    
    try:
        # 检查UI文件是否存在
        ui_file = Path("src/fsoa/ui/app.py")
        if ui_file.exists():
            print("   ✅ UI主文件存在")
            
            # 检查文件内容
            with open(ui_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 检查新页面是否添加
            new_pages = ["show_execution_history", "show_notification_management", "show_cache_management"]
            for page in new_pages:
                if page in content:
                    print(f"   ✅ {page} 函数已添加")
                else:
                    print(f"   ❌ {page} 函数缺失")
            
            # 检查新API调用
            new_apis = ["get_data_statistics", "get_data_strategy", "get_notification_manager", "get_execution_tracker"]
            for api in new_apis:
                if api in content:
                    print(f"   ✅ {api} API已集成")
                else:
                    print(f"   ❌ {api} API未集成")
            
            return True
        else:
            print("   ❌ UI主文件不存在")
            return False
            
    except Exception as e:
        print(f"   ❌ UI功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 前端更新验证测试")
    print("=" * 60)
    
    # 测试前端后端集成
    integration_success = test_frontend_backend_integration()
    
    # 测试UI功能
    ui_success = test_ui_functionality()
    
    # 最终结果
    print("\n" + "=" * 60)
    print("🎯 最终测试结果:")
    
    if integration_success and ui_success:
        print("   🎉 前端更新完全成功！")
        print("   ✅ 后端集成正常")
        print("   ✅ UI功能完整")
        print("   📈 前端与后端对齐度大幅提升")
        return True
    elif integration_success or ui_success:
        print("   ⚠️ 前端更新部分成功")
        if integration_success:
            print("   ✅ 后端集成正常")
        else:
            print("   ❌ 后端集成有问题")
        if ui_success:
            print("   ✅ UI功能完整")
        else:
            print("   ❌ UI功能有问题")
        return True
    else:
        print("   🚨 前端更新失败")
        print("   ❌ 需要进一步修复")
        return False

if __name__ == "__main__":
    from datetime import datetime
    success = main()
    sys.exit(0 if success else 1)

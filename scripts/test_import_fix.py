#!/usr/bin/env python3
"""
测试相对导入修复结果

验证UI应用中的导入问题已解决
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_ui_imports():
    """测试UI模块导入"""
    print("🔍 测试UI模块导入...")
    
    try:
        # 测试直接导入UI模块
        print("  - 导入UI应用模块...")
        import src.fsoa.ui.app as ui_app
        
        print("  - 检查关键函数...")
        assert hasattr(ui_app, 'show_dashboard'), "show_dashboard函数缺失"
        assert hasattr(ui_app, 'show_opportunity_list'), "show_opportunity_list函数缺失"
        assert hasattr(ui_app, 'show_agent_control'), "show_agent_control函数缺失"
        
        print("✅ UI模块导入成功")
        return True
        
    except Exception as e:
        print(f"❌ UI模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_tools_imports():
    """测试Agent工具导入"""
    print("\n🔍 测试Agent工具导入...")
    
    try:
        print("  - 导入Agent工具...")
        from src.fsoa.agent.tools import (
            get_data_statistics, get_data_strategy, get_system_health,
            get_execution_tracker, get_notification_manager
        )
        
        print("  - 测试函数调用...")
        # 测试基本函数调用
        health = get_system_health()
        assert isinstance(health, dict), "get_system_health应返回字典"
        
        stats = get_data_statistics()
        assert isinstance(stats, dict), "get_data_statistics应返回字典"
        
        print("✅ Agent工具导入和调用成功")
        return True
        
    except Exception as e:
        print(f"❌ Agent工具导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_imports():
    """测试数据库模块导入"""
    print("\n🔍 测试数据库模块导入...")
    
    try:
        print("  - 导入数据库模块...")
        from src.fsoa.data.database import get_database_manager
        from src.fsoa.utils.config import get_config
        
        print("  - 测试配置获取...")
        config = get_config()
        assert hasattr(config, 'database_url'), "配置缺少database_url"
        assert hasattr(config, 'wechat_webhook_list'), "配置缺少wechat_webhook_list兼容性属性"
        
        print("  - 测试数据库管理器...")
        db_manager = get_database_manager()
        assert db_manager is not None, "数据库管理器不应为None"
        
        print("✅ 数据库模块导入成功")
        return True
        
    except Exception as e:
        print(f"❌ 数据库模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scheduler_imports():
    """测试调度器模块导入"""
    print("\n🔍 测试调度器模块导入...")
    
    try:
        print("  - 导入调度器模块...")
        from src.fsoa.utils.scheduler import get_scheduler
        
        print("  - 测试调度器创建...")
        scheduler = get_scheduler()
        assert scheduler is not None, "调度器不应为None"
        
        print("  - 测试调度器方法...")
        jobs_info = scheduler.get_jobs()
        assert isinstance(jobs_info, dict), "get_jobs应返回字典"
        assert 'total_jobs' in jobs_info, "jobs_info应包含total_jobs"
        assert 'is_running' in jobs_info, "jobs_info应包含is_running"
        
        print("✅ 调度器模块导入成功")
        return True
        
    except Exception as e:
        print(f"❌ 调度器模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_notification_imports():
    """测试通知模块导入"""
    print("\n🔍 测试通知模块导入...")
    
    try:
        print("  - 导入通知模块...")
        from src.fsoa.notification.wechat import get_wechat_client
        
        print("  - 测试企微客户端...")
        client = get_wechat_client()
        assert client is not None, "企微客户端不应为None"
        
        print("  - 测试客户端方法...")
        org_mapping = client.get_org_webhook_mapping()
        assert isinstance(org_mapping, dict), "get_org_webhook_mapping应返回字典"
        
        internal_webhook = client.get_internal_ops_webhook()
        # internal_webhook可以为None或字符串
        
        print("✅ 通知模块导入成功")
        return True
        
    except Exception as e:
        print(f"❌ 通知模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_streamlit_compatibility():
    """测试Streamlit兼容性"""
    print("\n🔍 测试Streamlit兼容性...")
    
    try:
        # 模拟Streamlit环境
        print("  - 检查绝对导入路径...")
        
        # 检查UI文件中是否还有相对导入
        ui_file = project_root / "src" / "fsoa" / "ui" / "app.py"
        with open(ui_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否还有相对导入
        relative_imports = []
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'from ..' in line and 'import' in line:
                relative_imports.append(f"第{i}行: {line.strip()}")
        
        if relative_imports:
            print(f"  ❌ 发现相对导入:")
            for imp in relative_imports:
                print(f"    {imp}")
            return False
        else:
            print("  ✅ 没有发现相对导入")
        
        print("✅ Streamlit兼容性检查通过")
        return True
        
    except Exception as e:
        print(f"❌ Streamlit兼容性检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 相对导入修复验证测试")
    print("=" * 60)
    
    tests = [
        ("UI模块导入", test_ui_imports),
        ("Agent工具导入", test_agent_tools_imports),
        ("数据库模块导入", test_database_imports),
        ("调度器模块导入", test_scheduler_imports),
        ("通知模块导入", test_notification_imports),
        ("Streamlit兼容性", test_streamlit_compatibility),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"✅ {test_name}: 通过")
            else:
                print(f"❌ {test_name}: 失败")
        except Exception as e:
            print(f"❌ {test_name}: 异常 - {e}")
    
    # 最终结果
    print("\n" + "=" * 60)
    print("🎯 修复验证结果:")
    print(f"   ✅ 成功测试: {passed}")
    print(f"   ❌ 失败测试: {total - passed}")
    print(f"   📈 成功率: {passed / total * 100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！相对导入问题已完全修复！")
        print("   ✅ UI应用可以正常启动")
        print("   ✅ 所有模块导入正常")
        print("   ✅ Streamlit兼容性良好")
        print("\n💡 现在可以正常使用以下命令启动应用:")
        print("   python scripts/start_app.py")
        print("   或")
        print("   streamlit run src/fsoa/ui/app.py")
    elif passed / total >= 0.8:
        print("\n👍 大部分测试通过！修复基本完成")
        print("   📋 部分功能可能需要进一步检查")
    else:
        print("\n⚠️ 修复工作需要继续完善")
        print("   📋 请检查失败的测试项")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

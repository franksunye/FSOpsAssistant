#!/usr/bin/env python3
"""
测试完整应用启动的简化脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        print("  - 导入 dotenv...")
        from dotenv import load_dotenv
        
        print("  - 导入配置模块...")
        from src.fsoa.utils.config import get_config
        
        print("  - 导入数据库模块...")
        from src.fsoa.data.database import get_db_manager
        
        print("  - 导入Agent模块...")
        from src.fsoa.agent.orchestrator import AgentOrchestrator
        
        print("  - 导入调度器模块...")
        from src.fsoa.utils.scheduler import get_scheduler
        
        print("✅ 所有模块导入成功")
        return True
        
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """测试配置加载"""
    print("\n⚙️ 测试配置加载...")
    
    try:
        # 强制重新加载配置
        for key in list(os.environ.keys()):
            if key.startswith(('DEEPSEEK_', 'METABASE_', 'WECHAT_', 'AGENT_', 'NOTIFICATION_')):
                del os.environ[key]
        
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        if 'src.fsoa.utils.config' in sys.modules:
            del sys.modules['src.fsoa.utils.config']
        
        from src.fsoa.utils.config import get_config
        config = get_config()
        
        print(f"✅ 配置加载成功")
        print(f"   - Agent执行间隔: {config.agent_execution_interval}")
        print(f"   - 数据库URL: {config.database_url}")
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scheduler():
    """测试调度器"""
    print("\n⏰ 测试调度器...")
    
    try:
        from src.fsoa.utils.scheduler import get_scheduler
        
        scheduler = get_scheduler()
        print(f"✅ 调度器创建成功: {type(scheduler)}")
        
        # 测试调度器设置
        from src.fsoa.utils.scheduler import setup_agent_scheduler
        setup_agent_scheduler()
        print("✅ Agent调度任务设置成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 调度器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent():
    """测试Agent"""
    print("\n🤖 测试Agent...")
    
    try:
        from src.fsoa.agent.orchestrator import AgentOrchestrator
        
        agent = AgentOrchestrator()
        print("✅ Agent创建成功")
        
        # 执行干运行
        execution = agent.execute(dry_run=True)
        print(f"✅ Agent干运行成功: {execution.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🧪 完整应用组件测试")
    print("=" * 40)
    
    tests = [
        ("模块导入", test_imports),
        ("配置加载", test_config),
        ("调度器", test_scheduler),
        ("Agent", test_agent),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
        else:
            print(f"\n❌ {test_name} 测试失败，停止后续测试")
            break
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有组件测试通过，可以启动完整应用！")
    else:
        print("⚠️ 部分组件测试失败，需要修复后再启动完整应用")

if __name__ == "__main__":
    main()

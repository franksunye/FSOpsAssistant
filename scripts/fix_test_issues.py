#!/usr/bin/env python3
"""
FSOA 测试问题快速修复脚本

解决当前测试中的主要问题：
1. 数据库表缺失
2. Mock配置错误
3. 废弃模型引用
"""

import os
import sys
import sqlite3
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_test_database():
    """修复测试数据库，确保所有表都存在"""
    print("🔧 修复测试数据库...")
    
    try:
        from src.fsoa.data.database import DatabaseManager
        
        # 创建测试数据库
        test_db_path = project_root / "test.db"
        if test_db_path.exists():
            test_db_path.unlink()
        
        db_manager = DatabaseManager(f"sqlite:///{test_db_path}")
        db_manager.init_database()
        
        print("✅ 测试数据库创建成功")
        return True
        
    except Exception as e:
        print(f"❌ 数据库创建失败: {e}")
        return False

def check_table_exists(db_path, table_name):
    """检查表是否存在"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception:
        return False

def verify_database_tables():
    """验证数据库表是否完整"""
    print("🔍 验证数据库表...")
    
    test_db_path = project_root / "test.db"
    if not test_db_path.exists():
        print("❌ 测试数据库不存在")
        return False
    
    required_tables = [
        'opportunity_cache',
        'notification_tasks',
        'agent_runs',
        'agent_history',
        'system_config',
        'group_config'
    ]
    
    missing_tables = []
    for table in required_tables:
        if not check_table_exists(test_db_path, table):
            missing_tables.append(table)
    
    if missing_tables:
        print(f"❌ 缺失表: {', '.join(missing_tables)}")
        return False
    else:
        print("✅ 所有必要的表都存在")
        return True

def update_test_fixtures():
    """更新测试fixture，移除废弃引用"""
    print("🔧 更新测试fixture...")
    
    # 这里可以添加自动化的fixture更新逻辑
    # 目前先提供手动检查清单
    
    issues_found = []
    
    # 检查是否还有TaskInfo引用（排除注释和跳过标记）
    test_files = list(project_root.glob("tests/**/*.py"))
    for test_file in test_files:
        try:
            content = test_file.read_text()
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # 跳过注释行和跳过标记
                if line.strip().startswith('#') or 'pytest.mark.skip' in line or 'DeprecationWarning' in line:
                    continue
                if "TaskInfo" in line and "import" in line:
                    issues_found.append(f"TaskInfo导入: {test_file}:{i}")
                elif "sample_task" in line and not line.strip().startswith('#'):
                    issues_found.append(f"sample_task fixture: {test_file}:{i}")
        except Exception:
            continue
    
    if issues_found:
        print("⚠️ 发现需要更新的测试文件:")
        for issue in issues_found:
            print(f"  - {issue}")
        return False
    else:
        print("✅ 测试fixture检查通过")
        return True

def run_basic_tests():
    """运行基础测试验证修复效果"""
    print("🧪 运行基础测试...")
    
    import subprocess
    
    # 运行模型测试
    try:
        result = subprocess.run([
            "python", "-m", "pytest", 
            "tests/unit/test_models.py", 
            "-v", "--tb=short"
        ], cwd=project_root, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ 模型测试通过")
            return True
        else:
            print("❌ 模型测试失败")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        return False

def create_test_summary():
    """创建测试修复总结"""
    print("\n" + "="*60)
    print("📊 测试修复总结")
    print("="*60)
    
    # 检查各个组件
    checks = [
        ("数据库初始化", fix_test_database),
        ("数据库表验证", verify_database_tables),
        ("测试fixture检查", update_test_fixtures),
        ("基础测试运行", run_basic_tests)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            success = check_func()
            results.append((name, success))
            status = "✅ 通过" if success else "❌ 失败"
            print(f"{name}: {status}")
        except Exception as e:
            results.append((name, False))
            print(f"{name}: ❌ 异常 - {e}")
    
    # 总结
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n总结: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("🎉 所有检查通过！测试环境已修复")
    else:
        print("⚠️ 仍有问题需要手动解决")
        print("\n建议的下一步:")
        print("1. 检查数据库模型定义是否完整")
        print("2. 更新测试文件中的废弃引用")
        print("3. 修正Mock对象配置")
        print("4. 运行完整测试套件验证")
    
    return passed == total

def main():
    """主函数"""
    print("🚀 FSOA 测试问题快速修复")
    print(f"项目路径: {project_root}")
    
    # 设置测试环境变量
    os.environ.update({
        "DEEPSEEK_API_KEY": "test-key",
        "METABASE_URL": "http://test-metabase",
        "METABASE_USERNAME": "test-user", 
        "METABASE_PASSWORD": "test-pass",
        "INTERNAL_OPS_WEBHOOK": "http://test-webhook",
        "DATABASE_URL": "sqlite:///test.db",
        "LOG_LEVEL": "DEBUG",
        "DEBUG": "True",
        "TESTING": "True"
    })
    
    success = create_test_summary()
    
    if success:
        print("\n🎯 下一步建议:")
        print("1. 运行完整测试套件: python scripts/run_comprehensive_tests.py")
        print("2. 检查测试覆盖率: python -m pytest --cov=src/fsoa")
        print("3. 提交测试修复: git add . && git commit -m 'fix: 修复测试环境和配置问题'")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

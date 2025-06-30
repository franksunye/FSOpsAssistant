#!/usr/bin/env python3
"""
FSOA 系统性测试运行脚本

运行完整的测试套件，包括单元测试、集成测试和性能测试
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=project_root,
            capture_output=True, 
            text=True,
            timeout=300  # 5分钟超时
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} - 成功 ({duration:.2f}秒)")
            if result.stdout:
                print("输出:")
                print(result.stdout)
        else:
            print(f"❌ {description} - 失败 ({duration:.2f}秒)")
            if result.stderr:
                print("错误:")
                print(result.stderr)
            if result.stdout:
                print("输出:")
                print(result.stdout)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - 超时")
        return False
    except Exception as e:
        print(f"💥 {description} - 异常: {e}")
        return False

def check_environment():
    """检查测试环境"""
    print("🔍 检查测试环境...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 9):
        print(f"❌ Python版本过低: {python_version.major}.{python_version.minor}")
        return False
    
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查必要的包
    required_packages = ['pytest', 'pytest-cov', 'pytest-mock']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} 未安装")
    
    if missing_packages:
        print(f"\n请安装缺失的包: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def run_unit_tests():
    """运行单元测试"""
    commands = [
        ("python -m pytest tests/unit/ -v --tb=short", "单元测试"),
        ("python -m pytest tests/unit/ --cov=src/fsoa --cov-report=term-missing", "单元测试覆盖率"),
    ]
    
    results = []
    for command, description in commands:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def run_integration_tests():
    """运行集成测试"""
    commands = [
        ("python -m pytest tests/integration/ -v --tb=short", "集成测试"),
    ]
    
    results = []
    for command, description in commands:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def run_performance_tests():
    """运行性能测试"""
    commands = [
        ("python -m pytest tests/performance/ -v --tb=short", "性能测试"),
    ]
    
    results = []
    for command, description in commands:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def run_code_quality_checks():
    """运行代码质量检查"""
    commands = [
        ("python -m flake8 src/fsoa --max-line-length=100 --ignore=E203,W503", "代码风格检查"),
        ("python -m mypy src/fsoa --ignore-missing-imports", "类型检查"),
    ]
    
    results = []
    for command, description in commands:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def generate_test_report(all_results):
    """生成测试报告"""
    print(f"\n{'='*60}")
    print("📊 测试报告")
    print(f"{'='*60}")
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        print(f"\n{category}:")
        for description, success in results:
            status = "✅ 通过" if success else "❌ 失败"
            print(f"  {description}: {status}")
            total_tests += 1
            if success:
                passed_tests += 1
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n总结:")
    print(f"  总测试数: {total_tests}")
    print(f"  通过数: {passed_tests}")
    print(f"  失败数: {total_tests - passed_tests}")
    print(f"  成功率: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 所有测试通过！")
        return True
    else:
        print(f"\n⚠️  有 {total_tests - passed_tests} 个测试失败")
        return False

def main():
    """主函数"""
    print("🚀 FSOA 系统性测试开始")
    print(f"项目路径: {project_root}")
    
    # 检查环境
    if not check_environment():
        print("❌ 环境检查失败，退出测试")
        sys.exit(1)
    
    # 运行各类测试
    all_results = {}
    
    print("\n" + "="*60)
    print("🧪 开始运行测试套件")
    print("="*60)
    
    # 单元测试
    all_results["单元测试"] = run_unit_tests()
    
    # 集成测试
    all_results["集成测试"] = run_integration_tests()
    
    # 性能测试（可选）
    if "--include-performance" in sys.argv:
        all_results["性能测试"] = run_performance_tests()
    
    # 代码质量检查（可选）
    if "--include-quality" in sys.argv:
        all_results["代码质量"] = run_code_quality_checks()
    
    # 生成报告
    success = generate_test_report(all_results)
    
    # 退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

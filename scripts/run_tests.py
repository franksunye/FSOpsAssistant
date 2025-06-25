#!/usr/bin/env python3
"""
测试运行脚本

运行FSOA项目的各种测试
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd, cwd=None):
    """运行命令"""
    print(f"🔧 执行命令: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or project_root,
            check=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        return False, e.stderr


def check_python_environment():
    """检查Python环境"""
    print("🐍 检查Python环境...")

    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")

    if version.major != 3 or version.minor < 9:
        print("❌ 错误: 需要Python 3.9或更高版本")
        return False

    print("✅ Python版本检查通过")
    return True


def install_test_dependencies():
    """安装测试依赖"""
    print("📦 安装测试依赖...")
    
    test_packages = [
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-mock>=3.11.0",
        "pytest-asyncio>=0.21.0",
        "pytest-html>=3.1.0",
        "pytest-xdist>=3.3.0",  # 并行测试
        "psutil>=5.9.0"  # 性能测试
    ]
    
    for package in test_packages:
        success, _ = run_command([sys.executable, "-m", "pip", "install", package])
        if not success:
            print(f"❌ 安装 {package} 失败")
            return False
    
    print("✅ 测试依赖安装完成")
    return True


def run_unit_tests(coverage=False, verbose=False):
    """运行单元测试"""
    print("\n🧪 运行单元测试...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/unit/"]
    
    if coverage:
        cmd.extend(["--cov=src/fsoa", "--cov-report=html", "--cov-report=term"])
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "--tb=short",
        "--html=test-results/unit-tests.html",
        "--self-contained-html"
    ])
    
    # 确保测试结果目录存在
    os.makedirs("test-results", exist_ok=True)
    
    success, output = run_command(cmd)
    
    if success:
        print("✅ 单元测试通过")
    else:
        print("❌ 单元测试失败")
    
    return success


def run_integration_tests(verbose=False):
    """运行集成测试"""
    print("\n🔗 运行集成测试...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/integration/"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "--tb=short",
        "--html=test-results/integration-tests.html",
        "--self-contained-html"
    ])
    
    success, output = run_command(cmd)
    
    if success:
        print("✅ 集成测试通过")
    else:
        print("❌ 集成测试失败")
    
    return success


def run_performance_tests(verbose=False):
    """运行性能测试"""
    print("\n⚡ 运行性能测试...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/performance/"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "--tb=short",
        "--html=test-results/performance-tests.html",
        "--self-contained-html",
        "-s"  # 显示print输出
    ])
    
    success, output = run_command(cmd)
    
    if success:
        print("✅ 性能测试通过")
    else:
        print("❌ 性能测试失败")
    
    return success


def run_linting():
    """运行代码检查"""
    print("\n🔍 运行代码检查...")
    
    # 安装linting工具
    linting_packages = ["flake8", "black", "isort"]
    for package in linting_packages:
        run_command([sys.executable, "-m", "pip", "install", package])
    
    # 运行black格式检查
    print("📝 检查代码格式 (black)...")
    success_black, _ = run_command([
        sys.executable, "-m", "black", "--check", "--diff", "src/", "tests/", "scripts/"
    ])
    
    # 运行isort导入排序检查
    print("📦 检查导入排序 (isort)...")
    success_isort, _ = run_command([
        sys.executable, "-m", "isort", "--check-only", "--diff", "src/", "tests/", "scripts/"
    ])
    
    # 运行flake8代码风格检查
    print("🔍 检查代码风格 (flake8)...")
    success_flake8, _ = run_command([
        sys.executable, "-m", "flake8", "src/", "tests/", "scripts/",
        "--max-line-length=100",
        "--ignore=E203,W503"
    ])
    
    all_success = success_black and success_isort and success_flake8
    
    if all_success:
        print("✅ 代码检查通过")
    else:
        print("❌ 代码检查失败")
        if not success_black:
            print("  - 代码格式不符合black标准")
        if not success_isort:
            print("  - 导入排序不符合isort标准")
        if not success_flake8:
            print("  - 代码风格不符合flake8标准")
    
    return all_success


def run_security_check():
    """运行安全检查"""
    print("\n🔒 运行安全检查...")
    
    # 安装安全检查工具
    run_command([sys.executable, "-m", "pip", "install", "bandit", "safety"])
    
    # 运行bandit安全检查
    print("🛡️ 检查安全漏洞 (bandit)...")
    success_bandit, _ = run_command([
        sys.executable, "-m", "bandit", "-r", "src/", "-f", "json", "-o", "test-results/bandit-report.json"
    ])
    
    # 运行safety依赖安全检查
    print("📦 检查依赖安全 (safety)...")
    success_safety, _ = run_command([
        sys.executable, "-m", "safety", "check", "--json", "--output", "test-results/safety-report.json"
    ])
    
    all_success = success_bandit and success_safety
    
    if all_success:
        print("✅ 安全检查通过")
    else:
        print("❌ 安全检查发现问题")
    
    return all_success


def generate_test_report():
    """生成测试报告"""
    print("\n📊 生成测试报告...")
    
    report_content = f"""# FSOA 测试报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 测试结果

- 单元测试: {'✅ 通过' if unit_success else '❌ 失败'}
- 集成测试: {'✅ 通过' if integration_success else '❌ 失败'}
- 性能测试: {'✅ 通过' if performance_success else '❌ 失败'}
- 代码检查: {'✅ 通过' if linting_success else '❌ 失败'}
- 安全检查: {'✅ 通过' if security_success else '❌ 失败'}

## 详细报告

- [单元测试报告](unit-tests.html)
- [集成测试报告](integration-tests.html)
- [性能测试报告](performance-tests.html)
- [安全检查报告](bandit-report.json)
- [依赖安全报告](safety-report.json)

## 覆盖率报告

如果启用了覆盖率测试，请查看 `htmlcov/index.html`
"""
    
    with open("test-results/README.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print("✅ 测试报告生成完成: test-results/README.md")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FSOA测试运行器")
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    parser.add_argument("--integration", action="store_true", help="运行集成测试")
    parser.add_argument("--performance", action="store_true", help="运行性能测试")
    parser.add_argument("--lint", action="store_true", help="运行代码检查")
    parser.add_argument("--security", action="store_true", help="运行安全检查")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--coverage", action="store_true", help="启用覆盖率测试")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--install-deps", action="store_true", help="安装测试依赖")
    
    args = parser.parse_args()
    
    print("🤖 FSOA测试运行器")
    print("=" * 50)

    # 检查Python环境
    if not check_python_environment():
        sys.exit(1)
    
    # 安装测试依赖
    if args.install_deps or args.all:
        if not install_test_dependencies():
            sys.exit(1)
    
    # 确保测试结果目录存在
    os.makedirs("test-results", exist_ok=True)
    
    # 运行测试
    global unit_success, integration_success, performance_success, linting_success, security_success
    unit_success = integration_success = performance_success = linting_success = security_success = True
    
    if args.unit or args.all:
        unit_success = run_unit_tests(coverage=args.coverage, verbose=args.verbose)
    
    if args.integration or args.all:
        integration_success = run_integration_tests(verbose=args.verbose)
    
    if args.performance or args.all:
        performance_success = run_performance_tests(verbose=args.verbose)
    
    if args.lint or args.all:
        linting_success = run_linting()
    
    if args.security or args.all:
        security_success = run_security_check()
    
    # 生成报告
    if args.all:
        from datetime import datetime
        generate_test_report()
    
    # 总结
    print("\n" + "=" * 50)
    all_passed = all([unit_success, integration_success, performance_success, linting_success, security_success])
    
    if all_passed:
        print("🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分测试失败，请检查上述输出")
        sys.exit(1)


if __name__ == "__main__":
    main()

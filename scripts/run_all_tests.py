#!/usr/bin/env python3
"""
FSOA 统一测试执行脚本

提供便于重复测试的统一接口，支持不同类型的测试执行和覆盖率分析
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.project_root = project_root
        self.test_results = {}
        
    def setup_environment(self):
        """设置测试环境"""
        print("🔧 设置测试环境...")
        
        # 设置环境变量
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
        
        # 初始化测试数据库
        try:
            from src.fsoa.data.database import DatabaseManager
            test_db_path = self.project_root / "test.db"
            if test_db_path.exists():
                test_db_path.unlink()
            
            db_manager = DatabaseManager(f"sqlite:///{test_db_path}")
            db_manager.init_database()
            print("✅ 测试数据库初始化完成")
        except Exception as e:
            print(f"⚠️ 数据库初始化警告: {e}")
    
    def run_unit_tests(self, coverage: bool = True, verbose: bool = True) -> Dict[str, Any]:
        """运行单元测试"""
        print("\n🧪 运行单元测试...")
        
        cmd = ["python", "-m", "pytest"]
        
        if coverage:
            cmd.extend([
                "--cov=src/fsoa",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=json:coverage.json"
            ])
        
        if verbose:
            cmd.append("-v")
        
        # 单元测试路径
        cmd.extend([
            "tests/unit/",
            "--tb=short"
        ])
        
        result = self._run_command(cmd, "单元测试")
        self.test_results['unit'] = result
        return result
    
    def run_integration_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """运行集成测试"""
        print("\n🔗 运行集成测试...")
        
        cmd = ["python", "-m", "pytest"]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend([
            "tests/integration/",
            "--tb=short"
        ])
        
        result = self._run_command(cmd, "集成测试")
        self.test_results['integration'] = result
        return result
    
    def run_e2e_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """运行端到端测试"""
        print("\n🎯 运行端到端测试...")
        
        cmd = ["python", "-m", "pytest"]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend([
            "tests/e2e/",
            "--tb=short"
        ])
        
        result = self._run_command(cmd, "端到端测试")
        self.test_results['e2e'] = result
        return result
    
    def run_specific_tests(self, test_path: str, coverage: bool = False) -> Dict[str, Any]:
        """运行特定测试"""
        print(f"\n🎯 运行特定测试: {test_path}")
        
        cmd = ["python", "-m", "pytest"]
        
        if coverage:
            cmd.extend([
                "--cov=src/fsoa",
                "--cov-report=term-missing"
            ])
        
        cmd.extend([
            test_path,
            "-v",
            "--tb=short"
        ])
        
        result = self._run_command(cmd, f"特定测试 ({test_path})")
        return result
    
    def run_coverage_analysis(self) -> Dict[str, Any]:
        """运行覆盖率分析"""
        print("\n📊 运行覆盖率分析...")
        
        cmd = [
            "python", "-m", "pytest",
            "--cov=src/fsoa",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=json:coverage.json",
            "tests/unit/",
            "-q"
        ]
        
        result = self._run_command(cmd, "覆盖率分析")
        
        # 解析覆盖率数据
        try:
            import json
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                    result['coverage_percentage'] = total_coverage
                    print(f"📈 总体覆盖率: {total_coverage:.1f}%")
        except Exception as e:
            print(f"⚠️ 覆盖率数据解析失败: {e}")
        
        return result
    
    def run_all_tests(self, coverage: bool = True) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 运行完整测试套件...")
        
        # 设置环境
        self.setup_environment()
        
        # 运行各类测试
        unit_result = self.run_unit_tests(coverage=coverage)
        integration_result = self.run_integration_tests()
        e2e_result = self.run_e2e_tests()
        
        # 汇总结果
        summary = {
            'unit': unit_result,
            'integration': integration_result,
            'e2e': e2e_result,
            'overall_success': all([
                unit_result.get('success', False),
                integration_result.get('success', False),
                e2e_result.get('success', False)
            ])
        }
        
        self._print_summary(summary)
        return summary
    
    def _run_command(self, cmd: List[str], test_type: str) -> Dict[str, Any]:
        """执行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            success = result.returncode == 0
            
            print(f"{'✅' if success else '❌'} {test_type}: {'通过' if success else '失败'}")
            
            if not success:
                print("错误输出:")
                print(result.stderr)
            
            return {
                'success': success,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(cmd)
            }
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_type} 超时")
            return {
                'success': False,
                'error': 'timeout',
                'command': ' '.join(cmd)
            }
        except Exception as e:
            print(f"❌ {test_type} 执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'command': ' '.join(cmd)
            }
    
    def _print_summary(self, summary: Dict[str, Any]):
        """打印测试总结"""
        print("\n" + "="*60)
        print("📊 测试执行总结")
        print("="*60)
        
        for test_type, result in summary.items():
            if test_type == 'overall_success':
                continue
            
            status = "✅ 通过" if result.get('success') else "❌ 失败"
            print(f"{test_type.upper()}: {status}")
        
        overall_status = "✅ 全部通过" if summary['overall_success'] else "❌ 有失败"
        print(f"\n总体结果: {overall_status}")
        
        # 显示覆盖率信息
        unit_result = summary.get('unit', {})
        if 'coverage_percentage' in unit_result:
            coverage = unit_result['coverage_percentage']
            print(f"📈 代码覆盖率: {coverage:.1f}%")
        
        print("\n📁 生成的报告:")
        print("- HTML覆盖率报告: htmlcov/index.html")
        print("- JSON覆盖率数据: coverage.json")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FSOA 统一测试执行脚本")
    parser.add_argument(
        "test_type",
        choices=["all", "unit", "integration", "e2e", "coverage", "specific"],
        help="要运行的测试类型"
    )
    parser.add_argument(
        "--path",
        help="特定测试路径 (当test_type为specific时使用)"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="跳过覆盖率分析"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.test_type == "all":
            result = runner.run_all_tests(coverage=not args.no_coverage)
        elif args.test_type == "unit":
            runner.setup_environment()
            result = runner.run_unit_tests(coverage=not args.no_coverage, verbose=not args.quiet)
        elif args.test_type == "integration":
            runner.setup_environment()
            result = runner.run_integration_tests(verbose=not args.quiet)
        elif args.test_type == "e2e":
            runner.setup_environment()
            result = runner.run_e2e_tests(verbose=not args.quiet)
        elif args.test_type == "coverage":
            runner.setup_environment()
            result = runner.run_coverage_analysis()
        elif args.test_type == "specific":
            if not args.path:
                print("❌ 使用specific类型时必须指定--path参数")
                sys.exit(1)
            runner.setup_environment()
            result = runner.run_specific_tests(args.path, coverage=not args.no_coverage)
        
        # 根据结果设置退出码
        if isinstance(result, dict):
            success = result.get('success', result.get('overall_success', False))
        else:
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

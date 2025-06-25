#!/usr/bin/env python3
"""
虚拟环境设置脚本

自动创建和配置FSOA项目的Python虚拟环境
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
VENV_NAME = "fsoa_env"
VENV_PATH = PROJECT_ROOT / VENV_NAME


def run_command(cmd, check=True, shell=False):
    """运行命令"""
    print(f"🔧 执行命令: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(
            cmd, 
            check=check, 
            shell=shell,
            capture_output=True, 
            text=True,
            cwd=PROJECT_ROOT
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        raise


def check_python_version():
    """检查Python版本"""
    print("🐍 检查Python版本...")
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3 or version.minor < 9:
        print("❌ 错误: 需要Python 3.9或更高版本")
        print("请升级Python版本后重试")
        sys.exit(1)
    
    print("✅ Python版本检查通过")


def create_virtual_environment():
    """创建虚拟环境"""
    print(f"\n📦 创建虚拟环境: {VENV_NAME}")
    
    if VENV_PATH.exists():
        print(f"⚠️  虚拟环境已存在: {VENV_PATH}")
        response = input("是否删除并重新创建？(y/N): ")
        if response.lower() == 'y':
            print("🗑️  删除现有虚拟环境...")
            if platform.system() == "Windows":
                run_command(f"rmdir /s /q {VENV_PATH}", shell=True)
            else:
                run_command(["rm", "-rf", str(VENV_PATH)])
        else:
            print("📦 使用现有虚拟环境")
            return
    
    # 创建虚拟环境
    print("🔨 创建新的虚拟环境...")
    run_command([sys.executable, "-m", "venv", str(VENV_PATH)])
    print(f"✅ 虚拟环境创建成功: {VENV_PATH}")


def get_pip_path():
    """获取虚拟环境中的pip路径"""
    if platform.system() == "Windows":
        return VENV_PATH / "Scripts" / "pip.exe"
    else:
        return VENV_PATH / "bin" / "pip"


def get_python_path():
    """获取虚拟环境中的python路径"""
    if platform.system() == "Windows":
        return VENV_PATH / "Scripts" / "python.exe"
    else:
        return VENV_PATH / "bin" / "python"


def upgrade_pip():
    """升级pip"""
    print("\n📈 升级pip...")
    pip_path = get_pip_path()
    run_command([str(pip_path), "install", "--upgrade", "pip"])
    print("✅ pip升级完成")


def install_dependencies():
    """安装项目依赖"""
    print("\n📚 安装项目依赖...")
    pip_path = get_pip_path()
    requirements_file = PROJECT_ROOT / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ 错误: requirements.txt文件不存在")
        return False
    
    print(f"📋 从 {requirements_file} 安装依赖...")
    run_command([str(pip_path), "install", "-r", str(requirements_file)])
    print("✅ 依赖安装完成")
    return True


def verify_installation():
    """验证安装"""
    print("\n🔍 验证安装...")
    python_path = get_python_path()
    
    # 检查关键包
    key_packages = [
        "streamlit", "pydantic", "sqlalchemy", 
        "langgraph", "openai", "apscheduler"
    ]
    
    for package in key_packages:
        try:
            result = run_command([
                str(python_path), "-c", 
                f"import {package}; print(f'{package}: OK')"
            ])
            print(f"✅ {package}: 导入成功")
        except subprocess.CalledProcessError:
            print(f"❌ {package}: 导入失败")
            return False
    
    print("✅ 安装验证通过")
    return True


def create_activation_scripts():
    """创建激活脚本"""
    print("\n📝 创建激活脚本...")
    
    # Linux/Mac激活脚本
    activate_sh = PROJECT_ROOT / "activate.sh"
    with open(activate_sh, 'w') as f:
        f.write(f"""#!/bin/bash
# FSOA虚拟环境激活脚本

echo "🚀 激活FSOA虚拟环境..."
source {VENV_PATH}/bin/activate
echo "✅ 虚拟环境已激活: {VENV_NAME}"
echo "💡 使用 'deactivate' 命令退出虚拟环境"
echo ""
echo "🎯 常用命令:"
echo "  python scripts/init_db.py        # 初始化数据库"
echo "  python scripts/start_app.py      # 启动Web界面"
echo "  python scripts/start_agent.py    # 启动Agent服务"
echo ""
""")
    
    # Windows激活脚本
    activate_bat = PROJECT_ROOT / "activate.bat"
    with open(activate_bat, 'w') as f:
        f.write(f"""@echo off
REM FSOA虚拟环境激活脚本

echo 🚀 激活FSOA虚拟环境...
call {VENV_PATH}\\Scripts\\activate.bat
echo ✅ 虚拟环境已激活: {VENV_NAME}
echo 💡 使用 'deactivate' 命令退出虚拟环境
echo.
echo 🎯 常用命令:
echo   python scripts\\init_db.py        # 初始化数据库
echo   python scripts\\start_app.py      # 启动Web界面
echo   python scripts\\start_agent.py    # 启动Agent服务
echo.
""")
    
    # 设置执行权限
    if platform.system() != "Windows":
        os.chmod(activate_sh, 0o755)
    
    print(f"✅ 激活脚本创建完成:")
    print(f"   Linux/Mac: ./activate.sh")
    print(f"   Windows: activate.bat")


def print_usage_instructions():
    """打印使用说明"""
    print("\n" + "="*60)
    print("🎉 FSOA虚拟环境设置完成！")
    print("="*60)
    
    print("\n📋 下一步操作:")
    
    if platform.system() == "Windows":
        print("1. 激活虚拟环境:")
        print(f"   {VENV_PATH}\\Scripts\\activate")
        print("   或运行: activate.bat")
    else:
        print("1. 激活虚拟环境:")
        print(f"   source {VENV_PATH}/bin/activate")
        print("   或运行: ./activate.sh")
    
    print("\n2. 配置环境变量:")
    print("   cp .env.example .env")
    print("   # 编辑 .env 文件，填入实际配置")
    
    print("\n3. 初始化数据库:")
    print("   python scripts/init_db.py")
    
    print("\n4. 启动应用:")
    print("   python scripts/start_app.py")
    
    print("\n💡 提示:")
    print("- 每次使用项目前都需要激活虚拟环境")
    print("- 使用 'deactivate' 命令退出虚拟环境")
    print("- 如遇问题，可删除虚拟环境重新创建")


def main():
    """主函数"""
    print("🤖 FSOA虚拟环境设置工具")
    print("="*50)
    
    try:
        # 检查Python版本
        check_python_version()
        
        # 创建虚拟环境
        create_virtual_environment()
        
        # 升级pip
        upgrade_pip()
        
        # 安装依赖
        if not install_dependencies():
            print("❌ 依赖安装失败")
            sys.exit(1)
        
        # 验证安装
        if not verify_installation():
            print("❌ 安装验证失败")
            sys.exit(1)
        
        # 创建激活脚本
        create_activation_scripts()
        
        # 打印使用说明
        print_usage_instructions()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 设置过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
修复所有TaskInfo引用

彻底清理所有对TaskInfo的引用
"""

import sys
from pathlib import Path
import re

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def fix_tools_imports():
    """修复tools.py中的导入"""
    print("🔧 修复tools.py导入")
    print("-" * 40)
    
    try:
        tools_file = project_root / "src/fsoa/agent/tools.py"
        with open(tools_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除TaskInfo导入
        content = content.replace(
            "from ..data.models import (\n    TaskInfo, NotificationInfo, NotificationStatus, Priority, OpportunityInfo,\n    TaskStatus, NotificationTask\n)",
            "from ..data.models import (\n    NotificationInfo, NotificationStatus, Priority, OpportunityInfo,\n    TaskStatus, NotificationTask\n)"
        )
        
        with open(tools_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已修复tools.py导入")
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False


def fix_metabase_references():
    """修复metabase.py中的TaskInfo引用"""
    print("🔧 修复metabase.py引用")
    print("-" * 40)
    
    try:
        metabase_file = project_root / "src/fsoa/data/metabase.py"
        with open(metabase_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除TaskInfo相关的方法
        # 1. 移除get_overdue_tasks_legacy方法
        pattern = r'def get_overdue_tasks_legacy\(self.*?return tasks'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # 2. 移除_convert_raw_task_to_model方法
        pattern = r'def _convert_raw_task_to_model\(self.*?return TaskInfo\(.*?\)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # 3. 移除TaskInfo导入
        content = content.replace("TaskInfo, ", "")
        content = content.replace(", TaskInfo", "")
        content = content.replace("from ..data.models import TaskInfo", "")
        
        with open(metabase_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已修复metabase.py引用")
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False


def fix_test_files():
    """修复测试文件中的TaskInfo引用"""
    print("🔧 修复测试文件")
    print("-" * 40)
    
    try:
        # 1. 修复test_tools.py
        test_tools_file = project_root / "tests/unit/test_tools.py"
        if test_tools_file.exists():
            with open(test_tools_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除TaskInfo相关的导入和测试
            content = content.replace("fetch_overdue_tasks, send_notification, update_task_status,", "")
            content = content.replace("from src.fsoa.data.models import TaskInfo, TaskStatus, Priority, NotificationInfo",
                                    "from src.fsoa.data.models import TaskStatus, Priority, NotificationInfo")
            
            with open(test_tools_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 已修复test_tools.py")
        
        # 2. 修复test_models.py
        test_models_file = project_root / "tests/unit/test_models.py"
        if test_models_file.exists():
            with open(test_models_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除TaskInfo相关的测试
            content = content.replace("TaskInfo, ", "")
            content = content.replace(", TaskInfo", "")
            
            # 移除TestTaskInfo类
            pattern = r'class TestTaskInfo:.*?(?=class|\Z)'
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            with open(test_models_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 已修复test_models.py")
        
        # 3. 修复conftest.py
        conftest_file = project_root / "tests/conftest.py"
        if conftest_file.exists():
            with open(conftest_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除sample_task fixture
            pattern = r'@pytest\.fixture\ndef sample_task\(\):.*?(?=@|\Z)'
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            with open(conftest_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 已修复conftest.py")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False


def fix_models_references():
    """修复models.py中的TaskInfo引用"""
    print("🔧 修复models.py引用")
    print("-" * 40)
    
    try:
        models_file = project_root / "src/fsoa/data/models.py"
        with open(models_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除DecisionContext中的TaskInfo引用
        content = content.replace("task: TaskInfo", "# task: TaskInfo  # 已废弃")
        
        with open(models_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已修复models.py引用")
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False


def fix_documentation():
    """修复文档中的TaskInfo引用"""
    print("🔧 修复文档引用")
    print("-" * 40)
    
    try:
        # 修复开发文档
        dev_doc = project_root / "docs/30_DEVELOPMENT.md"
        if dev_doc.exists():
            with open(dev_doc, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换TaskInfo示例为OpportunityInfo
            content = content.replace("class TaskInfo(BaseModel):", "class OpportunityInfo(BaseModel):")
            content = content.replace("TaskInfo", "OpportunityInfo")
            content = content.replace("fetch_overdue_tasks", "get_overdue_opportunities")
            
            with open(dev_doc, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 已修复开发文档")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False


def create_compatibility_stub():
    """创建兼容性存根，避免导入错误"""
    print("🔧 创建兼容性存根")
    print("-" * 40)
    
    try:
        models_file = project_root / "src/fsoa/data/models.py"
        with open(models_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 在文件末尾添加兼容性存根
        compatibility_stub = '''

# ==================== 兼容性存根 ====================
# 为了避免导入错误，提供TaskInfo的兼容性存根
# 新代码应该使用OpportunityInfo

class TaskInfo:
    """
    TaskInfo兼容性存根 - 已废弃
    
    ⚠️ 此类已废弃，仅用于避免导入错误
    新代码请使用OpportunityInfo
    """
    def __init__(self, **kwargs):
        raise DeprecationWarning(
            "TaskInfo is deprecated. Use OpportunityInfo instead."
        )

# 兼容性导入
__all__ = [
    'OpportunityInfo', 'OpportunityStatus', 'NotificationTask', 
    'NotificationTaskType', 'NotificationTaskStatus', 'NotificationInfo',
    'NotificationStatus', 'Priority', 'TaskStatus', 'AgentRun', 'AgentRunStatus',
    'AgentHistory', 'GroupConfig', 'MetabaseQuery', 'DecisionContext',
    'TaskInfo'  # 兼容性存根
]
'''
        
        # 如果还没有兼容性存根，则添加
        if "兼容性存根" not in content:
            content += compatibility_stub
        
        with open(models_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已创建兼容性存根")
        return True
        
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        return False


def main():
    """主函数"""
    print("🔧 FSOA TaskInfo引用修复")
    print("=" * 50)
    print("清理所有TaskInfo引用，避免导入错误")
    print("=" * 50)
    
    success_count = 0
    total_steps = 5
    
    try:
        # 1. 修复tools.py导入
        if fix_tools_imports():
            success_count += 1
        print()
        
        # 2. 修复metabase.py引用
        if fix_metabase_references():
            success_count += 1
        print()
        
        # 3. 修复测试文件
        if fix_test_files():
            success_count += 1
        print()
        
        # 4. 修复models.py引用
        if fix_models_references():
            success_count += 1
        print()
        
        # 5. 创建兼容性存根
        if create_compatibility_stub():
            success_count += 1
        print()
        
        # 总结
        print("=" * 50)
        print(f"🎯 修复完成: {success_count}/{total_steps} 步骤成功")
        
        if success_count == total_steps:
            print("🎉 所有TaskInfo引用修复成功！")
            print()
            print("✅ 修复内容:")
            print("  - 移除了tools.py中的TaskInfo导入")
            print("  - 清理了metabase.py中的TaskInfo方法")
            print("  - 修复了测试文件中的引用")
            print("  - 更新了models.py中的引用")
            print("  - 创建了兼容性存根避免导入错误")
            print()
            print("🚀 现在应用可以正常启动了")
        else:
            print("⚠️  部分修复步骤失败，请检查上述错误信息")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 修复过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

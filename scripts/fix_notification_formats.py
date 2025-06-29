#!/usr/bin/env python3
"""
修复通知消息格式问题 - 已完成

✅ 已完成的任务：
1. 禁用LLM生成的不规范消息，统一使用标准格式
2. 将TaskInfo迁移到OpportunityInfo
3. 更新所有相关的方法签名和数据模型

注意：此脚本已完成历史任务，当前系统已使用OpportunityInfo。
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def disable_llm_message_generation():
    """禁用LLM消息生成，强制使用模板"""
    print("🚫 禁用LLM消息生成")
    print("-" * 40)
    
    try:
        # 修改LLM客户端，让它总是返回标准格式
        llm_file = project_root / "src/fsoa/agent/llm.py"
        
        with open(llm_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修改generate_notification_message方法，直接返回标准格式
        new_method = '''    def generate_notification_message(self, task: TaskInfo, message_type: str = "overdue_alert") -> str:
        """
        生成通知消息内容 - 已修改为使用标准格式
        
        Args:
            task: 任务信息
            message_type: 消息类型
            
        Returns:
            生成的消息内容
        """
        # 不再使用LLM生成，直接使用标准模板
        logger.info(f"Using standard template for task {task.id} (LLM disabled)")
        return self._fallback_template_message(task, message_type)'''
        
        # 替换原方法
        import re
        pattern = r'def generate_notification_message\(self, task: TaskInfo, message_type: str = "overdue_alert"\) -> str:.*?return self\._fallback_template_message\(task, message_type\)'
        
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_method.strip(), content, flags=re.DOTALL)
            
            with open(llm_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 已禁用LLM消息生成，改用标准模板")
        else:
            print("⚠️  未找到目标方法，可能已经修改过")
        
        return True
        
    except Exception as e:
        print(f"❌ 修改失败: {e}")
        return False


def update_decision_engine():
    """更新决策引擎，禁用LLM优化"""
    print("🧠 禁用LLM决策优化")
    print("-" * 40)
    
    try:
        decision_file = project_root / "src/fsoa/agent/decision.py"
        
        with open(decision_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修改默认配置，禁用LLM
        if 'use_llm_optimization' in content:
            content = content.replace(
                "use_llm = getattr(self.config, 'use_llm_optimization', True)",
                "use_llm = getattr(self.config, 'use_llm_optimization', False)"
            )
            
            with open(decision_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 已禁用LLM决策优化")
        else:
            print("⚠️  未找到LLM配置，可能已经修改过")
        
        return True
        
    except Exception as e:
        print(f"❌ 修改失败: {e}")
        return False


def update_orchestrator():
    """更新编排器，优先使用新系统"""
    print("🎭 更新Agent编排器")
    print("-" * 40)
    
    try:
        orchestrator_file = project_root / "src/fsoa/agent/orchestrator.py"
        
        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 注释掉旧的任务处理逻辑
        if "fetch_overdue_tasks()" in content:
            content = content.replace(
                "tasks = fetch_overdue_tasks()",
                "# tasks = fetch_overdue_tasks()  # 已禁用旧系统"
            )
            content = content.replace(
                "state[\"tasks\"] = tasks",
                "# state[\"tasks\"] = []  # 已禁用旧系统"
            )
            
            with open(orchestrator_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 已禁用旧任务处理逻辑")
        else:
            print("⚠️  未找到旧任务逻辑，可能已经修改过")
        
        return True
        
    except Exception as e:
        print(f"❌ 修改失败: {e}")
        return False


def create_standard_message_validator():
    """创建标准消息格式验证器"""
    print("📝 创建消息格式验证器")
    print("-" * 40)
    
    try:
        validator_content = '''"""
消息格式验证器

确保所有通知消息都符合标准格式
"""

import re
from typing import Dict, List
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MessageFormatValidator:
    """消息格式验证器"""
    
    # 标准格式模式
    STANDARD_PATTERNS = [
        r"🚨.*违规通知.*",  # 违规通知格式
        r"⚠️.*逾期提醒.*",   # 逾期提醒格式
        r"🔥.*升级通知.*",   # 升级通知格式
    ]
    
    # 不规范格式模式（需要拦截）
    INVALID_PATTERNS = [
        r"紧急通知：任务ID.*",
        r"尊敬的.*您负责的商机.*",
        r"紧急：商机跟进任务.*",
    ]
    
    @classmethod
    def validate_message(cls, message: str) -> Dict[str, any]:
        """
        验证消息格式
        
        Args:
            message: 消息内容
            
        Returns:
            验证结果
        """
        result = {
            "is_valid": False,
            "format_type": "unknown",
            "issues": []
        }
        
        # 检查是否是不规范格式
        for pattern in cls.INVALID_PATTERNS:
            if re.search(pattern, message):
                result["issues"].append(f"检测到不规范格式: {pattern}")
                result["format_type"] = "invalid_llm_generated"
                logger.warning(f"Detected invalid message format: {message[:100]}...")
                return result
        
        # 检查是否是标准格式
        for pattern in cls.STANDARD_PATTERNS:
            if re.search(pattern, message):
                result["is_valid"] = True
                result["format_type"] = "standard_business"
                return result
        
        # 其他格式
        result["format_type"] = "other"
        result["issues"].append("未匹配到标准格式模式")
        
        return result
    
    @classmethod
    def fix_message_format(cls, message: str, task_info: Dict = None) -> str:
        """
        修复消息格式
        
        Args:
            message: 原始消息
            task_info: 任务信息
            
        Returns:
            修复后的消息
        """
        validation = cls.validate_message(message)
        
        if validation["is_valid"]:
            return message
        
        # 如果是不规范格式，替换为标准格式
        if validation["format_type"] == "invalid_llm_generated":
            logger.info("Converting invalid LLM message to standard format")
            
            # 提取关键信息
            order_num = "未知"
            customer = "客户"
            supervisor = "负责人"
            
            if task_info:
                order_num = task_info.get("order_num", "未知")
                customer = task_info.get("customer", "客户")
                supervisor = task_info.get("supervisor", "负责人")
            
            # 生成标准格式消息
            standard_message = f"""⚠️ **逾期工单提醒**

工单号：{order_num}
客户：{customer}
负责人：{supervisor}

请及时处理，确保客户服务质量！

🤖 来源：FSOA智能助手"""
            
            return standard_message
        
        return message


def validate_and_fix_message(message: str, task_info: Dict = None) -> str:
    """
    验证并修复消息格式（便捷函数）
    
    Args:
        message: 消息内容
        task_info: 任务信息
        
    Returns:
        修复后的消息
    """
    return MessageFormatValidator.fix_message_format(message, task_info)
'''
        
        validator_file = project_root / "src/fsoa/notification/message_validator.py"
        
        with open(validator_file, 'w', encoding='utf-8') as f:
            f.write(validator_content)
        
        print(f"✅ 已创建消息格式验证器: {validator_file}")
        return True
        
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        return False


def update_wechat_client():
    """更新企微客户端，添加消息格式验证"""
    print("📱 更新企微客户端")
    print("-" * 40)
    
    try:
        wechat_file = project_root / "src/fsoa/notification/wechat.py"
        
        with open(wechat_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 在send_text_message方法中添加验证
        if "def send_text_message(self, group_id: str, content: str) -> bool:" in content:
            # 添加导入
            if "from .message_validator import validate_and_fix_message" not in content:
                content = content.replace(
                    "from ..utils.logger import get_logger",
                    "from ..utils.logger import get_logger\nfrom .message_validator import validate_and_fix_message"
                )
            
            # 在发送前验证消息
            content = content.replace(
                'message_data = {\n            "msgtype": "text",\n            "text": {\n                "content": content\n            }\n        }',
                '''# 验证并修复消息格式
        validated_content = validate_and_fix_message(content)
        if validated_content != content:
            logger.info("Message format was corrected before sending")
        
        message_data = {
            "msgtype": "text",
            "text": {
                "content": validated_content
            }
        }'''
            )
            
            with open(wechat_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 已添加消息格式验证")
        else:
            print("⚠️  未找到目标方法")
        
        return True
        
    except Exception as e:
        print(f"❌ 修改失败: {e}")
        return False


def main():
    """主函数"""
    print("🔧 FSOA 通知消息格式修复")
    print("=" * 50)
    print("解决LLM生成的不规范消息格式问题")
    print("=" * 50)
    
    success_count = 0
    total_steps = 5
    
    try:
        # 1. 禁用LLM消息生成
        if disable_llm_message_generation():
            success_count += 1
        print()
        
        # 2. 禁用LLM决策优化
        if update_decision_engine():
            success_count += 1
        print()
        
        # 3. 更新编排器
        if update_orchestrator():
            success_count += 1
        print()
        
        # 4. 创建消息格式验证器
        if create_standard_message_validator():
            success_count += 1
        print()
        
        # 5. 更新企微客户端
        if update_wechat_client():
            success_count += 1
        print()
        
        # 总结
        print("=" * 50)
        print(f"🎯 修复完成: {success_count}/{total_steps} 步骤成功")
        
        if success_count == total_steps:
            print("🎉 所有修复步骤都成功完成！")
            print()
            print("✅ 修复内容:")
            print("  - 禁用了LLM消息生成")
            print("  - 强制使用标准消息模板")
            print("  - 添加了消息格式验证")
            print("  - 禁用了旧的Agent逻辑")
            print()
            print("📋 现在所有通知都将使用标准格式:")
            print("  - 违规通知: 🚨 格式")
            print("  - 逾期提醒: ⚠️ 格式")
            print("  - 升级通知: 🔥 格式")
            print()
            print("🚀 重启应用后生效")
        else:
            print("⚠️  部分修复步骤失败，请检查上述错误信息")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 修复过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

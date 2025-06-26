#!/usr/bin/env python3
"""
彻底重构通知架构

1. 删除旧Agent逻辑
2. 统一通知流程到notification_tasks表
3. 在NotificationManager中支持LLM格式化选项
4. 移除不必要的格式验证
"""

import sys
from pathlib import Path
import os

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def remove_legacy_agent_logic():
    """彻底删除旧Agent逻辑"""
    print("🗑️ 删除旧Agent逻辑")
    print("-" * 40)
    
    try:
        # 1. 删除TaskInfo相关代码
        models_file = project_root / "src/fsoa/data/models.py"
        with open(models_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除TaskInfo类定义
        import re
        pattern = r'class TaskInfo\(BaseModel\):.*?(?=class|\Z)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        with open(models_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已删除TaskInfo模型")
        
        # 2. 删除fetch_overdue_tasks函数
        tools_file = project_root / "src/fsoa/agent/tools.py"
        with open(tools_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除fetch_overdue_tasks函数
        pattern = r'@log_function_call.*?def fetch_overdue_tasks\(\).*?(?=@|\ndef|\Z)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # 移除send_notification函数
        pattern = r'@log_function_call.*?def send_notification\(.*?\n    """.*?""".*?(?=@|\ndef|\Z)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        with open(tools_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已删除旧的工具函数")
        
        # 3. 清理orchestrator中的旧逻辑
        orchestrator_file = project_root / "src/fsoa/agent/orchestrator.py"
        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除旧任务相关的导入和逻辑
        content = content.replace(
            "fetch_overdue_tasks, send_notification, send_business_notifications, update_task_status",
            "send_business_notifications"
        )
        
        # 移除旧任务处理逻辑
        pattern = r'# 向后兼容：尝试获取传统任务.*?except Exception as e:.*?output\["legacy_task_count"\] = 0'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        with open(orchestrator_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已清理orchestrator旧逻辑")
        
        return True
        
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        return False


def enhance_notification_manager():
    """增强NotificationManager，支持LLM格式化选项"""
    print("🔧 增强NotificationManager")
    print("-" * 40)
    
    try:
        # 修改NotificationManager，添加LLM格式化选项
        manager_file = project_root / "src/fsoa/agent/managers/notification_manager.py"
        
        with open(manager_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 在类初始化中添加LLM选项
        if "def __init__(self" in content:
            content = content.replace(
                "self.max_retry_count = max_retry_count",
                """self.max_retry_count = max_retry_count
        
        # LLM格式化选项
        from ...utils.config import get_config
        config = get_config()
        self.use_llm_formatting = getattr(config, 'use_llm_message_formatting', False)
        
        if self.use_llm_formatting:
            from ..llm import get_deepseek_client
            self.llm_client = get_deepseek_client()
            logger.info("LLM message formatting enabled")
        else:
            self.llm_client = None
            logger.info("Using standard message templates")"""
            )
        
        # 修改消息格式化逻辑
        format_method = '''    def _format_notification_message(self, org_name: str, tasks: List[NotificationTask],
                                   notification_type: NotificationTaskType) -> str:
        """格式化通知消息"""
        try:
            # 获取商机信息
            opportunities = [self._get_opportunity_info_for_notification(task) for task in tasks]
            
            if self.use_llm_formatting and self.llm_client:
                # 使用LLM格式化
                return self._format_with_llm(org_name, opportunities, notification_type)
            else:
                # 使用标准模板
                return self._format_with_template(org_name, opportunities, notification_type)
                
        except Exception as e:
            logger.error(f"Failed to format message: {e}")
            # 降级到标准模板
            return self._format_with_template(org_name, opportunities, notification_type)
    
    def _format_with_llm(self, org_name: str, opportunities: List[OpportunityInfo],
                        notification_type: NotificationTaskType) -> str:
        """使用LLM格式化消息"""
        try:
            # 构建LLM提示词
            prompt = self._build_llm_formatting_prompt(org_name, opportunities, notification_type)
            
            response = self.llm_client.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 低温度确保格式一致性
                max_tokens=800
            )
            
            message = response.choices[0].message.content.strip()
            logger.info(f"Generated LLM message for {org_name}")
            return message
            
        except Exception as e:
            logger.error(f"LLM formatting failed: {e}")
            # 降级到标准模板
            return self._format_with_template(org_name, opportunities, notification_type)
    
    def _format_with_template(self, org_name: str, opportunities: List[OpportunityInfo],
                            notification_type: NotificationTaskType) -> str:
        """使用标准模板格式化消息"""
        if notification_type == NotificationTaskType.VIOLATION:
            return self.formatter.format_violation_notification(org_name, opportunities)
        elif notification_type == NotificationTaskType.ESCALATION:
            return self.formatter.format_escalation_notification(org_name, opportunities)
        else:
            return self.formatter.format_org_overdue_notification(org_name, opportunities)
    
    def _build_llm_formatting_prompt(self, org_name: str, opportunities: List[OpportunityInfo],
                                   notification_type: NotificationTaskType) -> str:
        """构建LLM格式化提示词"""
        type_desc = {
            NotificationTaskType.VIOLATION: "违规通知（12小时未处理）",
            NotificationTaskType.STANDARD: "逾期提醒（24/48小时）",
            NotificationTaskType.ESCALATION: "升级通知（运营介入）"
        }
        
        opp_list = []
        for i, opp in enumerate(opportunities, 1):
            opp_list.append(f"{i}. 工单号：{opp.order_num}")
            opp_list.append(f"   客户：{opp.name}")
            opp_list.append(f"   地址：{opp.address}")
            opp_list.append(f"   负责人：{opp.supervisor_name}")
            opp_list.append(f"   已过时长：{opp.elapsed_hours:.1f}小时")
            opp_list.append("")
        
        prompt = f"""请为以下{type_desc.get(notification_type, "通知")}生成专业的企微群消息。

组织：{org_name}
通知类型：{type_desc.get(notification_type)}
工单信息：
{chr(10).join(opp_list)}

要求：
1. 使用适当的emoji（🚨违规、⚠️逾期、🔥升级）
2. 格式清晰，信息完整
3. 语气专业但紧迫
4. 包含明确的行动指示
5. 长度控制在500字以内

请直接返回消息内容，不需要解释。"""
        
        return prompt'''
        
        # 插入新方法
        if "_send_standard_notification" in content:
            content = content.replace(
                "    def _send_standard_notification(self, org_name: str, tasks: List[NotificationTask],",
                format_method + "\n\n    def _send_standard_notification(self, org_name: str, tasks: List[NotificationTask],"
            )
        
        # 更新发送方法使用新的格式化
        content = content.replace(
            "message = self.formatter.format_org_overdue_notification(",
            "message = self._format_notification_message(org_name, tasks, NotificationTaskType.STANDARD)"
        )
        content = content.replace(
            "[self._get_opportunity_info_for_notification(task) for task in tasks]",
            ""
        )
        
        content = content.replace(
            "message = self.formatter.format_violation_notification(",
            "message = self._format_notification_message(org_name, tasks, NotificationTaskType.VIOLATION)"
        )
        
        with open(manager_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已增强NotificationManager支持LLM格式化")
        return True
        
    except Exception as e:
        print(f"❌ 增强失败: {e}")
        return False


def remove_format_validator():
    """移除不必要的格式验证器"""
    print("🗑️ 移除格式验证器")
    print("-" * 40)
    
    try:
        # 删除格式验证器文件
        validator_file = project_root / "src/fsoa/notification/message_validator.py"
        if validator_file.exists():
            os.remove(validator_file)
            print("✅ 已删除message_validator.py")
        
        # 从企微客户端移除验证逻辑
        wechat_file = project_root / "src/fsoa/notification/wechat.py"
        with open(wechat_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除导入
        content = content.replace(
            "from .message_validator import validate_and_fix_message\n", ""
        )
        
        # 移除验证逻辑
        content = content.replace(
            '''# 验证并修复消息格式
        validated_content = validate_and_fix_message(content)
        if validated_content != content:
            logger.info("Message format was corrected before sending")
        
        message_data = {
            "msgtype": "text",
            "text": {
                "content": validated_content
            }
        }''',
            '''message_data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }'''
        )
        
        with open(wechat_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已移除企微客户端的格式验证")
        return True
        
    except Exception as e:
        print(f"❌ 移除失败: {e}")
        return False


def update_configuration():
    """更新配置文件，添加LLM格式化选项"""
    print("⚙️ 更新配置")
    print("-" * 40)
    
    try:
        config_file = project_root / "src/fsoa/utils/config.py"
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 在Config类中添加新配置项
        if "class Config(BaseSettings):" in content:
            # 找到类定义后添加新字段
            content = content.replace(
                "# Agent执行配置",
                """# 通知消息格式化配置
    use_llm_message_formatting: bool = Field(
        default=False,
        description="是否使用LLM格式化通知消息"
    )
    
    # Agent执行配置"""
            )
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已添加LLM格式化配置选项")
        return True
        
    except Exception as e:
        print(f"❌ 配置更新失败: {e}")
        return False


def main():
    """主函数"""
    print("🏗️ FSOA 通知架构彻底重构")
    print("=" * 60)
    print("统一通知流程，支持LLM格式化选项")
    print("=" * 60)
    
    success_count = 0
    total_steps = 4
    
    try:
        # 1. 删除旧Agent逻辑
        if remove_legacy_agent_logic():
            success_count += 1
        print()
        
        # 2. 增强NotificationManager
        if enhance_notification_manager():
            success_count += 1
        print()
        
        # 3. 移除格式验证器
        if remove_format_validator():
            success_count += 1
        print()
        
        # 4. 更新配置
        if update_configuration():
            success_count += 1
        print()
        
        # 总结
        print("=" * 60)
        print(f"🎯 重构完成: {success_count}/{total_steps} 步骤成功")
        
        if success_count == total_steps:
            print("🎉 架构重构成功完成！")
            print()
            print("✅ 重构内容:")
            print("  - 彻底删除了旧Agent逻辑（TaskInfo、fetch_overdue_tasks等）")
            print("  - 统一通知流程到notification_tasks表")
            print("  - NotificationManager支持LLM格式化选项")
            print("  - 移除了不必要的格式验证")
            print()
            print("📋 新架构:")
            print("  商机数据 → NotificationManager → notification_tasks表")
            print("                    ↓")
            print("  (LLM格式化 或 标准模板) → 企微发送")
            print()
            print("⚙️ 配置选项:")
            print("  use_llm_message_formatting = True/False")
            print()
            print("🚀 重启应用后生效")
        else:
            print("⚠️  部分重构步骤失败，请检查上述错误信息")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 重构过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

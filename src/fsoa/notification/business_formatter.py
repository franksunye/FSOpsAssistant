"""
业务通知格式化模块

按照业务需求格式化通知内容
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from ..data.models import OpportunityInfo, OpportunityStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BusinessNotificationFormatter:
    """业务通知格式化器 - 支持动态SLA阈值的消息模板"""

    @staticmethod
    def _get_display_config() -> Dict[str, int]:
        """获取消息显示配置"""
        try:
            from ..data.database import get_database_manager
            db_manager = get_database_manager()

            return {
                'reminder_max': int(db_manager.get_system_config("reminder_max_display_orders") or "10"),
                'escalation_max': int(db_manager.get_system_config("escalation_max_display_orders") or "5"),
            }
        except Exception:
            # 降级到默认值
            return {
                'reminder_max': 10,
                'escalation_max': 5,
            }

    @staticmethod
    def _get_sla_threshold_text(opportunities: List[OpportunityInfo], threshold_type: str = "reminder") -> str:
        """
        获取SLA阈值文本描述

        Args:
            opportunities: 商机列表
            threshold_type: 阈值类型

        Returns:
            SLA阈值文本，如"4小时"或"4/8小时"（如果有多种状态）
        """
        if not opportunities:
            return "未知"

        # 收集不同状态的阈值
        thresholds = set()
        for opp in opportunities:
            threshold = opp.get_sla_threshold(threshold_type)
            if threshold > 0:
                thresholds.add(threshold)

        if len(thresholds) == 1:
            return f"{list(thresholds)[0]}小时"
        elif len(thresholds) > 1:
            sorted_thresholds = sorted(thresholds)
            return f"{'/'.join(map(str, sorted_thresholds))}小时"
        else:
            return "未知"

    @staticmethod
    def format_reminder_notification(org_name: str, opportunities: List[OpportunityInfo]) -> str:
        """
        格式化提醒通知（4/8小时）- 发送到服务商群

        Args:
            org_name: 组织名称
            opportunities: 需要提醒的商机列表

        Returns:
            格式化的提醒消息
        """
        if not opportunities:
            return ""

        message_parts = []
        message_parts.append(f"💡 **服务提醒** ({org_name})")
        message_parts.append("")
        message_parts.append(f"有 {len(opportunities)} 个商机需要关注：")
        message_parts.append("")

        # 获取显示配置
        display_config = BusinessNotificationFormatter._get_display_config()
        max_display = display_config['reminder_max']

        for i, opp in enumerate(opportunities[:max_display], 1):
            elapsed_str = f"{opp.elapsed_hours:.1f}小时" if opp.elapsed_hours else "未知"

            message_parts.append(f"{i:02d}. 工单号：{opp.order_num}")
            message_parts.append(f"     已用时长：{elapsed_str}")
            message_parts.append(f"     客户：{opp.name}")
            message_parts.append(f"     负责人：{opp.supervisor_name}")
            message_parts.append(f"     状态：{opp.order_status}")
            message_parts.append("")

        if len(opportunities) > max_display:
            message_parts.append(f"... 还有 {len(opportunities) - max_display} 个商机")
            message_parts.append("")

        message_parts.append("📝 请及时跟进处理，感谢配合！")
        return "\n".join(message_parts)

    @staticmethod
    def format_violation_notification(org_name: str, opportunities: List[OpportunityInfo]) -> str:
        """
        格式化违规通知（动态SLA阈值）

        Args:
            org_name: 组织名称
            opportunities: 违规商机列表

        Returns:
            格式化的通知消息
        """
        if not opportunities:
            return ""

        # 按状态分组
        status_groups = {}
        for opp in opportunities:
            status = opp.order_status
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(opp)

        # 获取动态SLA阈值文本
        sla_threshold_text = BusinessNotificationFormatter._get_sla_threshold_text(opportunities, "reminder")

        # 构建消息
        message_parts = [f"⚠️ SLA违规提醒 ({org_name})"]
        message_parts.append("")

        total_count = len(opportunities)
        message_parts.append(f"共有 {total_count} 个工单违反{sla_threshold_text}SLA规范：")
        message_parts.append("")

        # 获取显示配置
        display_config = BusinessNotificationFormatter._get_display_config()
        max_display = display_config['reminder_max']

        # 按状态显示（应用截断逻辑）
        item_index = 1
        displayed_count = 0

        for status, status_opps in status_groups.items():
            for opp in status_opps:
                if displayed_count >= max_display:
                    break

                elapsed_hours = opp.elapsed_hours or 0
                elapsed_days = int(elapsed_hours // 24)
                remaining_hours = int(elapsed_hours % 24)

                if elapsed_days > 0:
                    time_str = f"{elapsed_days}天{remaining_hours}小时"
                else:
                    time_str = f"{remaining_hours}小时"

                create_time_str = opp.create_time.strftime("%m-%d %H:%M") if opp.create_time else "未知"

                message_parts.append(f"{item_index:02d}. 工单号：{opp.order_num}")
                message_parts.append(f"     违规时长：{time_str}")
                message_parts.append(f"     客户：{opp.name}")
                message_parts.append(f"     地址：{opp.address}")
                message_parts.append(f"     负责人：{opp.supervisor_name}")
                message_parts.append(f"     创建时间：{create_time_str}")
                message_parts.append(f"     状态：{status}")
                message_parts.append("")

                item_index += 1
                displayed_count += 1

            if displayed_count >= max_display:
                break

        # 添加截断提示
        if total_count > max_display:
            message_parts.append(f"... 还有 {total_count - max_display} 个工单需要处理")
            message_parts.append("")

        message_parts.append("🚨 请销售人员立即处理，确保客户服务质量！")
        message_parts.append("💡 处理后系统将自动停止提醒")

        return "\n".join(message_parts)

    @staticmethod
    def format_org_overdue_notification(org_name: str, opportunities: List[OpportunityInfo]) -> str:
        """
        格式化组织逾期通知消息
        
        Args:
            org_name: 组织名称
            opportunities: 逾期商机列表
            
        Returns:
            格式化的通知消息
        """
        if not opportunities:
            return ""
        
        # 按状态分组
        pending_appointment = [opp for opp in opportunities if opp.order_status == OpportunityStatus.PENDING_APPOINTMENT]
        not_visiting = [opp for opp in opportunities if opp.order_status == OpportunityStatus.TEMPORARILY_NOT_VISITING]
        
        # 构建消息
        message_parts = []
        
        # 待预约工单
        if pending_appointment:
            message_parts.append(f"📋 待预约工单提醒 ({org_name})")
            message_parts.append("")
            message_parts.append(f"共有 {len(pending_appointment)} 个工单待预约：")
            message_parts.append("")
            
            for i, opp in enumerate(pending_appointment[:10], 1):  # 最多显示10个
                days_overdue = int(opp.elapsed_hours / 24)
                create_date = opp.create_time.strftime("%m-%d")
                
                message_parts.append(f"{i:02d}. 工单号：{opp.order_num}")
                message_parts.append(f"     滞留时长：{days_overdue}天")
                message_parts.append(f"     客户：{opp.name}")
                message_parts.append(f"     地址：{opp.address}")
                message_parts.append(f"     负责人：{opp.supervisor_name}")
                message_parts.append(f"     创建时间：{create_date}")
                message_parts.append(f"     状态：{opp.order_status}")
                message_parts.append("")
        
        # 暂不上门工单
        if not_visiting:
            if pending_appointment:
                message_parts.append("─" * 30)
                message_parts.append("")
            
            message_parts.append(f"📋 暂不上门工单提醒 ({org_name})")
            message_parts.append("")
            message_parts.append(f"共有 {len(not_visiting)} 个工单需跟进：")
            message_parts.append("")
            
            # 获取显示配置
            display_config = BusinessNotificationFormatter._get_display_config()
            max_display = display_config['reminder_max']

            for i, opp in enumerate(not_visiting[:max_display], 1):
                days_overdue = int(opp.elapsed_hours / 24)
                create_date = opp.create_time.strftime("%m-%d")

                message_parts.append(f"{i:02d}. 工单号：{opp.order_num}")
                message_parts.append(f"     滞留时长：{days_overdue}天")
                message_parts.append(f"     客户：{opp.name}")
                message_parts.append(f"     地址：{opp.address}")
                message_parts.append(f"     负责人：{opp.supervisor_name}")
                message_parts.append(f"     创建时间：{create_date}")
                message_parts.append(f"     状态：{opp.order_status}")
                message_parts.append("")

            if len(not_visiting) > max_display:
                message_parts.append(f"... 还有 {len(not_visiting) - max_display} 个工单需跟进")
                message_parts.append("")
        
        # 添加结尾
        message_parts.append("请及时跟进处理，如有疑问请联系运营人员。")
        
        return "\n".join(message_parts)
    
    @staticmethod
    def format_escalation_notification(org_name: str, opportunities: List[OpportunityInfo],
                                     mention_users: List[str] = None) -> str:
        """
        格式化升级通知消息（8/16小时）- 发送到运营群

        Args:
            org_name: 组织名称
            opportunities: 需要升级的商机列表
            mention_users: 需要@的用户列表

        Returns:
            格式化的升级通知消息
        """
        # 🔧 新增：调试信息
        from ..utils.logger import get_logger
        logger = get_logger(__name__)

        if not opportunities:
            logger.warning(f"No opportunities provided for escalation notification of {org_name}")
            return ""

        # 🔧 修复：去重商机列表，避免重复工单号
        unique_opportunities = []
        seen_order_nums = set()
        for opp in opportunities:
            if opp.order_num not in seen_order_nums:
                unique_opportunities.append(opp)
                seen_order_nums.add(opp.order_num)
            else:
                logger.warning(f"Duplicate order number {opp.order_num} found in escalation opportunities, skipping")

        if len(unique_opportunities) != len(opportunities):
            logger.info(f"Removed {len(opportunities) - len(unique_opportunities)} duplicate opportunities")

        # 使用去重后的商机列表
        opportunities = unique_opportunities

        # 获取显示配置
        display_config = BusinessNotificationFormatter._get_display_config()
        max_display = display_config['escalation_max']

        total_count = len(opportunities)
        display_count = min(total_count, max_display)
        remaining_count = max(0, total_count - max_display)

        logger.info(f"Formatting escalation notification for {org_name}: "
                   f"total={total_count}, display={display_count}, remaining={remaining_count}")

        message_parts = []
        message_parts.append("🚨 **运营升级通知**")
        message_parts.append("")
        message_parts.append(f"组织：{org_name}")
        message_parts.append(f"需要升级处理的工单数：{total_count}")
        message_parts.append("")

        # 显示需要升级的工单
        for i, opp in enumerate(opportunities[:max_display], 1):
            elapsed_str = f"{opp.elapsed_hours:.1f}小时" if opp.elapsed_hours else "未知"
            create_date = opp.create_time.strftime("%m-%d %H:%M") if opp.create_time else "未知"

            message_parts.append(f"{i}. 工单号：{opp.order_num}")
            message_parts.append(f"   滞留时长：{elapsed_str}")
            message_parts.append(f"   客户：{opp.name}")
            message_parts.append(f"   负责人：{opp.supervisor_name}")
            message_parts.append(f"   状态：{opp.order_status}")
            message_parts.append(f"   创建时间：{create_date}")
            message_parts.append("")

        # 🔧 修复：更精确的截断逻辑
        if total_count > max_display:
            message_parts.append(f"... 还有 {remaining_count} 个工单需要处理")
            message_parts.append("")
            logger.info(f"Added truncation line: remaining {remaining_count} orders")

        message_parts.append("🔧 **请运营人员介入协调处理**")

        # 添加@用户
        if mention_users:
            message_parts.append("")
            mentions = " ".join([f"@{user}" for user in mention_users])
            message_parts.append(mentions)

        final_message = "\n".join(message_parts)
        logger.debug(f"Generated escalation message length: {len(final_message)} chars")

        return final_message

    @staticmethod
    def format_emergency_notification(org_name: str, opportunities: List[OpportunityInfo],
                                    mention_users: List[str] = None) -> str:
        """
        格式化紧急通知消息（24/48小时）- 管理层关注

        Args:
            org_name: 组织名称
            opportunities: 紧急处理的商机列表
            mention_users: 需要@的用户列表

        Returns:
            格式化的紧急通知消息
        """
        if not opportunities:
            return ""

        # 🔧 修复：去重商机列表，避免重复工单号
        from ..utils.logger import get_logger
        logger = get_logger(__name__)

        unique_opportunities = []
        seen_order_nums = set()
        for opp in opportunities:
            if opp.order_num not in seen_order_nums:
                unique_opportunities.append(opp)
                seen_order_nums.add(opp.order_num)
            else:
                logger.warning(f"Duplicate order number {opp.order_num} found in emergency opportunities, skipping")

        if len(unique_opportunities) != len(opportunities):
            logger.info(f"Removed {len(opportunities) - len(unique_opportunities)} duplicate opportunities from emergency notification")

        # 使用去重后的商机列表
        opportunities = unique_opportunities

        # 获取显示配置
        display_config = BusinessNotificationFormatter._get_display_config()
        max_display = display_config['escalation_max']

        message_parts = []
        message_parts.append("🔥 **紧急通知** - 严重超时")
        message_parts.append("")
        message_parts.append(f"组织：{org_name}")
        message_parts.append(f"严重超时工单数：{len(opportunities)}")
        message_parts.append("")

        # 显示最严重的工单
        for i, opp in enumerate(opportunities[:max_display], 1):
            days = int(opp.elapsed_hours / 24) if opp.elapsed_hours else 0
            hours = int(opp.elapsed_hours % 24) if opp.elapsed_hours else 0
            create_date = opp.create_time.strftime("%m-%d") if opp.create_time else "未知"

            message_parts.append(f"{i}. 工单号：{opp.order_num}")
            message_parts.append(f"   严重超时：{days}天{hours}小时")
            message_parts.append(f"   客户：{opp.name}")
            message_parts.append(f"   负责人：{opp.supervisor_name}")
            message_parts.append(f"   状态：{opp.order_status}")
            message_parts.append(f"   创建时间：{create_date}")
            message_parts.append("")

        if len(opportunities) > max_display:
            message_parts.append(f"... 还有 {len(opportunities) - max_display} 个严重超时工单")
            message_parts.append("")

        message_parts.append("⚡ **需要管理层立即关注和处理！**")
        message_parts.append("📞 建议直接联系相关负责人")

        # 添加@用户
        if mention_users:
            message_parts.append("")
            mentions = " ".join([f"@{user}" for user in mention_users])
            message_parts.append(mentions)

        return "\n".join(message_parts)
    
    @staticmethod
    def format_summary_notification(total_opportunities: int, org_count: int, 
                                  escalation_count: int) -> str:
        """
        格式化汇总通知消息
        
        Args:
            total_opportunities: 总逾期商机数
            org_count: 涉及组织数
            escalation_count: 需要升级的数量
            
        Returns:
            格式化的汇总消息
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message_parts = []
        message_parts.append("📊 **FSOA 系统监控汇总**")
        message_parts.append("")
        message_parts.append(f"🕐 检查时间：{current_time}")
        message_parts.append("")
        message_parts.append("📈 **统计数据：**")
        message_parts.append(f"• 逾期商机总数：{total_opportunities}")
        message_parts.append(f"• 涉及组织数量：{org_count}")
        message_parts.append(f"• 需要升级处理：{escalation_count}")
        message_parts.append("")
        
        if escalation_count > 0:
            message_parts.append("⚠️ **注意：有严重逾期工单需要立即处理！**")
        else:
            message_parts.append("✅ **系统运行正常，无严重逾期工单**")
        
        message_parts.append("")
        message_parts.append("🤖 来源：FSOA智能助手")
        
        return "\n".join(message_parts)
    
    @staticmethod
    def calculate_retention_time_text(elapsed_hours: float) -> str:
        """
        计算滞留时间的文本表示
        
        Args:
            elapsed_hours: 已过时间（小时）
            
        Returns:
            滞留时间文本
        """
        if elapsed_hours < 24:
            return f"{elapsed_hours:.0f}小时"
        else:
            days = int(elapsed_hours / 24)
            hours = elapsed_hours % 24
            if hours < 1:
                return f"{days}天"
            else:
                return f"{days}天{hours:.0f}小时"

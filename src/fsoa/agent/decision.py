"""
决策引擎模块

实现规则引擎+LLM的混合决策机制
"""

from datetime import datetime, timedelta

# 导入时区工具
from ..utils.timezone_utils import now_china_naive
from typing import Dict, Any, List, Optional
from enum import Enum

from ..data.models import OpportunityInfo, DecisionResult, Priority, DecisionContext
from ..data.database import get_db_manager
from ..utils.logger import get_logger
from ..utils.config import get_config
from .llm import get_deepseek_client
from .llm_observer import get_llm_observer

logger = get_logger(__name__)


class DecisionMode(str, Enum):
    """决策模式"""
    RULE_ONLY = "rule_only"          # 仅规则
    LLM_ONLY = "llm_only"            # 仅LLM
    HYBRID = "hybrid"                # 混合模式
    LLM_FALLBACK = "llm_fallback"    # LLM优先，规则降级


class RuleEngine:
    """规则引擎"""
    
    def __init__(self):
        self.config = get_config()
    
    def evaluate_task(self, opportunity: OpportunityInfo, context: DecisionContext = None) -> DecisionResult:
        """
        基于规则评估商机

        Args:
            opportunity: 商机信息
            context: 决策上下文

        Returns:
            决策结果
        """
        logger.info(f"Evaluating opportunity {opportunity.order_num} with rules")

        # 规则1: 检查是否超时
        if not opportunity.is_overdue:
            return DecisionResult(
                action="skip",
                priority=Priority.LOW,
                reasoning="商机未超时，无需处理",
                confidence=1.0
            )

        # 规则2: 检查通知冷却时间
        if self._is_in_cooldown(opportunity):
            return DecisionResult(
                action="skip",
                priority=Priority.LOW,
                reasoning="商机在通知冷却期内",
                confidence=1.0
            )

        # 规则3: 基于超时程度决策
        overdue_ratio = opportunity.overdue_hours / opportunity.sla_threshold_hours if opportunity.sla_threshold_hours > 0 else 0
        
        if overdue_ratio >= 2.0:  # 超时100%以上
            return DecisionResult(
                action="escalate",
                priority=Priority.URGENT,
                message=self._generate_escalation_message(opportunity),
                reasoning=f"商机严重超时{overdue_ratio:.1%}，需要升级处理",
                confidence=1.0
            )
        elif overdue_ratio >= 1.5:  # 超时50%以上
            return DecisionResult(
                action="notify",
                priority=Priority.HIGH,
                message=self._generate_high_priority_message(opportunity),
                reasoning=f"商机超时{overdue_ratio:.1%}，需要高优先级通知",
                confidence=1.0
            )
        elif overdue_ratio >= 1.2:  # 超时20%以上
            return DecisionResult(
                action="notify",
                priority=Priority.NORMAL,
                message=self._generate_normal_message(opportunity),
                reasoning=f"商机超时{overdue_ratio:.1%}，发送常规通知",
                confidence=1.0
            )
        else:  # 刚刚超时
            return DecisionResult(
                action="notify",
                priority=Priority.LOW,
                message=self._generate_gentle_reminder(opportunity),
                reasoning=f"商机刚刚超时{overdue_ratio:.1%}，发送温和提醒",
                confidence=1.0
            )
    
    def _is_in_cooldown(self, opportunity: OpportunityInfo) -> bool:
        """检查是否在冷却期内"""
        # OpportunityInfo没有last_notification字段，这个检查应该在通知管理器中处理
        # 这里简化为总是返回False，让通知管理器处理冷却逻辑
        return False
    
    def _generate_escalation_message(self, opportunity: OpportunityInfo) -> str:
        """生成升级消息"""
        return f"""🚨 紧急升级通知

工单号: {opportunity.order_num}
客户: {opportunity.name}
负责人: {opportunity.supervisor_name}
服务地址: {opportunity.address}
超时时间: {opportunity.overdue_hours:.1f}小时

⚠️ 商机已严重超时，需要立即处理！
请联系相关负责人并评估是否需要额外资源支持。"""

    def _generate_high_priority_message(self, opportunity: OpportunityInfo) -> str:
        """生成高优先级消息"""
        return f"""⚠️ 高优先级提醒

工单号: {opportunity.order_num}
客户: {opportunity.name}
负责人: {opportunity.supervisor_name}
超时时间: {opportunity.overdue_hours:.1f}小时

请尽快处理此商机，避免进一步延误。"""

    def _generate_normal_message(self, opportunity: OpportunityInfo) -> str:
        """生成常规消息"""
        return f"""⏰ 商机超时提醒

工单号: {opportunity.order_num}
客户: {opportunity.name}
负责人: {opportunity.supervisor_name}
超时时间: {opportunity.overdue_hours:.1f}小时

请及时处理，确保服务质量。"""

    def _generate_gentle_reminder(self, opportunity: OpportunityInfo) -> str:
        """生成温和提醒"""
        return f"""📋 商机时效提醒

工单号: {opportunity.order_num}
客户: {opportunity.name}
负责人: {opportunity.supervisor_name}

商机已超过预定时间，请关注进度。"""


class DecisionEngine:
    """混合决策引擎"""
    
    def __init__(self, mode: DecisionMode = DecisionMode.HYBRID):
        self.mode = mode
        self.rule_engine = RuleEngine()
        self.config = get_config()
        
    def make_decision(self, opportunity: OpportunityInfo, context: DecisionContext = None) -> DecisionResult:
        """
        做出决策

        Args:
            opportunity: 商机信息
            context: 决策上下文

        Returns:
            决策结果
        """
        logger.info(f"Making decision for opportunity {opportunity.order_num} with mode {self.mode}")

        if self.mode == DecisionMode.RULE_ONLY:
            return self._rule_only_decision(opportunity, context)
        elif self.mode == DecisionMode.LLM_ONLY:
            return self._llm_only_decision(opportunity, context)
        elif self.mode == DecisionMode.HYBRID:
            return self._hybrid_decision(opportunity, context)
        elif self.mode == DecisionMode.LLM_FALLBACK:
            return self._llm_fallback_decision(opportunity, context)
        else:
            logger.warning(f"Unknown decision mode: {self.mode}, using rule only")
            return self._rule_only_decision(opportunity, context)
    
    def _rule_only_decision(self, opportunity: OpportunityInfo, context: DecisionContext = None) -> DecisionResult:
        """仅使用规则决策"""
        return self.rule_engine.evaluate_task(opportunity, context)

    def _llm_only_decision(self, opportunity: OpportunityInfo, context: DecisionContext = None) -> DecisionResult:
        """仅使用LLM决策"""
        try:
            deepseek_client = get_deepseek_client()
            context_dict = self._build_context_dict(opportunity, context)
            return deepseek_client.analyze_task_priority(opportunity, context_dict)
        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            # 降级到规则决策
            return self.rule_engine.evaluate_task(opportunity, context)

    def _hybrid_decision(self, opportunity: OpportunityInfo, context: DecisionContext = None) -> DecisionResult:
        """混合决策：规则预筛选 + LLM优化"""
        # 首先使用规则引擎进行基础判断
        rule_result = self.rule_engine.evaluate_task(opportunity, context)

        # 如果规则建议跳过，直接返回
        if rule_result.action == "skip":
            return rule_result

        # 对于需要处理的商机，使用LLM优化决策
        try:
            # 检查是否启用LLM优化 - 从数据库读取配置
            from ..data.database import get_database_manager
            db_manager = get_database_manager()
            use_llm_config = db_manager.get_system_config("use_llm_optimization")
            use_llm = use_llm_config and use_llm_config.lower() == "true" if use_llm_config else False

            if use_llm:
                deepseek_client = get_deepseek_client()
                context_dict = self._build_context_dict(opportunity, context)
                context_dict["rule_suggestion"] = {
                    "action": rule_result.action,
                    "priority": rule_result.priority.value,
                    "reasoning": rule_result.reasoning
                }

                # 获取观测器
                observer = get_llm_observer()

                llm_result = deepseek_client.analyze_task_priority(opportunity, context_dict)

                # 合并规则和LLM的结果
                merged_result = self._merge_decisions(rule_result, llm_result)

                # 记录决策上下文到观测器（在LLM调用完成后）
                if observer:
                    # 获取最近完成的LLM调用ID
                    llm_call_id = None
                    if hasattr(observer, '_last_completed_call_id'):
                        llm_call_id = observer._last_completed_call_id
                    elif hasattr(observer, '_current_call') and observer._current_call:
                        llm_call_id = observer._current_call.call_id

                    if llm_call_id:
                        observer.record_decision_context(
                            call_id=llm_call_id,
                            rule_suggestion={
                                "action": rule_result.action,
                                "priority": rule_result.priority.value,
                                "reasoning": rule_result.reasoning,
                                "confidence": rule_result.confidence
                            },
                            final_decision={
                                "action": merged_result.action,
                                "priority": merged_result.priority.value,
                                "reasoning": merged_result.reasoning,
                                "confidence": merged_result.confidence,
                                "llm_used": merged_result.llm_used
                            }
                        )

                return merged_result
            else:
                return rule_result
                
        except Exception as e:
            logger.error(f"LLM optimization failed: {e}")
            return rule_result
    
    def _llm_fallback_decision(self, opportunity: OpportunityInfo, context: DecisionContext = None) -> DecisionResult:
        """LLM优先，规则降级"""
        try:
            deepseek_client = get_deepseek_client()
            context_dict = self._build_context_dict(opportunity, context)
            return deepseek_client.analyze_task_priority(opportunity, context_dict)
        except Exception as e:
            logger.warning(f"LLM decision failed, falling back to rules: {e}")
            return self.rule_engine.evaluate_task(opportunity, context)

    def _build_context_dict(self, opportunity: OpportunityInfo, context: DecisionContext = None) -> Dict[str, Any]:
        """构建上下文字典"""
        context_dict = {}

        if context:
            # 添加历史通知信息 - 🔧 修复：使用NotificationTask的正确属性
            if context.history:
                context_dict["notification_history"] = [
                    {
                        "type": notif.notification_type.value,  # 使用notification_type而不是type
                        "sent_at": notif.sent_at.isoformat() if notif.sent_at else None,
                        "status": notif.status.value,
                        "order_num": notif.order_num,
                        "org_name": notif.org_name,
                        "due_time": notif.due_time.isoformat() if notif.due_time else None
                    }
                    for notif in context.history[-5:]  # 最近5条
                ]

            # 添加群组配置
            if context.group_config:
                context_dict["group_config"] = {
                    "name": context.group_config.name,
                    "webhook_url": context.group_config.webhook_url,
                    "enabled": context.group_config.enabled,
                    "cooldown_minutes": context.group_config.notification_cooldown_minutes
                }

            # 添加系统配置
            if context.system_config:
                context_dict["system_config"] = context.system_config
        
        # 添加当前时间信息
        now = now_china_naive()
        context_dict["current_time"] = {
            "timestamp": now.isoformat(),
            "hour": now.hour,
            "weekday": now.weekday(),
            "is_business_hours": 9 <= now.hour <= 18 and now.weekday() < 5
        }

        return context_dict

    def _check_llm_optimization_enabled(self) -> bool:
        """检查是否启用LLM优化"""
        try:
            from ..data.database import get_database_manager
            db_manager = get_database_manager()
            use_llm_config = db_manager.get_system_config("use_llm_optimization")
            return use_llm_config and use_llm_config.lower() == "true"
        except Exception as e:
            logger.error(f"Failed to read LLM config: {e}")
            return False  # 默认关闭
    
    def _merge_decisions(self, rule_result: DecisionResult, llm_result: DecisionResult) -> DecisionResult:
        """合并规则和LLM的决策结果"""
        # 使用LLM的决策，但保留规则的置信度信息
        merged_result = DecisionResult(
            action=llm_result.action,
            priority=llm_result.priority,
            message=llm_result.message or rule_result.message,
            reasoning=f"规则建议: {rule_result.reasoning}; LLM分析: {llm_result.reasoning}",
            confidence=min(rule_result.confidence, llm_result.confidence),
            llm_used=True
        )
        
        # 安全检查：如果LLM建议的行动比规则更激进，使用规则结果
        action_priority = {"skip": 0, "notify": 1, "escalate": 2}
        if action_priority.get(llm_result.action, 0) > action_priority.get(rule_result.action, 0) + 1:
            logger.warning(f"LLM suggestion too aggressive, using rule result")
            return rule_result
        
        return merged_result
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """获取决策统计信息"""
        # 这里可以添加决策统计逻辑
        return {
            "mode": self.mode.value,
            "total_decisions": 0,
            "rule_decisions": 0,
            "llm_decisions": 0,
            "hybrid_decisions": 0
        }


def create_decision_engine(mode: str = None) -> DecisionEngine:
    """
    创建决策引擎实例

    Args:
        mode: 决策模式

    Returns:
        决策引擎实例
    """
    if mode:
        decision_mode = DecisionMode(mode)
    else:
        # 从数据库读取默认模式
        db_manager = get_db_manager()
        use_llm_config = db_manager.get_system_config("use_llm_optimization")
        use_llm = use_llm_config and use_llm_config.lower() == "true" if use_llm_config else True
        decision_mode = DecisionMode.HYBRID if use_llm else DecisionMode.RULE_ONLY

    return DecisionEngine(decision_mode)

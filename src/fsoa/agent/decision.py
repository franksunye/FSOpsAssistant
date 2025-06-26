"""
决策引擎模块

实现规则引擎+LLM的混合决策机制
"""

from datetime import datetime, timedelta

# 导入时区工具
from ..utils.timezone_utils import now_china_naive
from typing import Dict, Any, List, Optional
from enum import Enum

from ..data.models import TaskInfo, DecisionResult, Priority, DecisionContext
from ..data.database import get_db_manager
from ..utils.logger import get_logger
from ..utils.config import get_config
from .llm import get_deepseek_client

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
    
    def evaluate_task(self, task: TaskInfo, context: DecisionContext = None) -> DecisionResult:
        """
        基于规则评估任务
        
        Args:
            task: 任务信息
            context: 决策上下文
            
        Returns:
            决策结果
        """
        logger.info(f"Evaluating task {task.id} with rules")
        
        # 规则1: 检查是否超时
        if not task.is_overdue:
            return DecisionResult(
                action="skip",
                priority=Priority.LOW,
                reasoning="任务未超时，无需处理",
                confidence=1.0
            )
        
        # 规则2: 检查通知冷却时间
        if self._is_in_cooldown(task):
            return DecisionResult(
                action="skip",
                priority=Priority.LOW,
                reasoning="任务在通知冷却期内",
                confidence=1.0
            )
        
        # 规则3: 基于超时程度决策
        overdue_ratio = task.overdue_ratio
        
        if overdue_ratio >= 2.0:  # 超时100%以上
            return DecisionResult(
                action="escalate",
                priority=Priority.URGENT,
                message=self._generate_escalation_message(task),
                reasoning=f"任务严重超时{overdue_ratio:.1%}，需要升级处理",
                confidence=1.0
            )
        elif overdue_ratio >= 1.5:  # 超时50%以上
            return DecisionResult(
                action="notify",
                priority=Priority.HIGH,
                message=self._generate_high_priority_message(task),
                reasoning=f"任务超时{overdue_ratio:.1%}，需要高优先级通知",
                confidence=1.0
            )
        elif overdue_ratio >= 1.2:  # 超时20%以上
            return DecisionResult(
                action="notify",
                priority=Priority.NORMAL,
                message=self._generate_normal_message(task),
                reasoning=f"任务超时{overdue_ratio:.1%}，发送常规通知",
                confidence=1.0
            )
        else:  # 刚刚超时
            return DecisionResult(
                action="notify",
                priority=Priority.LOW,
                message=self._generate_gentle_reminder(task),
                reasoning=f"任务刚刚超时{overdue_ratio:.1%}，发送温和提醒",
                confidence=1.0
            )
    
    def _is_in_cooldown(self, task: TaskInfo) -> bool:
        """检查是否在冷却期内"""
        if not task.last_notification:
            return False
        
        cooldown_minutes = self.config.notification_cooldown
        time_since_last = now_china_naive() - task.last_notification
        cooldown_period = timedelta(minutes=cooldown_minutes)
        
        return time_since_last < cooldown_period
    
    def _generate_escalation_message(self, task: TaskInfo) -> str:
        """生成升级消息"""
        return f"""🚨 紧急升级通知

任务ID: {task.id}
任务标题: {task.title}
负责人: {task.assignee or '未分配'}
客户: {task.customer or '未知'}
超时时间: {task.overdue_hours:.1f}小时

⚠️ 任务已严重超时，需要立即处理！
请联系相关负责人并评估是否需要额外资源支持。"""
    
    def _generate_high_priority_message(self, task: TaskInfo) -> str:
        """生成高优先级消息"""
        return f"""⚠️ 高优先级提醒

任务ID: {task.id}
任务标题: {task.title}
负责人: {task.assignee or '未分配'}
超时时间: {task.overdue_hours:.1f}小时

请尽快处理此任务，避免进一步延误。"""
    
    def _generate_normal_message(self, task: TaskInfo) -> str:
        """生成常规消息"""
        return f"""⏰ 任务超时提醒

任务ID: {task.id}
任务标题: {task.title}
负责人: {task.assignee or '未分配'}
超时时间: {task.overdue_hours:.1f}小时

请及时处理，确保服务质量。"""
    
    def _generate_gentle_reminder(self, task: TaskInfo) -> str:
        """生成温和提醒"""
        return f"""📋 任务时效提醒

任务ID: {task.id}
任务标题: {task.title}
负责人: {task.assignee or '未分配'}

任务已超过预定时间，请关注进度。"""


class DecisionEngine:
    """混合决策引擎"""
    
    def __init__(self, mode: DecisionMode = DecisionMode.HYBRID):
        self.mode = mode
        self.rule_engine = RuleEngine()
        self.config = get_config()
        
    def make_decision(self, task: TaskInfo, context: DecisionContext = None) -> DecisionResult:
        """
        做出决策
        
        Args:
            task: 任务信息
            context: 决策上下文
            
        Returns:
            决策结果
        """
        logger.info(f"Making decision for task {task.id} with mode {self.mode}")
        
        if self.mode == DecisionMode.RULE_ONLY:
            return self._rule_only_decision(task, context)
        elif self.mode == DecisionMode.LLM_ONLY:
            return self._llm_only_decision(task, context)
        elif self.mode == DecisionMode.HYBRID:
            return self._hybrid_decision(task, context)
        elif self.mode == DecisionMode.LLM_FALLBACK:
            return self._llm_fallback_decision(task, context)
        else:
            logger.warning(f"Unknown decision mode: {self.mode}, using rule only")
            return self._rule_only_decision(task, context)
    
    def _rule_only_decision(self, task: TaskInfo, context: DecisionContext = None) -> DecisionResult:
        """仅使用规则决策"""
        return self.rule_engine.evaluate_task(task, context)
    
    def _llm_only_decision(self, task: TaskInfo, context: DecisionContext = None) -> DecisionResult:
        """仅使用LLM决策"""
        try:
            deepseek_client = get_deepseek_client()
            context_dict = self._build_context_dict(task, context)
            return deepseek_client.analyze_task_priority(task, context_dict)
        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            # 降级到规则决策
            return self.rule_engine.evaluate_task(task, context)
    
    def _hybrid_decision(self, task: TaskInfo, context: DecisionContext = None) -> DecisionResult:
        """混合决策：规则预筛选 + LLM优化"""
        # 首先使用规则引擎进行基础判断
        rule_result = self.rule_engine.evaluate_task(task, context)
        
        # 如果规则建议跳过，直接返回
        if rule_result.action == "skip":
            return rule_result
        
        # 对于需要处理的任务，使用LLM优化决策
        try:
            # 检查是否启用LLM优化
            use_llm = getattr(self.config, 'use_llm_optimization', False)
            if use_llm:
                deepseek_client = get_deepseek_client()
                context_dict = self._build_context_dict(task, context)
                context_dict["rule_suggestion"] = {
                    "action": rule_result.action,
                    "priority": rule_result.priority.value,
                    "reasoning": rule_result.reasoning
                }
                
                llm_result = deepseek_client.analyze_task_priority(task, context_dict)
                
                # 合并规则和LLM的结果
                return self._merge_decisions(rule_result, llm_result)
            else:
                return rule_result
                
        except Exception as e:
            logger.error(f"LLM optimization failed: {e}")
            return rule_result
    
    def _llm_fallback_decision(self, task: TaskInfo, context: DecisionContext = None) -> DecisionResult:
        """LLM优先，规则降级"""
        try:
            deepseek_client = get_deepseek_client()
            context_dict = self._build_context_dict(task, context)
            return deepseek_client.analyze_task_priority(task, context_dict)
        except Exception as e:
            logger.warning(f"LLM decision failed, falling back to rules: {e}")
            return self.rule_engine.evaluate_task(task, context)
    
    def _build_context_dict(self, task: TaskInfo, context: DecisionContext = None) -> Dict[str, Any]:
        """构建上下文字典"""
        context_dict = {}
        
        if context:
            # 添加历史通知信息
            if context.history:
                context_dict["notification_history"] = [
                    {
                        "type": notif.type,
                        "sent_at": notif.sent_at.isoformat() if notif.sent_at else None,
                        "status": notif.status.value
                    }
                    for notif in context.history[-5:]  # 最近5条
                ]
            
            # 添加群组配置
            if context.group_config:
                context_dict["group_config"] = {
                    "name": context.group_config.name,
                    "max_notifications_per_hour": context.group_config.max_notifications_per_hour,
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
        # 从配置中读取默认模式
        config = get_config()
        use_llm = getattr(config, 'use_llm_optimization', True)
        decision_mode = DecisionMode.HYBRID if use_llm else DecisionMode.RULE_ONLY
    
    return DecisionEngine(decision_mode)

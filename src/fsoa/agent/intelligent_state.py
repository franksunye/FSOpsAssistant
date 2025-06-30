"""
智能Agent状态管理模块

实现AI Native的状态管理，包含思考记录、上下文记忆和学习洞察
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from ..data.models import OpportunityInfo, DecisionResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ThinkingType(str, Enum):
    """思考类型"""
    PERCEPTION = "perception"      # 感知分析
    ANALYSIS = "analysis"         # 数据分析
    DECISION = "decision"         # 决策思考
    PLANNING = "planning"         # 规划思考
    REFLECTION = "reflection"     # 反思学习
    STRATEGY = "strategy"         # 策略思考


@dataclass
class ThoughtRecord:
    """Agent思考记录"""
    timestamp: datetime
    node_name: str                # 哪个节点的思考
    thinking_type: ThinkingType   # 思考类型
    situation: str                # 当前情况描述
    thoughts: str                 # 思考内容
    confidence: float             # 置信度 (0.0-1.0)
    reasoning_steps: List[str]    # 推理步骤
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "node_name": self.node_name,
            "thinking_type": self.thinking_type.value,
            "situation": self.situation,
            "thoughts": self.thoughts,
            "confidence": self.confidence,
            "reasoning_steps": self.reasoning_steps
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThoughtRecord':
        """从字典创建思考记录"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_name=data["node_name"],
            thinking_type=ThinkingType(data["thinking_type"]),
            situation=data["situation"],
            thoughts=data["thoughts"],
            confidence=data["confidence"],
            reasoning_steps=data["reasoning_steps"]
        )


@dataclass
class ReasoningChain:
    """推理链"""
    step_id: int
    premise: str                  # 前提
    reasoning: str                # 推理过程
    conclusion: str               # 结论
    confidence: float             # 置信度
    evidence: List[str]           # 支持证据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "step_id": self.step_id,
            "premise": self.premise,
            "reasoning": self.reasoning,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "evidence": self.evidence
        }


@dataclass
class ExecutionSummary:
    """执行摘要"""
    execution_id: str
    timestamp: datetime
    opportunities_count: int
    decisions_made: int
    notifications_sent: int
    success_rate: float
    key_insights: List[str]
    challenges_faced: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat(),
            "opportunities_count": self.opportunities_count,
            "decisions_made": self.decisions_made,
            "notifications_sent": self.notifications_sent,
            "success_rate": self.success_rate,
            "key_insights": self.key_insights,
            "challenges_faced": self.challenges_faced
        }


@dataclass
class SuccessPattern:
    """成功模式"""
    pattern_id: str
    description: str
    conditions: List[str]         # 触发条件
    actions: List[str]            # 成功行动
    success_rate: float           # 成功率
    usage_count: int              # 使用次数
    last_used: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "pattern_id": self.pattern_id,
            "description": self.description,
            "conditions": self.conditions,
            "actions": self.actions,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat()
        }


@dataclass
class LearningInsight:
    """学习洞察"""
    insight_id: str
    category: str                 # 洞察类别
    description: str              # 洞察描述
    confidence: float             # 置信度
    supporting_evidence: List[str] # 支持证据
    actionable_suggestions: List[str] # 可行建议
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "insight_id": self.insight_id,
            "category": self.category,
            "description": self.description,
            "confidence": self.confidence,
            "supporting_evidence": self.supporting_evidence,
            "actionable_suggestions": self.actionable_suggestions,
            "created_at": self.created_at.isoformat()
        }


class ContextMemory:
    """上下文记忆管理"""
    
    def __init__(self, max_recent_executions: int = 10):
        self.recent_executions: List[ExecutionSummary] = []
        self.successful_patterns: List[SuccessPattern] = []
        self.failure_lessons: List[Dict[str, Any]] = []
        self.business_insights: List[LearningInsight] = []
        self.max_recent_executions = max_recent_executions
    
    def add_execution_memory(self, execution_summary: ExecutionSummary):
        """添加执行记忆"""
        self.recent_executions.append(execution_summary)
        
        # 保持最近N次执行记录
        if len(self.recent_executions) > self.max_recent_executions:
            self.recent_executions.pop(0)
        
        logger.info(f"添加执行记忆: {execution_summary.execution_id}")
    
    def add_success_pattern(self, pattern: SuccessPattern):
        """添加成功模式"""
        # 检查是否已存在相同模式
        existing_pattern = self.find_pattern(pattern.pattern_id)
        if existing_pattern:
            # 更新现有模式
            existing_pattern.usage_count += 1
            existing_pattern.last_used = datetime.now()
            existing_pattern.success_rate = (
                existing_pattern.success_rate * 0.8 + pattern.success_rate * 0.2
            )  # 加权平均
        else:
            # 添加新模式
            self.successful_patterns.append(pattern)
        
        logger.info(f"添加/更新成功模式: {pattern.pattern_id}")
    
    def find_pattern(self, pattern_id: str) -> Optional[SuccessPattern]:
        """查找成功模式"""
        for pattern in self.successful_patterns:
            if pattern.pattern_id == pattern_id:
                return pattern
        return None
    
    def get_relevant_patterns(self, situation_keywords: List[str]) -> List[SuccessPattern]:
        """获取相关的成功模式"""
        relevant_patterns = []
        
        for pattern in self.successful_patterns:
            # 简单的关键词匹配
            relevance_score = 0
            for keyword in situation_keywords:
                if any(keyword.lower() in condition.lower() for condition in pattern.conditions):
                    relevance_score += 1
                if keyword.lower() in pattern.description.lower():
                    relevance_score += 1
            
            if relevance_score > 0:
                relevant_patterns.append((pattern, relevance_score))
        
        # 按相关性排序
        relevant_patterns.sort(key=lambda x: x[1], reverse=True)
        return [pattern for pattern, _ in relevant_patterns[:5]]  # 返回前5个最相关的
    
    def get_recent_context(self, days_back: int = 7) -> Dict[str, Any]:
        """获取最近的上下文信息"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        recent_executions = [
            exec_summary for exec_summary in self.recent_executions
            if exec_summary.timestamp >= cutoff_date
        ]
        
        recent_insights = [
            insight for insight in self.business_insights
            if insight.created_at >= cutoff_date
        ]
        
        return {
            "recent_executions_count": len(recent_executions),
            "average_success_rate": sum(e.success_rate for e in recent_executions) / len(recent_executions) if recent_executions else 0,
            "common_challenges": self._extract_common_challenges(recent_executions),
            "recent_insights": [insight.description for insight in recent_insights],
            "active_patterns": len([p for p in self.successful_patterns if p.last_used >= cutoff_date])
        }
    
    def _extract_common_challenges(self, executions: List[ExecutionSummary]) -> List[str]:
        """提取常见挑战"""
        all_challenges = []
        for execution in executions:
            all_challenges.extend(execution.challenges_faced)
        
        # 简单的频率统计
        challenge_counts = {}
        for challenge in all_challenges:
            challenge_counts[challenge] = challenge_counts.get(challenge, 0) + 1
        
        # 返回出现频率最高的挑战
        sorted_challenges = sorted(challenge_counts.items(), key=lambda x: x[1], reverse=True)
        return [challenge for challenge, count in sorted_challenges[:3]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于序列化）"""
        return {
            "recent_executions": [exec_summary.to_dict() for exec_summary in self.recent_executions],
            "successful_patterns": [pattern.to_dict() for pattern in self.successful_patterns],
            "failure_lessons": self.failure_lessons,
            "business_insights": [insight.to_dict() for insight in self.business_insights]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextMemory':
        """从字典创建上下文记忆"""
        memory = cls()
        
        # 恢复执行记录
        for exec_data in data.get("recent_executions", []):
            exec_summary = ExecutionSummary(
                execution_id=exec_data["execution_id"],
                timestamp=datetime.fromisoformat(exec_data["timestamp"]),
                opportunities_count=exec_data["opportunities_count"],
                decisions_made=exec_data["decisions_made"],
                notifications_sent=exec_data["notifications_sent"],
                success_rate=exec_data["success_rate"],
                key_insights=exec_data["key_insights"],
                challenges_faced=exec_data["challenges_faced"]
            )
            memory.recent_executions.append(exec_summary)
        
        # 恢复成功模式
        for pattern_data in data.get("successful_patterns", []):
            pattern = SuccessPattern(
                pattern_id=pattern_data["pattern_id"],
                description=pattern_data["description"],
                conditions=pattern_data["conditions"],
                actions=pattern_data["actions"],
                success_rate=pattern_data["success_rate"],
                usage_count=pattern_data["usage_count"],
                last_used=datetime.fromisoformat(pattern_data["last_used"])
            )
            memory.successful_patterns.append(pattern)
        
        # 恢复其他数据
        memory.failure_lessons = data.get("failure_lessons", [])
        
        # 恢复业务洞察
        for insight_data in data.get("business_insights", []):
            insight = LearningInsight(
                insight_id=insight_data["insight_id"],
                category=insight_data["category"],
                description=insight_data["description"],
                confidence=insight_data["confidence"],
                supporting_evidence=insight_data["supporting_evidence"],
                actionable_suggestions=insight_data["actionable_suggestions"],
                created_at=datetime.fromisoformat(insight_data["created_at"])
            )
            memory.business_insights.append(insight)
        
        return memory


@dataclass
class ExecutionStrategy:
    """执行策略"""
    strategy_id: str
    name: str
    description: str
    priority_weights: Dict[str, float]  # 优先级权重
    decision_thresholds: Dict[str, float]  # 决策阈值
    adaptation_rules: List[str]  # 自适应规则
    success_criteria: List[str]  # 成功标准
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "priority_weights": self.priority_weights,
            "decision_thresholds": self.decision_thresholds,
            "adaptation_rules": self.adaptation_rules,
            "success_criteria": self.success_criteria
        }


def create_default_context_memory() -> ContextMemory:
    """创建默认的上下文记忆"""
    return ContextMemory()


def create_default_execution_strategy() -> ExecutionStrategy:
    """创建默认的执行策略"""
    return ExecutionStrategy(
        strategy_id="default_strategy",
        name="默认执行策略",
        description="基于规则和LLM的混合决策策略",
        priority_weights={
            "overdue_hours": 0.4,
            "customer_importance": 0.3,
            "business_impact": 0.2,
            "resource_availability": 0.1
        },
        decision_thresholds={
            "notify_threshold": 0.6,
            "escalate_threshold": 0.8,
            "confidence_threshold": 0.7
        },
        adaptation_rules=[
            "如果连续3次决策置信度低于0.5，降级到规则模式",
            "如果成功率低于80%，调整决策阈值",
            "如果出现新的业务模式，更新策略权重"
        ],
        success_criteria=[
            "通知发送成功率 > 95%",
            "决策准确率 > 90%",
            "客户满意度提升",
            "SLA合规率提升"
        ]
    )

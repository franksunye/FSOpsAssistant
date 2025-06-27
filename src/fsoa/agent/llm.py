"""
DeepSeek LLM集成模块

提供与DeepSeek API的集成，支持智能决策和内容生成
"""

import json
from typing import Dict, Any, Optional, List
from openai import OpenAI
from datetime import datetime

from ..utils.logger import get_logger
from ..utils.config import get_config
from ..data.models import TaskInfo, DecisionResult, Priority

logger = get_logger(__name__)


class DeepSeekError(Exception):
    """DeepSeek相关异常"""
    pass


class DeepSeekClient:
    """DeepSeek LLM客户端"""
    
    def __init__(self):
        self.config = get_config()
        try:
            # 尝试创建 OpenAI 客户端
            self.client = OpenAI(
                api_key=self.config.deepseek_api_key,
                base_url=self.config.deepseek_base_url
            )
        except TypeError as e:
            if "proxies" in str(e):
                # 如果遇到 proxies 参数错误，尝试使用简化的初始化
                import httpx
                http_client = httpx.Client()
                self.client = OpenAI(
                    api_key=self.config.deepseek_api_key,
                    base_url=self.config.deepseek_base_url,
                    http_client=http_client
                )
            else:
                raise
        
    def analyze_task_priority(self, task: TaskInfo, context: Dict[str, Any] = None) -> DecisionResult:
        """
        分析任务优先级和处理建议
        
        Args:
            task: 任务信息
            context: 额外上下文信息
            
        Returns:
            决策结果
        """
        try:
            prompt = self._build_priority_analysis_prompt(task, context)

            # 从数据库读取LLM温度参数
            from ..data.database import get_db_manager
            db_manager = get_db_manager()
            temperature_config = db_manager.get_system_config("llm_temperature")
            temperature = float(temperature_config) if temperature_config else 0.1

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            result_data = self._parse_decision_result(result_text)
            
            return DecisionResult(
                action=result_data.get("action", "skip"),
                priority=Priority(result_data.get("priority", "normal")),
                message=result_data.get("message"),
                reasoning=result_data.get("reasoning"),
                confidence=result_data.get("confidence", 0.8),
                llm_used=True
            )
            
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            # 降级到规则决策
            return self._fallback_rule_decision(task)
    
    def generate_notification_message(self, task: TaskInfo, message_type: str = "overdue_alert") -> str:
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
        return self._fallback_template_message(task, message_type)
    
    def optimize_decision_strategy(self, task: TaskInfo, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        基于历史数据优化决策策略
        
        Args:
            task: 当前任务
            history: 历史决策和结果
            
        Returns:
            优化建议
        """
        try:
            prompt = self._build_strategy_optimization_prompt(task, history)

            # 从数据库读取LLM温度参数，策略优化使用稍高的温度
            from ..data.database import get_db_manager
            db_manager = get_db_manager()
            temperature_config = db_manager.get_system_config("llm_temperature")
            base_temperature = float(temperature_config) if temperature_config else 0.1
            temperature = min(base_temperature + 0.1, 1.0)  # 策略优化使用稍高的温度

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=800
            )
            
            result_text = response.choices[0].message.content
            optimization = self._parse_optimization_result(result_text)
            
            logger.info(f"Generated optimization strategy for task {task.id}")
            return optimization
            
        except Exception as e:
            logger.error(f"Failed to optimize strategy: {e}")
            return {"status": "error", "message": str(e)}
    
    def _build_priority_analysis_prompt(self, task: TaskInfo, context: Dict[str, Any] = None) -> str:
        """构建优先级分析提示词"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        prompt = f"""你是一个现场服务运营专家，请分析以下任务的紧急程度和处理建议。

任务信息：
- 任务ID: {task.id}
- 任务标题: {task.title}
- 任务描述: {task.description or '无'}
- 当前状态: {task.status.value}
- 当前优先级: {task.priority.value}
- SLA时间: {task.sla_hours}小时
- 已用时间: {task.elapsed_hours:.1f}小时
- 超时时间: {task.overdue_hours:.1f}小时
- 超时比例: {task.overdue_ratio:.1%}
- 负责人: {task.assignee or '未分配'}
- 客户: {task.customer or '未知'}
- 服务地点: {task.location or '未知'}
- 最后通知时间: {task.last_notification or '从未'}

当前时间: {current_time}

额外上下文: {json.dumps(context or {}, ensure_ascii=False, indent=2)}

请基于以上信息，分析任务的处理优先级和建议行动，返回JSON格式：

{{
    "action": "skip|notify|escalate",
    "priority": "low|normal|high|urgent", 
    "message": "建议的通知消息内容",
    "reasoning": "决策理由和分析过程",
    "confidence": 0.0-1.0
}}

分析要点：
1. 考虑超时程度和业务影响
2. 评估客户重要性和服务紧急性
3. 分析历史通知频率，避免过度骚扰
4. 提供具体可行的行动建议
5. 确保消息内容专业、简洁、有效"""

        return prompt
    
    def _build_message_generation_prompt(self, task: TaskInfo, message_type: str) -> str:
        """构建消息生成提示词"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        prompt = f"""请为以下现场服务任务生成一条专业的{message_type}通知消息。

任务信息：
- 任务ID: {task.id}
- 任务标题: {task.title}
- 负责人: {task.assignee or '未分配'}
- 客户: {task.customer or '未知'}
- 服务地点: {task.location or '未知'}
- SLA时间: {task.sla_hours}小时
- 已用时间: {task.elapsed_hours:.1f}小时
- 超时时间: {task.overdue_hours:.1f}小时

消息要求：
1. 语言简洁专业，突出重点
2. 包含关键信息（任务ID、超时情况、负责人）
3. 提供明确的行动建议
4. 语气适中，既紧急又不失礼貌
5. 长度控制在200字以内
6. 使用适当的emoji增强可读性

请直接返回消息内容，不需要JSON格式。"""

        return prompt
    
    def _build_strategy_optimization_prompt(self, task: TaskInfo, history: List[Dict[str, Any]]) -> str:
        """构建策略优化提示词"""
        prompt = f"""作为运营优化专家，请基于历史数据分析当前任务的最佳处理策略。

当前任务：
- 任务ID: {task.id}
- 超时情况: {task.overdue_hours:.1f}小时
- 客户: {task.customer}
- 负责人: {task.assignee}

历史数据：
{json.dumps(history, ensure_ascii=False, indent=2)}

请分析：
1. 类似任务的处理模式
2. 通知效果和响应时间
3. 最佳通知时机和频率
4. 升级策略的触发条件

返回JSON格式的优化建议：
{{
    "recommended_action": "具体建议行动",
    "optimal_timing": "最佳处理时机",
    "escalation_threshold": "升级阈值建议",
    "notification_frequency": "通知频率建议",
    "success_probability": "成功概率评估",
    "reasoning": "分析理由"
}}"""

        return prompt
    
    def _parse_decision_result(self, result_text: str) -> Dict[str, Any]:
        """解析决策结果"""
        try:
            # 尝试提取JSON
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = result_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                logger.warning("No JSON found in LLM response, using fallback")
                return self._extract_fallback_decision(result_text)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}, using fallback")
            return self._extract_fallback_decision(result_text)
    
    def _parse_optimization_result(self, result_text: str) -> Dict[str, Any]:
        """解析优化结果"""
        try:
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = result_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {"status": "parsed_error", "content": result_text}
                
        except json.JSONDecodeError:
            return {"status": "json_error", "content": result_text}
    
    def _extract_fallback_decision(self, text: str) -> Dict[str, Any]:
        """从文本中提取决策信息（降级方案）"""
        text_lower = text.lower()
        
        # 简单的关键词匹配
        if "escalate" in text_lower or "升级" in text_lower:
            action = "escalate"
            priority = "urgent"
        elif "notify" in text_lower or "通知" in text_lower:
            action = "notify"
            priority = "high" if "urgent" in text_lower or "紧急" in text_lower else "normal"
        else:
            action = "skip"
            priority = "low"
        
        return {
            "action": action,
            "priority": priority,
            "message": "系统自动生成的提醒消息",
            "reasoning": "基于关键词匹配的降级决策",
            "confidence": 0.5
        }
    
    def _fallback_rule_decision(self, task: TaskInfo) -> DecisionResult:
        """规则决策降级方案"""
        if task.overdue_hours > task.sla_hours:
            action = "escalate"
            priority = Priority.URGENT
        elif task.overdue_hours > 0:
            action = "notify"
            priority = Priority.HIGH
        else:
            action = "skip"
            priority = Priority.NORMAL
        
        return DecisionResult(
            action=action,
            priority=priority,
            message="基于规则的自动决策",
            reasoning=f"任务超时{task.overdue_hours:.1f}小时，触发{action}动作",
            confidence=1.0,
            llm_used=False
        )
    
    def _fallback_template_message(self, task: TaskInfo, message_type: str) -> str:
        """模板消息降级方案"""
        if message_type == "overdue_alert":
            return f"""🚨 任务超时提醒

任务ID: {task.id}
任务标题: {task.title}
负责人: {task.assignee or '未分配'}
超时时间: {task.overdue_hours:.1f}小时

请及时处理，确保服务质量！"""
        else:
            return f"任务 {task.id} 需要关注，请及时处理。"
    
    def test_connection(self) -> bool:
        """测试DeepSeek连接"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hello, please respond with 'OK'"}],
                temperature=0,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip()
            logger.info("DeepSeek connection test successful")
            return "OK" in result.upper()
            
        except Exception as e:
            logger.error(f"DeepSeek connection test failed: {e}")
            return False


# 全局客户端实例
_deepseek_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    """获取DeepSeek客户端实例"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client

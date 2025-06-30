"""
DeepSeek LLM集成模块

提供与DeepSeek API的集成，支持智能决策和内容生成
集成LLM可观测性功能，提供完整的调用监控和日志记录
"""

import json
import time
from typing import Dict, Any, Optional, List
from openai import OpenAI
from datetime import datetime

from ..utils.logger import get_logger
from ..utils.config import get_config
from ..data.models import OpportunityInfo, DecisionResult, Priority
from .llm_observer import get_llm_observer, LLMCallStatus

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
        
    def analyze_task_priority(self, opportunity: OpportunityInfo, context: Dict[str, Any] = None) -> DecisionResult:
        """
        分析商机优先级和处理建议

        Args:
            opportunity: 商机信息
            context: 额外上下文信息

        Returns:
            决策结果
        """
        observer = get_llm_observer()
        start_time = time.time()

        try:
            prompt = self._build_priority_analysis_prompt(opportunity, context)

            # 从数据库读取LLM温度参数
            from ..data.database import get_database_manager
            db_manager = get_database_manager()
            temperature_config = db_manager.get_system_config("llm_temperature")
            try:
                temperature = float(temperature_config) if temperature_config else 0.1
            except (ValueError, TypeError):
                logger.warning(f"Invalid temperature config: {temperature_config}, using default 0.1")
                temperature = 0.1

            # 开始观测记录
            call_id = observer.start_call(
                opportunity_id=opportunity.order_num,
                context_data=context or {},
                prompt_text=prompt,
                model_name="deepseek-chat",
                temperature=temperature,
                max_tokens=1000
            )

            logger.info(f"🚀 开始调用DeepSeek API", extra={"call_id": call_id, "opportunity": opportunity.order_num})

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=1000
            )

            duration_ms = (time.time() - start_time) * 1000
            result_text = response.choices[0].message.content

            # 提取Token使用信息
            tokens_used = getattr(response, 'usage', {}).get('total_tokens') if hasattr(response, 'usage') else None
            tokens_prompt = getattr(response, 'usage', {}).get('prompt_tokens') if hasattr(response, 'usage') else None
            tokens_completion = getattr(response, 'usage', {}).get('completion_tokens') if hasattr(response, 'usage') else None

            logger.info(f"📡 DeepSeek API响应成功", extra={
                "call_id": call_id,
                "duration_ms": duration_ms,
                "tokens_used": tokens_used,
                "response_length": len(result_text)
            })

            result_data = self._parse_decision_result(result_text)

            # 记录成功调用
            observer.record_success(
                call_id=call_id,
                response_text=result_text,
                parsed_result=result_data,
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion
            )

            return DecisionResult(
                action=result_data.get("action", "skip"),
                priority=Priority(result_data.get("priority", "normal")),
                message=result_data.get("message"),
                reasoning=result_data.get("reasoning"),
                confidence=result_data.get("confidence", 0.8),
                llm_used=True
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            error_message = str(e)

            # 安全获取call_id
            call_id = 'unknown'
            if observer and hasattr(observer, '_current_call') and observer._current_call:
                call_id = observer._current_call.call_id

            logger.error(f"❌ DeepSeek API调用失败", extra={
                "call_id": call_id,
                "error_type": error_type,
                "error_message": error_message,
                "duration_ms": duration_ms
            })

            # 记录失败调用（如果观测器已初始化）
            if observer and hasattr(observer, '_current_call') and observer._current_call:
                observer.record_failure(
                    call_id=observer._current_call.call_id,
                    error_message=error_message,
                    error_type=error_type,
                    duration_ms=duration_ms
                )

            # 降级到规则决策
            return self._fallback_rule_decision(opportunity)
    
    def generate_notification_message(self, opportunity: OpportunityInfo, message_type: str = "overdue_alert") -> str:
        """
        生成通知消息内容 - 已修改为使用标准格式

        Args:
            opportunity: 商机信息
            message_type: 消息类型

        Returns:
            生成的消息内容
        """
        # 不再使用LLM生成，直接使用标准模板
        logger.info(f"Using standard template for opportunity {opportunity.order_num} (LLM disabled)")
        return self._fallback_template_message(opportunity, message_type)
    
    def optimize_decision_strategy(self, opportunity: OpportunityInfo, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        基于历史数据优化决策策略

        Args:
            opportunity: 当前商机
            history: 历史决策和结果

        Returns:
            优化建议
        """
        try:
            prompt = self._build_strategy_optimization_prompt(opportunity, history)

            # 从数据库读取LLM温度参数，策略优化使用稍高的温度
            from ..data.database import get_database_manager
            db_manager = get_database_manager()
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

            logger.info(f"Generated optimization strategy for opportunity {opportunity.order_num}")
            return optimization

        except Exception as e:
            logger.error(f"Failed to optimize strategy: {e}")
            return {"status": "error", "message": str(e)}
    
    def _build_priority_analysis_prompt(self, opportunity: OpportunityInfo, context: Dict[str, Any] = None) -> str:
        """构建优先级分析提示词"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        prompt = f"""你是一个现场服务运营专家，请分析以下商机的紧急程度和处理建议。

商机信息：
- 工单号: {opportunity.order_num}
- 客户姓名: {opportunity.name}
- 服务地址: {opportunity.address}
- 当前状态: {opportunity.order_status}
- 负责人: {opportunity.supervisor_name}
- 组织: {opportunity.org_name}
- SLA阈值: {opportunity.sla_threshold_hours or '未设置'}小时
- 已用时间: {(opportunity.elapsed_hours or 0):.1f}小时
- 超时时间: {(opportunity.overdue_hours or 0):.1f}小时
- 是否违规: {'是' if opportunity.is_violation else '否'}
- 是否逾期: {'是' if opportunity.is_overdue else '否'}
- 升级级别: {opportunity.escalation_level or 0}
- 创建时间: {opportunity.create_time.strftime('%Y-%m-%d %H:%M:%S') if opportunity.create_time else '未知'}

当前时间: {current_time}

额外上下文: {json.dumps(context or {}, ensure_ascii=False, indent=2)}

请基于以上信息，分析商机的处理优先级和建议行动，返回JSON格式：

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
3. 分析商机状态和处理难度
4. 提供具体可行的行动建议
5. 确保消息内容专业、简洁、有效"""

        return prompt
    
    def _build_message_generation_prompt(self, opportunity: OpportunityInfo, message_type: str) -> str:
        """构建消息生成提示词"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        prompt = f"""请为以下现场服务商机生成一条专业的{message_type}通知消息。

商机信息：
- 工单号: {opportunity.order_num}
- 客户姓名: {opportunity.name}
- 负责人: {opportunity.supervisor_name}
- 服务地址: {opportunity.address}
- 组织: {opportunity.org_name}
- SLA阈值: {opportunity.sla_threshold_hours}小时
- 已用时间: {opportunity.elapsed_hours:.1f}小时
- 超时时间: {opportunity.overdue_hours:.1f}小时

消息要求：
1. 语言简洁专业，突出重点
2. 包含关键信息（工单号、超时情况、负责人）
3. 提供明确的行动建议
4. 语气适中，既紧急又不失礼貌
5. 长度控制在200字以内
6. 使用适当的emoji增强可读性

请直接返回消息内容，不需要JSON格式。"""

        return prompt
    
    def _build_strategy_optimization_prompt(self, opportunity: OpportunityInfo, history: List[Dict[str, Any]]) -> str:
        """构建策略优化提示词"""
        prompt = f"""作为运营优化专家，请基于历史数据分析当前商机的最佳处理策略。

当前商机：
- 工单号: {opportunity.order_num}
- 超时情况: {opportunity.overdue_hours:.1f}小时
- 客户: {opportunity.name}
- 负责人: {opportunity.supervisor_name}
- 组织: {opportunity.org_name}

历史数据：
{json.dumps(history, ensure_ascii=False, indent=2)}

请分析：
1. 类似商机的处理模式
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
                parsed_result = json.loads(json_str)

                # 确保必需字段存在，提供默认值
                result = {
                    "action": parsed_result.get("action", "skip"),
                    "priority": parsed_result.get("priority", "normal"),
                    "message": parsed_result.get("message", "系统自动生成的提醒消息"),
                    "reasoning": parsed_result.get("reasoning", "LLM分析结果"),
                    "confidence": parsed_result.get("confidence", 0.8)
                }
                return result
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
    
    def _fallback_rule_decision(self, opportunity: OpportunityInfo) -> DecisionResult:
        """规则决策降级方案"""
        # 安全处理None值
        overdue_hours = opportunity.overdue_hours or 0
        sla_threshold = opportunity.sla_threshold_hours or 24  # 默认24小时

        if overdue_hours > sla_threshold:
            action = "escalate"
            priority = Priority.URGENT
        elif overdue_hours > 0:
            action = "notify"
            priority = Priority.HIGH
        else:
            action = "skip"
            priority = Priority.NORMAL

        return DecisionResult(
            action=action,
            priority=priority,
            message="基于规则的自动决策",
            reasoning=f"商机超时{overdue_hours:.1f}小时，触发{action}动作",
            confidence=1.0,
            llm_used=False
        )
    
    def _fallback_template_message(self, opportunity: OpportunityInfo, message_type: str) -> str:
        """模板消息降级方案"""
        if message_type == "overdue_alert":
            return f"""🚨 商机超时提醒

工单号: {opportunity.order_num}
客户: {opportunity.name}
负责人: {opportunity.supervisor_name}
超时时间: {opportunity.overdue_hours:.1f}小时

请及时处理，确保服务质量！"""
        else:
            return f"工单 {opportunity.order_num} 需要关注，请及时处理。"
    
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

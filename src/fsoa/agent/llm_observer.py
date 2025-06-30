"""
LLM可观测性模块

提供LLM调用的全面监控和日志记录功能，支持：
- Context内容记录
- 提示词完整记录
- API调用状态监控
- 响应内容记录
- Token使用统计
- 性能指标收集
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.logger import get_logger
from ..utils.timezone_utils import now_china_naive

logger = get_logger(__name__)


class LLMCallStatus(str, Enum):
    """LLM调用状态"""
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


@dataclass
class LLMCallRecord:
    """LLM调用记录"""
    call_id: str
    timestamp: datetime
    opportunity_id: str
    status: LLMCallStatus
    
    # 输入数据
    context_data: Dict[str, Any]
    prompt_text: str
    model_name: str
    temperature: float
    max_tokens: int
    
    # 输出数据
    response_text: Optional[str] = None
    parsed_result: Optional[Dict[str, Any]] = None
    
    # 性能指标
    duration_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    
    # 错误信息
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # 决策信息
    rule_suggestion: Optional[Dict[str, Any]] = None
    final_decision: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class LLMObserver:
    """LLM观测器"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._call_records: List[LLMCallRecord] = []  # 内存缓存，用于快速访问
        self._current_call: Optional[LLMCallRecord] = None
        self._use_database = True  # 是否使用数据库持久化
    
    def start_call(self, opportunity_id: str, context_data: Dict[str, Any], 
                   prompt_text: str, model_name: str = "deepseek-chat",
                   temperature: float = 0.1, max_tokens: int = 1000) -> str:
        """开始LLM调用记录"""
        call_id = f"llm_{int(time.time() * 1000)}_{opportunity_id}"
        
        self._current_call = LLMCallRecord(
            call_id=call_id,
            timestamp=now_china_naive(),
            opportunity_id=opportunity_id,
            status=LLMCallStatus.STARTED,
            context_data=context_data,
            prompt_text=prompt_text,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # 记录详细的调用开始日志
        self.logger.info(
            "🤖 LLM调用开始",
            extra={
                "call_id": call_id,
                "opportunity_id": opportunity_id,
                "model": model_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "context_keys": list(context_data.keys()),
                "prompt_length": len(prompt_text)
            }
        )
        
        # 记录完整的Context内容（调试模式）
        self._log_context_details(call_id, context_data)
        
        # 记录完整的提示词内容（调试模式）
        self._log_prompt_details(call_id, prompt_text)

        # 保存到数据库
        if self._use_database:
            self._save_to_database()

        return call_id
    
    def record_success(self, call_id: str, response_text: str, 
                      parsed_result: Dict[str, Any], duration_ms: float,
                      tokens_used: Optional[int] = None,
                      tokens_prompt: Optional[int] = None,
                      tokens_completion: Optional[int] = None):
        """记录成功的LLM调用"""
        if not self._current_call or self._current_call.call_id != call_id:
            self.logger.warning(f"未找到对应的LLM调用记录: {call_id}")
            return
        
        self._current_call.status = LLMCallStatus.SUCCESS
        self._current_call.response_text = response_text
        self._current_call.parsed_result = parsed_result
        self._current_call.duration_ms = duration_ms
        self._current_call.tokens_used = tokens_used
        self._current_call.tokens_prompt = tokens_prompt
        self._current_call.tokens_completion = tokens_completion
        
        # 记录成功日志
        self.logger.info(
            "✅ LLM调用成功",
            extra={
                "call_id": call_id,
                "duration_ms": duration_ms,
                "tokens_used": tokens_used,
                "tokens_prompt": tokens_prompt,
                "tokens_completion": tokens_completion,
                "action": parsed_result.get("action"),
                "priority": parsed_result.get("priority"),
                "confidence": parsed_result.get("confidence")
            }
        )
        
        # 记录完整的响应内容（调试模式）
        self._log_response_details(call_id, response_text, parsed_result)

        # 更新数据库
        if self._use_database:
            self._update_database()

        self._finalize_call()
    
    def record_failure(self, call_id: str, error_message: str, 
                      error_type: str, duration_ms: float):
        """记录失败的LLM调用"""
        if not self._current_call or self._current_call.call_id != call_id:
            self.logger.warning(f"未找到对应的LLM调用记录: {call_id}")
            return
        
        self._current_call.status = LLMCallStatus.FAILED
        self._current_call.error_message = error_message
        self._current_call.error_type = error_type
        self._current_call.duration_ms = duration_ms
        
        # 记录失败日志
        self.logger.error(
            "❌ LLM调用失败",
            extra={
                "call_id": call_id,
                "duration_ms": duration_ms,
                "error_type": error_type,
                "error_message": error_message
            }
        )

        # 更新数据库
        if self._use_database:
            self._update_database()

        self._finalize_call()
    
    def record_decision_context(self, call_id: str, rule_suggestion: Dict[str, Any],
                               final_decision: Dict[str, Any]):
        """记录决策上下文"""
        if not self._current_call or self._current_call.call_id != call_id:
            return
        
        self._current_call.rule_suggestion = rule_suggestion
        self._current_call.final_decision = final_decision
        
        self.logger.info(
            "🔄 决策合并完成",
            extra={
                "call_id": call_id,
                "rule_action": rule_suggestion.get("action"),
                "llm_action": final_decision.get("action"),
                "final_action": final_decision.get("action"),
                "llm_used": final_decision.get("llm_used", False)
            }
        )
    
    def _log_context_details(self, call_id: str, context_data: Dict[str, Any]):
        """记录Context详细内容"""
        self.logger.debug(
            "📋 LLM Context详情",
            extra={
                "call_id": call_id,
                "context_summary": self._summarize_context(context_data),
                "full_context": json.dumps(context_data, ensure_ascii=False, indent=2)
            }
        )
    
    def _log_prompt_details(self, call_id: str, prompt_text: str):
        """记录提示词详细内容"""
        self.logger.debug(
            "📝 LLM提示词详情",
            extra={
                "call_id": call_id,
                "prompt_length": len(prompt_text),
                "prompt_lines": prompt_text.count('\n') + 1,
                "full_prompt": prompt_text
            }
        )
    
    def _log_response_details(self, call_id: str, response_text: str, 
                             parsed_result: Dict[str, Any]):
        """记录响应详细内容"""
        self.logger.debug(
            "📤 LLM响应详情",
            extra={
                "call_id": call_id,
                "response_length": len(response_text),
                "raw_response": response_text,
                "parsed_result": json.dumps(parsed_result, ensure_ascii=False, indent=2)
            }
        )
    
    def _summarize_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成Context摘要"""
        summary = {}
        
        if "notification_history" in context_data:
            history = context_data["notification_history"]
            summary["notification_count"] = len(history)
            if history:
                summary["latest_notification"] = {
                    "type": history[-1].get("type"),
                    "status": history[-1].get("status"),
                    "sent_at": history[-1].get("sent_at")
                }
        
        if "group_config" in context_data:
            group = context_data["group_config"]
            summary["group_name"] = group.get("name")
            summary["cooldown_minutes"] = group.get("cooldown_minutes")
        
        if "current_time" in context_data:
            time_info = context_data["current_time"]
            summary["is_business_hours"] = time_info.get("is_business_hours")
            summary["current_hour"] = time_info.get("hour")
        
        if "rule_suggestion" in context_data:
            rule = context_data["rule_suggestion"]
            summary["rule_action"] = rule.get("action")
            summary["rule_priority"] = rule.get("priority")
        
        return summary

    def _save_to_database(self):
        """保存当前调用到数据库"""
        if not self._current_call:
            return

        try:
            from ..data.database import get_database_manager
            db_manager = get_database_manager()

            record_data = {
                'call_id': self._current_call.call_id,
                'timestamp': self._current_call.timestamp,
                'opportunity_id': self._current_call.opportunity_id,
                'status': self._current_call.status.value,
                'context_data': self._current_call.context_data,
                'prompt_text': self._current_call.prompt_text,
                'model_name': self._current_call.model_name,
                'temperature': self._current_call.temperature,
                'max_tokens': self._current_call.max_tokens,
                'response_text': self._current_call.response_text,
                'parsed_result': self._current_call.parsed_result,
                'duration_ms': self._current_call.duration_ms,
                'tokens_used': self._current_call.tokens_used,
                'tokens_prompt': self._current_call.tokens_prompt,
                'tokens_completion': self._current_call.tokens_completion,
                'error_message': self._current_call.error_message,
                'error_type': self._current_call.error_type,
                'rule_suggestion': self._current_call.rule_suggestion,
                'final_decision': self._current_call.final_decision
            }

            db_manager.create_llm_call_record(record_data)

        except Exception as e:
            self.logger.error(f"Failed to save LLM call record to database: {e}")

    def _update_database(self):
        """更新数据库中的调用记录"""
        if not self._current_call:
            return

        try:
            from ..data.database import get_database_manager
            db_manager = get_database_manager()

            update_data = {
                'status': self._current_call.status.value,
                'response_text': self._current_call.response_text,
                'parsed_result': self._current_call.parsed_result,
                'duration_ms': self._current_call.duration_ms,
                'tokens_used': self._current_call.tokens_used,
                'tokens_prompt': self._current_call.tokens_prompt,
                'tokens_completion': self._current_call.tokens_completion,
                'error_message': self._current_call.error_message,
                'error_type': self._current_call.error_type,
                'rule_suggestion': self._current_call.rule_suggestion,
                'final_decision': self._current_call.final_decision
            }

            db_manager.update_llm_call_record(self._current_call.call_id, update_data)

        except Exception as e:
            self.logger.error(f"Failed to update LLM call record in database: {e}")

    def _finalize_call(self):
        """完成调用记录"""
        if self._current_call:
            self._call_records.append(self._current_call)
            self._current_call = None
    
    def get_call_history(self, limit: int = 10, use_database: bool = True) -> List[Dict[str, Any]]:
        """获取调用历史"""
        if use_database and self._use_database:
            try:
                from ..data.database import get_database_manager
                db_manager = get_database_manager()
                return db_manager.get_llm_call_records(limit=limit)
            except Exception as e:
                self.logger.error(f"Failed to get call history from database: {e}")
                # 降级到内存数据
                return [record.to_dict() for record in self._call_records[-limit:]]
        else:
            return [record.to_dict() for record in self._call_records[-limit:]]
    
    def get_statistics(self, use_database: bool = True) -> Dict[str, Any]:
        """获取统计信息"""
        if use_database and self._use_database:
            try:
                from ..data.database import get_database_manager
                db_manager = get_database_manager()
                return db_manager.get_llm_call_statistics()
            except Exception as e:
                self.logger.error(f"Failed to get statistics from database: {e}")
                # 降级到内存数据
                pass

        # 使用内存数据计算统计
        if not self._call_records:
            return {"total_calls": 0}

        total_calls = len(self._call_records)
        success_calls = len([r for r in self._call_records if r.status == LLMCallStatus.SUCCESS])
        failed_calls = len([r for r in self._call_records if r.status == LLMCallStatus.FAILED])

        # 计算平均响应时间
        durations = [r.duration_ms for r in self._call_records if r.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # 计算Token使用
        total_tokens = sum([r.tokens_used for r in self._call_records if r.tokens_used])

        return {
            "total_calls": total_calls,
            "success_calls": success_calls,
            "failed_calls": failed_calls,
            "success_rate": success_calls / total_calls if total_calls > 0 else 0,
            "avg_duration_ms": avg_duration,
            "total_tokens_used": total_tokens
        }


# 全局观测器实例
_llm_observer = None


def get_llm_observer() -> LLMObserver:
    """获取LLM观测器实例"""
    global _llm_observer
    if _llm_observer is None:
        _llm_observer = LLMObserver()
    return _llm_observer

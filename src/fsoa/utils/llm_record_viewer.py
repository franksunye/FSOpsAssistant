"""
LLM调用记录查看工具
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..data.database import get_database_manager
from ..utils.logger import get_logger

logger = get_logger(__name__)


def view_llm_records(limit: int = 10, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    查看LLM调用记录
    
    Args:
        limit: 返回记录数量限制
        status: 过滤状态（success, failed, started等）
    
    Returns:
        格式化的记录列表
    """
    db = get_database_manager()
    
    try:
        with db.get_session() as session:
            from ..data.database import LLMCallRecordTable
            
            query = session.query(LLMCallRecordTable).order_by(LLMCallRecordTable.timestamp.desc())
            
            if status:
                query = query.filter_by(status=status)
            
            records = query.limit(limit).all()
            
            formatted_records = []
            for record in records:
                formatted_record = {
                    'call_id': record.call_id,
                    'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'opportunity_id': record.opportunity_id,
                    'status': record.status,
                    'duration_ms': record.duration_ms,
                    'tokens_used': record.tokens_used,
                    'tokens_prompt': record.tokens_prompt,
                    'tokens_completion': record.tokens_completion,
                    'model_name': record.model_name,
                    'temperature': record.temperature,
                    'error_message': record.error_message,
                    'rule_suggestion': _parse_json_field(record.rule_suggestion),
                    'final_decision': _parse_json_field(record.final_decision),
                    'parsed_result': _parse_json_field(record.parsed_result),
                    'context_data': _parse_json_field(record.context_data)
                }
                formatted_records.append(formatted_record)
            
            return formatted_records
            
    except Exception as e:
        logger.error(f"Failed to view LLM records: {e}")
        return []


def _parse_json_field(field_value) -> Optional[Dict[str, Any]]:
    """解析JSON字段"""
    if field_value is None:
        return None
    
    try:
        if isinstance(field_value, str):
            return json.loads(field_value)
        elif isinstance(field_value, dict):
            return field_value
        else:
            return field_value
    except (json.JSONDecodeError, TypeError):
        return str(field_value)


def print_llm_record(record: Dict[str, Any], show_details: bool = False):
    """打印单个LLM记录"""
    print(f"=== LLM调用记录 ===")
    print(f"调用ID: {record['call_id']}")
    print(f"时间: {record['timestamp']}")
    print(f"商机ID: {record['opportunity_id']}")
    print(f"状态: {record['status']}")
    print(f"模型: {record['model_name']}")
    print(f"温度: {record['temperature']}")
    
    if record['duration_ms']:
        print(f"耗时: {record['duration_ms']:.1f}ms")
    
    if record['tokens_used']:
        print(f"Token使用: {record['tokens_used']} (输入: {record['tokens_prompt']}, 输出: {record['tokens_completion']})")
    
    if record['error_message']:
        print(f"错误: {record['error_message']}")
    
    # 规则建议
    if record['rule_suggestion']:
        rule = record['rule_suggestion']
        print(f"\n规则建议:")
        print(f"  动作: {rule.get('action')}")
        print(f"  优先级: {rule.get('priority')}")
        print(f"  推理: {rule.get('reasoning', '')[:100]}...")
    
    # 最终决策
    if record['final_decision']:
        decision = record['final_decision']
        print(f"\n最终决策:")
        print(f"  动作: {decision.get('action')}")
        print(f"  优先级: {decision.get('priority')}")
        print(f"  使用LLM: {decision.get('llm_used', False)}")
        print(f"  推理: {decision.get('reasoning', '')[:100]}...")
    
    # LLM解析结果
    if record['parsed_result']:
        result = record['parsed_result']
        print(f"\nLLM解析结果:")
        print(f"  动作: {result.get('action')}")
        print(f"  优先级: {result.get('priority')}")
        print(f"  置信度: {result.get('confidence')}")
        if result.get('message'):
            print(f"  消息: {result.get('message')[:100]}...")
    
    if show_details:
        # 上下文数据
        if record['context_data']:
            print(f"\n上下文数据:")
            context = record['context_data']
            if 'current_time' in context:
                time_info = context['current_time']
                print(f"  当前时间: {time_info.get('timestamp')}")
                print(f"  工作时间: {time_info.get('is_business_hours')}")
            
            if 'rule_suggestion' in context:
                rule_ctx = context['rule_suggestion']
                print(f"  规则上下文: {rule_ctx.get('action')} - {rule_ctx.get('priority')}")
    
    print()


def view_recent_llm_calls(count: int = 5, show_details: bool = False):
    """查看最近的LLM调用"""
    records = view_llm_records(limit=count)
    
    if not records:
        print("没有找到LLM调用记录")
        return
    
    print(f"最近 {len(records)} 次LLM调用:")
    print()
    
    for record in records:
        print_llm_record(record, show_details=show_details)


def view_llm_stats():
    """查看LLM调用统计"""
    db = get_database_manager()
    
    try:
        with db.get_session() as session:
            from ..data.database import LLMCallRecordTable
            from sqlalchemy import func
            
            # 总调用次数
            total_calls = session.query(func.count(LLMCallRecordTable.id)).scalar()
            
            # 按状态统计
            status_stats = session.query(
                LLMCallRecordTable.status,
                func.count(LLMCallRecordTable.id)
            ).group_by(LLMCallRecordTable.status).all()
            
            # Token使用统计
            token_stats = session.query(
                func.sum(LLMCallRecordTable.tokens_used),
                func.avg(LLMCallRecordTable.tokens_used),
                func.sum(LLMCallRecordTable.tokens_prompt),
                func.sum(LLMCallRecordTable.tokens_completion)
            ).first()
            
            # 平均耗时
            avg_duration = session.query(func.avg(LLMCallRecordTable.duration_ms)).scalar()
            
            print("=== LLM调用统计 ===")
            print(f"总调用次数: {total_calls}")
            print()
            
            print("状态分布:")
            for status, count in status_stats:
                print(f"  {status}: {count}")
            print()
            
            if token_stats[0]:
                print("Token使用统计:")
                print(f"  总Token: {token_stats[0]}")
                print(f"  平均Token: {token_stats[1]:.1f}")
                print(f"  输入Token: {token_stats[2]}")
                print(f"  输出Token: {token_stats[3]}")
                print()
            
            if avg_duration:
                print(f"平均耗时: {avg_duration:.1f}ms")
            
    except Exception as e:
        logger.error(f"Failed to get LLM stats: {e}")
        print(f"获取统计信息失败: {e}")


if __name__ == "__main__":
    # 示例用法
    print("查看最近5次LLM调用:")
    view_recent_llm_calls(5, show_details=True)
    
    print("\n" + "="*50 + "\n")
    
    print("LLM调用统计:")
    view_llm_stats()

#!/usr/bin/env python3
"""
测试Unicode转义序列问题并验证修复方案
"""

from src.fsoa.data.database import get_database_manager
from src.fsoa.agent.llm_observer import LLMObserver
import json
import uuid

def test_unicode_issue():
    """测试Unicode转义序列问题"""
    
    # 创建包含中文的测试数据
    test_data = {
        "message": "超时说明。",
        "description": "这是一个包含中文的测试数据",
        "action": "escalate",
        "reasoning": "商机严重超时，需要升级处理"
    }
    
    print("=== 测试Unicode转义序列问题 ===")
    print(f"原始数据: {test_data}")
    
    # 测试1: 直接使用json.dumps with ensure_ascii=True (会产生Unicode转义)
    json_with_escape = json.dumps(test_data, ensure_ascii=True)
    print(f"\n使用ensure_ascii=True: {json_with_escape}")
    
    # 测试2: 使用json.dumps with ensure_ascii=False (不会产生Unicode转义)
    json_without_escape = json.dumps(test_data, ensure_ascii=False)
    print(f"使用ensure_ascii=False: {json_without_escape}")
    
    # 测试3: 模拟保存到数据库并读取
    db = get_database_manager()
    
    # 创建测试记录 - 使用会产生Unicode转义的方式
    test_call_id = f"test_unicode_{uuid.uuid4().hex[:8]}"
    
    record_data = {
        'call_id': test_call_id,
        'timestamp': '2025-06-30 18:30:00',
        'opportunity_id': 'TEST001',
        'status': 'success',
        'context_data': json_with_escape,  # 故意使用有Unicode转义的JSON
        'prompt_text': 'Test prompt',
        'model_name': 'test-model',
        'temperature': 0.1,
        'max_tokens': 1000,
        'parsed_result': json_with_escape,  # 故意使用有Unicode转义的JSON
        'rule_suggestion': json_with_escape,  # 故意使用有Unicode转义的JSON
        'final_decision': json_with_escape   # 故意使用有Unicode转义的JSON
    }
    
    print(f"\n创建测试记录: {test_call_id}")
    success = db.create_llm_call_record(record_data)
    print(f"创建结果: {success}")
    
    if success:
        # 读取记录并检查
        records = db.get_llm_call_records(limit=1)
        if records and records[0]['call_id'] == test_call_id:
            record = records[0]
            print(f"\n读取的记录:")
            for field in ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']:
                value = record.get(field)
                print(f"{field}: {type(value)} - {value}")
                
                # 验证是否正确解析为字典
                if isinstance(value, dict):
                    print(f"  ✅ {field} 正确解析为字典")
                    print(f"  内容: {value}")
                else:
                    print(f"  ❌ {field} 未正确解析: {type(value)}")
        
        # 清理测试数据
        print(f"\n清理测试记录...")
        with db.get_session() as session:
            from src.fsoa.data.database import LLMCallRecordTable
            test_record = session.query(LLMCallRecordTable).filter_by(call_id=test_call_id).first()
            if test_record:
                session.delete(test_record)
                session.commit()
                print("测试记录已删除")

def test_llm_observer():
    """测试LLMObserver的JSON处理"""
    print("\n=== 测试LLMObserver ===")
    
    observer = LLMObserver()
    
    # 创建包含中文的测试数据
    context_data = {
        "message": "超时说明。",
        "description": "这是一个包含中文的测试数据",
        "current_time": {
            "timestamp": "2025-06-30T18:30:00",
            "is_business_hours": True
        }
    }
    
    # 开始调用
    call_id = observer.start_call(
        opportunity_id="TEST002",
        context_data=context_data,
        prompt_text="测试提示",
        model_name="test-model"
    )
    
    print(f"创建调用: {call_id}")
    
    # 记录决策上下文
    rule_suggestion = {
        "action": "escalate",
        "reasoning": "商机严重超时，需要升级处理",
        "confidence": 1.0
    }
    
    final_decision = {
        "action": "escalate",
        "reasoning": "规则建议: 商机严重超时，需要升级处理",
        "confidence": 0.95
    }
    
    observer.record_decision_context(call_id, rule_suggestion, final_decision)
    
    # 完成调用
    observer.complete_call(
        response_text="测试响应",
        parsed_result={"action": "escalate", "message": "测试消息"},
        duration_ms=1000.0,
        tokens_used=100
    )
    
    print("LLMObserver测试完成")

if __name__ == "__main__":
    test_unicode_issue()
    test_llm_observer()

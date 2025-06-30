#!/usr/bin/env python3
"""
测试Unicode转义序列问题的修复方案
"""

from src.fsoa.data.database import get_database_manager
from src.fsoa.agent.llm_observer import LLMObserver
import json
import uuid

def test_unicode_issue_reproduction():
    """重现Unicode转义序列问题"""
    
    print("=== 测试Unicode转义序列问题重现 ===")
    
    # 创建包含中文的测试数据
    test_data = {
        "message": "超时说明。",
        "description": "这是一个包含中文的测试数据",
        "action": "escalate",
        "reasoning": "商机严重超时，需要升级处理",
        "details": {
            "客户": "张三",
            "地址": "北京市朝阳区",
            "状态": "待预约"
        }
    }
    
    print(f"原始数据: {test_data}")
    
    # 测试不同的JSON序列化方式
    print("\n--- 测试JSON序列化方式 ---")
    
    # 方式1: 使用ensure_ascii=True (会产生Unicode转义)
    json_with_escape = json.dumps(test_data, ensure_ascii=True)
    print(f"ensure_ascii=True: {json_with_escape}")
    
    # 方式2: 使用ensure_ascii=False (不会产生Unicode转义)
    json_without_escape = json.dumps(test_data, ensure_ascii=False)
    print(f"ensure_ascii=False: {json_without_escape}")
    
    # 测试当前LLMObserver的处理方式
    print("\n--- 测试LLMObserver处理 ---")
    
    observer = LLMObserver()
    
    # 创建测试调用
    call_id = observer.start_call(
        opportunity_id="TEST_UNICODE",
        context_data=test_data,
        prompt_text="测试Unicode处理",
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
        "confidence": 0.95,
        "message": "紧急通知：工单已严重超时，请立即处理"
    }
    
    observer.record_decision_context(call_id, rule_suggestion, final_decision)
    
    # 完成调用
    parsed_result = {
        "action": "escalate",
        "message": "工单已严重超时，当前状态为待预约，请立即处理",
        "reasoning": "该商机已超时，需要升级处理"
    }
    
    observer.record_success(
        call_id=call_id,
        response_text="测试响应",
        parsed_result=parsed_result,
        duration_ms=1000.0,
        tokens_used=100
    )
    
    print("LLMObserver测试完成")
    
    # 验证数据库中的存储
    print("\n--- 验证数据库存储 ---")
    db = get_database_manager()
    
    with db.get_session() as session:
        from src.fsoa.data.database import LLMCallRecordTable
        
        record = session.query(LLMCallRecordTable).filter_by(call_id=call_id).first()
        
        if record:
            json_fields = ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']
            
            for field_name in json_fields:
                field_value = getattr(record, field_name)
                print(f"\n{field_name}:")
                print(f"  类型: {type(field_value)}")
                
                if field_value:
                    if isinstance(field_value, str):
                        if '\\u' in field_value:
                            print(f"  ⚠️  包含Unicode转义序列")
                            print(f"  原始: {field_value[:100]}...")
                            
                            # 尝试解码
                            try:
                                decoded = field_value.encode().decode('unicode_escape')
                                print(f"  解码: {decoded[:100]}...")
                            except Exception as e:
                                print(f"  解码失败: {e}")
                        else:
                            print(f"  ✅ 正常JSON字符串")
                            print(f"  内容: {field_value[:100]}...")
                    elif isinstance(field_value, dict):
                        print(f"  ✅ 字典类型")
                        print(f"  键: {list(field_value.keys())}")
                    else:
                        print(f"  其他类型: {field_value}")
        
        # 清理测试数据
        if record:
            session.delete(record)
            session.commit()
            print(f"\n测试记录已清理")

def test_manual_unicode_insertion():
    """手动测试Unicode转义序列的插入和处理"""
    
    print("\n=== 手动测试Unicode转义序列插入 ===")
    
    db = get_database_manager()
    
    # 创建包含Unicode转义序列的测试数据
    unicode_escaped_json = '{"message": "\\u8d85\\u65f6\\u8bf4\\u660e\\u3002", "action": "escalate"}'
    
    print(f"Unicode转义JSON: {unicode_escaped_json}")
    
    # 解码验证
    try:
        decoded = unicode_escaped_json.encode().decode('unicode_escape')
        print(f"解码后: {decoded}")
        
        parsed = json.loads(decoded)
        print(f"解析后: {parsed}")
    except Exception as e:
        print(f"处理失败: {e}")
    
    # 手动插入到数据库
    test_call_id = f"test_manual_unicode_{uuid.uuid4().hex[:8]}"
    
    record_data = {
        'call_id': test_call_id,
        'timestamp': '2025-06-30 18:30:00',
        'opportunity_id': 'TEST_MANUAL',
        'status': 'success',
        'context_data': unicode_escaped_json,  # 故意使用Unicode转义
        'prompt_text': 'Test prompt',
        'model_name': 'test-model',
        'temperature': 0.1,
        'max_tokens': 1000,
        'parsed_result': unicode_escaped_json,
        'rule_suggestion': unicode_escaped_json,
        'final_decision': unicode_escaped_json
    }
    
    print(f"\n插入测试记录: {test_call_id}")
    success = db.create_llm_call_record(record_data)
    print(f"插入结果: {success}")
    
    if success:
        # 读取并验证
        records = db.get_llm_call_records(limit=1)
        if records and records[0]['call_id'] == test_call_id:
            record = records[0]
            print(f"\n读取的记录:")
            
            for field in ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']:
                value = record.get(field)
                print(f"{field}: {type(value)}")
                
                if isinstance(value, dict):
                    print(f"  ✅ 正确解析为字典: {value}")
                elif isinstance(value, str):
                    print(f"  ⚠️  仍为字符串: {value[:100]}...")
                else:
                    print(f"  其他类型: {value}")
        
        # 清理测试数据
        with db.get_session() as session:
            from src.fsoa.data.database import LLMCallRecordTable
            test_record = session.query(LLMCallRecordTable).filter_by(call_id=test_call_id).first()
            if test_record:
                session.delete(test_record)
                session.commit()
                print(f"\n手动测试记录已清理")

if __name__ == "__main__":
    test_unicode_issue_reproduction()
    test_manual_unicode_insertion()

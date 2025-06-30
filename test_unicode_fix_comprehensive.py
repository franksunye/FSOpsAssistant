#!/usr/bin/env python3
"""
全面测试Unicode转义序列问题的修复方案
"""

from src.fsoa.data.database import get_database_manager
import json
import uuid
from datetime import datetime

def test_unicode_escape_handling():
    """测试Unicode转义序列的处理"""
    
    print("=== 全面测试Unicode转义序列处理 ===")
    
    db = get_database_manager()
    
    # 测试数据：包含Unicode转义序列的JSON字符串
    test_cases = [
        {
            "name": "正常中文JSON",
            "data": '{"message": "超时说明。", "action": "escalate"}',
            "expected_message": "超时说明。"
        },
        {
            "name": "Unicode转义JSON",
            "data": '{"message": "\\u8d85\\u65f6\\u8bf4\\u660e\\u3002", "action": "escalate"}',
            "expected_message": "超时说明。"
        },
        {
            "name": "混合Unicode转义",
            "data": '{"message": "工单\\u5df2\\u4e25\\u91cd\\u8d85\\u65f6", "status": "待预约"}',
            "expected_message": "工单已严重超时"
        },
        {
            "name": "复杂Unicode转义",
            "data": '{"reasoning": "\\u5546\\u673a\\u4e25\\u91cd\\u8d85\\u65f6\\uff0c\\u9700\\u8981\\u5347\\u7ea7\\u5904\\u7406"}',
            "expected_reasoning": "商机严重超时，需要升级处理"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n--- 测试案例 {i+1}: {test_case['name']} ---")
        
        # 创建测试记录
        test_call_id = f"test_unicode_fix_{uuid.uuid4().hex[:8]}"
        
        record_data = {
            'call_id': test_call_id,
            'timestamp': datetime.now(),
            'opportunity_id': f'TEST_{i+1}',
            'status': 'success',
            'context_data': test_case['data'],
            'prompt_text': 'Test prompt',
            'model_name': 'test-model',
            'temperature': 0.1,
            'max_tokens': 1000,
            'parsed_result': test_case['data'],
            'rule_suggestion': test_case['data'],
            'final_decision': test_case['data']
        }
        
        print(f"原始数据: {test_case['data']}")
        
        # 插入记录
        success = db.create_llm_call_record(record_data)
        print(f"插入结果: {success}")
        
        if success:
            # 读取并验证
            records = db.get_llm_call_records(limit=1)
            if records and records[0]['call_id'] == test_call_id:
                record = records[0]
                
                # 验证每个JSON字段
                for field in ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']:
                    value = record.get(field)
                    print(f"  {field}: {type(value)}")
                    
                    if isinstance(value, dict):
                        print(f"    ✅ 正确解析为字典")
                        
                        # 验证特定字段的内容
                        if 'message' in value and 'expected_message' in test_case:
                            actual_message = value['message']
                            expected_message = test_case['expected_message']
                            if actual_message == expected_message:
                                print(f"    ✅ 消息内容正确: '{actual_message}'")
                            else:
                                print(f"    ❌ 消息内容不匹配: 期望 '{expected_message}', 实际 '{actual_message}'")
                        
                        if 'reasoning' in value and 'expected_reasoning' in test_case:
                            actual_reasoning = value['reasoning']
                            expected_reasoning = test_case['expected_reasoning']
                            if actual_reasoning == expected_reasoning:
                                print(f"    ✅ 推理内容正确: '{actual_reasoning}'")
                            else:
                                print(f"    ❌ 推理内容不匹配: 期望 '{expected_reasoning}', 实际 '{actual_reasoning}'")
                    
                    elif isinstance(value, str):
                        print(f"    ⚠️  仍为字符串: {value[:50]}...")
                    else:
                        print(f"    ❌ 其他类型: {value}")
            
            # 清理测试数据
            with db.get_session() as session:
                from src.fsoa.data.database import LLMCallRecordTable
                test_record = session.query(LLMCallRecordTable).filter_by(call_id=test_call_id).first()
                if test_record:
                    session.delete(test_record)
                    session.commit()
        
        print(f"测试案例 {i+1} 完成")

def test_llm_record_viewer():
    """测试LLM记录查看器的Unicode处理"""
    
    print("\n=== 测试LLM记录查看器 ===")
    
    from src.fsoa.utils.llm_record_viewer import view_llm_records, _parse_json_field
    
    # 测试_parse_json_field函数
    test_cases = [
        {
            "name": "正常JSON字符串",
            "input": '{"message": "超时说明。"}',
            "expected_type": dict,
            "expected_message": "超时说明。"
        },
        {
            "name": "Unicode转义JSON字符串",
            "input": '{"message": "\\u8d85\\u65f6\\u8bf4\\u660e\\u3002"}',
            "expected_type": dict,
            "expected_message": "超时说明。"
        },
        {
            "name": "已解析的字典",
            "input": {"message": "超时说明。"},
            "expected_type": dict,
            "expected_message": "超时说明。"
        },
        {
            "name": "无效JSON字符串",
            "input": "invalid json",
            "expected_type": dict,
            "expected_raw_value": "invalid json"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n测试 {i+1}: {test_case['name']}")
        print(f"输入: {test_case['input']}")
        
        result = _parse_json_field(test_case['input'])
        print(f"输出: {result}")
        print(f"类型: {type(result)}")
        
        # 验证结果
        if isinstance(result, test_case['expected_type']):
            print("✅ 类型正确")
            
            if 'expected_message' in test_case and 'message' in result:
                if result['message'] == test_case['expected_message']:
                    print(f"✅ 消息内容正确: '{result['message']}'")
                else:
                    print(f"❌ 消息内容不匹配: 期望 '{test_case['expected_message']}', 实际 '{result['message']}'")
            
            if 'expected_raw_value' in test_case and 'raw_value' in result:
                if result['raw_value'] == test_case['expected_raw_value']:
                    print(f"✅ 原始值正确: '{result['raw_value']}'")
                else:
                    print(f"❌ 原始值不匹配: 期望 '{test_case['expected_raw_value']}', 实际 '{result['raw_value']}'")
        else:
            print(f"❌ 类型不匹配: 期望 {test_case['expected_type']}, 实际 {type(result)}")

def test_existing_records():
    """测试现有记录的处理"""
    
    print("\n=== 测试现有记录处理 ===")
    
    db = get_database_manager()
    records = db.get_llm_call_records(limit=5)
    
    print(f"检查最近 {len(records)} 条记录...")
    
    for i, record in enumerate(records):
        print(f"\n记录 {i+1}: {record['call_id']}")
        
        for field in ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']:
            value = record.get(field)
            if value:
                print(f"  {field}: {type(value)}")
                if isinstance(value, dict):
                    print(f"    ✅ 字典类型，键: {list(value.keys())}")
                elif isinstance(value, str):
                    print(f"    ⚠️  字符串类型: {value[:50]}...")
                else:
                    print(f"    ❓ 其他类型: {value}")
            else:
                print(f"  {field}: None")

if __name__ == "__main__":
    test_unicode_escape_handling()
    test_llm_record_viewer()
    test_existing_records()

#!/usr/bin/env python3
"""
测试最终的Unicode解决方案
"""

from src.fsoa.data.database import get_database_manager
from src.fsoa.agent.llm_observer import LLMObserver
import json

def test_new_data_storage():
    """测试新数据的存储"""
    
    print("=== 测试新数据存储 ===")
    
    observer = LLMObserver()
    
    # 创建包含中文的测试数据
    context_data = {
        "message": "工单已严重超时",
        "description": "这是一个包含中文的测试数据",
        "details": {
            "客户": "张三",
            "地址": "北京市朝阳区",
            "状态": "待预约",
            "超时原因": "商机严重超时，需要升级处理"
        }
    }
    
    # 开始调用
    call_id = observer.start_call(
        opportunity_id="TEST_FINAL",
        context_data=context_data,
        prompt_text="测试最终解决方案",
        model_name="test-model"
    )
    
    print(f"创建调用: {call_id}")
    
    # 记录决策上下文
    rule_suggestion = {
        "action": "escalate",
        "reasoning": "商机严重超时1500%，需要立即升级处理",
        "confidence": 1.0,
        "message": "紧急通知：工单已严重超时，请立即处理"
    }
    
    final_decision = {
        "action": "escalate",
        "reasoning": "规则建议: 商机严重超时1500%，需要立即升级处理; LLM分析: 该商机已超时严重，需要立即升级",
        "confidence": 0.95,
        "message": "紧急通知：工单已严重超时，请立即处理并联系客户解释延误原因"
    }
    
    observer.record_decision_context(call_id, rule_suggestion, final_decision)
    
    # 完成调用
    parsed_result = {
        "action": "escalate",
        "message": "工单已严重超时，当前状态为待预约，请立即处理",
        "reasoning": "该商机已超时，需要升级处理",
        "details": "客户张三位于北京市朝阳区，工单状态为待预约"
    }
    
    observer.record_success(
        call_id=call_id,
        response_text="测试响应",
        parsed_result=parsed_result,
        duration_ms=1000.0,
        tokens_used=100
    )
    
    print("✅ 新数据存储完成")
    return call_id

def test_database_readability():
    """测试数据库可读性"""
    
    print("\n=== 测试数据库可读性 ===")
    
    import sqlite3
    conn = sqlite3.connect("fsoa.db")
    cursor = conn.cursor()
    
    # 查询最新记录
    cursor.execute("""
        SELECT call_id, context_data, parsed_result, rule_suggestion, final_decision 
        FROM llm_call_records 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    record = cursor.fetchone()
    if record:
        call_id, context_data, parsed_result, rule_suggestion, final_decision = record
        
        print(f"最新记录: {call_id}")
        print(f"Context数据: {context_data}")
        print(f"解析结果: {parsed_result}")
        print(f"规则建议: {rule_suggestion}")
        print(f"最终决策: {final_decision}")
        
        # 验证中文字符是否可读
        if context_data and "工单已严重超时" in context_data:
            print("✅ Context数据中文可读")
        else:
            print("❌ Context数据中文不可读")
            
        if parsed_result and "工单已严重超时" in parsed_result:
            print("✅ 解析结果中文可读")
        else:
            print("❌ 解析结果中文不可读")
            
        if rule_suggestion and "商机严重超时" in rule_suggestion:
            print("✅ 规则建议中文可读")
        else:
            print("❌ 规则建议中文不可读")
            
        if final_decision and "商机严重超时" in final_decision:
            print("✅ 最终决策中文可读")
        else:
            print("❌ 最终决策中文不可读")
    
    conn.close()

def test_api_compatibility():
    """测试API兼容性"""
    
    print("\n=== 测试API兼容性 ===")
    
    db = get_database_manager()
    records = db.get_llm_call_records(limit=2)
    
    print(f"获取到 {len(records)} 条记录")
    
    for i, record in enumerate(records):
        print(f"\n记录 {i+1}: {record['call_id']}")
        
        for field in ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']:
            value = record.get(field)
            if value:
                print(f"  {field}: {type(value)}")
                if isinstance(value, dict):
                    print(f"    ✅ 正确解析为字典")
                    # 检查是否包含中文
                    json_str = json.dumps(value, ensure_ascii=False)
                    if any(ord(c) > 127 for c in json_str):
                        print(f"    ✅ 包含中文字符")
                elif isinstance(value, str):
                    print(f"    ⚠️  仍为字符串: {value[:50]}...")
                else:
                    print(f"    ❓ 其他类型: {value}")
            else:
                print(f"  {field}: None")

def test_unicode_handling():
    """测试Unicode处理"""
    
    print("\n=== 测试Unicode处理 ===")
    
    # 测试各种Unicode字符
    test_data = {
        "中文": "这是中文测试",
        "emoji": "🚀 测试 emoji 字符",
        "特殊符号": "测试特殊符号：①②③④⑤",
        "混合": "Mixed 中英文 content with 特殊字符 123"
    }
    
    # 序列化
    json_str = json.dumps(test_data, ensure_ascii=False, separators=(',', ':'))
    print(f"序列化结果: {json_str}")
    
    # 反序列化
    parsed_data = json.loads(json_str)
    print(f"反序列化结果: {parsed_data}")
    
    # 验证数据完整性
    if test_data == parsed_data:
        print("✅ Unicode数据完整性验证通过")
    else:
        print("❌ Unicode数据完整性验证失败")

if __name__ == "__main__":
    # 测试新数据存储
    call_id = test_new_data_storage()
    
    # 测试数据库可读性
    test_database_readability()
    
    # 测试API兼容性
    test_api_compatibility()
    
    # 测试Unicode处理
    test_unicode_handling()
    
    print(f"\n🎉 最终解决方案测试完成！")
    print(f"📋 新记录ID: {call_id}")
    print(f"💡 JSON数据现在完全可读，支持中文字符")

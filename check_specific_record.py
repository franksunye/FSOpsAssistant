#!/usr/bin/env python3
"""
查询特定LLM调用记录的原始数据格式
"""

from src.fsoa.data.database import get_database_manager
import json

def check_specific_record():
    """查询特定记录的原始数据"""
    db = get_database_manager()
    
    # 直接查询原始数据
    with db.get_session() as session:
        from src.fsoa.data.database import LLMCallRecordTable
        
        # 查询特定记录
        record = session.query(LLMCallRecordTable).filter_by(
            call_id="llm_1751279120393_GD20250601176"
        ).first()
        
        if not record:
            print("❌ 未找到指定记录")
            return
            
        print(f"=== 记录详情: {record.call_id} ===")
        print(f"状态: {record.status}")
        print(f"时间: {record.timestamp}")
        print(f"商机ID: {record.opportunity_id}")
        
        # 检查每个JSON字段的原始存储格式
        json_fields = ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']
        
        for field_name in json_fields:
            field_value = getattr(record, field_name)
            print(f"\n--- {field_name} ---")
            print(f"类型: {type(field_value)}")
            
            if field_value is None:
                print("值: None")
                continue
                
            # 显示原始值的前500个字符
            raw_str = repr(field_value)
            print(f"原始值: {raw_str[:500]}...")
            
            # 检查是否包含Unicode转义序列
            if isinstance(field_value, str):
                if '\\u' in field_value:
                    print("⚠️  包含Unicode转义序列")
                    
                    # 显示一些具体的Unicode转义示例
                    import re
                    unicode_matches = re.findall(r'\\u[0-9a-fA-F]{4}', field_value)
                    if unicode_matches:
                        print(f"发现的Unicode转义: {unicode_matches[:10]}...")  # 显示前10个
                        
                        # 尝试解码第一个Unicode转义
                        try:
                            first_unicode = unicode_matches[0]
                            decoded_char = first_unicode.encode().decode('unicode_escape')
                            print(f"示例解码: {first_unicode} -> '{decoded_char}'")
                        except Exception as e:
                            print(f"解码失败: {e}")
                    
                    # 尝试完整解码
                    try:
                        decoded_full = field_value.encode().decode('unicode_escape')
                        print(f"完整解码后: {decoded_full[:200]}...")
                        
                        # 尝试JSON解析解码后的内容
                        try:
                            parsed_json = json.loads(decoded_full)
                            print(f"解码后JSON解析成功: {type(parsed_json)}")
                            if isinstance(parsed_json, dict):
                                print(f"字典键: {list(parsed_json.keys())}")
                        except json.JSONDecodeError as je:
                            print(f"解码后JSON解析失败: {je}")
                            
                    except Exception as de:
                        print(f"Unicode解码失败: {de}")
                else:
                    print("✅ 不包含Unicode转义序列")
                    
                    # 尝试直接JSON解析
                    try:
                        parsed_json = json.loads(field_value)
                        print(f"直接JSON解析成功: {type(parsed_json)}")
                        if isinstance(parsed_json, dict):
                            print(f"字典键: {list(parsed_json.keys())}")
                    except json.JSONDecodeError as je:
                        print(f"直接JSON解析失败: {je}")
            
            elif isinstance(field_value, dict):
                print("✅ 已经是字典类型")
                print(f"字典键: {list(field_value.keys())}")
            
            else:
                print(f"其他类型: {type(field_value)}")

if __name__ == "__main__":
    check_specific_record()

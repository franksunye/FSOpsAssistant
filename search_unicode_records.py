#!/usr/bin/env python3
"""
搜索包含Unicode转义序列的记录
"""

from src.fsoa.data.database import get_database_manager
import json

def search_unicode_records():
    """搜索包含Unicode转义序列的记录"""
    db = get_database_manager()
    
    # 直接查询原始数据
    with db.get_session() as session:
        from src.fsoa.data.database import LLMCallRecordTable
        
        # 查询所有记录
        records = session.query(LLMCallRecordTable).order_by(
            LLMCallRecordTable.timestamp.desc()
        ).all()
        
        print(f"=== 搜索Unicode转义序列 (共{len(records)}条记录) ===")
        
        unicode_records = []
        json_fields = ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']
        
        for record in records:
            record_has_unicode = False
            unicode_details = {}
            
            for field_name in json_fields:
                field_value = getattr(record, field_name)
                
                if field_value and isinstance(field_value, str):
                    # 检查是否包含Unicode转义序列
                    if '\\u' in field_value:
                        record_has_unicode = True
                        
                        # 查找具体的Unicode转义
                        import re
                        unicode_matches = re.findall(r'\\u[0-9a-fA-F]{4}', field_value)
                        unicode_details[field_name] = {
                            'count': len(unicode_matches),
                            'examples': unicode_matches[:5],  # 前5个示例
                            'preview': field_value[:200]  # 前200个字符
                        }
            
            if record_has_unicode:
                unicode_records.append({
                    'call_id': record.call_id,
                    'timestamp': record.timestamp,
                    'details': unicode_details
                })
        
        if unicode_records:
            print(f"\n⚠️  发现 {len(unicode_records)} 条包含Unicode转义序列的记录:")
            
            for i, rec in enumerate(unicode_records):
                print(f"\n记录 {i+1}: {rec['call_id']}")
                print(f"时间: {rec['timestamp']}")
                
                for field_name, details in rec['details'].items():
                    print(f"  {field_name}:")
                    print(f"    Unicode转义数量: {details['count']}")
                    print(f"    示例: {details['examples']}")
                    print(f"    预览: {details['preview']}...")
                    
                    # 尝试解码第一个示例
                    if details['examples']:
                        try:
                            first_unicode = details['examples'][0]
                            decoded_char = first_unicode.encode().decode('unicode_escape')
                            print(f"    解码示例: {first_unicode} -> '{decoded_char}'")
                        except Exception as e:
                            print(f"    解码失败: {e}")
        else:
            print("\n✅ 未发现包含Unicode转义序列的记录")
        
        # 特别检查您提到的特定模式
        print(f"\n=== 搜索特定模式: \\u8d85\\u65f6\\u8bf4\\u660e ===")
        specific_pattern_found = False
        
        for record in records:
            for field_name in json_fields:
                field_value = getattr(record, field_name)
                
                if field_value and isinstance(field_value, str):
                    if '\\u8d85\\u65f6\\u8bf4\\u660e' in field_value:
                        specific_pattern_found = True
                        print(f"发现在记录 {record.call_id} 的 {field_name} 字段")
                        print(f"内容: {field_value[:300]}...")
                        
                        # 尝试解码
                        try:
                            decoded = field_value.encode().decode('unicode_escape')
                            print(f"解码后: {decoded[:300]}...")
                        except Exception as e:
                            print(f"解码失败: {e}")
        
        if not specific_pattern_found:
            print("✅ 未发现您提到的特定Unicode转义模式")

if __name__ == "__main__":
    search_unicode_records()

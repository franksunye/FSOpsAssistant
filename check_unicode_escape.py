#!/usr/bin/env python3
"""
检查数据库中是否有Unicode转义序列的记录
"""

from src.fsoa.data.database import get_database_manager
import json

def check_unicode_escape():
    db = get_database_manager()
    
    # 直接查询原始数据
    with db.get_session() as session:
        from src.fsoa.data.database import LLMCallRecordTable
        
        # 查询更多记录
        records = session.query(LLMCallRecordTable).order_by(
            LLMCallRecordTable.timestamp.desc()
        ).limit(10).all()
        
        print('=== 检查Unicode转义序列 ===')
        unicode_found = False
        
        for i, record in enumerate(records):
            print(f'\n记录 {i+1}: {record.call_id}')
            
            # 检查每个JSON字段是否包含Unicode转义
            for field_name in ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']:
                field_value = getattr(record, field_name)
                if field_value and isinstance(field_value, str):
                    if '\\u' in field_value:
                        unicode_found = True
                        print(f'  ⚠️  {field_name} 包含Unicode转义序列')
                        print(f'     原始: {field_value[:100]}...')
                        
                        # 尝试解码
                        try:
                            # 先尝试直接JSON解析
                            parsed = json.loads(field_value)
                            print(f'     JSON解析成功: {type(parsed)}')
                        except json.JSONDecodeError as e:
                            print(f'     JSON解析失败: {e}')
                            
                            # 尝试Unicode解码
                            try:
                                decoded = field_value.encode().decode('unicode_escape')
                                print(f'     Unicode解码: {decoded[:100]}...')
                                
                                # 再次尝试JSON解析
                                parsed = json.loads(decoded)
                                print(f'     解码后JSON解析成功: {type(parsed)}')
                            except Exception as decode_e:
                                print(f'     Unicode解码失败: {decode_e}')
        
        if not unicode_found:
            print('\n✅ 未发现包含Unicode转义序列的记录')
        else:
            print(f'\n⚠️  发现包含Unicode转义序列的记录')

if __name__ == "__main__":
    check_unicode_escape()

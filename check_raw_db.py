#!/usr/bin/env python3
"""
直接查询数据库原始数据格式
"""

from src.fsoa.data.database import get_database_manager
import json

def check_raw_db():
    db = get_database_manager()
    
    # 直接查询原始数据
    with db.get_session() as session:
        from src.fsoa.data.database import LLMCallRecordTable
        
        records = session.query(LLMCallRecordTable).order_by(
            LLMCallRecordTable.timestamp.desc()
        ).limit(3).all()
        
        print('=== 数据库原始存储格式 ===')
        for i, record in enumerate(records):
            print(f'\n记录 {i+1}:')
            print(f'call_id: {record.call_id}')
            print(f'status: {record.status}')
            
            # 检查原始字段类型和内容
            for field_name in ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']:
                field_value = getattr(record, field_name)
                if field_value:
                    print(f'{field_name}: {type(field_value)} - {repr(field_value)[:200]}...')
                    
                    # 如果是字符串，检查是否包含Unicode转义
                    if isinstance(field_value, str):
                        if '\\u' in field_value:
                            print(f'  ⚠️  {field_name} 包含Unicode转义序列')
                            # 尝试解码
                            try:
                                decoded = field_value.encode().decode('unicode_escape')
                                print(f'  解码后: {decoded[:100]}...')
                            except Exception as e:
                                print(f'  解码失败: {e}')
                else:
                    print(f'{field_name}: None')
            print('---')

if __name__ == "__main__":
    check_raw_db()

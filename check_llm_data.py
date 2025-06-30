#!/usr/bin/env python3
"""
检查LLM调用记录中的JSON数据格式
"""

from src.fsoa.data.database import get_database_manager
import json

def check_llm_data():
    db = get_database_manager()
    records = db.get_llm_call_records(limit=3)
    
    print('=== 数据库中的实际数据 ===')
    for i, record in enumerate(records):
        print(f'\n记录 {i+1}:')
        print(f'call_id: {record.get("call_id", "N/A")}')
        print(f'status: {record.get("status", "N/A")}')
        
        # 检查各个JSON字段的实际存储格式
        for field in ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']:
            value = record.get(field)
            if value:
                print(f'{field}: {type(value)} - {repr(value)[:200]}...')
            else:
                print(f'{field}: None')
        print('---')

if __name__ == "__main__":
    check_llm_data()

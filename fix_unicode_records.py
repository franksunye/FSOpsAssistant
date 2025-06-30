#!/usr/bin/env python3
"""
修复数据库中可能存在的Unicode转义序列问题
"""

from src.fsoa.data.database import get_database_manager
import json

def fix_unicode_records():
    """修复数据库中的Unicode转义序列记录"""
    
    print("=== 修复数据库Unicode转义序列记录 ===")
    
    db = get_database_manager()
    
    with db.get_session() as session:
        from src.fsoa.data.database import LLMCallRecordTable
        
        # 查询所有记录
        records = session.query(LLMCallRecordTable).all()
        
        print(f"检查 {len(records)} 条记录...")
        
        fixed_count = 0
        json_fields = ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']
        
        for record in records:
            record_fixed = False
            
            for field_name in json_fields:
                field_value = getattr(record, field_name)
                
                # 只处理字符串类型的字段
                if field_value and isinstance(field_value, str):
                    # 检查是否包含Unicode转义序列
                    if '\\u' in field_value:
                        try:
                            # 尝试解码Unicode转义序列
                            decoded_value = field_value.encode().decode('unicode_escape')
                            
                            # 验证解码后的内容是否为有效JSON
                            parsed_json = json.loads(decoded_value)
                            
                            # 重新序列化为正常的JSON字符串
                            fixed_value = json.dumps(parsed_json, ensure_ascii=False)
                            
                            # 更新字段值
                            setattr(record, field_name, fixed_value)
                            record_fixed = True
                            
                            print(f"  修复 {record.call_id} 的 {field_name} 字段")
                            print(f"    原始: {field_value[:100]}...")
                            print(f"    修复: {fixed_value[:100]}...")
                            
                        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as e:
                            print(f"  警告: {record.call_id} 的 {field_name} 字段修复失败: {e}")
            
            if record_fixed:
                fixed_count += 1
        
        # 提交更改
        if fixed_count > 0:
            session.commit()
            print(f"\n✅ 修复完成! 共修复 {fixed_count} 条记录")
        else:
            print(f"\n✅ 未发现需要修复的记录")
        
        return fixed_count

def validate_records():
    """验证修复后的记录"""
    
    print("\n=== 验证修复结果 ===")
    
    db = get_database_manager()
    records = db.get_llm_call_records(limit=10)
    
    print(f"验证最近 {len(records)} 条记录...")
    
    all_valid = True
    
    for i, record in enumerate(records):
        print(f"\n记录 {i+1}: {record['call_id']}")
        
        for field in ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']:
            value = record.get(field)
            if value:
                if isinstance(value, dict):
                    print(f"  ✅ {field}: 字典类型，键: {list(value.keys())}")
                elif isinstance(value, str):
                    print(f"  ⚠️  {field}: 仍为字符串类型")
                    all_valid = False
                else:
                    print(f"  ❓ {field}: 其他类型 {type(value)}")
            else:
                print(f"  - {field}: None")
    
    if all_valid:
        print(f"\n✅ 所有记录验证通过")
    else:
        print(f"\n⚠️  部分记录仍需要处理")
    
    return all_valid

def show_sample_data():
    """显示示例数据"""
    
    print("\n=== 显示示例数据 ===")
    
    db = get_database_manager()
    records = db.get_llm_call_records(limit=3)
    
    for i, record in enumerate(records):
        print(f"\n记录 {i+1}: {record['call_id']}")
        
        # 显示context_data的内容
        context_data = record.get('context_data')
        if context_data and isinstance(context_data, dict):
            print(f"  Context数据:")
            for key, value in context_data.items():
                if isinstance(value, str) and len(value) > 50:
                    print(f"    {key}: {value[:50]}...")
                else:
                    print(f"    {key}: {value}")
        
        # 显示parsed_result的内容
        parsed_result = record.get('parsed_result')
        if parsed_result and isinstance(parsed_result, dict):
            print(f"  解析结果:")
            for key, value in parsed_result.items():
                if isinstance(value, str) and len(value) > 50:
                    print(f"    {key}: {value[:50]}...")
                else:
                    print(f"    {key}: {value}")

if __name__ == "__main__":
    # 执行修复
    fixed_count = fix_unicode_records()
    
    # 验证结果
    validate_records()
    
    # 显示示例数据
    show_sample_data()
    
    print(f"\n=== 修复总结 ===")
    print(f"修复记录数: {fixed_count}")
    print(f"修复完成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if fixed_count > 0:
        print(f"✅ 数据库Unicode转义序列问题已修复")
    else:
        print(f"✅ 数据库中未发现Unicode转义序列问题")

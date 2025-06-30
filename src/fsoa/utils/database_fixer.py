"""
数据库修复工具 - 修复LLM调用记录中的JSON编码问题
"""

import json
from typing import Dict, Any, Optional
from ..data.database import get_database_manager
from ..utils.logger import get_logger

logger = get_logger(__name__)


def fix_json_encoding_in_llm_records():
    """修复LLM调用记录中的JSON编码问题"""
    db = get_database_manager()
    
    try:
        with db.get_session() as session:
            from ..data.database import LLMCallRecordTable
            
            # 获取所有记录
            records = session.query(LLMCallRecordTable).all()
            
            fixed_count = 0
            total_count = len(records)
            
            print(f"开始修复 {total_count} 条LLM调用记录...")
            
            for record in records:
                record_fixed = False
                
                # 修复 parsed_result 字段
                if record.parsed_result and isinstance(record.parsed_result, str):
                    try:
                        # 尝试解析JSON字符串
                        parsed_data = json.loads(record.parsed_result)
                        record.parsed_result = parsed_data
                        record_fixed = True
                        print(f"  修复 {record.call_id} 的 parsed_result 字段")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"  警告: {record.call_id} 的 parsed_result 字段无法解析: {e}")
                
                # 修复 rule_suggestion 字段
                if record.rule_suggestion and isinstance(record.rule_suggestion, str):
                    try:
                        parsed_data = json.loads(record.rule_suggestion)
                        record.rule_suggestion = parsed_data
                        record_fixed = True
                        print(f"  修复 {record.call_id} 的 rule_suggestion 字段")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"  警告: {record.call_id} 的 rule_suggestion 字段无法解析: {e}")
                
                # 修复 final_decision 字段
                if record.final_decision and isinstance(record.final_decision, str):
                    try:
                        parsed_data = json.loads(record.final_decision)
                        record.final_decision = parsed_data
                        record_fixed = True
                        print(f"  修复 {record.call_id} 的 final_decision 字段")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"  警告: {record.call_id} 的 final_decision 字段无法解析: {e}")
                
                # 修复 context_data 字段
                if record.context_data and isinstance(record.context_data, str):
                    try:
                        parsed_data = json.loads(record.context_data)
                        record.context_data = parsed_data
                        record_fixed = True
                        print(f"  修复 {record.call_id} 的 context_data 字段")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"  警告: {record.call_id} 的 context_data 字段无法解析: {e}")
                
                if record_fixed:
                    fixed_count += 1
            
            # 提交更改
            session.commit()
            
            print(f"修复完成! 共修复 {fixed_count} 条记录")
            return fixed_count
            
    except Exception as e:
        logger.error(f"修复数据库记录失败: {e}")
        print(f"修复失败: {e}")
        return 0


def validate_json_fields():
    """验证JSON字段的数据类型"""
    db = get_database_manager()
    
    try:
        with db.get_session() as session:
            from ..data.database import LLMCallRecordTable
            
            records = session.query(LLMCallRecordTable).all()
            
            print(f"验证 {len(records)} 条记录的JSON字段...")
            
            issues = []
            
            for record in records:
                # 检查 parsed_result
                if record.parsed_result:
                    if isinstance(record.parsed_result, str):
                        issues.append(f"{record.call_id}: parsed_result 是字符串类型")
                    elif not isinstance(record.parsed_result, dict):
                        issues.append(f"{record.call_id}: parsed_result 类型异常: {type(record.parsed_result)}")
                
                # 检查 rule_suggestion
                if record.rule_suggestion:
                    if isinstance(record.rule_suggestion, str):
                        issues.append(f"{record.call_id}: rule_suggestion 是字符串类型")
                    elif not isinstance(record.rule_suggestion, dict):
                        issues.append(f"{record.call_id}: rule_suggestion 类型异常: {type(record.rule_suggestion)}")
                
                # 检查 final_decision
                if record.final_decision:
                    if isinstance(record.final_decision, str):
                        issues.append(f"{record.call_id}: final_decision 是字符串类型")
                    elif not isinstance(record.final_decision, dict):
                        issues.append(f"{record.call_id}: final_decision 类型异常: {type(record.final_decision)}")
                
                # 检查 context_data
                if record.context_data:
                    if isinstance(record.context_data, str):
                        issues.append(f"{record.call_id}: context_data 是字符串类型")
                    elif not isinstance(record.context_data, dict):
                        issues.append(f"{record.call_id}: context_data 类型异常: {type(record.context_data)}")
            
            if issues:
                print(f"发现 {len(issues)} 个问题:")
                for issue in issues[:10]:  # 只显示前10个问题
                    print(f"  - {issue}")
                if len(issues) > 10:
                    print(f"  ... 还有 {len(issues) - 10} 个问题")
            else:
                print("所有JSON字段类型正确!")
            
            return len(issues)
            
    except Exception as e:
        logger.error(f"验证JSON字段失败: {e}")
        print(f"验证失败: {e}")
        return -1


def show_sample_records(count: int = 3):
    """显示示例记录的JSON字段内容"""
    db = get_database_manager()
    
    try:
        with db.get_session() as session:
            from ..data.database import LLMCallRecordTable
            
            records = session.query(LLMCallRecordTable).order_by(
                LLMCallRecordTable.timestamp.desc()
            ).limit(count).all()
            
            print(f"最近 {len(records)} 条记录的JSON字段内容:")
            
            for i, record in enumerate(records, 1):
                print(f"\n=== 记录 {i}: {record.call_id} ===")
                print(f"时间: {record.timestamp}")
                print(f"商机ID: {record.opportunity_id}")
                print(f"状态: {record.status}")
                
                # 显示 parsed_result
                if record.parsed_result:
                    print(f"parsed_result 类型: {type(record.parsed_result)}")
                    if isinstance(record.parsed_result, dict):
                        print(f"parsed_result 内容: {record.parsed_result}")
                    else:
                        print(f"parsed_result 原始: {str(record.parsed_result)[:200]}...")
                
                # 显示 rule_suggestion
                if record.rule_suggestion:
                    print(f"rule_suggestion 类型: {type(record.rule_suggestion)}")
                    if isinstance(record.rule_suggestion, dict):
                        print(f"rule_suggestion 内容: {record.rule_suggestion}")
                    else:
                        print(f"rule_suggestion 原始: {str(record.rule_suggestion)[:200]}...")
                
                # 显示 final_decision
                if record.final_decision:
                    print(f"final_decision 类型: {type(record.final_decision)}")
                    if isinstance(record.final_decision, dict):
                        print(f"final_decision 内容: {record.final_decision}")
                    else:
                        print(f"final_decision 原始: {str(record.final_decision)[:200]}...")
            
    except Exception as e:
        logger.error(f"显示示例记录失败: {e}")
        print(f"显示失败: {e}")


if __name__ == "__main__":
    print("=== 数据库修复工具 ===")
    print()
    
    # 1. 验证当前状态
    print("1. 验证当前JSON字段状态...")
    issues_count = validate_json_fields()
    print()
    
    # 2. 显示示例记录
    print("2. 显示示例记录...")
    show_sample_records(2)
    print()
    
    # 3. 询问是否修复
    if issues_count > 0:
        response = input(f"发现 {issues_count} 个问题，是否修复? (y/N): ")
        if response.lower() == 'y':
            print("3. 开始修复...")
            fixed_count = fix_json_encoding_in_llm_records()
            print()
            
            # 4. 再次验证
            print("4. 修复后验证...")
            validate_json_fields()
        else:
            print("跳过修复")
    else:
        print("3. 无需修复")

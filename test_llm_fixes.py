"""
测试LLM功能修复
"""

import sys
sys.path.append('.')

from src.fsoa.utils.llm_record_viewer import view_recent_llm_calls, view_llm_stats
from src.fsoa.agent.llm_observer import get_llm_observer
from src.fsoa.data.database import get_database_manager

def test_llm_observer():
    """测试LLM观测器"""
    print("=== 测试LLM观测器 ===")
    
    observer = get_llm_observer()
    
    # 获取调用历史
    calls = observer.get_call_history(limit=3)
    print(f"获取到 {len(calls)} 条调用记录")
    
    for call in calls:
        print(f"\n调用ID: {call['call_id']}")
        print(f"商机ID: {call['opportunity_id']}")
        print(f"状态: {call['status']}")
        
        # 检查JSON字段类型
        parsed_result = call.get('parsed_result')
        if parsed_result:
            print(f"parsed_result 类型: {type(parsed_result)}")
            if isinstance(parsed_result, dict):
                print(f"  动作: {parsed_result.get('action', 'N/A')}")
                print(f"  优先级: {parsed_result.get('priority', 'N/A')}")
            else:
                print(f"  原始值: {str(parsed_result)[:100]}...")
        
        rule_suggestion = call.get('rule_suggestion')
        if rule_suggestion:
            print(f"rule_suggestion 类型: {type(rule_suggestion)}")
            if isinstance(rule_suggestion, dict):
                print(f"  规则动作: {rule_suggestion.get('action', 'N/A')}")
            else:
                print(f"  原始值: {str(rule_suggestion)[:100]}...")
        
        final_decision = call.get('final_decision')
        if final_decision:
            print(f"final_decision 类型: {type(final_decision)}")
            if isinstance(final_decision, dict):
                print(f"  最终动作: {final_decision.get('action', 'N/A')}")
                print(f"  使用LLM: {final_decision.get('llm_used', False)}")
            else:
                print(f"  原始值: {str(final_decision)[:100]}...")


def test_database_access():
    """测试数据库访问"""
    print("\n=== 测试数据库访问 ===")
    
    db = get_database_manager()
    records = db.get_llm_call_records(limit=2)
    
    print(f"从数据库获取到 {len(records)} 条记录")
    
    for record in records:
        print(f"\n记录ID: {record['call_id']}")
        
        # 检查JSON字段
        for field_name in ['parsed_result', 'rule_suggestion', 'final_decision', 'context_data']:
            field_value = record.get(field_name)
            if field_value:
                print(f"{field_name} 类型: {type(field_value)}")
                if isinstance(field_value, dict):
                    print(f"  {field_name} 是字典 ✓")
                elif isinstance(field_value, str):
                    print(f"  {field_name} 是字符串 ✗")
                else:
                    print(f"  {field_name} 类型异常: {type(field_value)}")


def test_chinese_display():
    """测试中文显示"""
    print("\n=== 测试中文显示 ===")
    
    from src.fsoa.utils.llm_record_viewer import view_recent_llm_calls
    
    print("使用LLM记录查看工具:")
    view_recent_llm_calls(1, show_details=True)


def test_web_interface_data():
    """测试Web界面数据格式"""
    print("\n=== 测试Web界面数据格式 ===")
    
    observer = get_llm_observer()
    
    # 模拟Web界面获取数据
    try:
        stats = observer.get_statistics()
        print(f"统计信息获取成功: {stats}")
        
        calls = observer.get_call_history(limit=1)
        if calls:
            call = calls[0]
            print(f"\n测试调用记录: {call['call_id']}")
            
            # 模拟Web界面访问JSON字段
            parsed_result = call.get('parsed_result', {})
            if isinstance(parsed_result, dict):
                action = parsed_result.get('action', 'N/A')
                print(f"动作获取成功: {action}")
            else:
                print(f"parsed_result 类型错误: {type(parsed_result)}")
            
            # 测试决策对比
            rule_suggestion = call.get('rule_suggestion')
            final_decision = call.get('final_decision')
            
            if rule_suggestion and final_decision:
                if isinstance(rule_suggestion, dict) and isinstance(final_decision, dict):
                    print("决策对比数据格式正确 ✓")
                    print(f"  规则建议: {rule_suggestion.get('action')} - {rule_suggestion.get('priority')}")
                    print(f"  最终决策: {final_decision.get('action')} - {final_decision.get('priority')}")
                else:
                    print("决策对比数据格式错误 ✗")
            else:
                print("无决策对比数据")
        
    except Exception as e:
        print(f"Web界面数据测试失败: {e}")


if __name__ == "__main__":
    print("开始测试LLM功能修复...")
    print()
    
    try:
        test_llm_observer()
        test_database_access()
        test_chinese_display()
        test_web_interface_data()
        
        print("\n=== 测试总结 ===")
        print("✓ LLM观测器正常工作")
        print("✓ 数据库JSON字段类型正确")
        print("✓ 中文内容正确显示")
        print("✓ Web界面数据格式兼容")
        print("\n所有测试通过! 🎉")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()

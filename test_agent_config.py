#!/usr/bin/env python3
"""
测试Agent配置功能
验证系统设置页面的Agent配置是否正确保存和读取
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.fsoa.data.database import get_database_manager
from src.fsoa.agent.decision import create_decision_engine
from src.fsoa.agent.llm import get_deepseek_client


def test_agent_config():
    """测试Agent配置功能"""
    print("🧪 测试Agent配置功能")
    print("=" * 50)
    
    # 1. 获取数据库管理器
    db_manager = get_database_manager()
    
    # 2. 测试读取当前配置
    print("\n📖 当前配置:")
    configs = db_manager.get_all_system_configs()
    agent_configs = {
        "agent_execution_interval": configs.get("agent_execution_interval", "未设置"),
        "use_llm_optimization": configs.get("use_llm_optimization", "未设置"),
        "llm_temperature": configs.get("llm_temperature", "未设置"),
        "agent_max_retries": configs.get("agent_max_retries", "未设置"),
    }
    
    for key, value in agent_configs.items():
        print(f"  {key}: {value}")
    
    # 3. 测试修改配置
    print("\n✏️ 测试修改配置:")
    test_configs = [
        ("use_llm_optimization", "false", "禁用LLM优化"),
        ("llm_temperature", "0.5", "设置温度为0.5"),
        ("agent_execution_interval", "30", "设置执行间隔为30分钟"),
        ("agent_max_retries", "5", "设置最大重试次数为5"),
    ]
    
    for key, value, description in test_configs:
        success = db_manager.set_system_config(key, value, description)
        print(f"  {description}: {'✅ 成功' if success else '❌ 失败'}")
    
    # 4. 验证配置是否生效
    print("\n🔍 验证配置是否生效:")
    
    # 验证数据库中的值
    updated_configs = db_manager.get_all_system_configs()
    print("  数据库中的值:")
    for key, _, _ in test_configs:
        db_value = updated_configs.get(key, "未找到")
        print(f"    {key}: {db_value}")
    
    # 验证决策引擎是否读取到新配置
    print("  决策引擎配置:")
    try:
        decision_engine = create_decision_engine()
        print(f"    决策模式: {decision_engine.mode}")
        
        # 检查LLM优化是否被禁用
        use_llm_config = db_manager.get_system_config("use_llm_optimization")
        use_llm = use_llm_config and use_llm_config.lower() == "true" if use_llm_config else False
        print(f"    LLM优化启用: {use_llm}")
        
    except Exception as e:
        print(f"    ❌ 决策引擎测试失败: {e}")
    
    # 验证LLM客户端是否读取到新的温度参数
    print("  LLM客户端配置:")
    try:
        # 这里我们无法直接测试温度参数，因为它在调用时才读取
        # 但我们可以验证配置读取逻辑
        temperature_config = db_manager.get_system_config("llm_temperature")
        temperature = float(temperature_config) if temperature_config else 0.1
        print(f"    温度参数: {temperature}")
        
    except Exception as e:
        print(f"    ❌ LLM配置测试失败: {e}")
    
    # 5. 恢复原始配置
    print("\n🔄 恢复原始配置:")
    original_configs = [
        ("use_llm_optimization", "true", "启用LLM优化"),
        ("llm_temperature", "0.1", "设置温度为0.1"),
        ("agent_execution_interval", "60", "设置执行间隔为60分钟"),
        ("agent_max_retries", "3", "设置最大重试次数为3"),
    ]
    
    for key, value, description in original_configs:
        success = db_manager.set_system_config(key, value, description)
        print(f"  {description}: {'✅ 成功' if success else '❌ 失败'}")
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    test_agent_config()

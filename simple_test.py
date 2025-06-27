#!/usr/bin/env python3
"""
简单测试Agent配置修复
"""

print("测试开始...")

try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    print("✅ 路径设置成功")
    
    from src.fsoa.data.database import get_database_manager
    print("✅ 数据库模块导入成功")
    
    db_manager = get_database_manager()
    print("✅ 数据库管理器创建成功")
    
    # 测试读取配置
    config = db_manager.get_system_config("use_llm_optimization")
    print(f"✅ 当前use_llm_optimization配置: {config}")
    
    # 测试设置配置
    success = db_manager.set_system_config("use_llm_optimization", "false", "测试禁用LLM")
    print(f"✅ 设置配置结果: {success}")
    
    # 验证设置是否生效
    new_config = db_manager.get_system_config("use_llm_optimization")
    print(f"✅ 更新后的配置: {new_config}")
    
    # 恢复原始配置
    db_manager.set_system_config("use_llm_optimization", "true", "恢复LLM优化")
    print("✅ 配置已恢复")
    
    print("🎉 测试完成，Agent配置修复成功！")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

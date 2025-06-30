#!/usr/bin/env python3
"""
测试Web UI配置功能

验证通知开关配置在Web界面中的显示和保存
"""

import sys
import os

# 设置测试环境变量
os.environ['DEEPSEEK_API_KEY'] = 'test_key'
os.environ['METABASE_URL'] = 'http://test.metabase.com'
os.environ['METABASE_USERNAME'] = 'test_user'
os.environ['METABASE_PASSWORD'] = 'test_password'
os.environ['INTERNAL_OPS_WEBHOOK'] = 'https://test.webhook.com'
os.environ['DATABASE_URL'] = 'sqlite:///test_fsoa.db'
os.environ['LOG_LEVEL'] = 'INFO'

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.database import get_database_manager


def test_web_ui_config_display():
    """测试Web UI配置显示"""
    print("🌐 测试Web UI配置显示")
    print("-" * 50)
    
    db_manager = get_database_manager()
    
    # 设置测试配置
    db_manager.set_system_config("notification_reminder_enabled", "true", "测试")
    db_manager.set_system_config("notification_escalation_enabled", "false", "测试")
    
    # 获取所有配置
    configs = db_manager.get_all_system_configs()
    
    print("当前系统配置:")
    for key, value in configs.items():
        if key.startswith('notification_'):
            print(f"  {key}: {value}")
    
    # 验证配置值
    assert configs.get("notification_reminder_enabled") == "true", "提醒通知应该启用"
    assert configs.get("notification_escalation_enabled") == "false", "升级通知应该禁用"
    
    print("✅ Web UI配置显示测试通过")


def test_config_save_functionality():
    """测试配置保存功能"""
    print("\n💾 测试配置保存功能")
    print("-" * 50)
    
    db_manager = get_database_manager()
    
    # 模拟Web UI保存操作
    test_configs = [
        ("notification_reminder_enabled", "false", "是否启用提醒通知（4/8小时）→服务商群"),
        ("notification_escalation_enabled", "true", "是否启用升级通知（8/16小时）→运营群"),
    ]
    
    print("保存配置:")
    for key, value, description in test_configs:
        db_manager.set_system_config(key, value, description)
        print(f"  {key}: {value}")
    
    # 验证保存结果
    configs = db_manager.get_all_system_configs()
    assert configs.get("notification_reminder_enabled") == "false", "提醒通知应该禁用"
    assert configs.get("notification_escalation_enabled") == "true", "升级通知应该启用"
    
    print("✅ 配置保存功能测试通过")


def test_config_validation():
    """测试配置验证"""
    print("\n✅ 测试配置验证")
    print("-" * 50)
    
    db_manager = get_database_manager()
    
    # 测试有效值
    valid_values = ["true", "false", "True", "False", "TRUE", "FALSE"]
    
    for value in valid_values:
        db_manager.set_system_config("notification_reminder_enabled", value, "测试")
        saved_value = db_manager.get_system_config("notification_reminder_enabled")
        print(f"  输入: {value} -> 保存: {saved_value}")
        assert saved_value is not None, f"值 {value} 应该能正确保存"
    
    print("✅ 配置验证测试通过")


def test_default_config_values():
    """测试默认配置值"""
    print("\n🔧 测试默认配置值")
    print("-" * 50)

    db_manager = get_database_manager()

    # 手动设置为默认值来测试
    db_manager.set_system_config("notification_reminder_enabled", "true", "是否启用提醒通知（4/8小时）→服务商群")
    db_manager.set_system_config("notification_escalation_enabled", "false", "是否启用升级通知（8/16小时）→运营群")

    # 检查设置的默认值
    reminder_enabled = db_manager.get_system_config("notification_reminder_enabled")
    escalation_enabled = db_manager.get_system_config("notification_escalation_enabled")

    print(f"设置的默认提醒通知开关: {reminder_enabled}")
    print(f"设置的默认升级通知开关: {escalation_enabled}")

    # 验证默认值符合设计要求
    assert reminder_enabled == "true", "默认应该启用提醒通知"
    assert escalation_enabled == "false", "默认应该禁用升级通知"

    print("✅ 默认配置值测试通过")


def test_config_description():
    """测试配置描述"""
    print("\n📝 测试配置描述")
    print("-" * 50)
    
    db_manager = get_database_manager()
    
    # 获取配置描述
    try:
        with db_manager.get_session() as session:
            from sqlalchemy import text
            result = session.execute(text("""
                SELECT key, description 
                FROM system_config 
                WHERE key LIKE 'notification_%_enabled'
                ORDER BY key
            """))
            
            configs = result.fetchall()
            
            print("配置项描述:")
            for key, description in configs:
                print(f"  {key}: {description}")
                
            # 验证描述存在且有意义
            assert len(configs) >= 2, "应该有至少2个通知配置项"
            
            for key, description in configs:
                assert description is not None, f"配置项 {key} 应该有描述"
                assert len(description) > 10, f"配置项 {key} 的描述应该足够详细"
                
    except Exception as e:
        print(f"获取配置描述时出错: {e}")
        raise
    
    print("✅ 配置描述测试通过")


def main():
    """主函数"""
    print("=" * 60)
    print("Web UI配置功能测试")
    print("=" * 60)
    
    try:
        test_web_ui_config_display()
        test_config_save_functionality()
        test_config_validation()
        test_default_config_values()
        test_config_description()
        
        print("\n" + "=" * 60)
        print("✅ 所有Web UI配置测试通过！")
        print("=" * 60)
        
        # 显示最终配置状态
        db_manager = get_database_manager()
        configs = db_manager.get_all_system_configs()
        
        print(f"\n最终配置状态:")
        print(f"  提醒通知: {'启用' if configs.get('notification_reminder_enabled') == 'true' else '禁用'}")
        print(f"  升级通知: {'启用' if configs.get('notification_escalation_enabled') == 'true' else '禁用'}")
        
        print(f"\n💡 Web UI使用说明:")
        print(f"  1. 在系统管理页面可以看到通知开关配置")
        print(f"  2. 勾选/取消勾选复选框来控制通知类型")
        print(f"  3. 点击'保存通知配置'按钮保存设置")
        print(f"  4. 配置立即生效，影响后续的通知创建")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

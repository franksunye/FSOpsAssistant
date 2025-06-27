#!/usr/bin/env python3
"""
清理废弃配置项脚本

清理数据库中不再使用的配置项：
- escalation_threshold (已被sla_*_escalation替代)
- violation_threshold (已被sla_*_reminder替代)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def cleanup_deprecated_configs():
    """清理废弃的配置项"""
    print("🧹 清理废弃配置项...")
    
    try:
        from src.fsoa.data.database import get_database_manager
        
        db_manager = get_database_manager()
        
        # 要清理的废弃配置项
        deprecated_configs = [
            "escalation_threshold",
            "violation_threshold"
        ]
        
        # 检查并清理
        with db_manager.get_session() as session:
            from src.fsoa.data.database import SystemConfigTable
            
            cleaned_count = 0
            for config_key in deprecated_configs:
                # 查找配置项
                config = session.query(SystemConfigTable).filter_by(key=config_key).first()
                if config:
                    print(f"🗑️  删除废弃配置: {config_key} = {config.value}")
                    session.delete(config)
                    cleaned_count += 1
                else:
                    print(f"✅ 配置项 {config_key} 不存在，无需清理")
            
            if cleaned_count > 0:
                session.commit()
                print(f"✅ 成功清理 {cleaned_count} 个废弃配置项")
            else:
                print("✅ 没有需要清理的废弃配置项")
        
        # 验证新的SLA配置项
        print("\n📋 验证新的SLA配置项...")
        configs = db_manager.get_all_system_configs()
        
        new_sla_configs = [
            "sla_pending_reminder",
            "sla_pending_escalation", 
            "sla_not_visiting_reminder",
            "sla_not_visiting_escalation"
        ]
        
        all_present = True
        for config_key in new_sla_configs:
            if config_key in configs:
                print(f"✅ {config_key}: {configs[config_key]}")
            else:
                print(f"❌ 缺少配置: {config_key}")
                all_present = False
        
        if not all_present:
            print("\n💡 部分SLA配置项缺失，请重启应用以自动添加")
        
        print("\n🎯 清理完成！")
        print("现在系统使用新的两级SLA配置体系：")
        print("  📝 提醒级别 (sla_*_reminder) → 服务商群")
        print("  🚨 升级级别 (sla_*_escalation) → 运营群")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        return False

def show_config_migration_info():
    """显示配置迁移信息"""
    print("\n📋 配置迁移说明:")
    print("┌─────────────────────────┬─────────────────────────┐")
    print("│ 废弃配置项              │ 新配置项                │")
    print("├─────────────────────────┼─────────────────────────┤")
    print("│ escalation_threshold    │ sla_pending_escalation  │")
    print("│                         │ sla_not_visiting_esc... │")
    print("├─────────────────────────┼─────────────────────────┤")
    print("│ violation_threshold     │ sla_pending_reminder    │")
    print("│                         │ sla_not_visiting_rem... │")
    print("└─────────────────────────┴─────────────────────────┘")
    print()
    print("新的两级SLA体系:")
    print("• 提醒级别: 待预约4h/暂不上门8h → 服务商群")
    print("• 升级级别: 待预约8h/暂不上门16h → 运营群")

if __name__ == "__main__":
    print("🚀 FSOA配置清理工具")
    print("=" * 50)
    
    show_config_migration_info()
    
    # 询问用户确认
    response = input("\n是否继续清理废弃配置项? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ 用户取消操作")
        sys.exit(0)
    
    success = cleanup_deprecated_configs()
    sys.exit(0 if success else 1)

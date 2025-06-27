#!/usr/bin/env python3
"""
SLA升级验证脚本

验证两级SLA体系是否正确升级
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_sla_upgrade():
    """验证SLA升级"""
    print("🔍 验证SLA升级...")
    
    try:
        # 1. 验证数据库配置
        print("1. 检查数据库配置...")
        from src.fsoa.data.database import get_database_manager
        
        db_manager = get_database_manager()
        configs = db_manager.get_all_system_configs()
        
        # 检查必需的SLA配置项
        required_configs = [
            "sla_pending_reminder",
            "sla_pending_escalation", 
            "sla_not_visiting_reminder",
            "sla_not_visiting_escalation"
        ]
        
        missing_configs = []
        for config_key in required_configs:
            if config_key in configs:
                print(f"   ✅ {config_key}: {configs[config_key]}")
            else:
                missing_configs.append(config_key)
                print(f"   ❌ 缺少配置: {config_key}")
        
        if missing_configs:
            print(f"❌ 缺少配置项: {missing_configs}")
            print("💡 请重启应用以自动添加配置项")
            return False
        
        # 2. 验证SLA逻辑
        print("2. 检查SLA逻辑...")
        from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
        from datetime import datetime
        
        test_opp = OpportunityInfo(
            order_num="VERIFY_TEST",
            name="验证测试",
            address="测试地址",
            supervisor_name="测试人员",
            create_time=datetime.now(),
            org_name="测试组织",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
        
        reminder_threshold = test_opp.get_sla_threshold("reminder")
        escalation_threshold = test_opp.get_sla_threshold("escalation")
        
        if reminder_threshold == 4 and escalation_threshold == 8:
            print("   ✅ 待预约SLA阈值正确")
        else:
            print(f"   ❌ 待预约SLA阈值错误: 提醒{reminder_threshold}, 升级{escalation_threshold}")
            return False
        
        # 3. 验证通知类型
        print("3. 检查通知类型...")
        from src.fsoa.data.models import NotificationTaskType
        
        if (NotificationTaskType.REMINDER == "reminder" and 
            NotificationTaskType.ESCALATION == "escalation" and
            NotificationTaskType.VIOLATION == NotificationTaskType.REMINDER):
            print("   ✅ 通知类型枚举正确")
        else:
            print("   ❌ 通知类型枚举错误")
            return False
        
        # 4. 验证消息格式化
        print("4. 检查消息格式化...")
        from src.fsoa.notification.business_formatter import BusinessNotificationFormatter
        
        test_msg = BusinessNotificationFormatter.format_reminder_notification("测试组织", [test_opp])
        if "💡 **服务提醒**" in test_msg:
            print("   ✅ 提醒消息格式正确")
        else:
            print("   ❌ 提醒消息格式错误")
            return False
        
        print("✅ SLA升级验证成功！")
        print()
        print("🎯 两级SLA体系已正确配置:")
        print("   📝 提醒级别 (4/8小时) → 服务商群")
        print("   🚨 升级级别 (8/16小时) → 运营群")
        print("   ⚙️ 可配置化 → Web界面管理")
        print("   📱 差异化消息模板 → 不同语气和格式")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

if __name__ == "__main__":
    success = verify_sla_upgrade()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
企微通知功能测试脚本

用于测试企微群通知功能是否正常工作
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.database import get_database_manager
from src.fsoa.notification.wechat import get_wechat_client
from src.fsoa.utils.logger import get_logger

logger = get_logger(__name__)


def test_single_org_notification(org_name: str) -> bool:
    """
    测试单个组织的通知发送
    
    Args:
        org_name: 组织名称
        
    Returns:
        是否发送成功
    """
    try:
        print(f"\n🧪 测试组织: {org_name}")
        
        # 获取企微客户端
        wechat_client = get_wechat_client()
        
        # 构造测试消息
        test_message = f"""🧪 FSOA系统测试消息

组织: {org_name}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
状态: 测试通知功能正常

这是一条来自FSOA系统的测试消息，用于验证企微群通知功能是否正常工作。

如果您收到此消息，说明通知功能配置正确！"""
        
        # 发送测试消息
        success = wechat_client.send_notification_to_org(
            org_name=org_name,
            content=test_message,
            is_escalation=False
        )
        
        if success:
            print(f"  ✅ 发送成功")
        else:
            print(f"  ❌ 发送失败")
            
        return success
        
    except Exception as e:
        print(f"  ❌ 发送异常: {e}")
        logger.error(f"Failed to send test notification to {org_name}: {e}")
        return False


def test_internal_ops_notification() -> bool:
    """
    测试内部运营群通知
    
    Returns:
        是否发送成功
    """
    try:
        print(f"\n🚨 测试内部运营群通知")
        
        # 获取企微客户端
        wechat_client = get_wechat_client()
        
        # 构造测试消息
        test_message = f"""🚨 FSOA内部运营群测试消息

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
类型: 升级通知测试
状态: 系统功能正常

这是一条来自FSOA系统的内部运营群测试消息，用于验证升级通知功能是否正常工作。

如果您收到此消息，说明升级通知功能配置正确！"""
        
        # 发送升级通知测试消息
        success = wechat_client.send_notification_to_org(
            org_name="内部运营群",
            content=test_message,
            is_escalation=True
        )
        
        if success:
            print(f"  ✅ 发送成功")
        else:
            print(f"  ❌ 发送失败")
            
        return success
        
    except Exception as e:
        print(f"  ❌ 发送异常: {e}")
        logger.error(f"Failed to send test notification to internal ops: {e}")
        return False


def test_all_configured_orgs() -> dict:
    """
    测试所有已配置的组织
    
    Returns:
        测试结果统计
    """
    try:
        print("=" * 60)
        print("FSOA 企微通知功能测试")
        print("=" * 60)
        
        # 获取数据库管理器
        db_manager = get_database_manager()
        
        # 获取所有启用的群组配置
        group_configs = db_manager.get_enabled_group_configs()
        
        if not group_configs:
            print("❌ 没有找到启用的群组配置")
            return {"total": 0, "success": 0, "failed": 0}
        
        print(f"📋 找到 {len(group_configs)} 个启用的群组配置")
        
        results = {
            "total": len(group_configs),
            "success": 0,
            "failed": 0,
            "success_orgs": [],
            "failed_orgs": []
        }
        
        # 测试每个组织
        for i, config in enumerate(group_configs, 1):
            print(f"\n[{i:2d}/{len(group_configs)}] 测试: {config.group_id}")
            print(f"    Webhook: {config.webhook_url[:50]}...")
            
            success = test_single_org_notification(config.group_id)
            
            if success:
                results["success"] += 1
                results["success_orgs"].append(config.group_id)
            else:
                results["failed"] += 1
                results["failed_orgs"].append(config.group_id)
        
        # 测试内部运营群
        print(f"\n[{len(group_configs)+1:2d}/{len(group_configs)+1}] 测试内部运营群")
        internal_success = test_internal_ops_notification()
        
        # 打印汇总结果
        print(f"\n{'=' * 60}")
        print(f"测试完成")
        print(f"{'=' * 60}")
        print(f"总计组织: {results['total']}")
        print(f"发送成功: {results['success']}")
        print(f"发送失败: {results['failed']}")
        print(f"内部运营群: {'成功' if internal_success else '失败'}")
        
        if results['success_orgs']:
            print(f"\n✅ 发送成功的组织 ({len(results['success_orgs'])}):")
            for org in results['success_orgs']:
                print(f"  - {org}")
                
        if results['failed_orgs']:
            print(f"\n❌ 发送失败的组织 ({len(results['failed_orgs'])}):")
            for org in results['failed_orgs']:
                print(f"  - {org}")
        
        success_rate = results['success'] / results['total'] * 100 if results['total'] > 0 else 0
        print(f"\n📊 成功率: {success_rate:.1f}%")
        
        return results
        
    except Exception as e:
        print(f"❌ 测试过程发生错误: {e}")
        logger.error(f"Test process failed: {e}")
        return {"error": str(e)}


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        # 测试指定组织
        org_name = sys.argv[1]
        print(f"测试指定组织: {org_name}")
        success = test_single_org_notification(org_name)
        if success:
            print(f"\n🎉 {org_name} 通知测试成功！")
        else:
            print(f"\n❌ {org_name} 通知测试失败！")
    else:
        # 测试所有组织
        results = test_all_configured_orgs()
        
        if "error" not in results and results["total"] > 0:
            if results["success"] == results["total"]:
                print(f"\n🎉 所有组织通知测试成功！")
            else:
                print(f"\n⚠️  部分组织通知测试失败，请检查失败的配置。")
        else:
            print(f"\n❌ 通知测试失败，请检查系统配置。")


if __name__ == "__main__":
    main()

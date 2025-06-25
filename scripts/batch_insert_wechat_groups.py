#!/usr/bin/env python3
"""
批量插入企微群配置脚本

使用方法:
1. 直接运行脚本，使用预定义的组织列表
2. 或者修改 ORG_NAMES 列表来自定义组织名称

所有组织将使用统一的webhook地址
"""

import sys
import os
from datetime import datetime
from typing import List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.database import get_database_manager
from src.fsoa.utils.logger import get_logger

logger = get_logger(__name__)

# 真实的组织名称和对应的企微群webhook地址映射
ORG_WEBHOOK_MAPPING = {
    "北京经常亮工程技术有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=44b3d3db-009e-4477-bdbb-88832b232155",
    "虹途控股（北京）有限责任公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0cd6ba04-719d-4817-a8a5-4034c2e4781d",
    "北京顺建为安工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b81aae61-820c-4123-8ed7-0287540be82d",
    "北京九鼎建工科技工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=c6f36d8e-6b06-4614-9869-a095168de0dc",
    "北京久盾宏盛建筑工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2ea71190-53b6-46ff-ad83-9d249d9d67e3",
    "三河市中豫防水工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=8a3c889a-1109-477c-8bd8-bdb3ca8599ce",
    "北京恒润万通防水工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=77214359-c515-4463-a8d8-a80d691437d1",
    "北京浩圣科技有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=23f3fac2-5390-45e8-b54b-619b025e335a",
    "北京华夏精程防水工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=d6958739-31d9-4cfb-9ef0-238ff003061d",
    "北京腾飞瑞欧建筑装饰有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=d60d7366-e66d-4202-88d3-bd87f43f7cab",
    "云尚虹（北京）建筑工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=1f383a88-107a-4760-a455-f00297203675",
    "北京博远恒泰装饰装修有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a7696a0a-a392-412a-a5b6-ed34486ea6a0",
    "北京华庭装饰工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=9f0621da-2e4c-484b-b1f9-b65bcdd48cee",
    "北京德客声商贸有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=4ea9922b-1333-4e34-9fca-62cec5408c73",
    "北京虹象防水工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b61d1232-ddfd-4cc4-81ed-f8f6b9cdc7b9",
    "北京建君盛华技术服务有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b72b9e1d-1c82-4be6-8b58-239b2f941570",
    "北京怀军防水工程有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=09a26589-f1b2-4d1c-b27d-01703ec32820",
    "北京盛达洪雨防水技术有限公司": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=32aedd2b-ec5a-4fd8-a1bf-8a1e1a16ed6c",
}


def clear_all_group_configs(dry_run: bool = False) -> dict:
    """
    清理所有群组配置

    Args:
        dry_run: 是否为试运行模式

    Returns:
        包含操作结果的字典
    """
    try:
        db_manager = get_database_manager()
        existing_configs = db_manager.get_group_configs()

        if not existing_configs:
            print("数据库中没有群组配置需要清理")
            return {"cleared_count": 0}

        print(f"找到 {len(existing_configs)} 个现有配置需要清理:")
        for config in existing_configs:
            print(f"  - {config.group_id} ({config.name})")

        if not dry_run:
            # 实际删除配置
            from src.fsoa.data.database import GroupConfigTable
            with db_manager.get_session() as session:
                session.query(GroupConfigTable).delete()
                session.commit()
            print(f"✅ 已清理 {len(existing_configs)} 个配置")
        else:
            print(f"🔄 将清理 {len(existing_configs)} 个配置 (试运行)")

        return {"cleared_count": len(existing_configs)}

    except Exception as e:
        logger.error(f"Failed to clear group configs: {e}")
        print(f"❌ 清理配置失败: {e}")
        return {"error": str(e)}


def batch_insert_wechat_groups(org_webhook_mapping: dict,
                              skip_existing: bool = True, dry_run: bool = False) -> dict:
    """
    批量插入企微群配置

    Args:
        org_webhook_mapping: 组织名称到webhook地址的映射字典
        skip_existing: 是否跳过已存在的配置
        dry_run: 是否为试运行模式（不实际插入数据）

    Returns:
        包含操作结果的字典
    """
    try:
        db_manager = get_database_manager()

        # 获取现有配置
        existing_configs = db_manager.get_group_configs()
        existing_org_names = {config.group_id for config in existing_configs}

        results = {
            "total_orgs": len(org_webhook_mapping),
            "existing_count": 0,
            "created_count": 0,
            "updated_count": 0,
            "failed_count": 0,
            "created_orgs": [],
            "updated_orgs": [],
            "skipped_orgs": [],
            "failed_orgs": []
        }

        print(f"{'=' * 60}")
        print(f"批量插入企微群配置")
        print(f"{'=' * 60}")
        print(f"目标组织数量: {len(org_webhook_mapping)}")
        print(f"跳过已存在: {skip_existing}")
        print(f"试运行模式: {dry_run}")
        print(f"{'=' * 60}")

        for i, (org_name, webhook_url) in enumerate(org_webhook_mapping.items(), 1):
            print(f"\n[{i:2d}/{len(org_webhook_mapping)}] 处理组织: {org_name}")
            print(f"    Webhook: {webhook_url[:50]}...")

            try:
                if org_name in existing_org_names:
                    results["existing_count"] += 1
                    if skip_existing:
                        print(f"  ⏭️  跳过 (已存在)")
                        results["skipped_orgs"].append(org_name)
                        continue
                    else:
                        # 更新现有配置
                        if not dry_run:
                            config = db_manager.create_or_update_group_config(
                                group_id=org_name,
                                name=org_name,
                                webhook_url=webhook_url,
                                enabled=True
                            )
                            if config:
                                print(f"  ✅ 更新成功")
                                results["updated_count"] += 1
                                results["updated_orgs"].append(org_name)
                            else:
                                print(f"  ❌ 更新失败")
                                results["failed_count"] += 1
                                results["failed_orgs"].append(org_name)
                        else:
                            print(f"  🔄 将更新 (试运行)")
                            results["updated_count"] += 1
                            results["updated_orgs"].append(org_name)
                else:
                    # 创建新配置
                    if not dry_run:
                        config = db_manager.create_or_update_group_config(
                            group_id=org_name,
                            name=org_name,
                            webhook_url=webhook_url,
                            enabled=True
                        )
                        if config:
                            print(f"  ✅ 创建成功")
                            results["created_count"] += 1
                            results["created_orgs"].append(org_name)
                        else:
                            print(f"  ❌ 创建失败")
                            results["failed_count"] += 1
                            results["failed_orgs"].append(org_name)
                    else:
                        print(f"  ➕ 将创建 (试运行)")
                        results["created_count"] += 1
                        results["created_orgs"].append(org_name)

            except Exception as e:
                print(f"  ❌ 处理失败: {e}")
                results["failed_count"] += 1
                results["failed_orgs"].append(org_name)
                logger.error(f"Failed to process org {org_name}: {e}")
        
        # 打印汇总结果
        print(f"\n{'=' * 60}")
        print(f"批量操作完成")
        print(f"{'=' * 60}")
        print(f"总计组织: {results['total_orgs']}")
        print(f"创建成功: {results['created_count']}")
        print(f"更新成功: {results['updated_count']}")
        print(f"跳过已存在: {len(results['skipped_orgs'])}")
        print(f"操作失败: {results['failed_count']}")
        
        if results['created_orgs']:
            print(f"\n✅ 创建的组织 ({len(results['created_orgs'])}):")
            for org in results['created_orgs']:
                print(f"  - {org}")
                
        if results['updated_orgs']:
            print(f"\n🔄 更新的组织 ({len(results['updated_orgs'])}):")
            for org in results['updated_orgs']:
                print(f"  - {org}")
                
        if results['skipped_orgs']:
            print(f"\n⏭️  跳过的组织 ({len(results['skipped_orgs'])}):")
            for org in results['skipped_orgs']:
                print(f"  - {org}")
                
        if results['failed_orgs']:
            print(f"\n❌ 失败的组织 ({len(results['failed_orgs'])}):")
            for org in results['failed_orgs']:
                print(f"  - {org}")
        
        print(f"{'=' * 60}")
        
        return results
        
    except Exception as e:
        logger.error(f"Batch insert failed: {e}")
        print(f"❌ 批量操作失败: {e}")
        return {"error": str(e)}


def main():
    """主函数"""
    import sys

    print("FSOA 企微群配置批量插入工具")
    print("=" * 60)

    # 检查命令行参数
    dry_run = False
    skip_existing = True
    clear_first = False

    if len(sys.argv) > 1:
        if '--dry-run' in sys.argv:
            dry_run = True
        if '--force-update' in sys.argv:
            skip_existing = False
        if '--clear-first' in sys.argv:
            clear_first = True
    else:
        # 默认为清理后重新插入
        clear_first = True
        print("使用默认模式: 清理现有配置后重新插入")
        print("如需试运行，请使用: python scripts/batch_insert_wechat_groups.py --dry-run")
        print("如需强制更新已存在配置，请使用: --force-update")
        print("如需跳过清理步骤，请使用: 不加 --clear-first 参数")

    # 显示将要使用的组织列表
    print(f"\n将要处理的组织列表 ({len(ORG_WEBHOOK_MAPPING)} 个):")
    for i, (org_name, webhook_url) in enumerate(ORG_WEBHOOK_MAPPING.items(), 1):
        print(f"  {i:2d}. {org_name}")
        print(f"      Webhook: {webhook_url[:50]}...")

    print(f"\n配置参数:")
    print(f"  - 试运行模式: {dry_run}")
    print(f"  - 跳过已存在: {skip_existing}")
    print(f"  - 先清理配置: {clear_first}")

    # 先清理现有配置（如果需要）
    if clear_first:
        print(f"\n{'=' * 60}")
        print("第一步: 清理现有配置")
        print(f"{'=' * 60}")
        clear_results = clear_all_group_configs(dry_run=dry_run)
        if "error" in clear_results:
            print("❌ 清理配置失败，停止执行")
            return

    # 执行批量操作
    print(f"\n{'=' * 60}")
    print("第二步: 插入新配置")
    print(f"{'=' * 60}")
    results = batch_insert_wechat_groups(
        org_webhook_mapping=ORG_WEBHOOK_MAPPING,
        skip_existing=skip_existing,
        dry_run=dry_run
    )

    if "error" not in results:
        success_rate = (results['created_count'] + results['updated_count']) / results['total_orgs'] * 100
        print(f"\n📊 操作成功率: {success_rate:.1f}%")

        if not dry_run and (results['created_count'] > 0 or results['updated_count'] > 0):
            print("\n🎉 批量操作完成！您可以在Web界面的 [系统管理 → 企微群配置] 中查看结果。")


if __name__ == "__main__":
    main()

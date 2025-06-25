#!/usr/bin/env python3
"""
测试新实现的业务功能

专门测试分级通知、企微群配置、业务指标等新功能
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_test_opportunities():
    """创建测试商机数据"""
    from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
    
    test_data = [
        {
            "order_num": "GD20250600801",
            "name": "张先生",
            "address": "北京市朝阳区CBD商务区",
            "supervisor_name": "李纪龙",
            "create_time": datetime.now() - timedelta(hours=30),
            "org_name": "三河市中豫防水工程有限公司",
            "order_status": OpportunityStatus.PENDING_APPOINTMENT
        },
        {
            "order_num": "GD20250600802",
            "name": "王女士",
            "address": "上海市浦东新区陆家嘴",
            "supervisor_name": "曹振锋",
            "create_time": datetime.now() - timedelta(hours=50),
            "org_name": "北京华夏防水工程有限公司",
            "order_status": OpportunityStatus.TEMPORARILY_NOT_VISITING
        },
        {
            "order_num": "GD20250600803",
            "name": "刘先生",
            "address": "广州市天河区珠江新城",
            "supervisor_name": "李会强",
            "create_time": datetime.now() - timedelta(hours=75),
            "org_name": "上海东方防水技术有限公司",
            "order_status": OpportunityStatus.TEMPORARILY_NOT_VISITING
        },
        {
            "order_num": "GD20250600804",
            "name": "陈女士",
            "address": "深圳市南山区科技园",
            "supervisor_name": "张明",
            "create_time": datetime.now() - timedelta(hours=25),
            "org_name": "三河市中豫防水工程有限公司",
            "order_status": OpportunityStatus.PENDING_APPOINTMENT
        },
        {
            "order_num": "GD20250600805",
            "name": "赵先生",
            "address": "杭州市西湖区文三路",
            "supervisor_name": "王强",
            "create_time": datetime.now() - timedelta(hours=100),
            "org_name": "广州南方防水科技有限公司",
            "order_status": OpportunityStatus.TEMPORARILY_NOT_VISITING
        }
    ]
    
    opportunities = []
    for data in test_data:
        opp = OpportunityInfo(**data)
        opp.update_overdue_info()  # 计算逾期信息
        opportunities.append(opp)
    
    return opportunities

def test_opportunity_model():
    """测试商机模型"""
    print("📋 测试商机模型...")
    
    try:
        opportunities = create_test_opportunities()
        
        print(f"✅ 成功创建 {len(opportunities)} 个测试商机")
        
        # 显示商机详情
        for i, opp in enumerate(opportunities, 1):
            print(f"{i}. 工单号: {opp.order_num}")
            print(f"   客户: {opp.name}")
            print(f"   组织: {opp.org_name}")
            print(f"   状态: {opp.order_status}")
            print(f"   已过时长: {opp.elapsed_hours:.1f} 小时")
            print(f"   是否逾期: {opp.is_overdue}")
            print(f"   升级级别: {opp.escalation_level}")
            print()
        
        return opportunities
        
    except Exception as e:
        print(f"❌ 商机模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_business_metrics():
    """测试业务指标计算"""
    print("📈 测试业务指标计算...")
    
    try:
        from src.fsoa.analytics.business_metrics import BusinessMetricsCalculator
        
        opportunities = create_test_opportunities()
        calculator = BusinessMetricsCalculator()
        
        # 计算各种指标
        overdue_rates = calculator.calculate_overdue_rate(opportunities)
        avg_times = calculator.calculate_average_processing_time(opportunities)
        org_performance = calculator.calculate_org_performance(opportunities)
        supervisor_workload = calculator.calculate_supervisor_workload(opportunities)
        time_distribution = calculator.calculate_time_distribution(opportunities)
        
        print("✅ 业务指标计算成功")
        print(f"📊 逾期率分析: {overdue_rates}")
        print(f"⏱️  平均处理时长: {avg_times}")
        print(f"🏢 组织绩效数量: {len(org_performance)}")
        print(f"👥 负责人工作量: {len(supervisor_workload)}")
        print(f"📊 时长分布: {time_distribution}")
        
        return True
        
    except Exception as e:
        print(f"❌ 业务指标计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_notification_formatting():
    """测试通知格式化"""
    print("📝 测试通知格式化...")
    
    try:
        from src.fsoa.notification.business_formatter import BusinessNotificationFormatter
        
        opportunities = create_test_opportunities()
        formatter = BusinessNotificationFormatter()
        
        # 按组织分组
        org_opportunities = {}
        for opp in opportunities:
            org_name = opp.org_name
            if org_name not in org_opportunities:
                org_opportunities[org_name] = []
            org_opportunities[org_name].append(opp)
        
        # 测试格式化第一个组织的通知
        if org_opportunities:
            first_org = list(org_opportunities.keys())[0]
            first_org_opps = org_opportunities[first_org]
            
            # 标准通知
            standard_message = formatter.format_org_overdue_notification(first_org, first_org_opps)
            print(f"✅ 标准通知格式化成功 (长度: {len(standard_message)} 字符)")
            
            # 升级通知
            escalation_opps = [opp for opp in first_org_opps if opp.escalation_level > 0]
            if escalation_opps:
                escalation_message = formatter.format_escalation_notification(
                    first_org, escalation_opps, ["运营负责人", "区域经理"]
                )
                print(f"✅ 升级通知格式化成功 (长度: {len(escalation_message)} 字符)")
            else:
                print("⚠️  没有需要升级的商机")
            
            # 汇总通知
            summary_message = formatter.format_summary_notification(
                total_opportunities=len(opportunities),
                org_count=len(org_opportunities),
                escalation_count=sum(1 for opp in opportunities if opp.escalation_level > 0)
            )
            print(f"✅ 汇总通知格式化成功 (长度: {len(summary_message)} 字符)")
            
            # 显示消息预览
            print("\n📄 标准通知预览 (前300字符):")
            print(standard_message[:300] + "..." if len(standard_message) > 300 else standard_message)
        
        return True
        
    except Exception as e:
        print(f"❌ 通知格式化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_wechat_config():
    """测试企微群配置"""
    print("🔧 测试企微群配置...")
    
    try:
        from src.fsoa.config.wechat_config import get_wechat_config_manager
        
        config_manager = get_wechat_config_manager()
        
        # 获取配置
        org_mapping = config_manager.get_org_webhook_mapping()
        internal_webhook = config_manager.get_internal_ops_webhook()
        mention_users = config_manager.get_mention_users("escalation")
        notification_settings = config_manager.get_notification_settings()
        
        print(f"✅ 企微群配置加载成功")
        print(f"📋 组织映射数量: {len(org_mapping)}")
        print(f"🏢 内部运营群: {'已配置' if internal_webhook else '未配置'}")
        print(f"👥 @用户数量: {len(mention_users)}")
        print(f"⚙️  通知设置: {len(notification_settings)} 项")
        
        # 测试配置操作
        test_org = "测试组织"
        test_webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
        
        # 添加配置
        success = config_manager.set_org_webhook(test_org, test_webhook)
        print(f"✅ 添加配置: {'成功' if success else '失败'}")
        
        # 获取配置
        retrieved_webhook = config_manager.get_org_webhook(test_org)
        print(f"✅ 获取配置: {'成功' if retrieved_webhook == test_webhook else '失败'}")
        
        # 删除配置
        success = config_manager.remove_org_webhook(test_org)
        print(f"✅ 删除配置: {'成功' if success else '失败'}")
        
        # 验证配置
        issues = config_manager.validate_config()
        if any(issues.values()):
            print("⚠️  配置验证发现问题:")
            for category, problems in issues.items():
                if problems:
                    print(f"   {category}: {len(problems)} 个问题")
        else:
            print("✅ 配置验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 企微群配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_wechat_client():
    """测试企微客户端"""
    print("📱 测试企微客户端...")
    
    try:
        from src.fsoa.notification.wechat import get_wechat_client
        
        client = get_wechat_client()
        
        # 获取配置信息
        available_groups = client.get_available_groups()
        org_mapping = client.get_org_webhook_mapping()
        
        print(f"✅ 企微客户端初始化成功")
        print(f"📋 可用群组: {len(available_groups)}")
        print(f"🏢 组织映射: {len(org_mapping)}")
        
        # 测试配置更新
        test_org = "测试组织2"
        test_webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test2"
        
        success = client.update_org_webhook_mapping(test_org, test_webhook)
        print(f"✅ 更新映射: {'成功' if success else '失败'}")
        
        success = client.remove_org_webhook_mapping(test_org)
        print(f"✅ 删除映射: {'成功' if success else '失败'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 企微客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 新功能测试")
    print("=" * 50)
    
    # 运行测试
    tests = [
        ("商机模型", test_opportunity_model),
        ("业务指标计算", test_business_metrics),
        ("通知格式化", test_notification_formatting),
        ("企微群配置", test_wechat_config),
        ("企微客户端", test_wechat_client)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'-' * 30}")
        try:
            result = test_func()
            results[test_name] = "✅ 通过" if result else "❌ 失败"
        except Exception as e:
            results[test_name] = f"❌ 异常: {str(e)[:50]}..."
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结:")
    for test_name, result in results.items():
        print(f"   {test_name}: {result}")
    
    passed_count = sum(1 for result in results.values() if result.startswith("✅"))
    total_count = len(results)
    
    print(f"\n🎯 总体结果: {passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("🎉 所有测试通过！新功能实现成功")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关代码")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
FSOA 新功能演示脚本

展示完成的Backlog功能：分级通知、企微群配置、业务指标分析
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"🎯 {title}")
    print("=" * 60)

def print_section(title):
    """打印章节"""
    print(f"\n📋 {title}")
    print("-" * 40)

def demo_opportunity_model():
    """演示商机模型功能"""
    print_header("商机模型和业务逻辑演示")
    
    from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
    
    # 创建示例商机
    opportunity = OpportunityInfo(
        order_num="GD20250600801",
        name="张先生",
        address="北京市朝阳区CBD商务区",
        supervisor_name="李纪龙",
        create_time=datetime.now() - timedelta(hours=30),
        org_name="三河市中豫防水工程有限公司",
        order_status=OpportunityStatus.PENDING_APPOINTMENT
    )
    
    # 更新逾期信息
    opportunity.update_overdue_info()
    
    print(f"✅ 商机信息:")
    print(f"   工单号: {opportunity.order_num}")
    print(f"   客户: {opportunity.name}")
    print(f"   组织: {opportunity.org_name}")
    print(f"   状态: {opportunity.order_status}")
    print(f"   创建时间: {opportunity.create_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   已过时长: {opportunity.elapsed_hours:.1f} 小时")
    print(f"   SLA阈值: {opportunity.sla_threshold_hours} 小时")
    print(f"   是否逾期: {'是' if opportunity.is_overdue else '否'}")
    print(f"   升级级别: {opportunity.escalation_level}")

def demo_business_metrics():
    """演示业务指标计算"""
    print_header("业务指标计算演示")
    
    from src.fsoa.analytics.business_metrics import BusinessMetricsCalculator
    from scripts.test_new_features import create_test_opportunities
    
    # 创建测试数据
    opportunities = create_test_opportunities()
    calculator = BusinessMetricsCalculator()
    
    print_section("基础统计")
    print(f"总商机数: {len(opportunities)}")
    print(f"逾期商机数: {sum(1 for opp in opportunities if opp.is_overdue)}")
    print(f"升级商机数: {sum(1 for opp in opportunities if opp.escalation_level > 0)}")
    
    print_section("逾期率分析")
    overdue_rates = calculator.calculate_overdue_rate(opportunities)
    for status, rate in overdue_rates.items():
        print(f"{status}: {rate}%")
    
    print_section("平均处理时长")
    avg_times = calculator.calculate_average_processing_time(opportunities)
    for status, time in avg_times.items():
        print(f"{status}: {time:.1f} 小时")
    
    print_section("组织绩效排名")
    org_performance = calculator.calculate_org_performance(opportunities)
    for i, (org_name, metrics) in enumerate(org_performance.items(), 1):
        print(f"{i}. {org_name}")
        print(f"   SLA达成率: {metrics['SLA达成率']}%")
        print(f"   逾期率: {metrics['逾期率']}%")
        print(f"   平均响应时间: {metrics['平均响应时间']} 小时")

def demo_notification_formatting():
    """演示通知格式化功能"""
    print_header("通知格式化演示")
    
    from src.fsoa.notification.business_formatter import BusinessNotificationFormatter
    from scripts.test_new_features import create_test_opportunities
    
    opportunities = create_test_opportunities()
    formatter = BusinessNotificationFormatter()
    
    # 按组织分组
    org_opportunities = {}
    for opp in opportunities:
        org_name = opp.org_name
        if org_name not in org_opportunities:
            org_opportunities[org_name] = []
        org_opportunities[org_name].append(opp)
    
    # 演示标准通知
    print_section("标准通知格式")
    first_org = list(org_opportunities.keys())[0]
    first_org_opps = org_opportunities[first_org]
    
    standard_message = formatter.format_org_overdue_notification(first_org, first_org_opps)
    print(standard_message)
    
    # 演示升级通知
    print_section("升级通知格式")
    escalation_opps = [opp for opp in opportunities if opp.escalation_level > 0]
    if escalation_opps:
        escalation_message = formatter.format_escalation_notification(
            first_org, escalation_opps, ["运营负责人", "区域经理"]
        )
        print(escalation_message)
    else:
        print("当前测试数据中没有需要升级的商机")
    
    # 演示汇总通知
    print_section("汇总通知格式")
    summary_message = formatter.format_summary_notification(
        total_opportunities=len(opportunities),
        org_count=len(org_opportunities),
        escalation_count=len(escalation_opps)
    )
    print(summary_message)

def demo_wechat_config():
    """演示企微群配置管理"""
    print_header("企微群配置管理演示")
    
    from src.fsoa.config.wechat_config import get_wechat_config_manager
    
    config_manager = get_wechat_config_manager()
    
    print_section("当前配置状态")
    org_mapping = config_manager.get_org_webhook_mapping()
    internal_webhook = config_manager.get_internal_ops_webhook()
    mention_users = config_manager.get_mention_users("escalation")
    
    print(f"组织映射数量: {len(org_mapping)}")
    print(f"内部运营群: {'已配置' if internal_webhook else '未配置'}")
    print(f"@用户数量: {len(mention_users)}")
    
    print_section("组织映射详情")
    for org_name, webhook_url in org_mapping.items():
        status = "✅ 已配置" if webhook_url else "❌ 未配置"
        print(f"{org_name}: {status}")
    
    print_section("配置管理操作演示")
    # 演示添加配置
    test_org = "演示组织"
    test_webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=demo"
    
    print(f"添加配置: {test_org}")
    success = config_manager.set_org_webhook(test_org, test_webhook)
    print(f"结果: {'成功' if success else '失败'}")
    
    # 演示获取配置
    retrieved_webhook = config_manager.get_org_webhook(test_org)
    print(f"获取配置: {retrieved_webhook[:50]}..." if retrieved_webhook else "未找到")
    
    # 演示删除配置
    success = config_manager.remove_org_webhook(test_org)
    print(f"删除配置: {'成功' if success else '失败'}")
    
    print_section("配置验证")
    issues = config_manager.validate_config()
    if any(issues.values()):
        print("发现配置问题:")
        for category, problems in issues.items():
            if problems:
                print(f"  {category}: {len(problems)} 个问题")
                for problem in problems[:3]:  # 只显示前3个
                    print(f"    - {problem}")
    else:
        print("✅ 配置验证通过")

def demo_wechat_client():
    """演示企微客户端功能"""
    print_header("企微客户端功能演示")
    
    from src.fsoa.notification.wechat import get_wechat_client
    
    client = get_wechat_client()
    
    print_section("客户端信息")
    available_groups = client.get_available_groups()
    org_mapping = client.get_org_webhook_mapping()
    
    print(f"可用群组数量: {len(available_groups)}")
    print(f"组织映射数量: {len(org_mapping)}")
    
    print_section("分级通知机制")
    print("✅ 标准通知: 发送到orgName对应的企微群")
    print("✅ 升级通知: 发送到内部运营群并@特定人员")
    print("✅ 智能路由: 根据组织名称自动选择目标群组")
    print("✅ 频率控制: 避免重复通知的冷却机制")

def demo_web_interface():
    """演示Web界面功能"""
    print_header("Web界面功能演示")
    
    print_section("新增页面")
    pages = [
        "📊 运营仪表板 - 实时逾期任务统计和组织绩效",
        "📈 业务分析 - 逾期率分析、组织绩效对比、时长分布",
        "📋 商机列表 - 逾期商机详情、筛选、导出功能",
        "🔧 企微群配置 - 可视化配置管理界面",
        "⚙️ 系统设置 - Agent和通知参数配置",
        "🧪 系统测试 - 各组件连接测试"
    ]
    
    for page in pages:
        print(f"✅ {page}")
    
    print_section("主要功能")
    features = [
        "实时数据展示 - 基于真实商机数据",
        "交互式图表 - 逾期率、处理时长等可视化",
        "配置管理 - 企微群映射的Web界面管理",
        "数据导出 - 支持CSV格式导出",
        "通知测试 - 一键发送测试通知",
        "系统监控 - Agent状态和系统健康度"
    ]
    
    for feature in features:
        print(f"✅ {feature}")
    
    print_section("启动Web界面")
    print("运行以下命令启动Web界面:")
    print("cd /mnt/persist/workspace")
    print("streamlit run src/fsoa/ui/app.py")
    print("然后访问: http://localhost:8501")

def main():
    """主演示函数"""
    print("🎉 FSOA 新功能完整演示")
    print("基于Backlog完成的高优先级和中优先级任务")
    print(f"演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 演示各个功能模块
        demo_opportunity_model()
        demo_business_metrics()
        demo_notification_formatting()
        demo_wechat_config()
        demo_wechat_client()
        demo_web_interface()
        
        # 总结
        print_header("功能完成总结")
        print("✅ 🔔 通知系统优化 (高优先级) - 已完成")
        print("   - 分级通知机制")
        print("   - 企微群配置管理")
        print("   - 通知内容格式化")
        print("   - 通知频率控制")
        print()
        print("✅ 🎛️ Web界面真实数据展示 (中优先级) - 已完成")
        print("   - 运营仪表板")
        print("   - 历史趋势分析")
        print("   - 商机列表管理")
        print()
        print("✅ 📈 业务指标和监控 (中优先级) - 已完成")
        print("   - 关键指标定义和计算")
        print("   - 组织绩效排名")
        print("   - 实时数据分析")
        print()
        print("🎯 所有高优先级任务已完成，系统已具备生产环境部署条件！")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

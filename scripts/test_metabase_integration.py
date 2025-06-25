#!/usr/bin/env python3
"""
测试 Metabase 真实数据集成

验证 Card 1712 数据获取和商机逾期检测逻辑
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def force_reload_config():
    """强制重新加载配置"""
    # 清除所有相关的环境变量
    for key in list(os.environ.keys()):
        if key.startswith(('DEEPSEEK_', 'METABASE_', 'WECHAT_', 'AGENT_', 'NOTIFICATION_')):
            del os.environ[key]
    
    # 重新加载 .env 文件
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # 清除模块缓存
    modules_to_clear = [
        'src.fsoa.utils.config',
        'src.fsoa.data.metabase',
        'src.fsoa.data.models'
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]

def test_metabase_connection():
    """测试 Metabase 连接"""
    print("🔌 测试 Metabase 连接...")
    
    try:
        from src.fsoa.data.metabase import get_metabase_client
        
        client = get_metabase_client()
        
        # 测试认证
        if client.authenticate():
            print("✅ Metabase 认证成功")
            
            # 测试连接
            if client.test_connection():
                print("✅ Metabase 连接测试通过")
                return client
            else:
                print("❌ Metabase 连接测试失败")
                return None
        else:
            print("❌ Metabase 认证失败")
            return None
            
    except Exception as e:
        print(f"❌ Metabase 连接异常: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_card_1712_query(client):
    """测试 Card 1712 数据查询"""
    print("\n📊 测试 Card 1712 数据查询...")
    
    try:
        # 查询 Card 1712
        raw_data = client.query_card(1712)
        
        print(f"✅ 成功获取 {len(raw_data)} 条原始数据")
        
        if raw_data:
            # 显示第一条数据的结构
            first_record = raw_data[0]
            print("📋 数据结构示例:")
            for key, value in first_record.items():
                print(f"   {key}: {value}")
            
            # 验证必需字段
            required_fields = ['orderNum', 'name', 'address', 'supervisorName', 
                             'createTime', 'orgName', 'orderstatus']
            missing_fields = [f for f in required_fields if f not in first_record]
            
            if missing_fields:
                print(f"⚠️  缺少必需字段: {missing_fields}")
            else:
                print("✅ 所有必需字段都存在")
        
        return raw_data
        
    except Exception as e:
        print(f"❌ Card 1712 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_opportunity_conversion(client):
    """测试商机数据转换"""
    print("\n🔄 测试商机数据转换...")
    
    try:
        # 获取商机数据
        opportunities_data = client.get_field_service_opportunities()
        print(f"✅ 获取到 {len(opportunities_data)} 条有效商机数据")
        
        # 转换为商机模型
        from src.fsoa.data.models import OpportunityInfo
        
        opportunities = []
        for raw_opp in opportunities_data[:5]:  # 只测试前5条
            try:
                opp = client._convert_raw_opportunity_to_model(raw_opp)
                opp.update_overdue_info()
                opportunities.append(opp)
                
                print(f"📋 商机: {opp.order_num}")
                print(f"   客户: {opp.name}")
                print(f"   状态: {opp.order_status}")
                print(f"   创建时间: {opp.create_time}")
                print(f"   已过时长: {opp.elapsed_hours:.1f} 小时")
                print(f"   SLA阈值: {opp.sla_threshold_hours} 小时")
                print(f"   是否逾期: {opp.is_overdue}")
                if opp.is_overdue:
                    print(f"   逾期时长: {opp.overdue_hours:.1f} 小时")
                    print(f"   升级级别: {opp.escalation_level}")
                print()
                
            except Exception as e:
                print(f"⚠️  转换商机失败: {e}")
                continue
        
        return opportunities
        
    except Exception as e:
        print(f"❌ 商机数据转换失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_overdue_detection(client):
    """测试逾期检测逻辑"""
    print("\n⏰ 测试逾期检测逻辑...")
    
    try:
        # 获取逾期商机
        overdue_opportunities = client.get_overdue_opportunities()
        
        print(f"✅ 检测到 {len(overdue_opportunities)} 个逾期商机")
        
        # 按组织分组统计
        org_stats = {}
        escalation_count = 0
        
        for opp in overdue_opportunities:
            org_name = opp.org_name
            if org_name not in org_stats:
                org_stats[org_name] = {
                    'total': 0,
                    'pending_appointment': 0,
                    'temporarily_not_visiting': 0,
                    'escalation': 0
                }
            
            org_stats[org_name]['total'] += 1
            
            if opp.order_status == '待预约':
                org_stats[org_name]['pending_appointment'] += 1
            elif opp.order_status == '暂不上门':
                org_stats[org_name]['temporarily_not_visiting'] += 1
            
            if opp.escalation_level > 0:
                org_stats[org_name]['escalation'] += 1
                escalation_count += 1
        
        print(f"📊 逾期统计:")
        print(f"   总逾期数: {len(overdue_opportunities)}")
        print(f"   需要升级: {escalation_count}")
        print(f"   涉及组织: {len(org_stats)}")
        
        print(f"\n📋 各组织逾期情况:")
        for org_name, stats in org_stats.items():
            print(f"   {org_name}:")
            print(f"     总计: {stats['total']}")
            print(f"     待预约: {stats['pending_appointment']}")
            print(f"     暂不上门: {stats['temporarily_not_visiting']}")
            print(f"     需升级: {stats['escalation']}")
        
        return overdue_opportunities, org_stats
        
    except Exception as e:
        print(f"❌ 逾期检测失败: {e}")
        import traceback
        traceback.print_exc()
        return [], {}

def test_backward_compatibility(client):
    """测试向后兼容性"""
    print("\n🔄 测试向后兼容性...")
    
    try:
        # 测试原有的 get_overdue_tasks 方法
        overdue_tasks = client.get_overdue_tasks()
        
        print(f"✅ 向后兼容测试通过，转换了 {len(overdue_tasks)} 个任务")
        
        if overdue_tasks:
            task = overdue_tasks[0]
            print(f"📋 任务示例:")
            print(f"   ID: {task.id}")
            print(f"   标题: {task.title}")
            print(f"   描述: {task.description}")
            print(f"   状态: {task.status}")
            print(f"   优先级: {task.priority}")
            print(f"   负责人: {task.assignee}")
            print(f"   客户: {task.customer}")
        
        return True
        
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 Metabase 真实数据集成测试")
    print("=" * 50)
    
    # 强制重新加载配置
    force_reload_config()
    
    # 测试连接
    client = test_metabase_connection()
    if not client:
        print("❌ 无法连接到 Metabase，测试终止")
        return False
    
    # 测试 Card 1712 查询
    raw_data = test_card_1712_query(client)
    if not raw_data:
        print("❌ 无法获取 Card 1712 数据，测试终止")
        return False
    
    # 测试数据转换
    opportunities = test_opportunity_conversion(client)
    if not opportunities:
        print("⚠️  数据转换测试失败，但继续其他测试")
    
    # 测试逾期检测
    overdue_opportunities, org_stats = test_overdue_detection(client)
    
    # 测试向后兼容性
    backward_compatible = test_backward_compatibility(client)
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结:")
    print(f"   Metabase 连接: {'✅' if client else '❌'}")
    print(f"   Card 1712 查询: {'✅' if raw_data else '❌'}")
    print(f"   数据转换: {'✅' if opportunities else '❌'}")
    print(f"   逾期检测: {'✅' if overdue_opportunities else '❌'}")
    print(f"   向后兼容: {'✅' if backward_compatible else '❌'}")
    
    if overdue_opportunities:
        print(f"\n🎯 业务数据概览:")
        print(f"   原始数据: {len(raw_data)} 条")
        print(f"   逾期商机: {len(overdue_opportunities)} 个")
        print(f"   涉及组织: {len(org_stats)} 个")
        
        escalation_count = sum(1 for opp in overdue_opportunities if opp.escalation_level > 0)
        print(f"   需要升级: {escalation_count} 个")
    
    success = all([client, raw_data, backward_compatible])
    print(f"\n🎉 整体测试: {'通过' if success else '失败'}")
    
    return success

if __name__ == "__main__":
    main()

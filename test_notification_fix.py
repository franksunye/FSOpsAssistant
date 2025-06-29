#!/usr/bin/env python3
"""
通知系统修复验证脚本

用于验证通知系统修复后的行为是否正确
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta
from fsoa.data.models import OpportunityInfo, OpportunityStatus, NotificationTaskType
from fsoa.agent.managers.notification_manager import NotificationTaskManager
from fsoa.utils.logger import get_logger

logger = get_logger(__name__)

def create_test_opportunities():
    """创建测试商机数据"""
    base_time = datetime.now() - timedelta(hours=50)  # 50小时前创建
    
    opportunities = [
        OpportunityInfo(
            order_num="GD2025064176",
            name="付女士",
            address="龙湖滟澜山",
            supervisor_name="杜晓兴",
            create_time=base_time,
            org_name="北京虹象防水工程有限公司",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        ),
        OpportunityInfo(
            order_num="GD20250600782",
            name="先生",
            address="某地址",
            supervisor_name="燕伟",
            create_time=base_time - timedelta(hours=74),  # 124小时前
            org_name="北京虹象防水工程有限公司",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        ),
        OpportunityInfo(
            order_num="GD20250600912",
            name="王女士",
            address="某地址2",
            supervisor_name="燕伟",
            create_time=base_time - timedelta(hours=70),  # 120小时前
            org_name="北京虹象防水工程有限公司",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        ),
        # 添加另一个组织的商机
        OpportunityInfo(
            order_num="GD2025064999",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试负责人",
            create_time=base_time,
            org_name="测试组织",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
    ]
    
    # 更新所有商机的逾期信息
    for opp in opportunities:
        opp.update_overdue_info(use_business_time=True)
        logger.info(f"商机 {opp.order_num}: 违规={opp.is_violation}, 逾期={opp.is_overdue}, 升级级别={opp.escalation_level}")
    
    return opportunities

def test_notification_creation():
    """测试通知任务创建"""
    logger.info("=== 测试通知任务创建 ===")
    
    try:
        # 创建通知管理器
        notification_manager = NotificationTaskManager()
        
        # 创建测试商机
        opportunities = create_test_opportunities()
        
        # 创建通知任务
        tasks = notification_manager.create_tasks(opportunities, run_id=999)
        
        logger.info(f"创建了 {len(tasks)} 个通知任务")
        
        # 分析任务类型
        violation_tasks = [t for t in tasks if t.notification_type == NotificationTaskType.VIOLATION]
        standard_tasks = [t for t in tasks if t.notification_type == NotificationTaskType.STANDARD]
        escalation_tasks = [t for t in tasks if t.notification_type == NotificationTaskType.ESCALATION]
        
        logger.info(f"违规通知任务: {len(violation_tasks)}")
        logger.info(f"标准通知任务: {len(standard_tasks)}")
        logger.info(f"升级通知任务: {len(escalation_tasks)}")
        
        # 检查升级任务
        logger.info("=== 升级任务详情 ===")
        for task in escalation_tasks:
            logger.info(f"升级任务: order_num={task.order_num}, org_name={task.org_name}")
        
        # 验证预期结果
        expected_orgs = {"北京虹象防水工程有限公司", "测试组织"}
        actual_escalation_orgs = {task.org_name for task in escalation_tasks}
        
        logger.info(f"预期升级组织: {expected_orgs}")
        logger.info(f"实际升级组织: {actual_escalation_orgs}")
        
        if expected_orgs == actual_escalation_orgs:
            logger.info("✅ 升级任务创建正确")
        else:
            logger.error("❌ 升级任务创建有误")
        
        # 检查是否每个组织只有一个升级任务
        org_escalation_count = {}
        for task in escalation_tasks:
            org_escalation_count[task.org_name] = org_escalation_count.get(task.org_name, 0) + 1
        
        logger.info(f"各组织升级任务数量: {org_escalation_count}")
        
        if all(count == 1 for count in org_escalation_count.values()):
            logger.info("✅ 每个组织只有一个升级任务")
        else:
            logger.error("❌ 存在组织有多个升级任务")
        
        return tasks
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return []

def test_escalation_message_formatting():
    """测试升级通知消息格式化"""
    logger.info("=== 测试升级通知消息格式化 ===")
    
    try:
        from fsoa.notification.business_formatter import BusinessFormatter
        
        # 创建测试商机
        opportunities = create_test_opportunities()
        
        # 筛选出北京虹象的商机
        beijing_opportunities = [opp for opp in opportunities if opp.org_name == "北京虹象防水工程有限公司"]
        
        # 格式化升级通知
        message = BusinessFormatter.format_escalation_notification(
            "北京虹象防水工程有限公司", 
            beijing_opportunities
        )
        
        logger.info("=== 升级通知消息内容 ===")
        logger.info(message)
        
        # 验证消息内容
        lines = message.split('\n')
        
        # 检查工单数量显示
        count_line = None
        for line in lines:
            if "需要升级处理的工单数" in line:
                count_line = line
                break
        
        if count_line:
            logger.info(f"工单数量行: {count_line}")
            if f"需要升级处理的工单数：{len(beijing_opportunities)}" in count_line:
                logger.info("✅ 工单数量显示正确")
            else:
                logger.error("❌ 工单数量显示错误")
        
        # 检查截断逻辑
        if len(beijing_opportunities) > 5:
            remaining = len(beijing_opportunities) - 5
            expected_truncate = f"... 还有 {remaining} 个工单需要处理"
            if expected_truncate in message:
                logger.info("✅ 截断逻辑正确")
            else:
                logger.error(f"❌ 截断逻辑错误，期望: {expected_truncate}")
        
    except Exception as e:
        logger.error(f"消息格式化测试失败: {e}")

def main():
    """主测试函数"""
    logger.info("开始通知系统修复验证测试")
    
    # 测试1: 通知任务创建
    tasks = test_notification_creation()
    
    # 测试2: 消息格式化
    test_escalation_message_formatting()
    
    logger.info("测试完成")

if __name__ == "__main__":
    main()

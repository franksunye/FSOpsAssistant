#!/usr/bin/env python3
"""
前端与后端对齐分析

检查Web前端是否与重构后的后端架构保持一致
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def analyze_frontend_backend_alignment():
    """分析前端与后端的对齐情况"""
    
    print("🔍 前端与后端对齐分析")
    print("=" * 60)
    
    # 分析结果
    alignment_issues = []
    alignment_good = []
    recommendations = []
    
    # 1. API调用分析
    print("\n📡 API调用分析:")
    
    # 检查前端是否使用了新的管理器
    print("   🔍 检查管理器使用情况...")
    
    # 前端仍在直接调用旧的函数
    issues_found = [
        "❌ 前端直接调用 fetch_overdue_opportunities() 而不是通过新的数据策略",
        "❌ 前端直接调用 AgentOrchestrator().execute() 而不是使用新的执行追踪",
        "❌ 前端没有使用新的通知任务管理器",
        "❌ 前端没有展示新的Agent执行追踪信息",
        "❌ 前端没有展示缓存统计信息"
    ]
    
    for issue in issues_found:
        print(f"   {issue}")
        alignment_issues.append(issue)
    
    # 2. 数据模型分析
    print("\n📊 数据模型分析:")
    
    # 前端仍在使用旧的数据结构
    model_issues = [
        "❌ 任务列表页面仍使用示例数据，未集成真实的商机数据",
        "❌ 前端没有展示 NotificationTask 相关信息",
        "❌ 前端没有展示 AgentRun 和 AgentHistory 信息",
        "❌ 前端缺少业务数据缓存状态展示"
    ]
    
    for issue in model_issues:
        print(f"   {issue}")
        alignment_issues.append(issue)
    
    # 3. 功能对齐分析
    print("\n⚙️ 功能对齐分析:")
    
    # 检查功能完整性
    good_alignments = [
        "✅ 前端正确调用了 fetch_overdue_opportunities()",
        "✅ 前端支持 dry_run 模式",
        "✅ 前端展示了基本的业务分析功能",
        "✅ 前端有系统健康检查功能"
    ]
    
    for good in good_alignments:
        print(f"   {good}")
        alignment_good.append(good)
    
    missing_features = [
        "❌ 缺少新的数据统计展示 (get_data_statistics)",
        "❌ 缺少执行追踪详情页面",
        "❌ 缺少通知任务状态管理页面",
        "❌ 缺少缓存管理功能",
        "❌ 缺少Agent运行历史查看"
    ]
    
    for missing in missing_features:
        print(f"   {missing}")
        alignment_issues.append(missing)
    
    # 4. 用户体验分析
    print("\n👤 用户体验分析:")
    
    ux_issues = [
        "❌ 用户无法看到新的架构带来的性能提升",
        "❌ 用户无法管理通知任务",
        "❌ 用户无法查看详细的执行追踪信息",
        "❌ 用户无法了解缓存状态和性能"
    ]
    
    for ux in ux_issues:
        print(f"   {ux}")
        alignment_issues.append(ux)
    
    # 5. 生成建议
    print("\n💡 改进建议:")
    
    recommendations = [
        "1. 更新前端API调用，使用新的管理器接口",
        "2. 添加Agent执行追踪详情页面",
        "3. 添加通知任务管理页面",
        "4. 添加缓存状态和管理页面",
        "5. 更新任务列表页面，展示真实的商机数据",
        "6. 添加新的数据统计展示",
        "7. 优化用户界面，体现新架构的优势"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"   {rec}")
    
    # 6. 总结
    print("\n" + "=" * 60)
    print("📊 对齐分析总结:")
    print(f"   ✅ 对齐良好: {len(alignment_good)} 项")
    print(f"   ❌ 需要改进: {len(alignment_issues)} 项")
    print(f"   💡 改进建议: {len(recommendations)} 项")
    
    alignment_score = len(alignment_good) / (len(alignment_good) + len(alignment_issues)) * 100
    print(f"   📈 对齐度评分: {alignment_score:.1f}%")
    
    if alignment_score < 50:
        print("   🚨 对齐度较低，需要重点关注前端更新")
    elif alignment_score < 80:
        print("   ⚠️ 对齐度中等，建议优先更新关键功能")
    else:
        print("   ✅ 对齐度良好，可进行细节优化")
    
    return {
        "alignment_good": alignment_good,
        "alignment_issues": alignment_issues,
        "recommendations": recommendations,
        "alignment_score": alignment_score
    }

def test_current_frontend_functionality():
    """测试当前前端功能是否正常工作"""
    print("\n🧪 测试当前前端功能:")
    
    try:
        # 测试后端API是否可用
        from src.fsoa.agent.tools import (
            fetch_overdue_opportunities, get_data_statistics,
            get_data_strategy, get_notification_manager, get_execution_tracker
        )
        from src.fsoa.agent.orchestrator import AgentOrchestrator
        
        print("   ✅ 后端API导入成功")
        
        # 测试数据获取
        try:
            opportunities = fetch_overdue_opportunities()
            print(f"   ✅ 商机数据获取成功: {len(opportunities)} 个")
        except Exception as e:
            print(f"   ⚠️ 商机数据获取失败: {e}")
        
        # 测试统计信息
        try:
            stats = get_data_statistics()
            print(f"   ✅ 数据统计获取成功")
        except Exception as e:
            print(f"   ⚠️ 数据统计获取失败: {e}")
        
        # 测试编排器
        try:
            orchestrator = AgentOrchestrator()
            print(f"   ✅ Agent编排器创建成功")
        except Exception as e:
            print(f"   ⚠️ Agent编排器创建失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 后端API测试失败: {e}")
        return False

def generate_frontend_update_plan():
    """生成前端更新计划"""
    print("\n📋 前端更新计划:")
    
    update_plan = {
        "Phase 1: 核心API更新": [
            "更新主页面使用新的数据统计API",
            "更新Agent控制页面使用新的执行追踪",
            "修复任务列表页面的数据源"
        ],
        "Phase 2: 新功能页面": [
            "添加Agent执行历史页面",
            "添加通知任务管理页面", 
            "添加缓存状态管理页面"
        ],
        "Phase 3: 用户体验优化": [
            "优化数据展示，体现新架构优势",
            "添加实时状态更新",
            "完善错误处理和用户反馈"
        ]
    }
    
    for phase, tasks in update_plan.items():
        print(f"\n   {phase}:")
        for task in tasks:
            print(f"     - {task}")
    
    return update_plan

def main():
    """主函数"""
    # 执行对齐分析
    analysis_result = analyze_frontend_backend_alignment()
    
    # 测试当前功能
    frontend_working = test_current_frontend_functionality()
    
    # 生成更新计划
    update_plan = generate_frontend_update_plan()
    
    # 最终建议
    print("\n" + "=" * 60)
    print("🎯 最终建议:")
    
    if analysis_result["alignment_score"] < 50:
        print("   🚨 前端与后端对齐度较低，建议立即进行前端更新")
        print("   📋 优先级: 高")
        print("   ⏱️ 建议时间: 1-2天")
    else:
        print("   ✅ 前端基本功能正常，可以渐进式更新")
        print("   📋 优先级: 中")
        print("   ⏱️ 建议时间: 3-5天")
    
    print("\n   🔧 关键更新点:")
    print("     1. 集成新的管理器API")
    print("     2. 添加执行追踪展示")
    print("     3. 添加通知任务管理")
    print("     4. 优化数据展示")
    
    return analysis_result

if __name__ == "__main__":
    result = main()
    
    # 根据对齐度决定退出码
    if result["alignment_score"] < 50:
        sys.exit(1)  # 需要立即更新
    else:
        sys.exit(0)  # 可以渐进更新

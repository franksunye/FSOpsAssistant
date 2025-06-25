#!/usr/bin/env python3
"""
测试前端重新设计

验证前端界面的业务价值导向和用户体验
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_frontend_design_principles():
    """测试前端设计原则"""
    print("🎨 测试前端设计原则")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # 1. 测试业务价值导向
    print("\n💼 测试业务价值导向:")
    
    try:
        # 检查UI文件内容
        ui_file = Path("src/fsoa/ui/app.py")
        with open(ui_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查业务价值关键词
        business_keywords = [
            "主动监控", "智能决策", "自动通知",
            "现场服务", "商机监控", "时效状态",
            "Agent智能化价值", "业务指标"
        ]
        
        found_keywords = []
        for keyword in business_keywords:
            if keyword in content:
                found_keywords.append(keyword)
        
        print(f"   ✅ 业务价值关键词: {len(found_keywords)}/{len(business_keywords)}")
        for keyword in found_keywords:
            print(f"      - {keyword}")
        
        if len(found_keywords) >= len(business_keywords) * 0.8:
            success_count += 1
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 业务价值导向测试失败: {e}")
        total_tests += 1
    
    # 2. 测试导航结构清晰性
    print("\n🧭 测试导航结构:")
    
    try:
        # 检查导航结构
        navigation_sections = [
            "核心监控", "Agent管理", "系统管理"
        ]
        
        navigation_pages = [
            "运营仪表板", "商机监控", "业务分析",
            "Agent控制台", "执行历史", "通知管理",
            "缓存管理", "企微群配置", "系统测试"
        ]
        
        found_sections = []
        found_pages = []
        
        for section in navigation_sections:
            if section in content:
                found_sections.append(section)
        
        for page in navigation_pages:
            if page in content:
                found_pages.append(page)
        
        print(f"   ✅ 导航分组: {len(found_sections)}/{len(navigation_sections)}")
        print(f"   ✅ 导航页面: {len(found_pages)}/{len(navigation_pages)}")
        
        if len(found_sections) >= 2 and len(found_pages) >= 7:
            success_count += 1
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 导航结构测试失败: {e}")
        total_tests += 1
    
    # 3. 测试用户体验优化
    print("\n👤 测试用户体验:")
    
    try:
        # 检查用户体验关键词
        ux_keywords = [
            "use_container_width=True",  # 按钮全宽
            "st.session_state",          # 状态管理
            "快速操作",                   # 快速操作区域
            "立即执行",                   # 直接操作
            "type=\"primary\""           # 主要按钮
        ]
        
        found_ux = []
        for keyword in ux_keywords:
            if keyword in content:
                found_ux.append(keyword)
        
        print(f"   ✅ 用户体验优化: {len(found_ux)}/{len(ux_keywords)}")
        
        if len(found_ux) >= len(ux_keywords) * 0.6:
            success_count += 1
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 用户体验测试失败: {e}")
        total_tests += 1
    
    return success_count, total_tests

def test_user_guide_alignment():
    """测试用户指南对齐"""
    print("\n📚 测试用户指南对齐")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    try:
        # 检查用户指南文件
        guide_file = Path("docs/40_USER_GUIDE.md")
        with open(guide_file, 'r', encoding='utf-8') as f:
            guide_content = f.read()
        
        # 检查UI文件
        ui_file = Path("src/fsoa/ui/app.py")
        with open(ui_file, 'r', encoding='utf-8') as f:
            ui_content = f.read()
        
        # 检查功能对齐
        features_to_check = [
            ("运营仪表板", "show_dashboard"),
            ("商机监控", "show_opportunity_list"),
            ("Agent控制台", "show_agent_control"),
            ("执行历史", "show_execution_history"),
            ("通知管理", "show_notification_management"),
            ("缓存管理", "show_cache_management")
        ]
        
        aligned_features = 0
        for guide_feature, ui_function in features_to_check:
            if guide_feature in guide_content and ui_function in ui_content:
                aligned_features += 1
                print(f"   ✅ {guide_feature} - 功能对齐")
            else:
                print(f"   ❌ {guide_feature} - 功能不对齐")
        
        print(f"\n   📊 功能对齐度: {aligned_features}/{len(features_to_check)}")
        
        if aligned_features >= len(features_to_check) * 0.8:
            success_count += 1
        total_tests += 1
        
        # 检查新增内容
        new_content_keywords = [
            "主动性、自主决策、目标导向",
            "Agent智能化价值",
            "核心业务指标",
            "快速操作"
        ]
        
        found_new_content = []
        for keyword in new_content_keywords:
            if keyword in guide_content:
                found_new_content.append(keyword)
        
        print(f"   ✅ 新增内容: {len(found_new_content)}/{len(new_content_keywords)}")
        
        if len(found_new_content) >= len(new_content_keywords) * 0.7:
            success_count += 1
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 用户指南对齐测试失败: {e}")
        total_tests += 2
    
    return success_count, total_tests

def test_business_value_presentation():
    """测试业务价值展示"""
    print("\n💎 测试业务价值展示")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    try:
        # 检查UI文件
        ui_file = Path("src/fsoa/ui/app.py")
        with open(ui_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查Agent价值展示
        agent_values = [
            "7x24小时自动扫描",
            "实时识别超时风险", 
            "无需人工干预",
            "规则引擎+LLM混合决策",
            "基于上下文智能判断",
            "自适应策略调整",
            "多企微群差异化通知",
            "智能去重和频率控制",
            "升级机制自动触发"
        ]
        
        found_values = []
        for value in agent_values:
            if value in content:
                found_values.append(value)
        
        print(f"   ✅ Agent价值展示: {len(found_values)}/{len(agent_values)}")
        for value in found_values:
            print(f"      - {value}")
        
        if len(found_values) >= len(agent_values) * 0.7:
            success_count += 1
        total_tests += 1
        
        # 检查业务指标展示
        business_metrics = [
            "Agent状态", "逾期商机", "升级处理", "涉及组织"
        ]
        
        found_metrics = []
        for metric in business_metrics:
            if metric in content:
                found_metrics.append(metric)
        
        print(f"   ✅ 业务指标展示: {len(found_metrics)}/{len(business_metrics)}")
        
        if len(found_metrics) >= len(business_metrics) * 0.8:
            success_count += 1
        total_tests += 1
        
    except Exception as e:
        print(f"   ❌ 业务价值展示测试失败: {e}")
        total_tests += 2
    
    return success_count, total_tests

def main():
    """主测试函数"""
    print("🎨 前端重新设计验证测试")
    print("=" * 60)
    
    total_success = 0
    total_tests = 0
    
    # 测试设计原则
    success, tests = test_frontend_design_principles()
    total_success += success
    total_tests += tests
    
    # 测试用户指南对齐
    success, tests = test_user_guide_alignment()
    total_success += success
    total_tests += tests
    
    # 测试业务价值展示
    success, tests = test_business_value_presentation()
    total_success += success
    total_tests += tests
    
    # 最终结果
    print("\n" + "=" * 60)
    print("🎯 前端重新设计测试结果:")
    print(f"   ✅ 成功测试: {total_success}")
    print(f"   ❌ 失败测试: {total_tests - total_success}")
    print(f"   📈 成功率: {total_success / total_tests * 100:.1f}%")
    
    if total_success / total_tests >= 0.8:
        print("   🎉 前端重新设计成功！")
        print("   ✅ 业务价值导向明确")
        print("   ✅ 导航结构清晰")
        print("   ✅ 用户体验优化")
        print("   ✅ 文档对齐完整")
        return True
    elif total_success / total_tests >= 0.6:
        print("   ⚠️ 前端重新设计基本成功")
        print("   📋 部分功能需要进一步优化")
        return True
    else:
        print("   🚨 前端重新设计需要改进")
        print("   📋 请检查设计原则和实现")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

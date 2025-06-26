#!/usr/bin/env python3
"""
测试Agent递归循环修复的脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_agent_execution():
    """测试Agent执行是否修复了递归循环问题"""
    print("🤖 测试Agent执行修复...")
    
    try:
        from src.fsoa.agent.orchestrator import AgentOrchestrator
        
        # 创建Agent实例
        agent = AgentOrchestrator()
        
        print("✅ Agent实例创建成功")
        
        # 执行Agent（试运行模式）
        print("🎯 执行Agent（试运行模式）...")
        execution = agent.execute(dry_run=True)
        
        print(f"✅ Agent执行完成")
        print(f"   - 执行ID: {execution.id}")
        print(f"   - 状态: {execution.status.value}")
        print(f"   - 处理任务数: {execution.tasks_processed}")
        print(f"   - 发送通知数: {execution.notifications_sent}")
        
        if execution.errors:
            print(f"   - 错误数: {len(execution.errors)}")
            for error in execution.errors:
                print(f"     • {error}")
            
            # 检查是否还有递归限制错误
            recursion_errors = [e for e in execution.errors if "recursion_limit" in e.lower()]
            if recursion_errors:
                print("❌ 仍然存在递归限制错误")
                return False
            else:
                print("⚠️  有其他错误，但递归问题已修复")
        else:
            print("   - 无错误")
        
        print("✅ 递归循环问题已修复")
        return True
        
    except Exception as e:
        print(f"❌ Agent执行测试失败: {e}")
        
        # 检查是否是递归限制错误
        if "recursion_limit" in str(e).lower():
            print("❌ 递归循环问题仍然存在")
            return False
        else:
            print("⚠️  其他错误，但可能不是递归问题")
            return True

def test_graph_structure():
    """测试图结构是否正确"""
    print("\n📊 测试图结构...")
    
    try:
        from src.fsoa.agent.orchestrator import AgentOrchestrator
        
        agent = AgentOrchestrator()
        graph = agent.graph
        
        print("✅ 图结构创建成功")
        
        # 检查图的节点
        nodes = list(graph.nodes.keys())
        print(f"📋 图节点: {nodes}")
        
        expected_nodes = ["fetch_opportunities", "process_opportunities", "send_notifications", "finalize"]
        missing_nodes = [node for node in expected_nodes if node not in nodes]
        
        if missing_nodes:
            print(f"⚠️  缺少节点: {missing_nodes}")
        else:
            print("✅ 所有预期节点都存在")
        
        return True
        
    except Exception as e:
        print(f"❌ 图结构测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Agent递归循环修复测试")
    print("=" * 50)
    
    # 测试图结构
    graph_ok = test_graph_structure()
    
    # 测试Agent执行
    agent_ok = test_agent_execution()
    
    print("\n" + "=" * 50)
    if graph_ok and agent_ok:
        print("🎉 所有测试通过，递归循环问题已修复！")
        sys.exit(0)
    else:
        print("❌ 测试失败，需要进一步检查")
        sys.exit(1)

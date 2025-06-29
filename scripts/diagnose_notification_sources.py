#!/usr/bin/env python3
"""
诊断通知消息来源

分析当前系统中所有可能的通知发送路径，找出不规范消息的来源
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_notification_tasks():
    """检查notification_tasks表中的任务"""
    print("📋 检查notification_tasks表")
    print("-" * 40)
    
    try:
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        # 获取所有通知任务
        with db_manager.get_session() as session:
            from src.fsoa.data.database import NotificationTaskTable
            
            # 统计各种状态的任务
            total_tasks = session.query(NotificationTaskTable).count()
            pending_tasks = session.query(NotificationTaskTable).filter(
                NotificationTaskTable.status == 'pending'
            ).count()
            sent_tasks = session.query(NotificationTaskTable).filter(
                NotificationTaskTable.status == 'sent'
            ).count()
            failed_tasks = session.query(NotificationTaskTable).filter(
                NotificationTaskTable.status == 'failed'
            ).count()
            
            print(f"总任务数: {total_tasks}")
            print(f"待发送: {pending_tasks}")
            print(f"已发送: {sent_tasks}")
            print(f"发送失败: {failed_tasks}")
            
            # 检查最近的任务
            recent_tasks = session.query(NotificationTaskTable).filter(
                NotificationTaskTable.created_at >= datetime.now() - timedelta(hours=24)
            ).order_by(NotificationTaskTable.created_at.desc()).limit(5).all()
            
            if recent_tasks:
                print(f"\n最近24小时的任务:")
                for task in recent_tasks:
                    print(f"  ID: {task.id}, 类型: {task.notification_type}, 状态: {task.status}")
                    print(f"      工单: {task.order_num}, 组织: {task.org_name}")
                    print(f"      创建: {task.created_at}")
                    if task.message:
                        preview = task.message[:100] + "..." if len(task.message) > 100 else task.message
                        print(f"      消息预览: {preview}")
                    print()
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_agent_runs():
    """检查Agent执行记录"""
    print("🤖 检查Agent执行记录")
    print("-" * 40)
    
    try:
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            from src.fsoa.data.database import AgentRunTable
            
            # 获取最近的Agent执行记录
            recent_runs = session.query(AgentRunTable).filter(
                AgentRunTable.trigger_time >= datetime.now() - timedelta(hours=24)
            ).order_by(AgentRunTable.trigger_time.desc()).limit(10).all()
            
            if recent_runs:
                print(f"最近24小时的Agent执行:")
                for run in recent_runs:
                    print(f"  ID: {run.id}, 状态: {run.status}")
                    print(f"      触发时间: {run.trigger_time}")
                    print(f"      处理商机: {run.opportunities_processed}")
                    print(f"      发送通知: {run.notifications_sent}")
                    if run.errors:
                        print(f"      错误: {run.errors[:200]}...")
                    print()
            else:
                print("最近24小时没有Agent执行记录")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_scheduler_status():
    """检查调度器状态"""
    print("⏰ 检查调度器状态")
    print("-" * 40)
    
    try:
        from src.fsoa.utils.scheduler import get_scheduler
        
        scheduler = get_scheduler()
        
        if scheduler.is_running():
            print("✅ 调度器正在运行")
            
            jobs = scheduler.get_jobs()
            print(f"当前任务数: {len(jobs)}")
            
            for job in jobs:
                print(f"  任务ID: {job.id}")
                print(f"  函数: {job.func}")
                print(f"  下次执行: {job.next_run_time}")
                print()
        else:
            print("❌ 调度器未运行")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_llm_configuration():
    """检查LLM配置"""
    print("🧠 检查LLM配置")
    print("-" * 40)
    
    try:
        from src.fsoa.utils.config import get_config
        
        config = get_config()
        
        # 检查DeepSeek配置
        has_deepseek = hasattr(config, 'deepseek_api_key') and config.deepseek_api_key
        print(f"DeepSeek API配置: {'✅' if has_deepseek else '❌'}")
        
        # 检查是否启用LLM
        use_llm = getattr(config, 'use_llm_optimization', True)
        print(f"LLM优化启用: {'✅' if use_llm else '❌'}")
        
        # 测试LLM连接
        if has_deepseek:
            try:
                from src.fsoa.agent.llm import get_deepseek_client
                client = get_deepseek_client()
                print("✅ LLM客户端创建成功")
                
                # 这里可以添加简单的连接测试
                print("⚠️  注意: LLM可能正在生成不规范的消息格式")
                
            except Exception as e:
                print(f"❌ LLM客户端创建失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_legacy_systems():
    """检查旧系统残留"""
    print("🗂️ 检查旧系统残留")
    print("-" * 40)
    
    try:
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            # 检查是否还有废弃表
            from sqlalchemy import text
            
            result = session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE '%deprecated%'
            """))
            
            deprecated_tables = result.fetchall()
            
            if deprecated_tables:
                print("⚠️  发现废弃表:")
                for table in deprecated_tables:
                    print(f"  - {table[0]}")
                print("建议运行: python scripts/remove_deprecated_tables.py")
            else:
                print("✅ 没有发现废弃表")
            
            # 检查是否有旧的任务数据
            try:
                result = session.execute(text("SELECT COUNT(*) FROM tasks_deprecated"))
                count = result.fetchone()[0]
                if count > 0:
                    print(f"⚠️  发现 {count} 条旧任务数据")
            except:
                pass  # 表不存在是正常的
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def analyze_message_sources():
    """分析消息来源"""
    print("🔍 分析可能的消息来源")
    print("-" * 40)
    
    print("当前系统中存在以下通知路径:")
    print()
    
    print("1. 🆕 新的通知任务系统 (推荐)")
    print("   - 文件: notification_manager.py")
    print("   - 格式: 标准化的业务格式")
    print("   - 状态: ✅ 正常使用")
    print()
    
    print("2. 🧠 LLM生成消息 (可能问题来源)")
    print("   - 文件: agent/llm.py")
    print("   - 格式: AI生成，格式不固定")
    print("   - 状态: ⚠️  可能生成不规范消息")
    print()
    
    print("3. 🗂️ 旧Agent系统 (已废弃)")
    print("   - 文件: agent/orchestrator.py, agent/tools.py")
    print("   - 格式: 基于OpportunityInfo的商机数据")
    print("   - 状态: ✅ 已迁移到新架构")
    print()
    
    print("4. 📝 手动执行脚本")
    print("   - 文件: scripts/check_notification_tasks.py")
    print("   - 格式: 测试消息")
    print("   - 状态: ❓ 需要检查是否有人在运行")
    print()


def provide_recommendations():
    """提供建议"""
    print("💡 解决建议")
    print("-" * 40)
    
    print("1. 🚫 禁用LLM消息生成")
    print("   在配置中设置: use_llm_optimization = False")
    print("   或修改LLM提示词以生成标准格式")
    print()
    
    print("2. 🧹 清理旧系统")
    print("   运行: python scripts/remove_deprecated_tables.py")
    print("   停止旧的Agent调度器")
    print()
    
    print("3. ✅ 确保使用新系统")
    print("   检查只有notification_manager在发送消息")
    print("   验证所有消息都通过business_formatter格式化")
    print()
    
    print("4. 📊 监控消息格式")
    print("   添加消息格式验证")
    print("   记录消息来源信息")
    print()


def main():
    """主函数"""
    print("🔍 FSOA 通知消息来源诊断")
    print("=" * 60)
    print("分析您看到的不规范消息格式的来源")
    print("=" * 60)
    
    try:
        # 1. 检查notification_tasks表
        check_notification_tasks()
        print()
        
        # 2. 检查Agent执行记录
        check_agent_runs()
        print()
        
        # 3. 检查调度器状态
        check_scheduler_status()
        print()
        
        # 4. 检查LLM配置
        check_llm_configuration()
        print()
        
        # 5. 检查旧系统残留
        check_legacy_systems()
        print()
        
        # 6. 分析消息来源
        analyze_message_sources()
        print()
        
        # 7. 提供建议
        provide_recommendations()
        
        print("=" * 60)
        print("🎯 诊断完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

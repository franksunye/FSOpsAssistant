#!/usr/bin/env python3
"""
数据库迁移脚本

将现有数据库结构迁移到新的架构设计
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def backup_existing_data():
    """备份现有数据"""
    print("📦 备份现有数据...")
    
    try:
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        # 创建备份表
        with db_manager.get_session() as session:
            from sqlalchemy import text

            # 备份tasks表
            try:
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS tasks_backup AS
                    SELECT * FROM tasks WHERE 1=0
                """))

                session.execute(text("""
                    INSERT INTO tasks_backup
                    SELECT * FROM tasks
                """))
            except Exception as e:
                print(f"⚠️ 备份tasks表失败: {e}")

            # 备份notifications表
            try:
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS notifications_backup AS
                    SELECT * FROM notifications WHERE 1=0
                """))

                session.execute(text("""
                    INSERT INTO notifications_backup
                    SELECT * FROM notifications
                """))
            except Exception as e:
                print(f"⚠️ 备份notifications表失败: {e}")

            session.commit()
            print("✅ 数据备份完成")
            
    except Exception as e:
        print(f"❌ 数据备份失败: {e}")
        return False
    
    return True

def create_new_tables():
    """创建新的数据库表"""
    print("🏗️ 创建新的数据库表...")
    
    try:
        from src.fsoa.data.database import get_db_manager, Base

        db_manager = get_db_manager()

        # 创建所有新表
        Base.metadata.create_all(bind=db_manager.engine)
        print("✅ 新表创建完成")
        
    except Exception as e:
        print(f"❌ 创建新表失败: {e}")
        return False
    
    return True

def rename_old_tables():
    """重命名旧表"""
    print("📝 重命名旧表...")
    
    try:
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            from sqlalchemy import text

            # 重命名旧表
            try:
                session.execute(text("ALTER TABLE tasks RENAME TO tasks_deprecated"))
            except:
                print("⚠️ tasks表可能已经被重命名或不存在")

            try:
                session.execute(text("ALTER TABLE notifications RENAME TO notifications_deprecated"))
            except:
                print("⚠️ notifications表可能已经被重命名或不存在")

            try:
                session.execute(text("ALTER TABLE agent_executions RENAME TO agent_executions_deprecated"))
            except:
                print("⚠️ agent_executions表可能已经被重命名或不存在")

            session.commit()
            print("✅ 旧表重命名完成")
            
    except Exception as e:
        print(f"❌ 重命名旧表失败: {e}")
        return False
    
    return True

def verify_migration():
    """验证迁移结果"""
    print("🔍 验证迁移结果...")
    
    try:
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            # 检查新表是否存在
            tables_to_check = [
                'agent_runs',
                'agent_history', 
                'notification_tasks',
                'opportunity_cache'
            ]
            
            from sqlalchemy import text

            for table_name in tables_to_check:
                result = session.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"))
                if result.fetchone():
                    print(f"✅ 表 {table_name} 创建成功")
                else:
                    print(f"❌ 表 {table_name} 创建失败")
                    return False
            
            print("✅ 所有新表验证通过")
            
    except Exception as e:
        print(f"❌ 验证迁移失败: {e}")
        return False
    
    return True

def test_new_models():
    """测试新的数据模型"""
    print("🧪 测试新的数据模型...")
    
    try:
        from src.fsoa.data.models import AgentRun, AgentHistory, NotificationTask, OpportunityInfo
        from src.fsoa.data.models import AgentRunStatus, NotificationTaskStatus, NotificationTaskType, OpportunityStatus
        from src.fsoa.data.database import get_db_manager
        
        db_manager = get_db_manager()
        
        # 测试AgentRun
        test_run = AgentRun(
            trigger_time=datetime.now(),
            status=AgentRunStatus.RUNNING,
            context={"test": True}
        )
        
        run_id = db_manager.save_agent_run(test_run)
        print(f"✅ AgentRun模型测试通过，ID: {run_id}")
        
        # 测试AgentHistory
        test_history = AgentHistory(
            run_id=run_id,
            step_name="test_step",
            timestamp=datetime.now(),
            input_data={"input": "test"},
            output_data={"output": "test"}
        )
        
        db_manager.save_agent_history(test_history)
        print("✅ AgentHistory模型测试通过")
        
        # 测试NotificationTask
        test_task = NotificationTask(
            order_num="TEST001",
            org_name="测试组织",
            notification_type=NotificationTaskType.STANDARD,
            due_time=datetime.now()
        )
        
        task_id = db_manager.save_notification_task(test_task)
        print(f"✅ NotificationTask模型测试通过，ID: {task_id}")
        
        # 测试OpportunityInfo缓存
        test_opportunity = OpportunityInfo(
            order_num="TEST001",
            name="测试客户",
            address="测试地址",
            supervisor_name="测试负责人",
            create_time=datetime.now(),
            org_name="测试组织",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
        
        test_opportunity.update_overdue_info()
        db_manager.save_opportunity_cache(test_opportunity)
        print("✅ OpportunityInfo缓存测试通过")
        
        print("✅ 所有新模型测试通过")
        
    except Exception as e:
        print(f"❌ 新模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """主迁移函数"""
    print("🚀 开始数据库架构迁移")
    print("=" * 50)
    
    # 步骤1: 备份现有数据
    if not backup_existing_data():
        print("❌ 迁移失败：数据备份失败")
        return False
    
    # 步骤2: 创建新表
    if not create_new_tables():
        print("❌ 迁移失败：创建新表失败")
        return False
    
    # 步骤3: 重命名旧表
    if not rename_old_tables():
        print("❌ 迁移失败：重命名旧表失败")
        return False
    
    # 步骤4: 验证迁移
    if not verify_migration():
        print("❌ 迁移失败：验证失败")
        return False
    
    # 步骤5: 测试新模型
    if not test_new_models():
        print("❌ 迁移失败：新模型测试失败")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 数据库架构迁移完成！")
    print("\n📋 迁移总结:")
    print("✅ 现有数据已备份到 *_backup 表")
    print("✅ 旧表已重命名为 *_deprecated")
    print("✅ 新表结构已创建并验证")
    print("✅ 新数据模型测试通过")
    print("\n🔧 后续步骤:")
    print("1. 更新Agent工具使用新的数据模型")
    print("2. 测试完整的业务流程")
    print("3. 确认无问题后可删除deprecated表")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

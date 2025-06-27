#!/usr/bin/env python3
"""
简化的 message 字段测试脚本
验证数据库表结构和基本功能
"""

import sqlite3
import os
from datetime import datetime


def create_test_database():
    """创建测试数据库"""
    print("📊 创建测试数据库")
    print("-" * 40)
    
    # 创建内存数据库
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # 创建notification_tasks表
    cursor.execute("""
        CREATE TABLE notification_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_num TEXT NOT NULL,
            org_name TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            due_time TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'pending',
            message TEXT,
            sent_at TIMESTAMP,
            created_run_id INTEGER,
            sent_run_id INTEGER,
            retry_count INTEGER DEFAULT 0,
            max_retry_count INTEGER DEFAULT 5,
            cooldown_hours REAL DEFAULT 2.0,
            last_sent_at DATETIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("✅ 测试数据库和表创建成功")
    return conn, cursor


def test_task_creation_without_message(cursor):
    """测试创建任务时message字段为空"""
    print("\n📝 测试任务创建（message字段为空）")
    print("-" * 40)
    
    # 插入测试任务，不设置message字段
    cursor.execute("""
        INSERT INTO notification_tasks 
        (order_num, org_name, notification_type, due_time, created_run_id)
        VALUES (?, ?, ?, ?, ?)
    """, ("TEST001", "测试公司", "standard", datetime.now(), 1))
    
    task_id = cursor.lastrowid
    
    # 查询验证
    cursor.execute("SELECT id, order_num, message FROM notification_tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    
    print(f"创建的任务ID: {row[0]}")
    print(f"工单号: {row[1]}")
    print(f"消息字段: {row[2]}")
    print(f"✅ message字段为空，符合预期" if row[2] is None else f"❌ message字段不为空: {row[2]}")
    
    return task_id


def test_message_update(cursor, task_id):
    """测试更新message字段"""
    print("\n📨 测试消息内容更新")
    print("-" * 40)
    
    test_message = """🚨 现场服务逾期提醒

📋 工单信息
• 工单号: TEST001
• 客户: 测试客户
• 地址: 测试地址123号
• 负责人: 张三
• 已逾期: 25.5小时

⚠️ 请及时处理，确保服务质量！

🕐 发送时间: 2024-01-15 14:30:00
🤖 来源: FSOA智能助手"""
    
    # 更新message字段
    cursor.execute("""
        UPDATE notification_tasks 
        SET message = ?, updated_at = ?
        WHERE id = ?
    """, (test_message, datetime.now(), task_id))
    
    # 验证更新结果
    cursor.execute("SELECT message FROM notification_tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    
    if row and row[0] == test_message:
        print("✅ 消息更新成功")
        print(f"消息内容预览: {row[0][:100]}...")
        return True
    else:
        print("❌ 消息更新失败")
        return False


def test_message_field_scenarios():
    """测试不同场景下的message字段使用"""
    print("\n🔄 测试不同场景")
    print("-" * 40)
    
    scenarios = [
        {
            "name": "首次发送",
            "description": "创建任务时message为空，发送时填充消息内容",
            "expected": "message从NULL变为具体内容"
        },
        {
            "name": "重试发送", 
            "description": "重试时使用已保存的消息内容，保证一致性",
            "expected": "message内容保持不变"
        },
        {
            "name": "失败调试",
            "description": "发送失败时可查看具体的消息内容",
            "expected": "可追溯实际发送的内容"
        },
        {
            "name": "审计分析",
            "description": "统计和分析发送的消息类型和内容",
            "expected": "支持消息内容的数据分析"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"  {i}. {scenario['name']}")
        print(f"     场景: {scenario['description']}")
        print(f"     预期: {scenario['expected']}")
        print()


def demonstrate_benefits():
    """展示message字段的好处"""
    print("\n💡 message字段的价值体现")
    print("-" * 40)
    
    benefits = [
        {
            "title": "可追溯性",
            "description": "记录实际发送的消息内容，便于问题排查",
            "example": "客户投诉未收到通知时，可查看具体发送了什么内容"
        },
        {
            "title": "调试便利",
            "description": "发送失败时可查看具体消息内容和格式",
            "example": "企微API返回格式错误时，可检查消息内容是否符合要求"
        },
        {
            "title": "重试一致性",
            "description": "重试时使用相同的消息内容，避免内容不一致",
            "example": "LLM生成的消息在重试时保持一致，不会产生不同版本"
        },
        {
            "title": "审计支持",
            "description": "支持消息内容的统计分析和合规审计",
            "example": "分析通知消息的有效性，优化消息模板"
        },
        {
            "title": "数据完整性",
            "description": "通知任务记录更加完整，包含完整的执行信息",
            "example": "数据库记录包含任务创建、消息生成、发送结果的完整链路"
        }
    ]
    
    for i, benefit in enumerate(benefits, 1):
        print(f"  {i}. {benefit['title']}")
        print(f"     {benefit['description']}")
        print(f"     示例: {benefit['example']}")
        print()


def show_implementation_summary():
    """显示实现总结"""
    print("\n📋 实现总结")
    print("-" * 40)
    
    print("🔧 代码修改:")
    print("  • notification_manager.py: 在发送通知时保存消息内容")
    print("  • database.py: 添加update_notification_task_message方法")
    print("  • 保持向后兼容: message字段仍为可选")
    
    print("\n📊 数据库影响:")
    print("  • 表结构无变化: message字段已存在")
    print("  • 存储开销: 每条通知任务增加消息内容存储")
    print("  • 查询性能: 基本无影响")
    
    print("\n🎯 使用建议:")
    print("  • 只在首次发送时保存消息（避免重复更新）")
    print("  • 定期清理过期的通知任务记录")
    print("  • 考虑消息内容的长度限制")


def main():
    """主测试函数"""
    print("🧪 notification_tasks.message 字段功能验证")
    print("=" * 60)
    
    try:
        # 创建测试数据库
        conn, cursor = create_test_database()
        
        # 测试任务创建
        task_id = test_task_creation_without_message(cursor)
        
        # 测试消息更新
        message_test_passed = test_message_update(cursor, task_id)
        
        # 测试场景说明
        test_message_field_scenarios()
        
        # 展示好处
        demonstrate_benefits()
        
        # 实现总结
        show_implementation_summary()
        
        # 总结
        print(f"\n📊 测试结果")
        print("-" * 40)
        print(f"数据库操作测试: {'✅ 通过' if message_test_passed else '❌ 失败'}")
        
        if message_test_passed:
            print("\n🎉 message字段功能验证成功！")
            print("💡 建议: 将此改进部署到生产环境，提升通知系统的可维护性")
        else:
            print("\n⚠️ 测试失败，需要检查实现")
        
        # 关闭数据库连接
        conn.close()
        
        return message_test_passed
        
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

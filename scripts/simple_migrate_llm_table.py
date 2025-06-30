#!/usr/bin/env python3
"""
简化的LLM调用记录表迁移脚本

直接使用SQL创建LLM调用记录表，避免复杂的依赖
"""

import sqlite3
import os
from datetime import datetime


def create_llm_table():
    """创建LLM调用记录表"""
    print("🚀 开始创建LLM调用记录表...")
    
    # 数据库文件路径
    db_path = "fsoa.db"
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否已存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='llm_call_records'
        """)
        
        if cursor.fetchone():
            print("⚠️ LLM调用记录表已存在，跳过创建")
            conn.close()
            return True
        
        # 创建表的SQL
        create_table_sql = """
        CREATE TABLE llm_call_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id VARCHAR(100) NOT NULL UNIQUE,
            timestamp DATETIME NOT NULL,
            opportunity_id VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL,
            
            -- 输入数据
            context_data JSON,
            prompt_text TEXT,
            model_name VARCHAR(100) NOT NULL,
            temperature REAL NOT NULL,
            max_tokens INTEGER NOT NULL,
            
            -- 输出数据
            response_text TEXT,
            parsed_result JSON,
            
            -- 性能指标
            duration_ms REAL,
            tokens_used INTEGER,
            tokens_prompt INTEGER,
            tokens_completion INTEGER,
            
            -- 错误信息
            error_message TEXT,
            error_type VARCHAR(100),
            
            -- 决策信息
            rule_suggestion JSON,
            final_decision JSON,
            
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        print("📋 创建LLM调用记录表...")
        cursor.execute(create_table_sql)
        
        # 创建索引
        print("📊 创建索引...")
        indexes = [
            "CREATE INDEX idx_llm_call_id ON llm_call_records(call_id)",
            "CREATE INDEX idx_llm_timestamp ON llm_call_records(timestamp)",
            "CREATE INDEX idx_llm_opportunity_id ON llm_call_records(opportunity_id)",
            "CREATE INDEX idx_llm_status ON llm_call_records(status)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # 提交更改
        conn.commit()
        
        print("✅ LLM调用记录表创建成功！")
        
        # 验证表结构
        cursor.execute("PRAGMA table_info(llm_call_records)")
        columns = cursor.fetchall()
        
        print(f"📊 表结构验证 - 共 {len(columns)} 个字段:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 创建LLM调用记录表失败: {e}")
        return False


def test_llm_table():
    """测试LLM调用记录表功能"""
    print("\n🧪 测试LLM调用记录表功能...")
    
    db_path = "fsoa.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 测试插入记录
        print("📝 测试插入记录...")
        test_record = {
            'call_id': 'test_call_001',
            'timestamp': datetime.now().isoformat(),
            'opportunity_id': 'TEST001',
            'status': 'success',
            'context_data': '{"test": "data"}',
            'prompt_text': '测试提示词',
            'model_name': 'deepseek-chat',
            'temperature': 0.1,
            'max_tokens': 1000,
            'response_text': '{"action": "notify"}',
            'parsed_result': '{"action": "notify"}',
            'duration_ms': 1500.0,
            'tokens_used': 250,
            'tokens_prompt': 180,
            'tokens_completion': 70
        }
        
        insert_sql = """
        INSERT INTO llm_call_records (
            call_id, timestamp, opportunity_id, status,
            context_data, prompt_text, model_name, temperature, max_tokens,
            response_text, parsed_result, duration_ms, tokens_used, tokens_prompt, tokens_completion
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(insert_sql, (
            test_record['call_id'], test_record['timestamp'], test_record['opportunity_id'], test_record['status'],
            test_record['context_data'], test_record['prompt_text'], test_record['model_name'], 
            test_record['temperature'], test_record['max_tokens'],
            test_record['response_text'], test_record['parsed_result'], test_record['duration_ms'],
            test_record['tokens_used'], test_record['tokens_prompt'], test_record['tokens_completion']
        ))
        
        conn.commit()
        print("✅ 插入记录成功")
        
        # 测试查询记录
        print("🔍 测试查询记录...")
        cursor.execute("SELECT * FROM llm_call_records WHERE call_id = ?", (test_record['call_id'],))
        record = cursor.fetchone()
        
        if record:
            print(f"✅ 查询记录成功，记录ID: {record[0]}")
        else:
            print("❌ 查询记录失败")
            conn.close()
            return False
        
        # 测试统计功能
        print("📊 测试统计功能...")
        cursor.execute("SELECT COUNT(*) FROM llm_call_records")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM llm_call_records WHERE status = 'success'")
        success_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(duration_ms) FROM llm_call_records WHERE duration_ms IS NOT NULL")
        avg_duration = cursor.fetchone()[0]
        
        print(f"✅ 统计功能正常:")
        print(f"   - 总记录数: {total_count}")
        print(f"   - 成功记录数: {success_count}")
        print(f"   - 平均响应时间: {avg_duration:.1f}ms")
        
        # 测试更新记录
        print("🔄 测试更新记录...")
        cursor.execute(
            "UPDATE llm_call_records SET error_message = ? WHERE call_id = ?",
            ("测试更新", test_record['call_id'])
        )
        conn.commit()
        
        if cursor.rowcount > 0:
            print("✅ 更新记录成功")
        else:
            print("❌ 更新记录失败")
            conn.close()
            return False
        
        conn.close()
        print("🎉 所有测试通过！LLM调用记录表功能正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_table_info():
    """显示表信息"""
    print("\n📊 LLM调用记录表信息:")
    
    db_path = "fsoa.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='llm_call_records'
        """)
        
        if not cursor.fetchone():
            print("❌ LLM调用记录表不存在")
            conn.close()
            return
        
        # 获取表结构
        cursor.execute("PRAGMA table_info(llm_call_records)")
        columns = cursor.fetchall()
        
        print(f"📋 表结构 ({len(columns)} 个字段):")
        for col in columns:
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            default = f" DEFAULT {col[4]}" if col[4] else ""
            print(f"   {col[0]:2d}. {col[1]:20s} {col[2]:15s} {nullable}{default}")
        
        # 获取记录统计
        cursor.execute("SELECT COUNT(*) FROM llm_call_records")
        total_count = cursor.fetchone()[0]
        
        if total_count > 0:
            cursor.execute("SELECT COUNT(*) FROM llm_call_records WHERE status = 'success'")
            success_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM llm_call_records WHERE status = 'failed'")
            failed_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM llm_call_records")
            time_range = cursor.fetchone()
            
            print(f"\n📈 数据统计:")
            print(f"   - 总记录数: {total_count}")
            print(f"   - 成功记录: {success_count}")
            print(f"   - 失败记录: {failed_count}")
            print(f"   - 成功率: {success_count/total_count:.1%}")
            print(f"   - 时间范围: {time_range[0]} ~ {time_range[1]}")
        else:
            print(f"\n📈 数据统计: 暂无记录")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取表信息失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM调用记录表迁移脚本")
    parser.add_argument("--test-only", action="store_true", help="仅运行测试，不创建表")
    parser.add_argument("--info-only", action="store_true", help="仅显示表信息")
    parser.add_argument("--force", action="store_true", help="强制重新创建表")
    
    args = parser.parse_args()
    
    print("🔧 FSOA LLM调用记录表迁移脚本")
    print("=" * 50)
    
    if args.info_only:
        show_table_info()
        return 0
    
    success = True
    
    if not args.test_only:
        if args.force:
            print("⚠️ 强制模式：将删除现有表并重新创建")
            try:
                conn = sqlite3.connect("fsoa.db")
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS llm_call_records")
                conn.commit()
                conn.close()
                print("🗑️ 已删除现有表")
            except Exception as e:
                print(f"⚠️ 删除现有表时出错: {e}")
        
        success = create_llm_table()
    
    if success:
        success = test_llm_table()
    
    if success:
        show_table_info()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 LLM调用记录表迁移完成！")
        print("\n📋 后续步骤:")
        print("   1. 重启FSOA应用")
        print("   2. 访问LLM监控页面")
        print("   3. 验证数据持久化功能")
        print("   4. 查看'💾 数据管理'标签页")
    else:
        print("❌ LLM调用记录表迁移失败！")
        print("\n🔧 故障排查:")
        print("   1. 检查数据库文件权限")
        print("   2. 确认SQLite版本支持")
        print("   3. 查看详细错误信息")
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

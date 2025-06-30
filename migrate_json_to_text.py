#!/usr/bin/env python3
"""
数据库迁移脚本：将JSON列改为TEXT列
解决SQLite中JSON列存储Unicode转义序列的问题
"""

import sqlite3
import json
from pathlib import Path

def migrate_database():
    """迁移数据库结构和数据"""
    
    db_path = "fsoa.db"
    backup_path = "fsoa_backup_before_json_migration.db"
    
    print("=== SQLite JSON列迁移脚本 ===")
    print(f"数据库文件: {db_path}")
    
    # 检查数据库文件是否存在
    if not Path(db_path).exists():
        print(f"❌ 数据库文件 {db_path} 不存在")
        return False
    
    # 创建备份
    print(f"📋 创建备份: {backup_path}")
    import shutil
    shutil.copy2(db_path, backup_path)
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查当前表结构
        print("\n🔍 检查当前表结构...")
        
        # 检查llm_call_records表
        cursor.execute("PRAGMA table_info(llm_call_records)")
        columns = cursor.fetchall()
        
        json_columns = []
        for col in columns:
            col_name, col_type = col[1], col[2]
            if col_type == 'JSON':
                json_columns.append(col_name)
        
        if json_columns:
            print(f"发现JSON列: {json_columns}")
            
            # 迁移llm_call_records表
            print("\n🔄 迁移 llm_call_records 表...")
            migrate_llm_call_records(cursor)
            
            # 迁移agent_runs表
            print("\n🔄 迁移 agent_runs 表...")
            migrate_agent_runs(cursor)
            
            # 迁移agent_history表
            print("\n🔄 迁移 agent_history 表...")
            migrate_agent_history(cursor)
            
            conn.commit()
            print("\n✅ 数据库迁移完成!")
            
        else:
            print("✅ 数据库已经是最新结构，无需迁移")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def migrate_llm_call_records(cursor):
    """迁移llm_call_records表"""
    
    # 创建新表结构
    cursor.execute("""
        CREATE TABLE llm_call_records_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id VARCHAR(100) NOT NULL UNIQUE,
            timestamp DATETIME NOT NULL,
            opportunity_id VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL,
            
            -- 输入数据
            context_data TEXT,
            prompt_text TEXT,
            model_name VARCHAR(100) NOT NULL,
            temperature REAL NOT NULL,
            max_tokens INTEGER NOT NULL,
            
            -- 输出数据
            response_text TEXT,
            parsed_result TEXT,
            
            -- 性能指标
            duration_ms REAL,
            tokens_used INTEGER,
            tokens_prompt INTEGER,
            tokens_completion INTEGER,
            
            -- 错误信息
            error_message TEXT,
            error_type VARCHAR(100),
            
            -- 决策信息
            rule_suggestion TEXT,
            final_decision TEXT,
            
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 迁移数据，确保JSON字段正确序列化
    cursor.execute("SELECT * FROM llm_call_records")
    records = cursor.fetchall()
    
    # 获取列名
    cursor.execute("PRAGMA table_info(llm_call_records)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print(f"  迁移 {len(records)} 条记录...")
    
    for record in records:
        record_dict = dict(zip(columns, record))
        
        # 处理JSON字段
        json_fields = ['context_data', 'parsed_result', 'rule_suggestion', 'final_decision']
        for field in json_fields:
            if field in record_dict and record_dict[field] is not None:
                value = record_dict[field]
                if isinstance(value, str):
                    # 如果已经是字符串，确保是可读的JSON
                    try:
                        # 尝试解析并重新序列化
                        parsed = json.loads(value)
                        record_dict[field] = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
                    except (json.JSONDecodeError, TypeError):
                        # 如果解析失败，保持原值
                        pass
                else:
                    # 如果是其他类型，序列化为JSON
                    record_dict[field] = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        
        # 插入新表
        placeholders = ', '.join(['?' for _ in columns])
        values = [record_dict[col] for col in columns]
        
        cursor.execute(f"""
            INSERT INTO llm_call_records_new ({', '.join(columns)})
            VALUES ({placeholders})
        """, values)
    
    # 删除旧表，重命名新表
    cursor.execute("DROP TABLE llm_call_records")
    cursor.execute("ALTER TABLE llm_call_records_new RENAME TO llm_call_records")
    
    # 重建索引
    cursor.execute("CREATE INDEX idx_llm_call_id ON llm_call_records(call_id)")
    cursor.execute("CREATE INDEX idx_llm_timestamp ON llm_call_records(timestamp)")
    cursor.execute("CREATE INDEX idx_llm_opportunity_id ON llm_call_records(opportunity_id)")
    cursor.execute("CREATE INDEX idx_llm_status ON llm_call_records(status)")
    
    print("  ✅ llm_call_records 表迁移完成")

def migrate_agent_runs(cursor):
    """迁移agent_runs表"""
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_runs'")
    if not cursor.fetchone():
        print("  ⏭️  agent_runs 表不存在，跳过")
        return
    
    # 创建新表结构
    cursor.execute("""
        CREATE TABLE agent_runs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_time DATETIME NOT NULL,
            end_time DATETIME,
            status VARCHAR(50) NOT NULL,
            context TEXT,
            opportunities_processed INTEGER DEFAULT 0,
            notifications_sent INTEGER DEFAULT 0,
            errors TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 迁移数据
    cursor.execute("SELECT * FROM agent_runs")
    records = cursor.fetchall()
    
    cursor.execute("PRAGMA table_info(agent_runs)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print(f"  迁移 {len(records)} 条记录...")
    
    for record in records:
        record_dict = dict(zip(columns, record))
        
        # 处理JSON字段
        json_fields = ['context', 'errors']
        for field in json_fields:
            if field in record_dict and record_dict[field] is not None:
                value = record_dict[field]
                if not isinstance(value, str):
                    record_dict[field] = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        
        # 插入新表
        placeholders = ', '.join(['?' for _ in columns])
        values = [record_dict[col] for col in columns]
        
        cursor.execute(f"""
            INSERT INTO agent_runs_new ({', '.join(columns)})
            VALUES ({placeholders})
        """, values)
    
    # 删除旧表，重命名新表
    cursor.execute("DROP TABLE agent_runs")
    cursor.execute("ALTER TABLE agent_runs_new RENAME TO agent_runs")
    
    print("  ✅ agent_runs 表迁移完成")

def migrate_agent_history(cursor):
    """迁移agent_history表"""
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_history'")
    if not cursor.fetchone():
        print("  ⏭️  agent_history 表不存在，跳过")
        return
    
    # 创建新表结构
    cursor.execute("""
        CREATE TABLE agent_history_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            step_name VARCHAR(100) NOT NULL,
            input_data TEXT,
            output_data TEXT,
            timestamp DATETIME NOT NULL,
            duration_seconds REAL,
            error_message TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 迁移数据
    cursor.execute("SELECT * FROM agent_history")
    records = cursor.fetchall()
    
    cursor.execute("PRAGMA table_info(agent_history)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print(f"  迁移 {len(records)} 条记录...")
    
    for record in records:
        record_dict = dict(zip(columns, record))
        
        # 处理JSON字段
        json_fields = ['input_data', 'output_data']
        for field in json_fields:
            if field in record_dict and record_dict[field] is not None:
                value = record_dict[field]
                if not isinstance(value, str):
                    record_dict[field] = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        
        # 插入新表
        placeholders = ', '.join(['?' for _ in columns])
        values = [record_dict[col] for col in columns]
        
        cursor.execute(f"""
            INSERT INTO agent_history_new ({', '.join(columns)})
            VALUES ({placeholders})
        """, values)
    
    # 删除旧表，重命名新表
    cursor.execute("DROP TABLE agent_history")
    cursor.execute("ALTER TABLE agent_history_new RENAME TO agent_history")
    
    print("  ✅ agent_history 表迁移完成")

def verify_migration():
    """验证迁移结果"""
    
    print("\n=== 验证迁移结果 ===")
    
    conn = sqlite3.connect("fsoa.db")
    cursor = conn.cursor()
    
    try:
        # 检查表结构
        cursor.execute("PRAGMA table_info(llm_call_records)")
        columns = cursor.fetchall()
        
        print("llm_call_records 表结构:")
        for col in columns:
            col_name, col_type = col[1], col[2]
            print(f"  {col_name}: {col_type}")
        
        # 检查数据示例
        cursor.execute("SELECT call_id, context_data, parsed_result FROM llm_call_records LIMIT 2")
        records = cursor.fetchall()
        
        print(f"\n数据示例 (共{len(records)}条):")
        for record in records:
            call_id, context_data, parsed_result = record
            print(f"  {call_id}:")
            if context_data:
                print(f"    context_data: {context_data[:100]}...")
            if parsed_result:
                print(f"    parsed_result: {parsed_result[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate_database()
    if success:
        verify_migration()
        print(f"\n🎉 迁移完成！")
        print(f"📋 备份文件: fsoa_backup_before_json_migration.db")
        print(f"💡 现在JSON数据将以可读格式存储在数据库中")
    else:
        print(f"\n❌ 迁移失败，请检查错误信息")

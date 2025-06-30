import sqlite3

conn = sqlite3.connect('fsoa.db')
cursor = conn.cursor()

# 检查升级任务数量
cursor.execute("SELECT COUNT(*) FROM notification_tasks WHERE notification_type = 'escalation' AND status = 'pending'")
escalation_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT org_name) FROM notification_tasks WHERE notification_type = 'escalation' AND status = 'pending'")
org_count = cursor.fetchone()[0]

print(f'升级任务数: {escalation_count}')
print(f'组织数: {org_count}')

if escalation_count == org_count:
    print('✅ 每个组织只有一个升级任务 - 系统正常')
else:
    print('❌ 存在重复升级任务')

conn.close()

# FSOA API 接口文档

Field Service Operations Assistant - API接口规范

## 1. 接口设计原则

### 1.1 RESTful设计
- 使用标准HTTP方法（GET, POST, PUT, DELETE）
- 资源导向的URL设计
- 统一的响应格式
- 适当的HTTP状态码

### 1.2 数据格式
- 请求和响应均使用JSON格式
- 时间格式使用ISO 8601标准
- 分页使用标准的offset/limit模式

### 1.3 错误处理
```json
{
    "error": {
        "code": "TASK_NOT_FOUND",
        "message": "指定的任务不存在",
        "details": {
            "task_id": 123
        }
    }
}
```

## 2. Agent管理接口

### 2.1 获取Agent状态
```http
GET /api/agent/status
```

**响应示例：**
```json
{
    "status": "running",
    "last_execution": "2025-06-25T10:00:00Z",
    "next_execution": "2025-06-25T11:00:00Z",
    "tasks_processed": 15,
    "notifications_sent": 3,
    "errors": 0
}
```

### 2.2 手动触发Agent执行
```http
POST /api/agent/trigger
```

**请求体：**
```json
{
    "force": false,
    "dry_run": true
}
```

**响应示例：**
```json
{
    "execution_id": "exec_20250625_100001",
    "status": "started",
    "estimated_duration": 30
}
```

### 2.3 获取Agent执行历史
```http
GET /api/agent/executions?limit=20&offset=0
```

**响应示例：**
```json
{
    "executions": [
        {
            "id": "exec_20250625_100001",
            "start_time": "2025-06-25T10:00:00Z",
            "end_time": "2025-06-25T10:00:30Z",
            "status": "completed",
            "tasks_processed": 5,
            "notifications_sent": 2,
            "errors": []
        }
    ],
    "total": 100,
    "limit": 20,
    "offset": 0
}
```

## 3. 任务管理接口

### 3.1 获取任务列表
```http
GET /api/tasks?status=overdue&limit=50&offset=0
```

**查询参数：**
- `status`: 任务状态 (all, overdue, notified, resolved)
- `group_id`: 企微群ID过滤
- `limit`: 每页数量 (默认20, 最大100)
- `offset`: 偏移量

**响应示例：**
```json
{
    "tasks": [
        {
            "id": 123,
            "title": "现场设备维护",
            "status": "in_progress",
            "sla_hours": 8,
            "elapsed_hours": 10.5,
            "overdue_hours": 2.5,
            "group_id": "group_001",
            "created_at": "2025-06-25T08:00:00Z",
            "updated_at": "2025-06-25T10:00:00Z",
            "last_notification": "2025-06-25T10:00:00Z"
        }
    ],
    "total": 25,
    "limit": 50,
    "offset": 0
}
```

### 3.2 获取任务详情
```http
GET /api/tasks/{task_id}
```

**响应示例：**
```json
{
    "id": 123,
    "title": "现场设备维护",
    "description": "客户现场设备需要定期维护",
    "status": "in_progress",
    "priority": "high",
    "sla_hours": 8,
    "elapsed_hours": 10.5,
    "overdue_hours": 2.5,
    "group_id": "group_001",
    "assignee": "张三",
    "customer": "ABC公司",
    "location": "北京市朝阳区",
    "created_at": "2025-06-25T08:00:00Z",
    "updated_at": "2025-06-25T10:00:00Z",
    "notifications": [
        {
            "id": 456,
            "type": "overdue_alert",
            "message": "任务已超时2.5小时，请及时处理",
            "sent_at": "2025-06-25T10:00:00Z",
            "status": "sent"
        }
    ]
}
```

### 3.3 更新任务状态
```http
PUT /api/tasks/{task_id}/status
```

**请求体：**
```json
{
    "status": "resolved",
    "comment": "任务已完成，设备运行正常"
}
```

## 4. 通知管理接口

### 4.1 获取通知历史
```http
GET /api/notifications?task_id=123&limit=20&offset=0
```

**响应示例：**
```json
{
    "notifications": [
        {
            "id": 456,
            "task_id": 123,
            "type": "overdue_alert",
            "priority": "high",
            "message": "任务已超时2.5小时，请及时处理",
            "group_id": "group_001",
            "sent_at": "2025-06-25T10:00:00Z",
            "status": "sent",
            "delivery_status": "delivered"
        }
    ],
    "total": 10,
    "limit": 20,
    "offset": 0
}
```

### 4.2 发送自定义通知
```http
POST /api/notifications/send
```

**请求体：**
```json
{
    "task_id": 123,
    "group_id": "group_001",
    "message": "自定义提醒消息",
    "priority": "normal"
}
```

### 4.3 撤回通知
```http
DELETE /api/notifications/{notification_id}
```

## 5. 配置管理接口

### 5.1 获取系统配置
```http
GET /api/config
```

**响应示例：**
```json
{
    "notification_settings": {
        "max_notifications_per_hour": 10,
        "notification_cooldown_minutes": 30,
        "escalation_threshold_hours": 4
    },
    "agent_settings": {
        "execution_interval_minutes": 60,
        "use_llm_optimization": true,
        "llm_temperature": 0.1
    },
    "group_settings": [
        {
            "group_id": "group_001",
            "name": "运维组A",
            "webhook_url": "https://qyapi.weixin.qq.com/...",
            "enabled": true
        }
    ]
}
```

### 5.2 更新配置
```http
PUT /api/config
```

**请求体：**
```json
{
    "notification_settings": {
        "max_notifications_per_hour": 15
    }
}
```

## 6. 统计分析接口

### 6.1 获取统计数据
```http
GET /api/stats?period=7d
```

**查询参数：**
- `period`: 统计周期 (1d, 7d, 30d)
- `group_id`: 按群组过滤

**响应示例：**
```json
{
    "period": "7d",
    "summary": {
        "total_tasks": 150,
        "overdue_tasks": 25,
        "notifications_sent": 45,
        "resolution_rate": 0.85,
        "avg_response_time_hours": 2.5
    },
    "daily_stats": [
        {
            "date": "2025-06-25",
            "tasks_processed": 20,
            "notifications_sent": 5,
            "overdue_count": 3
        }
    ]
}
```

### 6.2 获取性能指标
```http
GET /api/metrics
```

**响应示例：**
```json
{
    "agent_performance": {
        "avg_execution_time_seconds": 15.5,
        "success_rate": 0.98,
        "error_rate": 0.02
    },
    "notification_performance": {
        "delivery_rate": 0.99,
        "avg_delivery_time_seconds": 2.1
    },
    "system_health": {
        "cpu_usage": 0.25,
        "memory_usage": 0.45,
        "disk_usage": 0.30
    }
}
```

## 7. Webhook接口

### 7.1 接收企微回调
```http
POST /api/webhooks/wechat
```

**请求体：**
```json
{
    "msgtype": "text",
    "text": {
        "content": "任务123已完成"
    },
    "from": {
        "userid": "zhangsan"
    }
}
```

## 8. 错误码定义

| 错误码 | HTTP状态码 | 描述 |
|--------|------------|------|
| SUCCESS | 200 | 请求成功 |
| INVALID_REQUEST | 400 | 请求参数错误 |
| UNAUTHORIZED | 401 | 未授权访问 |
| FORBIDDEN | 403 | 禁止访问 |
| NOT_FOUND | 404 | 资源不存在 |
| CONFLICT | 409 | 资源冲突 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| SERVICE_UNAVAILABLE | 503 | 服务不可用 |

### 业务错误码
- `TASK_NOT_FOUND`: 任务不存在
- `AGENT_BUSY`: Agent正在执行中
- `NOTIFICATION_FAILED`: 通知发送失败
- `CONFIG_INVALID`: 配置参数无效
- `RATE_LIMIT_EXCEEDED`: 请求频率超限

---
> API接口遵循RESTful设计原则，保持简洁和一致性
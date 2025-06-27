# 配置迁移说明

## 概述

为了提供更好的用户体验，我们将部分配置项从环境变量文件（.env）迁移到数据库管理，用户可以通过Web UI进行配置。

## 已迁移的配置项

### Agent配置
| 配置项 | 原环境变量 | 新管理方式 | 说明 |
|--------|------------|------------|------|
| 执行间隔 | `AGENT_EXECUTION_INTERVAL` | 数据库 + Web UI | Agent自动执行的时间间隔（分钟） |
| 最大重试次数 | `AGENT_MAX_RETRIES` | 数据库 + Web UI | Agent任务失败时的最大重试次数 |

### LLM配置
| 配置项 | 原环境变量 | 新管理方式 | 说明 |
|--------|------------|------------|------|
| LLM优化开关 | `USE_LLM_OPTIMIZATION` | 数据库 + Web UI | 是否启用AI智能决策优化 |
| LLM温度参数 | `LLM_TEMPERATURE` | 数据库 + Web UI | AI决策的随机性控制（0-1） |

### 通知配置
| 配置项 | 原环境变量 | 新管理方式 | 说明 |
|--------|------------|------------|------|
| 每小时最大通知数 | `MAX_NOTIFICATIONS_PER_HOUR` | 数据库 + Web UI | 单个群组每小时最大通知数量 |
| 通知冷却时间 | `NOTIFICATION_COOLDOWN` | 数据库 + Web UI | 同一商机通知间隔时间（分钟） |
| 升级阈值 | `ESCALATION_THRESHOLD_HOURS` | 数据库 + Web UI | 超时多久后升级到运营群（小时） |

## 保留的配置项

以下配置项仍保留在环境变量文件中，因为它们是技术配置，不需要用户经常修改：

### 核心服务配置
- `DEEPSEEK_API_KEY` - DeepSeek API密钥
- `DEEPSEEK_BASE_URL` - DeepSeek API地址
- `METABASE_URL` - Metabase服务地址
- `METABASE_USERNAME` - Metabase用户名
- `METABASE_PASSWORD` - Metabase密码
- `INTERNAL_OPS_WEBHOOK` - 内部运营群Webhook URL
- `DATABASE_URL` - 数据库连接字符串

### 技术配置
- `AGENT_TIMEOUT` - Agent执行超时时间（秒）
- `LLM_MAX_TOKENS` - LLM响应最大token数
- `USE_LLM_MESSAGE_FORMATTING` - 是否使用LLM消息格式化（实验性）
- `MAX_RETRY_COUNT` - 降级方案的最大重试次数

### 系统配置
- `LOG_LEVEL` - 日志级别
- `LOG_FILE` - 日志文件路径
- `DEBUG` - 调试模式开关
- `TESTING` - 测试模式开关

## 如何使用新的配置管理

### 1. 通过Web UI配置
1. 访问FSOA Web界面
2. 进入"系统管理"页面
3. 在"Agent设置"和"通知设置"选项卡中修改配置
4. 点击"保存"按钮

### 2. 配置生效机制
- **立即生效**：Web UI中的配置更改会立即保存到数据库
- **下次执行生效**：Agent在下次执行时会从数据库读取最新配置
- **调度器重启**：执行间隔的更改需要重启调度器才能生效

### 3. 配置优先级
1. **数据库配置**：优先级最高，用于业务配置
2. **环境变量**：用于技术配置和降级方案
3. **代码默认值**：最后的降级方案

## 迁移后的优势

### 1. 用户友好
- 无需编辑配置文件
- 通过Web界面直观配置
- 实时保存，无需重启服务

### 2. 配置管理
- 配置变更有记录
- 支持配置验证
- 降级机制保证系统稳定性

### 3. 运维便利
- 减少配置文件管理复杂度
- 支持动态配置调整
- 配置与代码分离

## 注意事项

### 1. 现有环境
- 现有的.env文件中的相关配置项已被注释或移除
- 系统会自动使用数据库中的配置
- 如果数据库中没有配置，会使用代码中的默认值

### 2. 备份建议
- 在修改重要配置前，建议备份数据库
- 记录重要的配置变更

### 3. 故障排除
- 如果配置不生效，检查数据库中的`system_config`表
- 查看日志文件了解配置加载情况
- 必要时可以通过数据库直接修改配置

## 数据库表结构

配置存储在`system_config`表中：

```sql
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at DATETIME NOT NULL
);
```

常用配置项：
- `agent_execution_interval` - Agent执行间隔（分钟）
- `use_llm_optimization` - 是否启用LLM优化（true/false）
- `llm_temperature` - LLM温度参数（0.0-1.0）
- `agent_max_retries` - Agent最大重试次数
- `max_notifications_per_hour` - 每小时最大通知数
- `notification_cooldown` - 通知冷却时间（分钟）
- `escalation_threshold` - 升级阈值（小时）

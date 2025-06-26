# FSOA 通知架构重构报告

**重构日期**: 2025-06-26  
**版本**: v0.3.0  
**GitHub提交**: 待提交

## 🎯 重构目标

基于用户的架构问题反馈，进行彻底的通知系统重构：

1. **统一通知流程** - 所有通知都通过 `notification_tasks` 表管理
2. **删除旧Agent逻辑** - 彻底移除 `TaskInfo`、`fetch_overdue_tasks` 等废弃代码
3. **可选LLM格式化** - 在统一架构下支持LLM或模板格式化
4. **简化架构** - 移除不必要的格式验证和补丁逻辑

## 🏗️ 新架构设计

### 统一通知流程
```
商机数据 (OpportunityInfo)
    ↓
NotificationManager.create_notification_tasks()
    ↓
notification_tasks 表
    ↓
NotificationManager.execute_pending_tasks()
    ↓
消息格式化 (LLM 或 模板)
    ↓
企微发送
```

### 核心组件

#### 1. **NotificationManager** (核心管理器)
- **职责**: 统一管理所有通知任务
- **功能**: 创建任务、执行任务、格式化消息
- **配置**: 支持LLM或模板格式化

#### 2. **notification_tasks 表** (统一存储)
- **职责**: 存储所有通知任务
- **字段**: order_num, org_name, notification_type, status, message等
- **状态**: pending → sent/failed

#### 3. **消息格式化器** (可选择)
- **模板格式化**: 使用 `BusinessFormatter` 标准模板
- **LLM格式化**: 使用 DeepSeek AI 生成消息
- **配置控制**: `use_llm_message_formatting = True/False`

## 🗑️ 删除的废弃组件

### 1. **TaskInfo 模型**
```python
# ❌ 已删除
class TaskInfo(BaseModel):
    id: int
    title: str
    # ... 其他字段
```

### 2. **fetch_overdue_tasks() 函数**
```python
# ❌ 已删除
def fetch_overdue_tasks() -> List[TaskInfo]:
    # 将商机包装为TaskInfo的混乱逻辑
```

### 3. **send_notification() 函数**
```python
# ❌ 已删除
def send_notification(task: TaskInfo, message: str) -> bool:
    # 绕过notification_tasks的直接发送
```

### 4. **格式验证器**
```python
# ❌ 已删除
class MessageFormatValidator:
    # 不必要的格式检查和修复逻辑
```

## ✅ 新增功能

### 1. **LLM格式化选项**
```python
class NotificationManager:
    def __init__(self):
        # 根据配置选择格式化方式
        self.use_llm_formatting = config.use_llm_message_formatting
        if self.use_llm_formatting:
            self.llm_client = get_deepseek_client()
    
    def _format_notification_message(self, org_name, tasks, notification_type):
        if self.use_llm_formatting:
            return self._format_with_llm(...)
        else:
            return self._format_with_template(...)
```

### 2. **配置选项**
```python
class Config(BaseSettings):
    # 新增配置项
    use_llm_message_formatting: bool = Field(
        default=False,
        description="是否使用LLM格式化通知消息"
    )
```

### 3. **LLM提示词优化**
```python
def _build_llm_formatting_prompt(self, org_name, opportunities, notification_type):
    """构建专业的LLM格式化提示词"""
    prompt = f"""请为以下{type_desc}生成专业的企微群消息。
    
    要求：
    1. 使用适当的emoji（🚨违规、⚠️逾期、🔥升级）
    2. 格式清晰，信息完整
    3. 语气专业但紧迫
    4. 包含明确的行动指示
    5. 长度控制在500字以内
    """
```

## 📊 架构对比

### 重构前（问题架构）
```
❌ 多个并行流程:
1. 商机 → NotificationManager → notification_tasks → 标准格式
2. 商机 → TaskInfo → LLM → 直接发送 (绕过notification_tasks)
3. 格式验证器 → 修复不规范消息

❌ 问题:
- 通知记录不完整
- 格式不一致
- 架构复杂
- 难以维护
```

### 重构后（清洁架构）
```
✅ 统一流程:
商机 → NotificationManager → notification_tasks → 格式化 → 发送

✅ 优势:
- 所有通知都有记录
- 格式化可配置
- 架构简洁
- 易于维护
```

## 🔧 使用方式

### 1. **标准模板格式化**（默认）
```python
# 配置
use_llm_message_formatting = False

# 结果：使用BusinessFormatter的标准模板
🚨 **违规通知** - 12小时未处理
组织：XXX公司
违规工单数：3
...
```

### 2. **LLM格式化**（可选）
```python
# 配置
use_llm_message_formatting = True

# 结果：LLM生成的专业消息
🚨 紧急通知：XXX公司有3个工单违规超时
工单详情：
1. 工单号：12345，客户：张先生...
请立即处理，确保客户服务质量！
```

### 3. **统一管理**
```python
# 所有通知都通过统一接口
notification_manager = get_notification_manager()

# 创建任务（自动保存到notification_tasks表）
tasks = notification_manager.create_notification_tasks(opportunities, run_id)

# 执行任务（自动格式化和发送）
result = notification_manager.execute_pending_tasks(run_id)
```

## 📈 重构收益

### 1. **架构清洁**
- ✅ 单一通知流程
- ✅ 统一数据管理
- ✅ 清晰的职责分离

### 2. **功能完整**
- ✅ 所有通知都有记录
- ✅ 支持重试和状态管理
- ✅ 完整的执行追踪

### 3. **灵活配置**
- ✅ 可选择LLM或模板格式化
- ✅ 配置驱动的行为
- ✅ 易于切换和测试

### 4. **维护性**
- ✅ 代码简洁
- ✅ 逻辑清晰
- ✅ 易于扩展

## 🚀 部署指南

### 1. **默认配置**（推荐）
```bash
# 使用标准模板格式化
export USE_LLM_MESSAGE_FORMATTING=false
```

### 2. **启用LLM格式化**
```bash
# 使用LLM生成消息
export USE_LLM_MESSAGE_FORMATTING=true
export DEEPSEEK_API_KEY=your_api_key
```

### 3. **验证部署**
```python
# 检查配置
from src.fsoa.utils.config import get_config
config = get_config()
print(f"LLM格式化: {config.use_llm_message_formatting}")

# 测试通知
from src.fsoa.agent.tools import send_business_notifications
result = send_business_notifications(opportunities)
```

## 🎯 总结

本次重构彻底解决了用户提出的架构问题：

### ✅ **解决的问题**
1. **统一了通知流程** - 所有通知都通过notification_tasks表
2. **删除了旧逻辑** - 彻底移除TaskInfo和相关废弃代码
3. **简化了架构** - 移除不必要的格式验证和补丁
4. **支持LLM选项** - 在统一架构下可选择LLM格式化

### 🏗️ **新架构特点**
- **单一数据流**: 商机 → NotificationManager → notification_tasks → 发送
- **配置驱动**: 通过配置选择格式化方式
- **完整记录**: 所有通知都有完整的生命周期管理
- **易于维护**: 清洁的代码结构和明确的职责分离

### 🎉 **核心改进**
从"多个混乱的并行流程"到"统一的清洁架构"

---
**重构完成**: ✅ 架构清洁、功能完整、易于维护  
**用户反馈**: ✅ 所有架构问题已解决

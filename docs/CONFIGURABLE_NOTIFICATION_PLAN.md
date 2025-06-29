# 可配置通知功能实现计划

## 概述

基于用户需求，设计并实现可配置的SLA通知功能，支持只发送提醒通知而不发送升级通知的场景。

## 需求分析

**当前状态**：
- 提醒通知（4/8小时）→ 服务商群
- 升级通知（8/16小时）→ 运营群

**目标状态**：
- 可配置是否发送提醒通知
- 可配置是否发送升级通知
- 默认：只发送提醒通知，不发送升级通知

## 技术方案

### 1. 配置项设计

在`system_config`表中新增配置项：

```sql
-- 通知开关配置
INSERT INTO system_config (config_key, config_value, description) VALUES
('notification_reminder_enabled', 'true', '是否启用提醒通知（4/8小时）→服务商群'),
('notification_escalation_enabled', 'false', '是否启用升级通知（8/16小时）→运营群');
```

### 2. 代码改动点

#### 2.1 数据库初始化 (`src/fsoa/data/database.py`)
- 在`_init_default_config`方法中添加新配置项

#### 2.2 通知管理器 (`src/fsoa/agent/managers/notification_manager.py`)
- 在`NotificationTaskManager.__init__`中添加配置属性
- 在`_load_config_from_db`方法中加载通知开关配置
- 在`create_notification_tasks`方法中添加配置检查逻辑

#### 2.3 Web界面 (`src/fsoa/ui/app.py`)
- 在系统管理页面添加通知开关配置界面

### 3. 实现优势

1. **最小化改动**：只需要在现有代码中添加配置检查
2. **向后兼容**：不改变现有API和数据结构
3. **灵活配置**：支持4种通知场景组合
4. **敏捷开发**：可分阶段实现，逐步验证

## 实现步骤

### 阶段1：数据库配置（30分钟）
1. 修改`database.py`添加默认配置项
2. 运行数据库初始化脚本
3. 验证配置项正确创建

**文件修改**：
- `src/fsoa/data/database.py`

### 阶段2：通知管理器改动（60分钟）
1. 在`NotificationTaskManager`中添加配置加载
2. 在通知任务创建中添加配置检查
3. 添加相关日志记录
4. 编写单元测试验证功能

**文件修改**：
- `src/fsoa/agent/managers/notification_manager.py`

### 阶段3：Web界面配置（45分钟）
1. 在系统管理页面添加通知开关
2. 实现配置保存功能
3. 测试界面交互

**文件修改**：
- `src/fsoa/ui/app.py`

### 阶段4：集成测试（30分钟）
1. 测试不同配置场景下的通知行为
2. 验证配置持久化和生效
3. 确认向后兼容性

## 配置场景

### 场景1：只发送提醒通知（推荐默认）
```
notification_reminder_enabled = true
notification_escalation_enabled = false
```
- ✅ 发送4/8小时提醒通知到服务商群
- ❌ 不发送8/16小时升级通知到运营群

### 场景2：完整两级通知
```
notification_reminder_enabled = true
notification_escalation_enabled = true
```
- ✅ 发送4/8小时提醒通知到服务商群
- ✅ 发送8/16小时升级通知到运营群

### 场景3：只发送升级通知
```
notification_reminder_enabled = false
notification_escalation_enabled = true
```
- ❌ 不发送4/8小时提醒通知
- ✅ 只发送8/16小时升级通知到运营群

### 场景4：关闭所有通知
```
notification_reminder_enabled = false
notification_escalation_enabled = false
```
- ❌ 不发送任何SLA通知（仅计算SLA状态）

## 风险评估

### 低风险
- 配置项为新增，不影响现有功能
- 代码改动集中在通知创建逻辑，影响范围可控
- 默认配置满足用户需求

### 缓解措施
- 分阶段实现，每个阶段独立验证
- 保持向后兼容，现有功能不受影响
- 添加详细日志，便于问题排查

## 验收标准

1. **功能验收**
   - [ ] 配置项正确创建和加载
   - [ ] 通知开关正确控制通知创建
   - [ ] Web界面配置功能正常
   - [ ] 不同场景下通知行为符合预期

2. **兼容性验收**
   - [ ] 现有通知功能不受影响
   - [ ] 现有API和数据结构保持不变
   - [ ] 升级后系统正常运行

3. **用户体验验收**
   - [ ] 配置界面简洁易用
   - [ ] 配置说明清晰明确
   - [ ] 配置生效及时

## 后续扩展

1. **细粒度控制**：支持按组织或商机状态配置通知开关
2. **时间窗口控制**：支持配置通知发送的时间窗口
3. **频率控制**：支持配置通知发送频率限制
4. **模板配置**：支持配置不同类型通知的消息模板

---

**预计总工时**：2.5小时  
**实现优先级**：高  
**技术复杂度**：低  
**业务价值**：高

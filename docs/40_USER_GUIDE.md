# FSOA 用户指南

Field Service Operations Assistant - 现场服务运营助手

## 1. 系统概述

FSOA是一个具备**主动性、自主决策、目标导向**的AI Agent系统，专为现场服务运营而设计：

### 1.1 核心价值
- **🎯 两级SLA监控**：4小时提醒 + 8小时升级的智能分级通知
- **🧠 智能决策**：规则引擎+LLM混合决策，基于真实业务数据分析
- **📱 智能路由**：提醒通知到组织群，升级通知到运营群
- **📊 统一数据架构**：基于OpportunityInfo的一致性数据模型
- **🏗️ 管理器模式**：DataStrategy、Notification、Decision三大管理器

### 1.2 业务场景
- **商机时效监控**：自动监控"待预约"、"暂不上门"等状态的SLA合规性
- **分级通知机制**：4小时提醒通知，8小时升级通知的渐进式处理
- **运营效率提升**：减少80%的重复性监控工作，提升响应速度
- **服务质量保障**：通过及时提醒提高商机跟进效率和转化率

## 2. 快速开始

### 2.1 访问系统
1. 打开浏览器，访问：`http://your-server:8501`
2. 系统无需登录，直接进入智能运营仪表板

### 2.2 界面布局
```
┌─────────────────────────────────────────────────────────┐
│                🤖 FSOA 智能运营仪表板                    │
│              现场服务运营助手 - 主动监控•智能决策•自动通知  │
├─────────────────┬───────────────────────────────────────┤
│  📊 核心监控     │           🎯 核心业务指标              │
│  🎯 运营仪表板   │  🤖Agent状态  ⚠️逾期商机  🚨升级处理   │
│  📋 商机监控     │                                      │
│  📈 业务分析     │           🚀 Agent智能化价值           │
│                │  🎯主动监控  🧠智能决策  📱自动通知      │
│  🤖 Agent管理   │                                      │
│  🎛️ Agent控制台 │           ⚡ 快速操作                 │
│  🔍 执行历史     │  🚀立即执行  📋查看商机  📬管理通知     │
│  📬 通知管理     │                                      │
│                │                                      │
│  ⚙️ 系统管理     │                                      │
│  💾 缓存管理     │                                      │
│  🔧 企微群配置   │                                      │
│  🧪 系统测试     │                                      │
└─────────────────┴───────────────────────────────────────┘
```

## 3. 功能详解

### 3.1 🎯 运营仪表板
**功能说明：** 系统核心价值展示和快速操作入口

**核心业务指标：**
- **🤖 Agent状态**：智能监控运行状态，实时显示系统健康度
- **⚠️ 逾期商机**：当前需要关注的超时商机数量
- **🚨 升级处理**：需要升级处理的紧急商机数量
- **🏢 涉及组织**：受影响的组织数量和缓存性能

**Agent智能化价值展示：**
- **🎯 主动监控**：7x24小时自动扫描，实时识别超时风险，无需人工干预
- **🧠 智能决策**：规则引擎+LLM混合决策，基于上下文智能判断，自适应策略调整
- **📱 自动通知**：多企微群差异化通知，智能去重和频率控制，升级机制自动触发

**快速操作：**
- **🚀 立即执行Agent**：手动触发Agent执行完整监控流程
- **📋 查看商机列表**：跳转到商机监控页面查看详细信息
- **📬 管理通知任务**：跳转到通知管理页面处理待发送任务
- **🔄 刷新数据**：刷新当前页面数据

### 3.2 📋 商机监控
**功能说明：** 实时监控现场服务商机时效状态

**商机信息字段：**
- **工单号**：Metabase中的唯一标识符
- **客户名称**：服务对象名称
- **服务地址**：现场服务地址
- **负责人**：现场服务负责人
- **创建时间**：商机创建时间
- **所属组织**：负责的运营组织
- **当前状态**：待预约/暂不上门/已完成等
- **已用时长**：从创建到现在的时间
- **超时状态**：是否超过SLA时间
- **升级级别**：0=正常，1=需要升级处理

**智能筛选：**
```
┌─────────────────────────────────────────────────────┐
│ 状态: [全部▼] 组织: [全部▼] 超时: [全部▼] 升级: [全部▼] │
│ 搜索: [工单号/客户名称/地址]              [🔍 搜索]  │
└─────────────────────────────────────────────────────┘
```

**智能操作：**
- **查看详情**：点击商机行查看完整信息和处理历史
- **手动通知**：对特定商机立即发送通知
- **标记处理**：更新商机处理状态
- **批量操作**：选择多个商机进行批量通知

### 3.3 🤖 Agent控制台
**功能说明：** Agent生命周期管理和执行监控

**Agent状态监控：**
- **运行状态**：当前Agent是否正在运行
- **调度器状态**：定时任务调度器状态
- **活跃任务数**：当前正在执行的任务数量
- **下次执行时间**：预计下次自动执行时间

**执行控制：**
- **🚀 立即执行Agent**：手动触发完整的监控流程
  - 获取商机数据 → 创建通知任务 → 执行通知发送 → 记录结果
  - 显示详细的执行统计：执行ID、处理商机数、发送通知数、失败数
- **🧪 试运行**：模拟执行流程，不实际发送通知
  - 显示缓存状态和统计信息
  - 预览将要处理的商机数量

**调度器管理：**
- **▶️ 启动调度器**：启动定时任务调度
- **⏸️ 停止调度器**：停止自动执行
- **🔄 重启调度器**：重新启动调度服务
- **📊 刷新状态**：更新当前状态信息

### 3.4 🔍 执行历史
**功能说明：** Agent执行历史和性能分析

**执行统计：**
- **总运行次数**：Agent历史执行总次数
- **成功运行**：成功完成的执行次数
- **失败运行**：执行失败的次数
- **平均耗时**：每次执行的平均时间

**步骤性能分析：**
- **fetch_opportunities**：获取商机数据的性能统计
- **process_opportunities**：处理商机逻辑的性能统计
- **send_notifications**：发送通知的性能统计
- 每个步骤显示：执行次数、成功次数、平均耗时

### 3.5 📬 通知管理
**功能说明：** 通知任务状态管理和监控

**通知统计：**
- **总任务数**：创建的通知任务总数
- **已发送**：成功发送的通知数量
- **发送失败**：发送失败的通知数量
- **待处理**：等待发送的通知数量

**待处理任务列表：**
- **工单号**：关联的商机工单号
- **组织**：负责的运营组织
- **类型**：standard（标准通知）/escalation（升级通知）
- **状态**：pending（待发送）/sent（已发送）/failed（失败）
- **应发送时间**：计划发送的时间
- **重试次数**：失败后的重试次数
- **消息内容**：通知的具体内容

**管理操作：**
- **🔄 刷新任务列表**：更新任务状态
- **🧹 清理旧任务**：清理已完成的历史任务

### 3.6 💾 缓存管理
**功能说明：** 业务数据缓存监控和管理

**缓存状态：**
- **缓存状态**：启用/禁用状态
- **缓存条目**：当前缓存的数据条目数
- **有效缓存**：未过期的缓存条目数
- **命中率**：缓存命中率百分比

**缓存详情：**
- **TTL设置**：缓存生存时间（小时）
- **逾期缓存**：缓存中的逾期商机数量
- **涉及组织**：缓存数据涉及的组织数量
- **缓存启用**：当前缓存策略是否启用

**缓存操作：**
- **🔄 刷新缓存**：从Metabase重新获取数据更新缓存
- **🧹 清理缓存**：清空所有缓存数据
- **🔍 验证一致性**：检查缓存数据与源数据的一致性

### 3.7 🔧 企微群配置
**功能说明：** 管理企业微信群组配置和通知路由

**群组配置界面：**
```
┌─────────────────────────────────────────────────────────────┐
│ 群组名称    │ Webhook地址           │ 状态   │ 通知限制 │ 操作 │
├─────────────────────────────────────────────────────────────┤
│ 运维组A     │ https://qyapi.weixin... │ 启用   │ 10/小时  │ 编辑 │
│ 运维组B     │ https://qyapi.weixin... │ 启用   │ 10/小时  │ 编辑 │
│ 运维组C     │ https://qyapi.weixin... │ 禁用   │ 10/小时  │ 编辑 │
└─────────────────────────────────────────────────────────────┘
[+ 添加新群组]
```

**配置参数说明：**
- **群组名称**：用于标识不同的运营团队，建议使用组织的实际名称
- **Webhook地址**：企业微信群机器人的完整Webhook URL
- **启用状态**：控制该群组是否接收通知
- **通知限制**：每小时最大通知数量，防止消息轰炸
- **冷却时间**：发送通知后的等待时间，避免频繁打扰

### 3.8 🧪 系统测试
**功能说明：** 系统功能测试和调试工具

**测试功能：**
- **🔗 连接测试**：测试Metabase、DeepSeek API、企微群连接状态
- **📊 数据测试**：验证商机数据获取和处理逻辑
- **📬 通知测试**：测试通知发送功能和消息格式
- **🧪 试运行模式**：模拟Agent执行流程，不实际发送通知

**调试模式使用：**

**启用方法：**
1. **环境变量方式**：在`.env`文件中添加 `DEBUG=true`
2. **测试模式**：设置 `TESTING=true`
3. **重启应用**：重新启动Streamlit应用使配置生效

**调试模式特性：**
- **详细日志**：显示更详细的执行日志和错误信息
- **友好格式**：使用易读的控制台日志格式而非JSON格式
- **试运行功能**：在Agent控制台中提供"🧪 试运行"按钮
- **性能分析**：显示各个步骤的详细执行时间和统计信息

**试运行操作步骤：**
1. 进入"🤖 Agent控制台"页面
2. 点击"🧪 试运行 (Dry Run)"按钮
3. 系统将模拟完整的Agent执行流程：
   - 获取商机数据统计
   - 分析缓存状态
   - 预览将要处理的商机数量
   - **不会实际发送通知**
4. 查看模拟结果和性能指标

### 3.9 ⚙️ 系统管理
**功能说明：** 系统参数配置和业务规则设置

#### 3.9.1 Agent设置
```
执行频率: [60] 分钟          # Agent自动执行的时间间隔
使用LLM优化: [✓] 启用        # 是否启用AI智能决策
LLM温度参数: [0.1]          # AI决策的随机性控制(0-1)
最大重试次数: [3]           # 失败任务的最大重试次数
执行超时: [300] 秒          # 单次执行的最大时间限制
```

**参数说明：**
- **执行频率**：建议设置为30-120分钟，过短会增加系统负载
- **LLM优化**：启用后使用AI进行智能决策，提高通知的准确性
- **温度参数**：0.1为保守策略，0.5为平衡策略，0.9为激进策略
- **重试次数**：建议3-5次，避免无限重试

#### 3.9.2 通知设置
```
每小时最大通知数: [10]      # 单个群组每小时最大通知数量
通知冷却时间: [2.0] 小时    # 同一商机通知间隔时间
升级阈值: [4] 小时          # 超时多久后升级到运营群
最大重试次数: [5]           # 通知发送失败的最大重试次数
启用智能去重: [✓] 启用      # 避免重复通知的智能过滤
```

**智能去重功能详解：**

**功能原理：**
智能去重通过多重机制避免对同一商机发送重复通知：

1. **任务级去重**：检查是否已存在相同商机的待处理通知任务
2. **时间去重**：在冷却时间内不会对同一商机重复发送通知
3. **状态去重**：商机状态未发生变化时不重复通知
4. **内容去重**：相同内容的通知消息不会重复发送

**配置建议：**
- **启用场景**：适用于大部分业务场景，建议保持启用
- **禁用场景**：需要强制发送通知或测试场景下可临时禁用
- **冷却时间**：配合"通知冷却时间"参数使用，建议设置2-4小时

**去重逻辑示例：**
```
商机A在10:00发送了"待预约超时"通知
↓
10:30 Agent再次检查商机A，状态仍为"待预约"
↓
智能去重判断：距离上次通知仅30分钟，且状态未变化
↓
跳过此次通知，避免重复打扰
```

#### 3.9.3 SLA阈值设置
```
违规阈值: [12] 小时         # 超过此时间算作违规，需要立即处理
升级阈值: [24] 小时         # 超过此时间需要运营人员介入
工作时间计算: [✓] 启用      # 是否按工作时间计算SLA
工作时间: 09:00-18:00      # 工作时间范围设置
工作日: 周一至周五          # 工作日设置
```

**阈值说明：**
- **违规阈值**：触发标准通知，发送到对应组织群
- **升级阈值**：触发升级通知，发送到内部运营群
- **工作时间**：启用后仅在工作时间内计算SLA，更符合实际业务场景

## 4. 典型使用场景

### 4.1 日常监控
**场景：** 运营人员每天查看任务状态

**操作步骤：**
1. 打开FSOA系统
2. 查看仪表板了解整体状况
3. 点击"商机监控"查看具体商机
4. 关注超时商机，确认是否需要人工干预

### 4.2 处理超时商机
**场景：** 发现有商机超时需要处理

**操作步骤：**
1. 在商机列表中筛选"已超时"状态
2. 点击具体商机查看详情
3. 如需立即提醒，点击"发送提醒"
4. 联系现场人员确认情况
5. 根据反馈更新商机状态

### 4.3 配置新的企微群
**场景：** 新增一个运维团队需要接收通知

**操作步骤：**
1. 进入"⚙️ 系统管理" → "🔧 企微群配置"
2. 点击"+ 添加新群组"
3. 填写群组信息：
   - **群组名称**：如"华东运维组"（使用实际组织名称）
   - **Webhook地址**：从企微群机器人设置中复制完整URL
   - **启用状态**：选择"启用"
   - **通知限制**：设置每小时最大通知数（建议10条）
   - **冷却时间**：设置通知间隔（建议30分钟）
4. 点击"💾 保存"完成配置
5. 点击"🧪 测试"按钮验证配置是否正确

### 4.4 调整通知策略
**场景：** 发现通知过于频繁，需要调整

**操作步骤：**
1. 进入"⚙️ 系统管理" → "通知设置"
2. 调整相关参数：
   - **增加冷却时间**：从2小时改为4小时，减少通知频率
   - **降低通知数量**：从每小时10条改为5条
   - **启用智能去重**：确保勾选此选项避免重复通知
3. 点击"💾 保存通知设置"
4. 观察后续几天的通知频率是否合适

### 4.5 使用调试模式排查问题
**场景：** 系统运行异常，需要查看详细信息

**操作步骤：**
1. **启用调试模式**：
   - 编辑`.env`文件，添加 `DEBUG=true`
   - 重启Streamlit应用：`streamlit run src/fsoa/ui/app.py`
2. **使用试运行功能**：
   - 进入"🤖 Agent控制台"
   - 点击"🧪 试运行 (Dry Run)"
   - 查看模拟执行结果和性能指标
3. **查看详细日志**：
   - 日志将显示更详细的执行信息
   - 错误信息会包含完整的堆栈跟踪
4. **分析问题原因**：
   - 检查连接测试结果
   - 查看数据获取是否正常
   - 确认通知发送状态

### 4.6 智能去重功能使用
**场景：** 避免对同一商机重复发送通知

**自动去重场景：**
```
时间线示例：
10:00 - 商机A状态"待预约"，发送首次通知 ✓
10:30 - Agent检查，商机A状态仍为"待预约"，智能去重跳过 ⏭️
12:00 - Agent检查，商机A状态仍为"待预约"，距离上次通知2小时，发送提醒 ✓
12:15 - 商机A状态变更为"已预约"，系统停止后续通知 ⏹️
```

**配置建议：**
- **保持启用**：大部分情况下建议启用智能去重
- **冷却时间**：配合设置合理的通知冷却时间（2-4小时）
- **特殊情况**：如需强制发送通知，可临时禁用去重功能

## 5. 故障排查

### 5.1 Agent未运行
**症状：** 仪表板显示Agent状态为"已停止"

**排查步骤：**
1. 检查系统日志是否有错误信息
2. 确认Metabase连接是否正常
3. 检查DeepSeek API是否可用
4. 尝试手动执行Agent
5. 如问题持续，联系技术支持

### 5.2 通知发送失败
**症状：** 通知历史显示发送状态为"失败"

**排查步骤：**
1. 检查企微群Webhook地址是否正确
2. 确认群机器人是否被禁用
3. 检查网络连接是否正常
4. 尝试重新发送通知
5. 如持续失败，检查企微群设置

### 5.3 数据不更新
**症状：** 任务列表数据长时间未更新

**排查步骤：**
1. 确认Metabase服务是否正常
2. 检查数据库连接是否正常
3. 查看Agent执行日志
4. 手动触发数据同步
5. 联系系统管理员检查数据源

## 6. 最佳实践

### 6.1 日常使用建议
- **定期检查**：每天至少查看一次仪表板
- **及时响应**：收到通知后及时跟进处理
- **状态更新**：任务完成后及时更新状态
- **参数调优**：根据实际情况调整通知参数

### 6.2 配置建议
- **通知频率**：避免过于频繁的通知造成骚扰
- **群组管理**：按团队职责合理分配通知群组
- **阈值设置**：根据业务SLA合理设置超时阈值
- **备份配置**：定期备份重要的配置信息

### 6.3 性能优化
- **数据清理**：定期清理历史数据避免系统变慢
- **监控指标**：关注系统性能指标
- **资源使用**：避免在高峰期进行大量操作
- **版本更新**：及时更新到最新版本

## 7. 常见问题

### Q1: 为什么有些商机没有收到通知？
**A:** 可能的原因：
- **商机尚未超时**：未达到SLA违规阈值（默认12小时）
- **智能去重生效**：在冷却时间内或状态未变化，被智能去重过滤
- **群组被禁用**：对应的企微群组配置被禁用
- **网络连接问题**：企微Webhook连接失败
- **通知限制**：已达到每小时最大通知数量限制

### Q2: 智能去重功能是如何工作的？
**A:** 智能去重通过以下机制避免重复通知：
- **任务去重**：检查是否已有相同商机的待处理通知任务
- **时间去重**：在设定的冷却时间内不重复发送
- **状态去重**：商机状态未变化时不重复通知
- **内容去重**：相同内容的消息不会重复发送

### Q3: 调试模式如何启用和使用？
**A:** 启用调试模式的步骤：
1. 在`.env`文件中添加 `DEBUG=true`
2. 重启Streamlit应用
3. 使用"🧪 试运行"功能进行模拟测试
4. 查看详细的控制台日志输出

### Q4: Agent多久执行一次检查？
**A:** 默认每60分钟执行一次，可在"⚙️ 系统管理"中调整执行频率（建议30-120分钟）。

### Q5: 系统支持多少个企微群？
**A:** 理论上无限制，但建议不超过20个群组以确保性能和管理便利性。

### Q6: 如何查看详细的执行日志？
**A:** 查看日志的方法：
- **Web界面**：在"🔍 执行历史"页面查看Agent执行统计
- **调试模式**：启用DEBUG模式查看详细控制台输出
- **日志文件**：查看 `logs/fsoa.log` 文件获取完整日志

### Q7: 通知发送失败如何处理？
**A:** 排查步骤：
1. 检查企微群Webhook地址是否正确
2. 确认群机器人是否被禁用或删除
3. 在"🧪 系统测试"中进行连接测试
4. 查看"📬 通知管理"中的失败任务详情
5. 检查网络连接和防火墙设置

### Q8: 如何优化系统性能？
**A:** 性能优化建议：
- **缓存管理**：定期清理过期缓存，保持缓存命中率
- **执行频率**：根据业务需求调整Agent执行间隔
- **通知限制**：合理设置每小时通知数量上限
- **数据清理**：定期清理历史执行记录和通知任务

## 8. 联系支持

如遇到问题或需要帮助，请联系：
- **技术支持**：发送邮件至 support@company.com
- **产品反馈**：通过系统内的反馈功能提交
- **紧急问题**：拨打24小时支持热线 400-xxx-xxxx

---
> 用户指南持续更新，欢迎提供使用反馈和改进建议
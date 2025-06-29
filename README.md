# FSOA - Field Service Operations Assistant

🤖 **智能现场服务运营助手** - 基于Agentic AI的企业级运营自动化解决方案

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-green.svg)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/Streamlit-Latest-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 项目概述

FSOA是一个具备**主动性、自主决策、目标导向**特性的AI Agent系统，专为现场服务运营场景设计。通过智能监控、自动决策和及时通知，大幅提升运营效率，减少人工干预。

**🚀 当前状态**: ✅ v0.3.0 生产就绪 - 统一数据模型，两级SLA通知，消息模板动态化，LLM决策优化，系统架构成熟稳定。

### 核心特性

- 🔄 **智能监控**：7x24小时自动监控商机处理时效
- 📊 **两级SLA通知**：4小时提醒 + 8小时升级的分级通知机制
- 📈 **业务分析**：实时逾期率、处理时长、组织绩效分析
- 🎛️ **可视化管理**：Web界面配置企微群映射和SLA参数
- 📱 **动态消息模板**：基于数据库配置的智能消息格式化
- 🔧 **配置管理**：支持动态SLA阈值和通知参数调整
- 🤖 **LLM决策优化**：可选的DeepSeek AI决策增强

### 技术亮点

- **统一数据模型**：基于OpportunityInfo的一致性架构
- **管理器模式**：DataStrategy + Notification + Decision分层管理
- **智能缓存系统**：多级缓存提升性能和数据一致性
- **两级SLA机制**：提醒(4h) + 升级(8h)的渐进式通知
- **非侵入式集成**：通过Metabase API获取数据，不影响现有系统
- **企业级设计**：支持多组织、多群组的复杂业务场景

## 🚀 快速开始

### 环境要求

- Python 3.9+
- 必要依赖：streamlit, pandas, requests, pydantic, pydantic-settings
- 企业微信群机器人webhook
- Metabase访问权限（可选，支持模拟数据）
- DeepSeek API密钥（可选，支持纯规则模式）

### 安装部署

```bash
# 1. 克隆项目
git clone https://github.com/franksunye/FSOpsAssistant.git
cd FSOpsAssistant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量（可选）
cp .env.example .env
# 编辑 .env 文件，填入API密钥和webhook配置

# 4. 初始化数据库
python scripts/init_db.py

# 5. 启动应用
python scripts/start_full_app.py  # Web + Agent

# 6. 访问界面
# 浏览器打开：http://localhost:8501
```

### 功能验证

```bash
# 测试新功能
python scripts/test_new_features.py

# 功能演示
python scripts/demo_new_features.py

# Web界面功能
# 📊 运营仪表板 - 实时逾期任务统计
# 📈 业务分析 - 逾期率分析和组织绩效对比
# 📋 商机列表 - 逾期商机管理和导出
# 🔧 企微群配置 - 可视化配置管理
```

### 配置说明

```bash
# .env 配置示例
DEEPSEEK_API_KEY=your_deepseek_api_key
METABASE_URL=http://metabase.fsgo365.cn:3000
METABASE_USERNAME=your_username
METABASE_PASSWORD=your_password
METABASE_DATABASE_ID=1712  # 真实业务数据源
DATABASE_URL=sqlite:///fsoa.db
LOG_LEVEL=INFO

# 企微配置已迁移到Web界面
# 请使用 [系统管理 → 企微群配置] 进行配置
```

### 业务功能亮点

FSOA已实现完整的业务功能：
- **两级SLA通知**: 4小时提醒通知 + 8小时升级通知的渐进式机制
- **智能路由**: 提醒通知到组织群，升级通知到运营群
- **动态配置**: SLA阈值、通知参数支持实时调整
- **统一数据模型**: 基于OpportunityInfo的一致性架构
- **LLM决策增强**: 可选的AI决策优化和消息生成

## 🏗️ 系统架构

```
┌─────────────────┐    ┌──────────────────────────────┐
│   Metabase      │    │        FSOA Agent            │
│  (数据源)        │◄───┤  ┌─────────────────────────┐  │
└─────────────────┘    │  │  DataStrategyManager    │  │
                       │  │   (数据策略管理)         │  │
┌─────────────────┐    │  └─────────────────────────┘  │
│  企微群 A/B/C    │◄───┤  ┌─────────────────────────┐  │
│  (通知渠道)      │    │  │ NotificationManager     │  │
└─────────────────┘    │  │   (通知任务管理)         │  │
                       │  │ • DecisionEngine        │  │
┌─────────────────┐    │  │ • BusinessFormatter     │  │
│   SQLite        │◄───┤  └─────────────────────────┘  │
│  (本地存储)      │    │  ┌─────────────────────────┐  │
└─────────────────┘    │  │    Streamlit UI         │  │
                       │  │   (Web管理界面)          │  │
┌─────────────────┐    │  │ • 运营仪表板             │  │
│   DeepSeek      │◄───┤  │ • 通知管理               │  │
│  (LLM服务)      │    │  │ • 系统配置               │  │
└─────────────────┘    │  └─────────────────────────┘  │
                       └──────────────────────────────┘
```

### 核心组件

- **DataStrategyManager**：统一的数据获取和缓存管理
- **NotificationManager**：两级SLA通知任务管理
- **DecisionEngine**：规则+LLM的混合决策系统
- **BusinessFormatter**：动态消息模板和格式化
- **Web管理界面**：完整的可视化配置和监控

## 📋 功能特性

### Agent能力

- ✅ **定时执行**：基于Cron的自动化调度
- ✅ **状态管理**：完整的执行状态追踪
- ✅ **错误处理**：异常捕获和自动恢复
- ✅ **工具调用**：标准化的Function Calling

### 业务功能

- ✅ **分级通知**：orgName智能路由，标准通知和升级通知
- ✅ **业务分析**：逾期率、处理时长、组织绩效实时分析
- ✅ **商机管理**：逾期商机列表、筛选、导出功能
- ✅ **格式化通知**：按业务需求格式化工单详情和滞留时长

### 管理功能

- ✅ **运营仪表板**：实时逾期任务统计和组织绩效展示
- ✅ **企微群配置**：Web界面管理orgName到webhook映射
- ✅ **配置验证**：自动验证配置有效性，支持导入导出
- ✅ **系统监控**：Agent状态监控和系统健康度检查

## 🔧 开发指南

### 项目结构

```
FSOpsAssistant/
├── src/fsoa/              # 源代码
│   ├── agent/             # Agent核心模块
│   │   ├── orchestrator.py    # Agent编排器 (LangGraph)
│   │   ├── tools.py           # Agent工具集
│   │   ├── decision.py        # 决策引擎
│   │   ├── llm.py            # LLM集成
│   │   └── managers/          # 管理器模块
│   │       ├── data_strategy.py      # 业务数据策略
│   │       ├── notification_manager.py # 通知任务管理
│   │       └── execution_tracker.py   # 执行追踪
│   ├── analytics/         # 业务分析模块
│   ├── data/              # 数据层
│   │   ├── models.py          # 数据模型
│   │   ├── database.py        # 数据库操作
│   │   └── metabase.py        # Metabase客户端
│   ├── notification/      # 通知模块
│   │   ├── wechat.py          # 企微通知
│   │   ├── business_formatter.py # 业务消息格式化
│   │   └── templates.py       # 消息模板
│   ├── ui/                # UI界面
│   │   ├── app.py             # 主应用
│   │   └── pages/             # 页面模块
│   └── utils/             # 工具模块
├── docs/                  # 项目文档 (精简优化)
│   ├── 00_BACKLOG.md         # 待办事项
│   ├── 00_PROJECT_OVERVIEW.md # 项目概述 + 业务需求
│   ├── 00_SYSTEM_STATUS.md   # 系统状态
│   ├── 01_CHANGELOG.md       # 变更日志
│   ├── 10_ARCHITECTURE.md    # 系统架构
│   ├── 11_DATA_IMPORT_DESIGN.md # 数据导入设计
│   ├── 12_SLA_DESIGN.md      # SLA模块设计
│   ├── 13_NOTIFICATION_DESIGN.md # 通知模块设计
│   ├── 20_API.md             # API文档
│   ├── 30_DEVELOPMENT.md     # 开发指南 + 部署指南
│   ├── 31_TESTING.md         # 测试指南
│   ├── 40_USER_GUIDE.md      # 用户指南
│   └── 50_DEPLOYMENT.md      # 部署指南
├── scripts/               # 核心脚本 (已精简)
│   ├── README.md             # 脚本使用说明
│   ├── init_db.py            # 数据库初始化
│   ├── run_tests.py          # 测试运行器
│   ├── start_web.py          # Web界面启动
│   ├── start_agent.py        # Agent服务启动
│   └── start_full_app.py     # 完整应用启动
└── config/                # 配置文件目录
```

### 开发流程

1. **阅读文档**：查看 `docs/` 目录下的详细文档
2. **环境搭建**：按照 `docs/30_DEVELOPMENT.md` 配置开发环境
3. **编写代码**：遵循项目代码规范和最佳实践
4. **编写测试**：参考 `docs/31_TESTING.md` 编写测试用例
5. **提交代码**：通过Pull Request提交代码变更

### 功能测试

```bash
# 测试新功能模块
python scripts/test_new_features.py

# 完整功能演示
python scripts/demo_new_features.py

# 业务通知测试
python scripts/test_business_notifications.py
```

## 📚 文档导航

| 文档 | 描述 | 目标读者 |
|------|------|----------|
| [项目概述](docs/00_PROJECT_OVERVIEW.md) | 项目背景、目标、业务需求 | 所有人 |
| [系统架构](docs/10_ARCHITECTURE.md) | 技术架构和设计原则 | 开发团队 |
| [数据导入设计](docs/11_DATA_IMPORT_DESIGN.md) | 数据导入模块详细设计 | 开发团队 |
| [SLA设计](docs/12_SLA_DESIGN.md) | SLA模块详细设计 | 开发团队 |
| [通知设计](docs/13_NOTIFICATION_DESIGN.md) | 通知模块详细设计 | 开发团队 |
| [开发指南](docs/30_DEVELOPMENT.md) | 开发环境、部署指南 | 开发团队 |
| [用户指南](docs/40_USER_GUIDE.md) | 使用说明和操作指南 | 最终用户 |

## 🎯 使用场景

### 典型工作流程

1. **数据获取**：从Metabase获取逾期商机数据
2. **业务分析**：计算逾期率、处理时长、组织绩效
3. **分级通知**：标准通知到orgName对应企微群，升级通知到运营群
4. **格式化消息**：按业务需求格式化工单详情和滞留时长
5. **配置管理**：Web界面管理企微群映射和通知参数
6. **实时监控**：运营仪表板展示业务数据和系统状态

### 业务价值

- **自动化监控**：替代人工监控，7x24小时实时检测
- **精准通知**：按组织分级通知，减少无关干扰
- **数据驱动**：实时业务指标支持运营决策
- **可视化管理**：直观的Web界面降低管理成本

## 🤝 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

1. Fork项目到你的GitHub账户
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交变更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

### 贡献类型

- 🐛 Bug修复
- ✨ 新功能开发
- 📝 文档改进
- 🎨 代码优化
- 🧪 测试增强

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持与反馈

- **Issues**：[GitHub Issues](https://github.com/franksunye/FSOpsAssistant/issues)
- **讨论**：[GitHub Discussions](https://github.com/franksunye/FSOpsAssistant/discussions)
- **邮件**：franksunye@hotmail.com

## 🙏 致谢

感谢以下开源项目的支持：

- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent编排框架
- [Streamlit](https://streamlit.io) - Web应用框架
- [DeepSeek](https://www.deepseek.com) - LLM服务提供商
- [SQLite](https://sqlite.org) - 轻量级数据库

---

**⭐ 如果这个项目对你有帮助，请给我们一个Star！**

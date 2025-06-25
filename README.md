# FSOA - Field Service Operations Assistant

🤖 **智能现场服务运营助手** - 基于Agentic AI的企业级运营自动化解决方案

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-green.svg)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/Streamlit-Latest-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 项目概述

FSOA是一个具备**主动性、自主决策、目标导向**特性的AI Agent系统，专为现场服务运营场景设计。通过智能监控、自动决策和及时通知，大幅提升运营效率，减少人工干预。

### 核心特性

- 🔄 **主动监控**：7x24小时自动监控现场服务时效
- 🧠 **智能决策**：规则引擎+LLM的混合决策机制
- 📱 **即时通知**：企业微信群自动通知相关人员
- 📊 **数据驱动**：基于Metabase的非侵入式数据集成
- 🎛️ **可配置化**：业务规则和策略支持动态调整
- 🔧 **可扩展性**：模块化架构支持功能扩展

### 技术亮点

- **Agentic AI架构**：基于LangGraph的Agent编排
- **混合决策引擎**：结合规则和LLM的智能决策
- **非侵入式集成**：通过API获取数据，不影响现有系统
- **企业级设计**：完整的监控、日志和错误处理机制

## 🚀 快速开始

### 环境要求

- Python 3.9+
- SQLite 3.x
- 企业微信群机器人
- Metabase访问权限
- DeepSeek API密钥

### 安装部署

```bash
# 1. 克隆项目
git clone https://github.com/franksunye/FSOpsAssistant.git
cd FSOpsAssistant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要配置

# 4. 初始化数据库
python scripts/init_db.py

# 5. 启动应用
python scripts/start_app.py
```

### 配置说明

```bash
# .env 配置示例
DEEPSEEK_API_KEY=your_deepseek_api_key
METABASE_URL=your_metabase_url
METABASE_USERNAME=your_username
METABASE_PASSWORD=your_password
WECHAT_WEBHOOK_URLS=webhook1,webhook2,webhook3
DATABASE_URL=sqlite:///fsoa.db
LOG_LEVEL=INFO
```

## 🏗️ 系统架构

```
┌─────────────────┐    ┌──────────────────────────────┐
│   Metabase      │    │        FSOA Agent            │
│  (数据源)        │◄───┤  ┌─────────────────────────┐  │
└─────────────────┘    │  │   Agent Orchestrator    │  │
                       │  │    (LangGraph DAG)      │  │
┌─────────────────┐    │  └─────────────────────────┘  │
│  企微群 A/B/C    │◄───┤  ┌─────────────────────────┐  │
│  (通知渠道)      │    │  │     Tool Layer          │  │
└─────────────────┘    │  │ • Data Fetcher          │  │
                       │  │ • Message Sender        │  │
┌─────────────────┐    │  │ • Decision Engine       │  │
│   SQLite        │◄───┤  │ • Memory Manager        │  │
│  (本地存储)      │    │  └─────────────────────────┘  │
└─────────────────┘    └──────────────────────────────┘
                                      ▲
┌─────────────────┐                   │
│  Streamlit UI   │───────────────────┘
│  (管理界面)      │
└─────────────────┘
```

### 核心组件

- **Agent Orchestrator**：基于LangGraph的智能编排引擎
- **Decision Engine**：规则+LLM的混合决策系统
- **Tool Layer**：标准化的工具函数集合
- **Data Layer**：统一的数据访问和存储层
- **UI Layer**：基于Streamlit的管理界面

## 📋 功能特性

### Agent能力

- ✅ **定时执行**：基于Cron的自动化调度
- ✅ **状态管理**：完整的执行状态追踪
- ✅ **错误处理**：异常捕获和自动恢复
- ✅ **工具调用**：标准化的Function Calling

### 业务功能

- ✅ **任务监控**：实时监控现场服务时效
- ✅ **超时检测**：基于SLA的智能超时判断
- ✅ **通知发送**：多群组的差异化通知
- ✅ **状态追踪**：完整的任务生命周期管理

### 管理功能

- ✅ **可视化界面**：直观的运营数据展示
- ✅ **配置管理**：灵活的参数和规则配置
- ✅ **日志监控**：详细的执行日志和审计
- ✅ **性能分析**：系统性能和业务指标分析

## 🔧 开发指南

### 项目结构

```
FSOpsAssistant/
├── src/fsoa/              # 源代码
│   ├── agent/             # Agent核心模块
│   ├── data/              # 数据层
│   ├── notification/      # 通知模块
│   ├── ui/                # UI界面
│   └── utils/             # 工具模块
├── tests/                 # 测试代码
├── docs/                  # 项目文档
├── scripts/               # 脚本文件
└── requirements.txt       # 依赖列表
```

### 开发流程

1. **阅读文档**：查看 `docs/` 目录下的详细文档
2. **环境搭建**：按照 `docs/30_DEVELOPMENT.md` 配置开发环境
3. **编写代码**：遵循项目代码规范和最佳实践
4. **编写测试**：参考 `docs/31_TESTING.md` 编写测试用例
5. **提交代码**：通过Pull Request提交代码变更

### 测试运行

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 生成覆盖率报告
pytest --cov=src/fsoa --cov-report=html

# 运行性能测试
pytest tests/performance/
```

## 📚 文档导航

| 文档 | 描述 | 目标读者 |
|------|------|----------|
| [项目概述](docs/00_PROJECT_OVERVIEW.md) | 项目背景、目标和价值主张 | 所有人 |
| [执行计划](docs/00_BACKLOG.md) | 开发计划和优先级 | 开发团队 |
| [系统架构](docs/10_ARCHITECTURE.md) | 技术架构和设计决策 | 技术人员 |
| [API文档](docs/20_API.md) | 接口规范和使用说明 | 开发者 |
| [开发指南](docs/30_DEVELOPMENT.md) | 开发环境和编码规范 | 开发者 |
| [测试指南](docs/31_TESTING.md) | 测试策略和实施方法 | 开发者 |
| [用户手册](docs/40_USER_GUIDE.md) | 功能使用和操作指南 | 最终用户 |

## 🎯 使用场景

### 典型工作流程

1. **自动监控**：Agent每小时自动检查任务状态
2. **智能判断**：基于SLA时间和业务规则判断是否超时
3. **决策优化**：可选使用LLM优化通知内容和优先级
4. **即时通知**：向对应企微群发送格式化通知
5. **状态更新**：记录执行结果和通知状态
6. **持续优化**：基于反馈调整策略和参数

### 业务价值

- **效率提升**：减少80%的重复性监控工作
- **响应加速**：从小时级降低到分钟级响应
- **质量改善**：通过及时提醒提升服务时效合规率
- **成本降低**：减少人工成本，提高运营ROI

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

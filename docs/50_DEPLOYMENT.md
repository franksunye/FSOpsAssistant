# FSOA 部署指南

Field Service Operations Assistant - 轻量级本地部署指南

## 📋 部署概述

本指南提供FSOA的轻量级本地部署方案，适用于开发和小规模生产环境。

## 🔧 环境要求

### 系统要求
- **Python版本**: 3.9+
- **内存**: 最小1GB，推荐2GB+
- **存储**: 最小2GB
- **网络**: 稳定的互联网连接

### 依赖服务
- **Metabase**: 数据源服务
- **企业微信**: 通知渠道
- **DeepSeek API**: LLM服务

## 🚀 快速部署

### 1. 环境准备

```bash
# 确保Python 3.9+已安装
python --version

# 安装Git（如果未安装）
# Ubuntu/Debian:
sudo apt install git -y
# CentOS/RHEL:
sudo yum install git -y
# macOS:
brew install git
```

### 2. 项目部署

```bash
# 克隆项目
git clone https://github.com/franksunye/FSOpsAssistant.git
cd FSOpsAssistant

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑配置文件
nano .env  # 或使用其他编辑器
```

### 3. 配置文件设置

编辑 `.env` 文件，填入实际配置：

```bash
# DeepSeek LLM配置
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Metabase数据源配置
METABASE_URL=https://your-metabase-server.com
METABASE_USERNAME=fsoa_user
METABASE_PASSWORD=your_password
METABASE_DATABASE_ID=1

# 企业微信通知配置
# 注意：企微配置已迁移到Web界面管理
# 请在部署后通过 [系统管理 → 企微群配置] 进行配置

# 数据库配置
DATABASE_URL=sqlite:///data/fsoa.db

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/fsoa.log

# Agent配置
AGENT_EXECUTION_INTERVAL=60
USE_LLM_OPTIMIZATION=true
LLM_TEMPERATURE=0.1

# 运行环境
DEBUG=false
TESTING=false
```

### 4. 初始化和启动

```bash
# 初始化数据库
python scripts/init_db.py

# 启动Web界面
python scripts/start_app.py

# 或启动Agent服务（另一个终端）
python scripts/start_agent.py
```

## 🔧 系统配置

### 后台服务配置（可选）

如需将FSOA作为系统服务运行：

#### 创建systemd服务

```bash
# 创建Web服务文件
sudo nano /etc/systemd/system/fsoa-web.service
```

```ini
[Unit]
Description=FSOA Web Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/path/to/FSOpsAssistant
ExecStart=/usr/bin/python scripts/start_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 创建Agent服务文件
sudo nano /etc/systemd/system/fsoa-agent.service
```

```ini
[Unit]
Description=FSOA Agent Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/path/to/FSOpsAssistant
ExecStart=/usr/bin/python scripts/start_agent.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

#### 启用和管理服务

```bash
# 重新加载systemd
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable fsoa-web fsoa-agent

# 启动服务
sudo systemctl start fsoa-web fsoa-agent

# 查看状态
sudo systemctl status fsoa-web fsoa-agent

# 查看日志
sudo journalctl -u fsoa-web -f
sudo journalctl -u fsoa-agent -f
```

## 🔒 安全配置

### 1. 防火墙设置

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8501/tcp
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload
```

### 2. 环境变量安全

```bash
# 设置文件权限
chmod 600 .env

# 使用系统环境变量（推荐）
export DEEPSEEK_API_KEY="your_api_key"
export METABASE_PASSWORD="your_password"
```

## 📊 监控和维护

### 1. 日志管理

```bash
# 查看应用日志
tail -f logs/fsoa.log

# 查看系统服务日志
sudo journalctl -u fsoa-web -f
sudo journalctl -u fsoa-agent -f
```

### 2. 健康检查

```bash
# 检查Web服务
curl -f http://localhost:8501

# 检查进程状态
ps aux | grep python | grep fsoa

# 检查端口占用
netstat -tlnp | grep 8501
```

### 3. 备份策略

```bash
# 备份数据库
cp data/fsoa.db backup/fsoa_$(date +%Y%m%d).db

# 备份配置文件
cp .env backup/env_$(date +%Y%m%d).backup

# 备份日志
tar -czf backup/logs_$(date +%Y%m%d).tar.gz logs/
```

## 🔄 更新和升级

### 应用更新

```bash
# 停止服务
sudo systemctl stop fsoa-web fsoa-agent

# 备份当前版本
cp -r . ../FSOpsAssistant_backup_$(date +%Y%m%d)

# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt

# 重启服务
sudo systemctl start fsoa-web fsoa-agent
```

## 🚨 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查日志
   sudo journalctl -u fsoa-web -n 50
   
   # 检查配置
   python scripts/init_db.py
   ```

2. **数据库连接问题**
   ```bash
   # 检查数据库文件
   ls -la data/
   
   # 重新初始化数据库
   python scripts/init_db.py
   ```

3. **网络连接问题**
   ```bash
   # 测试外部连接
   curl -I https://api.deepseek.com
   curl -I $METABASE_URL
   ```

4. **端口占用问题**
   ```bash
   # 查看端口占用
   netstat -tlnp | grep 8501
   
   # 杀死占用进程
   sudo kill -9 <PID>
   ```

### 性能优化

1. **内存优化**
   - 监控内存使用: `htop` 或 `top`
   - 调整Python GC参数
   - 定期重启服务

2. **数据库优化**
   - 定期清理旧数据
   - 使用WAL模式: `PRAGMA journal_mode=WAL;`

3. **网络优化**
   - 设置合适的超时时间
   - 使用连接池
   - 启用HTTP缓存

## 📞 技术支持

### 使用帮助

1. **Web界面**: http://localhost:8501
2. **系统测试**: 在Web界面的"系统测试"页面
3. **Agent控制**: 在Web界面的"Agent控制"页面

### 故障排查步骤

1. 检查系统日志
2. 验证配置文件
3. 测试网络连接
4. 重启相关服务

### 联系方式

如遇部署问题，请：
- 查看项目文档
- 检查GitHub Issues
- 联系技术支持: franksunye@hotmail.com

---

## 📝 快速参考

### 常用命令

```bash
# 启动应用
python scripts/start_app.py

# 启动Agent
python scripts/start_agent.py

# 初始化数据库
python scripts/init_db.py

# 运行测试
python scripts/run_tests.py --all

# 查看日志
tail -f logs/fsoa.log

# 检查服务状态
sudo systemctl status fsoa-web fsoa-agent
```

### 重要文件

- **配置文件**: `.env`
- **数据库**: `data/fsoa.db`
- **日志文件**: `logs/fsoa.log`
- **启动脚本**: `scripts/start_*.py`

### 默认端口

- **Web界面**: 8501
- **Agent服务**: 后台运行，无端口

# FSOA 部署指南

**版本**: v0.2.0  
**更新时间**: 2025-06-26

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Git
- 网络连接（访问Metabase和企微）

### 1. 克隆项目
```bash
git clone https://github.com/franksunye/FSOpsAssistant.git
cd FSOpsAssistant
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境
```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
nano .env
```

### 4. 初始化数据库
```bash
# 新部署
python scripts/init_db.py

# 从v0.1.x升级
python scripts/migrate_notification_tasks.py

# 完全重置（开发环境）
python scripts/reset_database.py
```

### 5. 启动应用
```bash
# 仅Web界面（开发/配置）
python scripts/start_web.py

# 完整应用（Web + Agent）
python scripts/start_full_app.py

# 仅Agent服务（生产后台）
python scripts/start_agent.py
```

## ⚙️ 配置说明

### 核心配置项
```env
# 数据库配置
DATABASE_URL=sqlite:///fsoa.db

# Metabase配置
METABASE_BASE_URL=https://your-metabase.com
METABASE_USERNAME=your-username
METABASE_PASSWORD=your-password

# 企微配置
WECHAT_WEBHOOK_LIST=["https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"]

# v0.2.0 新增配置
NOTIFICATION_COOLDOWN=120  # 2小时冷静时间
MAX_RETRY_COUNT=5          # 最大重试次数
```

### 工作时间配置
系统默认工作时间：早9点到晚7点，周一到周五。
可通过Web界面的"系统设置 → 工作时间设置"进行调整。

## 🔄 升级指南

### 从v0.1.x升级到v0.2.0

#### 1. 备份数据
```bash
cp fsoa.db fsoa_backup_$(date +%Y%m%d).db
```

#### 2. 更新代码
```bash
git pull origin main
pip install -r requirements.txt
```

#### 3. 数据库迁移
```bash
python scripts/migrate_notification_tasks.py
```

#### 4. 验证升级
```bash
python scripts/test_new_sla_features.py
```

#### 5. 重启服务
```bash
# 停止现有服务
pkill -f "streamlit\|python.*start_"

# 启动新版本
python scripts/start_full_app.py
```

### 升级验证清单
- [ ] 数据库迁移成功
- [ ] Web界面显示新功能
- [ ] 工作时间计算正常
- [ ] 通知类型显示正确
- [ ] SLA规则生效

## 🏗️ 生产部署

### 推荐架构
```
┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   FSOA App      │
│   (反向代理)     │◄───┤   (Streamlit)   │
└─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   FSOA Agent    │
                       │   (后台服务)     │
                       └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   SQLite/       │
                       │   PostgreSQL    │
                       └─────────────────┘
```

### 部署步骤

#### 1. 服务器准备
```bash
# 创建专用用户
sudo useradd -m -s /bin/bash fsoa
sudo su - fsoa

# 安装Python环境
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev
```

#### 2. 应用部署
```bash
# 克隆代码
git clone https://github.com/franksunye/FSOpsAssistant.git
cd FSOpsAssistant

# 创建虚拟环境
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. 配置文件
```bash
# 生产环境配置
cp .env.example .env.production
nano .env.production

# 设置生产配置
export FSOA_ENV=production
```

#### 4. 数据库初始化
```bash
python scripts/init_db.py
```

#### 5. 系统服务配置
```bash
# 创建systemd服务文件
sudo nano /etc/systemd/system/fsoa-agent.service
```

```ini
[Unit]
Description=FSOA Agent Service
After=network.target

[Service]
Type=simple
User=fsoa
WorkingDirectory=/home/fsoa/FSOpsAssistant
Environment=PATH=/home/fsoa/FSOpsAssistant/venv/bin
ExecStart=/home/fsoa/FSOpsAssistant/venv/bin/python scripts/start_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable fsoa-agent
sudo systemctl start fsoa-agent
```

#### 6. Web服务配置
```bash
# 创建Web服务
sudo nano /etc/systemd/system/fsoa-web.service
```

```ini
[Unit]
Description=FSOA Web Service
After=network.target

[Service]
Type=simple
User=fsoa
WorkingDirectory=/home/fsoa/FSOpsAssistant
Environment=PATH=/home/fsoa/FSOpsAssistant/venv/bin
ExecStart=/home/fsoa/FSOpsAssistant/venv/bin/streamlit run src/fsoa/ui/app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 7. Nginx配置
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔍 监控和维护

### 日志查看
```bash
# Agent服务日志
sudo journalctl -u fsoa-agent -f

# Web服务日志
sudo journalctl -u fsoa-web -f

# 应用日志
tail -f logs/fsoa.log
```

### 健康检查
```bash
# 检查服务状态
sudo systemctl status fsoa-agent
sudo systemctl status fsoa-web

# 检查数据库
python scripts/test_database.py

# 检查外部连接
python scripts/test_connections.py
```

### 备份策略
```bash
# 数据库备份
cp fsoa.db backups/fsoa_$(date +%Y%m%d_%H%M%S).db

# 配置备份
cp .env backups/env_$(date +%Y%m%d_%H%M%S).backup

# 自动备份脚本
crontab -e
# 添加: 0 2 * * * /home/fsoa/backup_fsoa.sh
```

## 🚨 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库文件权限
ls -la fsoa.db
chmod 664 fsoa.db

# 重新初始化
python scripts/reset_database.py
```

#### 2. Metabase连接失败
```bash
# 测试连接
python scripts/test_metabase.py

# 检查配置
grep METABASE .env
```

#### 3. 企微通知失败
```bash
# 测试webhook
python scripts/test_wechat.py

# 检查配置
grep WECHAT .env
```

#### 4. Agent不执行
```bash
# 检查调度器
python scripts/check_scheduler.py

# 手动执行
python scripts/manual_run.py
```

### 性能优化
- 定期清理旧的Agent执行记录
- 监控数据库大小和性能
- 调整通知频率和冷静时间
- 优化Metabase查询性能

---
> 如有问题，请查看项目文档或提交Issue

# FSOA 部署指南

Field Service Operations Assistant - 生产环境部署指南

## 📋 部署概述

本指南提供FSOA在生产环境中的完整部署方案，包括环境准备、安装配置、监控维护等。

## 🔧 环境要求

### 系统要求
- **操作系统**: Linux (Ubuntu 20.04+ / CentOS 8+ / RHEL 8+)
- **Python版本**: 3.9+
- **内存**: 最小2GB，推荐4GB+
- **存储**: 最小10GB，推荐50GB+
- **网络**: 稳定的互联网连接

### 依赖服务
- **Metabase**: 数据源服务
- **企业微信**: 通知渠道
- **DeepSeek API**: LLM服务

## 🚀 部署方式

### 方式一：标准部署（推荐）

#### 1. 环境准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
sudo yum update -y                      # CentOS/RHEL

# 安装Python 3.9+
sudo apt install python3.9 python3.9-venv python3.9-dev -y  # Ubuntu
sudo yum install python39 python39-devel -y                  # CentOS

# 安装系统依赖
sudo apt install git curl wget build-essential -y  # Ubuntu
sudo yum groupinstall "Development Tools" -y       # CentOS

# 创建部署用户
sudo useradd -m -s /bin/bash fsoa
sudo usermod -aG sudo fsoa  # 可选：添加sudo权限
```

#### 2. 项目部署

```bash
# 切换到部署用户
sudo su - fsoa

# 克隆项目
git clone https://github.com/franksunye/FSOpsAssistant.git
cd FSOpsAssistant

# 创建虚拟环境
python3.9 -m venv fsoa_env
source fsoa_env/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑配置文件
nano .env
```

#### 3. 配置文件设置

```bash
# .env 生产环境配置示例
DEEPSEEK_API_KEY=your_production_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

METABASE_URL=https://your-metabase-server.com
METABASE_USERNAME=fsoa_user
METABASE_PASSWORD=secure_password
METABASE_DATABASE_ID=1

WECHAT_WEBHOOK_URLS=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=webhook1,https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=webhook2

DATABASE_URL=sqlite:///var/lib/fsoa/fsoa.db
LOG_LEVEL=INFO
LOG_FILE=/var/log/fsoa/fsoa.log

AGENT_EXECUTION_INTERVAL=60
USE_LLM_OPTIMIZATION=true
LLM_TEMPERATURE=0.1

DEBUG=false
TESTING=false
```

#### 4. 初始化系统

```bash
# 创建必要目录
sudo mkdir -p /var/lib/fsoa /var/log/fsoa
sudo chown fsoa:fsoa /var/lib/fsoa /var/log/fsoa

# 初始化数据库
python scripts/init_db.py

# 测试系统
python scripts/start_app.py --test
```

### 方式二：Docker部署

#### 1. 创建Dockerfile

```dockerfile
# Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建非root用户
RUN useradd -m -u 1000 fsoa && chown -R fsoa:fsoa /app
USER fsoa

# 暴露端口
EXPOSE 8501

# 启动命令
CMD ["python", "scripts/start_app.py"]
```

#### 2. 创建docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  fsoa-app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - METABASE_URL=${METABASE_URL}
      - METABASE_USERNAME=${METABASE_USERNAME}
      - METABASE_PASSWORD=${METABASE_PASSWORD}
      - WECHAT_WEBHOOK_URLS=${WECHAT_WEBHOOK_URLS}
    volumes:
      - fsoa_data:/app/data
      - fsoa_logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501"]
      interval: 30s
      timeout: 10s
      retries: 3

  fsoa-agent:
    build: .
    command: ["python", "scripts/start_agent.py"]
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - METABASE_URL=${METABASE_URL}
      - METABASE_USERNAME=${METABASE_USERNAME}
      - METABASE_PASSWORD=${METABASE_PASSWORD}
      - WECHAT_WEBHOOK_URLS=${WECHAT_WEBHOOK_URLS}
    volumes:
      - fsoa_data:/app/data
      - fsoa_logs:/app/logs
    restart: unless-stopped
    depends_on:
      - fsoa-app

volumes:
  fsoa_data:
  fsoa_logs:
```

#### 3. Docker部署命令

```bash
# 构建和启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 🔧 系统服务配置

### 创建systemd服务

#### 1. FSOA Web服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/fsoa-web.service
```

```ini
[Unit]
Description=FSOA Web Application
After=network.target

[Service]
Type=simple
User=fsoa
Group=fsoa
WorkingDirectory=/home/fsoa/FSOpsAssistant
Environment=PATH=/home/fsoa/FSOpsAssistant/fsoa_env/bin
ExecStart=/home/fsoa/FSOpsAssistant/fsoa_env/bin/python scripts/start_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. FSOA Agent服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/fsoa-agent.service
```

```ini
[Unit]
Description=FSOA Agent Service
After=network.target

[Service]
Type=simple
User=fsoa
Group=fsoa
WorkingDirectory=/home/fsoa/FSOpsAssistant
Environment=PATH=/home/fsoa/FSOpsAssistant/fsoa_env/bin
ExecStart=/home/fsoa/FSOpsAssistant/fsoa_env/bin/python scripts/start_agent.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

#### 3. 启用和管理服务

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

### 2. SSL/TLS配置

使用Nginx作为反向代理：

```bash
# 安装Nginx
sudo apt install nginx -y  # Ubuntu
sudo yum install nginx -y  # CentOS

# 配置Nginx
sudo nano /etc/nginx/sites-available/fsoa
```

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. 环境变量安全

```bash
# 设置文件权限
chmod 600 .env
chown fsoa:fsoa .env

# 使用系统环境变量（推荐）
sudo nano /etc/environment
```

## 📊 监控和维护

### 1. 日志管理

```bash
# 配置logrotate
sudo nano /etc/logrotate.d/fsoa
```

```
/var/log/fsoa/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 fsoa fsoa
    postrotate
        systemctl reload fsoa-web fsoa-agent
    endscript
}
```

### 2. 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

# 检查Web服务
if curl -f http://localhost:8501 > /dev/null 2>&1; then
    echo "✅ Web服务正常"
else
    echo "❌ Web服务异常"
    sudo systemctl restart fsoa-web
fi

# 检查Agent服务
if systemctl is-active --quiet fsoa-agent; then
    echo "✅ Agent服务正常"
else
    echo "❌ Agent服务异常"
    sudo systemctl restart fsoa-agent
fi

# 检查磁盘空间
DISK_USAGE=$(df /var/lib/fsoa | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "⚠️ 磁盘使用率过高: ${DISK_USAGE}%"
fi
```

### 3. 备份策略

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/fsoa"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
cp /var/lib/fsoa/fsoa.db $BACKUP_DIR/fsoa_${DATE}.db

# 备份配置文件
cp /home/fsoa/FSOpsAssistant/.env $BACKUP_DIR/env_${DATE}.backup

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.backup" -mtime +30 -delete

echo "备份完成: $BACKUP_DIR"
```

## 🔄 更新和升级

### 1. 应用更新

```bash
#!/bin/bash
# update.sh

cd /home/fsoa/FSOpsAssistant

# 停止服务
sudo systemctl stop fsoa-web fsoa-agent

# 备份当前版本
cp -r . ../FSOpsAssistant_backup_$(date +%Y%m%d)

# 拉取最新代码
git pull origin main

# 激活虚拟环境
source fsoa_env/bin/activate

# 更新依赖
pip install -r requirements.txt

# 数据库迁移（如有需要）
python scripts/migrate_db.py

# 重启服务
sudo systemctl start fsoa-web fsoa-agent

echo "更新完成"
```

### 2. 回滚策略

```bash
#!/bin/bash
# rollback.sh

BACKUP_DIR="../FSOpsAssistant_backup_$1"

if [ -d "$BACKUP_DIR" ]; then
    sudo systemctl stop fsoa-web fsoa-agent
    
    # 备份当前版本
    mv FSOpsAssistant FSOpsAssistant_failed_$(date +%Y%m%d)
    
    # 恢复备份版本
    cp -r $BACKUP_DIR FSOpsAssistant
    cd FSOpsAssistant
    
    # 重启服务
    sudo systemctl start fsoa-web fsoa-agent
    
    echo "回滚完成"
else
    echo "备份目录不存在: $BACKUP_DIR"
fi
```

## 🚨 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查日志
   sudo journalctl -u fsoa-web -n 50
   
   # 检查配置
   python scripts/init_db.py --check
   ```

2. **数据库连接问题**
   ```bash
   # 检查数据库文件权限
   ls -la /var/lib/fsoa/
   
   # 重新初始化数据库
   python scripts/init_db.py --reset
   ```

3. **网络连接问题**
   ```bash
   # 测试外部连接
   curl -I https://api.deepseek.com
   curl -I $METABASE_URL
   ```

### 性能优化

1. **数据库优化**
   - 定期清理旧数据
   - 添加适当索引
   - 使用WAL模式

2. **内存优化**
   - 调整Python GC参数
   - 监控内存使用
   - 设置合适的worker数量

3. **网络优化**
   - 使用连接池
   - 设置合适的超时时间
   - 启用HTTP/2

---

## 📞 技术支持

如遇部署问题，请：

1. 查看系统日志
2. 检查配置文件
3. 运行健康检查
4. 联系技术支持

**联系方式**: franksunye@hotmail.com

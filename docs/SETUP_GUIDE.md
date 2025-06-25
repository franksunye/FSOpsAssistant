# FSOA 本地环境配置指南

## 🎉 环境测试结果

✅ **所有核心组件测试通过！**

- ✅ 模块导入正常
- ✅ 配置系统正常
- ✅ 数据库连接正常
- ✅ 日志系统正常
- ✅ Agent组件正常
- ✅ 通知系统正常

## 📋 下一步配置

### 1. 配置 API 密钥和服务地址

编辑 `.env` 文件，填入您的实际配置：

```bash
# DeepSeek LLM Configuration
DEEPSEEK_API_KEY=your_actual_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Metabase Configuration
METABASE_URL=http://your-actual-metabase-server:3000
METABASE_USERNAME=your_actual_metabase_username
METABASE_PASSWORD=your_actual_metabase_password
METABASE_DATABASE_ID=1

# WeChat Work Webhook Configuration
WECHAT_WEBHOOK_URLS=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_actual_webhook_key
```

### 2. 测试外部服务连接

运行以下命令测试各个外部服务的连接：

```bash
# 测试 DeepSeek API
python -c "
from src.fsoa.agent.llm import get_deepseek_client
try:
    client = get_deepseek_client()
    print('✅ DeepSeek API 配置正确')
except Exception as e:
    print(f'❌ DeepSeek API 配置错误: {e}')
"

# 测试 Metabase 连接
python -c "
from src.fsoa.data.metabase import get_metabase_client
try:
    client = get_metabase_client()
    if client.test_connection():
        print('✅ Metabase 连接正常')
    else:
        print('❌ Metabase 连接失败')
except Exception as e:
    print(f'❌ Metabase 配置错误: {e}')
"

# 测试企微 Webhook
python -c "
from src.fsoa.notification.wechat import WeChatClient
try:
    client = WeChatClient()
    print('✅ 企微 Webhook 配置正确')
except Exception as e:
    print(f'❌ 企微 Webhook 配置错误: {e}')
"
```

### 3. 启动应用

#### 方式一：启动 Web 界面（推荐用于测试）

```bash
streamlit run src/fsoa/ui/app.py
```

然后在浏览器中访问：http://localhost:8501

#### 方式二：启动完整应用（包含定时任务）

```bash
python scripts/start_app.py
```

### 4. 验证功能

在 Web 界面中可以进行以下操作：

1. **系统状态检查**：查看各个组件的运行状态
2. **手动执行 Agent**：测试 Agent 的工作流程
3. **查看执行历史**：检查 Agent 的执行记录
4. **配置管理**：调整系统参数
5. **测试通知**：发送测试消息到企微群

## 🔧 常见问题解决

### 问题1：配置文件解析错误

**错误信息：**
```
Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='60  # minutes']
```

**解决方案：**
```bash
# .env 文件中的数值配置不能包含注释
# 错误写法：
AGENT_EXECUTION_INTERVAL=60  # minutes

# 正确写法：
AGENT_EXECUTION_INTERVAL=60
```

### 问题2：Web界面模块导入失败

**错误信息：**
```
模块导入失败，请检查项目结构
```

**解决方案：**
```bash
# 确保从项目根目录启动
cd /path/to/FSOA
python scripts/start_web.py

# 或直接运行
streamlit run src/fsoa/ui/app.py
```

### 问题3：DeepSeek API 连接错误

**错误信息：**
```
Client.__init__() got an unexpected keyword argument 'proxies'
```

**解决方案：**
这是 OpenAI 客户端版本兼容性问题，代码已自动处理。如果仍有问题：
```bash
pip install --upgrade openai httpx
```

### 问题4：Metabase 连接失败

**解决方案：**
1. 确认 Metabase 服务器地址正确
2. 检查用户名和密码
3. 确认网络可达性

### 问题5：企微消息发送失败

**解决方案：**
1. 检查 Webhook URL 是否正确
2. 确认机器人已添加到群聊
3. 测试 Webhook 是否有效

### 问题6：数据库相关错误

**解决方案：**
```bash
# 重新初始化数据库
python scripts/init_db.py
```

## 📊 监控和日志

### 查看日志

```bash
# 查看实时日志
tail -f logs/fsoa.log

# 查看最近的日志
tail -n 100 logs/fsoa.log
```

### 日志级别配置

在 `.env` 文件中调整日志级别：

```bash
LOG_LEVEL=DEBUG  # 详细调试信息
LOG_LEVEL=INFO   # 一般信息（推荐）
LOG_LEVEL=WARNING # 仅警告和错误
LOG_LEVEL=ERROR  # 仅错误信息
```

## 🚀 生产环境部署

### 使用 Docker（推荐）

```bash
# 构建镜像
docker build -t fsoa:latest .

# 运行容器
docker run -d \
  --name fsoa \
  -p 8501:8501 \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  --env-file .env \
  fsoa:latest
```

### 使用 systemd 服务

创建服务文件 `/etc/systemd/system/fsoa.service`：

```ini
[Unit]
Description=FSOA Service
After=network.target

[Service]
Type=simple
User=fsoa
WorkingDirectory=/path/to/FSOA
ExecStart=/path/to/python scripts/start_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl enable fsoa
sudo systemctl start fsoa
sudo systemctl status fsoa
```

## 📞 技术支持

如果遇到问题，请：

1. 查看日志文件：`logs/fsoa.log`
2. 运行环境测试：`python scripts/test_environment.py`
3. 检查配置文件：`.env`
4. 查看文档：`docs/` 目录下的相关文档

---

🎉 **恭喜！您的 FSOA 环境已经配置完成，可以开始使用了！**

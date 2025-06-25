# FSOA Docker镜像
FROM python:3.9-slim

# 设置标签
LABEL maintainer="Ye Sun <franksunye@hotmail.com>"
LABEL description="Field Service Operations Assistant - Agentic AI for Service Operations"
LABEL version="0.1.0"

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd -m -u 1000 fsoa && \
    mkdir -p /app/data /app/logs && \
    chown -R fsoa:fsoa /app

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 设置文件权限
RUN chown -R fsoa:fsoa /app

# 切换到非root用户
USER fsoa

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501 || exit 1

# 默认启动命令
CMD ["python", "scripts/start_app.py"]

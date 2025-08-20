FROM python:3.11-slim-bookworm
WORKDIR /app

# 安装依赖
RUN apt-get update && apt-get install -y --no-install-recommends gcc libssl-dev curl python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制代码
COPY requirements.txt .
COPY tg_bot_webhook.py .
COPY actions.yaml .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露Webhook端口和健康检查端口
EXPOSE 8443 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
CMD ["python", "tg_bot_webhook.py"]
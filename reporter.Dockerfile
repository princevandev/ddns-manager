FROM python:3.12-slim

WORKDIR /app

# 安装 iproute2 提供 ip 命令
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir requests

COPY reporter.py .

# 环境变量配置
ENV DDNS_MANAGER_URL=""
ENV DDNS_MACHINE_TOKEN=""
ENV DDNS_INTERFACE_NAME="eth0"
ENV DDNS_REPORT_INTERVAL="3600"

CMD ["python", "reporter.py"]
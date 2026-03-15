FROM python:3.12-alpine

WORKDIR /app

# 安装 iproute2 提供 ip 命令
RUN apk add --no-cache iproute2

# 只安装必要的依赖
RUN pip install --no-cache-dir requests

COPY reporter.py .

# 环境变量配置
ENV DDNS_MANAGER_URL=""
ENV DDNS_MACHINE_TOKEN=""
ENV DDNS_INTERFACE_NAME="eth0"
ENV DDNS_REPORT_INTERVAL="60"
ENV PYTHONUNBUFFERED=1

CMD ["python", "reporter.py"]
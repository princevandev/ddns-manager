# DDNS Manager

个人 DDNS 管理系统，包含管理端和上报端。

## 快速开始

### 方式一：Docker 命令

**启动管理端**

```bash
docker run -d \
  --name ddns-manager \
  -p 8765:8000 \
  -v ddns-data:/data \
  -e DDNS_ADMIN_USERNAME=admin \
  -e DDNS_ADMIN_PASSWORD=yourpassword \
  princevan/ddns-manager:v0.0.1
```

访问 `http://your-ip:8765`，登录后创建机器获取 Token。

**启动上报端**

```bash
docker run -d \
  --name ddns-reporter \
  --network host \
  --restart unless-stopped \
  -e DDNS_MANAGER_URL=http://your-manager-ip:8765 \
  -e DDNS_MACHINE_TOKEN=your-token \
  -e DDNS_INTERFACE_NAME=eth0 \
  -e DDNS_REPORT_INTERVAL=60 \
  princevan/ddns-reporter:v0.0.1
```

> 上报端使用 `--network host` 以便访问宿主机网卡获取 IPv6 地址。

### 方式二：Docker Compose

**管理端**

```bash
# 创建配置文件
cat > .env << EOF
DDNS_ADMIN_USERNAME=admin
DDNS_ADMIN_PASSWORD=yourpassword
EOF

# 启动
docker compose -f docker-compose.manager.yml up -d

# 查看日志
docker compose -f docker-compose.manager.yml logs -f
```

**上报端**

```bash
# 创建配置文件
cat > .env << EOF
DDNS_MANAGER_URL=http://your-manager-ip:8765
DDNS_MACHINE_TOKEN=your-token
DDNS_INTERFACE_NAME=eth0
DDNS_REPORT_INTERVAL=60
EOF

# 启动
docker compose -f docker-compose.reporter.yml up -d

# 查看日志
docker compose -f docker-compose.reporter.yml logs -f
```

### 配置 Cloudflare

在管理端设置页面填入 Cloudflare API Token，然后给机器绑定域名即可。

---

## 手动部署

### 环境要求

- Python 3.10+
- SQLite（Python 自带）

### 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 启动管理端

```bash
export DDNS_ADMIN_USERNAME=admin
export DDNS_ADMIN_PASSWORD=yourpassword

uvicorn app.main:app --host 0.0.0.0 --port 8765
```

### 启动上报端

```bash
export DDNS_MANAGER_URL=http://your-manager-ip:8765
export DDNS_MACHINE_TOKEN=your-token
export DDNS_INTERFACE_NAME=eth0
export DDNS_REPORT_INTERVAL=60

python reporter.py
```

---

## 使用说明

1. 打开管理端，登录后创建机器，获取 Token
2. 在目标机器部署上报端，配置环境变量
3. 在管理端设置页面配置 Cloudflare API Token
4. 给机器绑定域名（Zone ID 自动获取）
5. 点击「同步」手动同步，或等待上报端自动更新

---

## 环境变量

### 管理端

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `DDNS_ADMIN_USERNAME` | ✅ | - | 管理员用户名 |
| `DDNS_ADMIN_PASSWORD` | ✅ | - | 管理员密码 |
| `DDNS_DB_PATH` | ❌ | ./data/ddns.sqlite | 数据库路径 |

### 上报端

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `DDNS_MANAGER_URL` | ✅ | - | 管理端地址 |
| `DDNS_MACHINE_TOKEN` | ✅ | - | 机器 Token |
| `DDNS_INTERFACE_NAME` | ✅ | eth0 | 网卡名称 |
| `DDNS_REPORT_INTERVAL` | ❌ | 3600 | 上报间隔（秒） |

---

## API 接口

- `POST /api/report` - 上报 IP
- `POST /api/sync/{machine_id}` - 同步 DNS
- `GET/POST /api/machines` - 机器管理
- `GET/POST/DELETE /api/domains` - 域名管理
- `GET/POST /api/settings` - 配置管理
- `POST /api/cloudflare/test` - 测试 Cloudflare 连接
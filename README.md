# DDNS Manager

Personal DDNS management system with a FastAPI manager and a single-file Python reporter.

## 快速开始

一行命令部署 Manager 和 Reporter：

### 1. 启动管理端

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

### 2. 启动上报端

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

> **注意**: 上报端使用 `--network host` 以便访问宿主机网卡获取 IPv6 地址。

### 3. 配置 Cloudflare

在管理端 Settings 页面填入 Cloudflare API Token，然后给机器绑定域名即可。

---

## Docker Deployment

### Manager (管理端)

```bash
# 创建 .env 文件
cat > .env << EOF
DDNS_ADMIN_USERNAME=admin
DDNS_ADMIN_PASSWORD=yourpassword
EOF

# 构建并启动
docker compose -f docker-compose.manager.yml up -d --build

# 查看日志
docker compose -f docker-compose.manager.yml logs -f

# 停止
docker compose -f docker-compose.manager.yml down
```

访问: `http://your-ip:8765`

### Reporter (上报端)

```bash
# 创建 .env 文件
cat > .env << EOF
DDNS_MANAGER_URL=http://your-manager-ip:8765
DDNS_MACHINE_TOKEN=从管理端创建机器后获取
DDNS_INTERFACE_NAME=eth0
DDNS_REPORT_INTERVAL=60
EOF

# 构建并启动
docker compose -f docker-compose.reporter.yml up -d --build

# 查看日志
docker compose -f docker-compose.reporter.yml logs -f
```

**环境变量说明：**
| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `DDNS_MANAGER_URL` | ✅ | - | 管理端地址 |
| `DDNS_MACHINE_TOKEN` | ✅ | - | 机器 Token |
| `DDNS_INTERFACE_NAME` | ✅ | eth0 | 网卡名称 |
| `DDNS_REPORT_INTERVAL` | ❌ | 3600 | 上报间隔(秒) |

> **注意**: 上报端使用 `network_mode: host` 以便访问宿主机网卡获取 IPv6 地址。

---

## Manual Setup (手动部署)

### Requirements
- Python 3.10+
- SQLite (bundled with Python)

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Manager Setup
```bash
export DDNS_ADMIN_USERNAME=admin
export DDNS_ADMIN_PASSWORD=yourpassword

uvicorn app.main:app --host 0.0.0.0 --port 8765
```

### Reporter Setup
```bash
export DDNS_MANAGER_URL=http://your-manager-ip:8765
export DDNS_MACHINE_TOKEN=your-machine-token
export DDNS_INTERFACE_NAME=eth0
export DDNS_REPORT_INTERVAL=60

python reporter.py
```

---

## 使用说明

1. 打开管理端，登录后创建机器，获取 token
2. 在目标机器部署上报端，配置环境变量
3. 在管理端 Settings 页面配置 Cloudflare API Token
4. 给机器绑定域名（Zone ID 自动获取）
5. 点击 "Sync DNS Now" 手动同步，或等待上报端自动更新

## API Endpoints
- `POST /api/report` - 上报 IP
- `POST /api/sync/{machine_id}` - 手动同步 DNS
- `GET/POST /api/machines` - 机器管理
- `GET/POST/DELETE /api/domains` - 域名管理
- `GET/POST /api/settings` - 配置管理
- `POST /api/cloudflare/test` - 测试 Cloudflare 连接
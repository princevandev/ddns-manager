# DDNS Manager

轻量级 DDNS 管理系统，支持 IPv6 地址自动上报与 Cloudflare DNS 解析更新。

## 功能介绍

- **多机器管理**：支持管理多台机器，每台机器独立 Token 认证
- **IPv6 支持**：自动获取本机 IPv6 地址并上报
- **自动同步**：IP 变化时自动更新 Cloudflare DNS 解析记录
- **域名绑定**：一台机器可绑定多个域名，支持自动获取 Zone ID
- **实时状态**：在线状态检测、同步状态显示、IP 历史记录
- **Web 管理界面**：深色/明亮主题切换、响应式设计、移动端适配

## 系统架构

```
┌─────────────────┐         ┌─────────────────┐
│   上报端        │  HTTP   │    管理端       │
│  (reporter)     │ ──────> │   (manager)     │
│                 │         │                 │
│ - 获取本机IP    │         │ - Web UI        │
│ - 定时上报      │         │ - 机器/域名管理 │
│ - IPv6 支持     │         │ - DNS 同步      │
└─────────────────┘         └────────┬────────┘
                                     │
                                     │ API
                                     ▼
                            ┌─────────────────┐
                            │   Cloudflare    │
                            │   DNS API       │
                            └─────────────────┘
```

**架构特点：**

- **上报端无状态**：单文件 Python 脚本，无需数据库，适合嵌入式设备
- **管理端轻量**：FastAPI + SQLite，单容器部署，资源占用低
- **解耦设计**：上报端与管理端分离，可独立部署、独立扩容

## 项目特点

### 为什么选择 DDNS Manager？

| 特点 | 说明 |
|------|------|
| 🚀 **极速部署** | 一行 Docker 命令即可启动，无需复杂配置 |
| 📦 **镜像小巧** | 基于 python:3.12-slim，镜像体积小、启动快 |
| 🔐 **Token 认证** | 每台机器独立 Token，安全可靠 |
| 🌐 **IPv6 优先** | 原生支持 IPv6，适合家庭宽带、云服务器 |
| 🎨 **现代 UI** | Vue 3 + Tailwind CSS，支持深色/明亮主题 |
| ⚡ **实时同步** | IP 变化即时更新 DNS，支持一键批量同步 |
| 💾 **历史记录** | 保留 IP 上报历史，便于追溯 |
| 🔧 **灵活配置** | 支持全局默认间隔和单机独立配置 |

### 与其他方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **ddns-go** | 功能全面、社区活跃 | Go 语言部署、配置相对复杂 |
| **Cloudflare DDNS 脚本** | 简单直接 | 无管理界面、多机器管理困难 |
| **DDNS Manager** | 轻量、Web UI、多机器管理 | 功能相对精简 |

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

1. 在 Cloudflare 控制台创建 API Token，权限选择 `Zone.DNS` 编辑
2. 在管理端「设置」页面填入 API Token
3. 给机器绑定域名（Zone ID 自动获取）
4. 点击「测试连接」验证配置

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

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/report` | POST | 上报 IP 地址 |
| `/api/sync/{machine_id}` | POST | 同步 DNS 记录 |
| `/api/machines` | GET/POST | 机器列表/创建 |
| `/api/machines/{id}` | GET/DELETE/PATCH | 机器详情/删除/更新 |
| `/api/domains` | GET/POST | 域名列表/创建 |
| `/api/domains/{id}` | DELETE | 删除域名 |
| `/api/settings` | GET/POST | 配置管理 |
| `/api/cloudflare/test` | POST | 测试 Cloudflare 连接 |

---

## 技术栈

**管理端**
- FastAPI - Web 框架
- SQLAlchemy - ORM
- SQLite - 数据库
- Jinja2 - 模板引擎
- Vue 3 (CDN) - 前端框架
- Tailwind CSS (CDN) - 样式框架

**上报端**
- Python 标准库
- requests - HTTP 客户端
# OREP 云服务器部署上线指南

> 适用场景：将当前 OREP 项目部署到一台云服务器，用域名和 HTTPS 证书正式对外访问。  
> 当前检查日期：2026-05-19  
> 当前项目结构依据：`backend/`、`frontend/user/`、`frontend/admin/`、`ai-scoring/`、`signaling/`、`recording-bot/`、`livekit.yaml`、`deploy/docker-compose.yml`、`deploy/nginx.conf`

---

## 1. 结论先说

### 1.1 4 核 16G 是否够用

**够用，但只建议作为 OREP 第一阶段单机上线配置，不建议承诺高并发。**

当前 OREP 不是单纯的前后端系统，它至少包含：

- 用户端 Vue 前端
- 管理端 Vue 前端
- Spring Boot 后端
- MySQL 8.0
- Redis
- Nginx 反向代理
- Socket.IO 信令服务
- LiveKit Server
- MinIO 对象存储
- 录制 Bot，依赖 Puppeteer/Chromium
- AI 评分 / AI PPT 生成服务，Python + FastAPI + ffmpeg + 多模型 API

在 4 核 16G 服务器上，建议按下面规模上线：

| 使用场景 | 建议结论 |
|---|---|
| 试运行、演示、学校内部小规模使用 | 4 核 16G 可以 |
| 同时 1-2 个会议房间，每个房间 5-10 人 | 基本可以 |
| 同时开启 1 路会议录制 | 可以，但要观察 CPU 和内存 |
| 同时多人生成 PPT / 多个 AI 评分任务 | 勉强，容易排队或变慢 |
| 3 个以上会议房间同时运行，且有录制和 AI 任务 | 建议升级到 8 核 32G |
| 正式长期承载多个学校/多租户 | 建议至少 8 核 32G，数据库和对象存储后期拆出去 |

### 1.2 资源估算

| 服务 | 建议内存预算 | CPU 压力 | 说明 |
|---|---:|---|---|
| 操作系统 + Docker | 1-1.5G | 低 | Ubuntu Server 无桌面即可 |
| MySQL 8.0 | 1-2G | 中 | 不建议只给 512M，正式环境太紧 |
| Redis | 256-512M | 低 | 缓存和 LiveKit 可共用，但生产建议设置密码 |
| Spring Boot 后端 | 1-1.5G | 中 | Java 21，建议限制 JVM 堆 |
| 用户端/管理端 Nginx | 128-256M | 低 | 静态文件服务 |
| 总入口 Nginx | 128-256M | 低 | HTTPS、反向代理、WebSocket |
| Socket.IO 信令 | 256-512M | 中 | 房间人数多时增长 |
| LiveKit Server | 512M-2G+ | 中高 | 与房间数、视频流数量、码率强相关 |
| MinIO | 512M-1G | 中 | 录像和 AI 报告占磁盘更多 |
| 录制 Bot | 1.5-3G | 高 | Chromium 录制很吃内存和 CPU |
| AI 服务 | 2-5G | 中高 | PPT 生成、音视频处理、PDF/图片转换会吃内存 |
| 系统余量 | 2-3G | - | 必须保留，避免 OOM |

**结论：**4 核 16G 可以跑完整 OREP，但要控制同时会议数、同时录制数和 AI 任务并发。上线初期建议加限制：同一时间最多 1 路录制、AI PPT 生成任务排队执行、会议房间人数先按 10 人以内验收。

### 1.3 磁盘和带宽建议

4 核 16G 只是 CPU/内存配置，OREP 还必须重视磁盘和带宽：

- 系统盘：至少 100GB SSD，推荐 200GB。
- 录像和上传材料增长很快，MinIO 数据目录必须持久化。
- 如有大量会议录像，建议后期把 MinIO 迁移到云厂商对象存储。
- 带宽建议至少 10Mbps 起步；视频会议人数多时优先考虑 20Mbps 以上。
- LiveKit 媒体端口必须放行 UDP 端口段，否则浏览器可能能进房间但听不到/看不到。

---

## 2. 操作系统推荐

### 2.1 推荐系统

**首选：Ubuntu Server 24.04 LTS**

理由：

- Docker、Nginx、证书、运维资料最成熟，部署和排错成本低。
- 24.04 LTS 已经稳定运行较长时间，适合作为生产首发系统。
- Docker 官方文档明确支持 Ubuntu 24.04 LTS 和 26.04 LTS。
- Ubuntu 26.04 LTS 已在 2026-04 发布，但刚发布不久，除非云厂商镜像和 Docker 生态已经充分验证，否则 OREP 首次上线更稳妥地选 24.04 LTS。

可选：

| 系统 | 是否推荐 | 说明 |
|---|---|---|
| Ubuntu Server 24.04 LTS | 推荐 | 最适合当前 OREP，上线稳 |
| Ubuntu Server 26.04 LTS | 可选 | 最新 LTS，已发布，但刚发布，首发上线略激进 |
| Debian 12 | 可选 | 稳定，但部分资料不如 Ubuntu 直接 |
| CentOS 7 | 不推荐 | 太老，不适合新项目上线 |
| Windows Server | 不推荐 | Docker、Nginx、LiveKit、AI 服务维护成本更高 |

参考资料：

- Ubuntu 官方当前版本列表显示 Ubuntu 26.04 LTS 于 2026-04-23 发布，24.04 LTS 标准支持到 2029 年。
- Docker 官方 Ubuntu 安装文档列出了 Docker Engine 支持 Ubuntu 26.04 LTS、25.10、24.04 LTS、22.04 LTS。

---

## 3. 推荐部署架构

### 3.1 单机 Docker Compose 架构

第一阶段建议采用单机 Docker Compose，方便部署和维护：

```text
用户浏览器
  |
  | HTTPS:443
  v
Nginx 总入口
  |-- /                  -> 用户端 frontend-user
  |-- /admin/            -> 管理端 frontend-admin
  |-- /api/              -> Spring Boot backend
  |-- /api/ai/           -> AI 服务 ai-scoring
  |-- /api/ppt/          -> AI 服务 ai-scoring
  |-- /socket.io/        -> signaling
  |-- /room/             -> signaling
  |-- /ws-stomp          -> backend WebSocket
  |-- /livekit/          -> LiveKit WebSocket/HTTP

内部服务：
  backend -> MySQL / Redis / MinIO / recording-bot / LiveKit
  ai-scoring -> MinIO / backend callback / 外部大模型 API
  recording-bot -> LiveKit / backend callback
  LiveKit -> Redis
```

### 3.2 对公网开放的端口

| 端口 | 协议 | 用途 | 是否必须开放公网 |
|---:|---|---|---|
| 22 | TCP | SSH | 必须，但建议限制 IP |
| 80 | TCP | HTTP 跳转 HTTPS | 建议开放 |
| 443 | TCP | HTTPS 主入口 | 必须 |
| 7881 | TCP | LiveKit TCP fallback | 建议开放 |
| 50100-50200 | UDP | LiveKit WebRTC 媒体端口 | 必须 |

不建议公网开放：

- 3306 MySQL
- 6379 Redis
- 8080 backend
- 8090 AI service
- 8091 recording-bot
- 9000/9001 MinIO
- 3000 signaling
- 7880 LiveKit HTTP

这些服务应只在 Docker 内网中访问，由 Nginx 统一代理。

---

## 4. 域名和证书规划

下面用占位符表示，你上线时替换为真实值：

```bash
DOMAIN=orep.example.com
PUBLIC_IP=你的服务器公网IP
CERT_CRT=/opt/orep/certs/fullchain.pem
CERT_KEY=/opt/orep/certs/privkey.pem
```

DNS 解析：

| 记录类型 | 主机记录 | 值 |
|---|---|---|
| A | `orep` 或 `@` | 服务器公网 IP |

访问路径建议：

| 功能 | URL |
|---|---|
| 用户端 | `https://orep.example.com/` |
| 管理端 | `https://orep.example.com/admin/` |
| 后端 API | `https://orep.example.com/api/` |
| AI API | `https://orep.example.com/api/ai/`、`https://orep.example.com/api/ppt/` |
| LiveKit | `wss://orep.example.com/livekit` |
| Socket.IO | `https://orep.example.com/socket.io/` |

---

## 5. 当前项目里必须改的配置点

> 已按本节落地生产配置文件：`deploy/docker-compose.prod.yml`、`deploy/nginx.prod.conf`、`deploy/livekit.prod.yaml`、`deploy/render-livekit-config.sh`、`deploy/.env.production.example`。本地开发配置保持可运行，生产环境通过 `.env.production` 覆盖。

### 5.1 总体原则

生产环境不要把域名、IP、密码、API Key 写死在代码里。推荐做法：

- Java 后端：用环境变量覆盖 `application.yml`。
- Python AI 服务：用 `.env.production` 或 Compose `env_file`。
- Node 服务：用环境变量。
- 前端：生产环境尽量使用同源相对路径，例如 `/api`、`/socket.io`、`/livekit`。
- Nginx：负责域名、HTTPS、路径转发。

### 5.2 需要检查和修改的文件

| 文件 | 当前问题 | 上线处理 |
|---|---|---|
| `deploy/nginx.conf` | 只监听 80，缺少 HTTPS 和 `/livekit` 代理 | 改成 80 跳 443，443 配证书，补 `/livekit` |
| `deploy/docker-compose.yml` | 有默认密码、真实 API Key、内网 IP、没有 LiveKit 服务 | 改用 `.env.production`，补 LiveKit 服务，删除明文密钥 |
| `backend/src/main/resources/application.yml` | 有 `localhost`、`127.0.0.1`、`172.168.1.173` 和明文密码 | 保留默认开发配置，生产用环境变量覆盖 |
| `livekit.yaml` | `node_ip: 172.168.1.173` 是本地 IP | 生产改为公网 IP 或 `use_external_ip: true` |
| `livekit-egress.yaml` | 使用 `127.0.0.1` | 如果启用 Egress，改 Docker 内网服务名 |
| `livekit-proxy.js` | 写死 `172.168.1.173` | 生产建议不用它，交给 Nginx 代理；若保留则改为环境变量 |
| `ai-scoring/.env` | 有本地 MinIO、回调地址和 API Key | 不要直接上传生产，改 `.env.production` |
| `recording-bot/src/server.js` | fallback 写死 `172.168.1.173` | Compose 环境变量覆盖；后续建议代码默认值改为服务名 |
| `frontend/user/src/views/MeetingRoom.vue` | 已使用同源 `/livekit` | 生产无需改，重点是 Nginx 要代理 `/livekit` |
| `frontend/user/vite.config.js` | 本地开发代理 | 只影响开发环境，生产构建后不使用 |
| `frontend/admin/vite.config.js` | 本地开发代理里有 `172.168.1.173` | 只影响开发，但建议后续改成 `localhost` 或环境变量 |
| `frontend/*/nginx-default.conf` | `server_name 172.168.1.173` | 容器内静态 Nginx 可改成 `_`，真实域名放总入口 Nginx |

### 5.3 上线前必须轮换密钥

当前项目配置中出现过数据库密码、邮箱授权码、AI API Key、LiveKit Secret、MinIO 密钥等敏感信息。上线前请全部重新生成：

- MySQL root 密码
- Redis 密码
- JWT Secret
- LiveKit API Secret
- MinIO Access Key / Secret Key
- Recording Bot Secret
- 邮箱授权码
- DashScope / DeepSeek / MiniMax / MIMO 等所有 AI Key

已经写入过代码仓库或文档的密钥，都按“已泄露”处理。

---

## 6. 服务器初始化

以下命令以 Ubuntu Server 24.04 LTS 为例。

### 6.1 创建部署目录

```bash
sudo mkdir -p /opt/orep
sudo chown -R $USER:$USER /opt/orep
mkdir -p /opt/orep/certs /opt/orep/data/mysql /opt/orep/data/minio /opt/orep/logs
```

### 6.2 安装基础工具

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release ufw tar unzip htop jq
```

### 6.3 安装 Docker Engine 和 Compose 插件

生产环境建议使用 Docker 官方 apt 仓库安装，不建议用一键脚本。

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

重新登录 SSH 后验证：

```bash
docker version
docker compose version
docker run --rm hello-world
```

### 6.4 配置防火墙

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 7881/tcp
sudo ufw allow 50100:50200/udp
sudo ufw enable
sudo ufw status
```

云厂商安全组也要同步放行这些端口，尤其是 `50100-50200/udp`。

---

## 7. 打包和上传项目

### 7.1 本地打包

在本地项目根目录执行：

```bash
cd /Users/liuyixing/项目/OREP

tar czf orep-release-$(date +%F).tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='*/node_modules' \
  --exclude='target' \
  --exclude='*/dist' \
  --exclude='logs' \
  --exclude='minio-data' \
  --exclude='ai-scoring/uploads' \
  --exclude='ai-scoring/**/*.db' \
  --exclude='outputs' \
  .
```

说明：

- 不要把本地 `minio-data`、`logs`、AI 临时产物打进部署包。
- 不要把本地 `.env` 当生产配置直接上传。
- 证书如果已经在服务器上，可以不打包本地 `certs/`。

### 7.2 上传到服务器

```bash
scp orep-release-2026-05-19.tar.gz user@你的服务器IP:/opt/orep/
```

### 7.3 解压

```bash
ssh user@你的服务器IP
cd /opt/orep
tar xzf orep-release-2026-05-19.tar.gz
```

建议最终目录结构：

```text
/opt/orep/
  backend/
  frontend/
  ai-scoring/
  signaling/
  recording-bot/
  sql/
  deploy/
  livekit.yaml
  certs/
  data/
```

---

## 8. 生产环境变量文件

在服务器创建：

```bash
cd /opt/orep
nano .env.production
```

模板如下：

```bash
# 基础
DOMAIN=orep.example.com
PUBLIC_IP=你的服务器公网IP
TZ=Asia/Shanghai

# MySQL
MYSQL_ROOT_PASSWORD=请改成强密码
MYSQL_DATABASE=orep
MYSQL_USER=orep_app
MYSQL_PASSWORD=请改成强密码

# Redis
REDIS_PASSWORD=请改成强密码

# Spring Boot
JWT_SECRET=请生成至少64位随机字符串
SPRING_PROFILES_ACTIVE=prod
JAVA_OPTS=-Xms512m -Xmx1200m -XX:+UseG1GC

# LiveKit
LIVEKIT_API_KEY=orep-prod-key
LIVEKIT_API_SECRET=请生成至少32位随机字符串
LIVEKIT_WS_URL=wss://orep.example.com/livekit

# Recording Bot
RECORDING_BOT_SECRET=请生成随机字符串

# MinIO
MINIO_ROOT_USER=请改成随机用户名
MINIO_ROOT_PASSWORD=请改成强密码
MINIO_BUCKET_RECORDINGS=meeting-recordings

# AI 服务
DASHSCOPE_API_KEY=替换为生产key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DEEPSEEK_API_KEY=替换为生产key
DEEPSEEK_BASE_URL=https://api.deepseek.com
MINIMAX_API_KEY=替换为生产key
MINIMAX_BASE_URL=https://api.minimax.chat/v1

PPT_TEXT_API_KEY=替换为生产key
PPT_TEXT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PPT_TEXT_MODEL=qwen3.6-plus
PPT_HTML_API_KEY=替换为生产key
PPT_HTML_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PPT_HTML_MODEL=qwen3-coder-plus
PPT_VISION_API_KEY=替换为生产key
PPT_VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PPT_VISION_MODEL=qwen3.6-plus

# 邮件
MAIL_HOST=smtp.qq.com
MAIL_PORT=587
MAIL_USERNAME=你的邮箱
MAIL_PASSWORD=你的邮箱授权码
MAIL_FROM=你的邮箱
```

生成随机密钥示例：

```bash
openssl rand -base64 48
openssl rand -hex 32
```

权限：

```bash
chmod 600 /opt/orep/.env.production
```

---

## 9. 推荐生产 Docker Compose

当前 `deploy/docker-compose.yml` 可以作为基础，但上线建议改成下面这种结构：统一读取 `.env.production`，只暴露 Nginx 和 LiveKit 媒体端口。

建议新建：

```bash
nano /opt/orep/deploy/docker-compose.prod.yml
```

内容：

```yaml
services:
  mysql:
    image: mysql:8.0
    container_name: orep-mysql
    env_file:
      - ../.env.production
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --default-time-zone=+08:00
    volumes:
      - mysql_data:/var/lib/mysql
      - ../sql/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
      - ../sql/ppt_tables.sql:/docker-entrypoint-initdb.d/02-ppt.sql:ro
      - ../sql/ppt_history_tables.sql:/docker-entrypoint-initdb.d/03-ppt-history.sql:ro
      - ../sql/meeting_recording_upgrade.sql:/docker-entrypoint-initdb.d/04-recording.sql:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -uroot -p$${MYSQL_ROOT_PASSWORD} --silent"]
      interval: 10s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    container_name: orep-redis
    env_file:
      - ../.env.production
    command: ["redis-server", "--appendonly", "yes", "--requirepass", "${REDIS_PASSWORD}"]
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a $${REDIS_PASSWORD} ping | grep PONG"]
      interval: 10s
      timeout: 5s
      retries: 10

  minio:
    image: minio/minio:latest
    container_name: orep-minio
    env_file:
      - ../.env.production
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    restart: unless-stopped

  livekit:
    image: livekit/livekit-server:v1.9.12
    container_name: orep-livekit
    env_file:
      - ../.env.production
    command: --config /etc/livekit.yaml
    volumes:
      - ./livekit.rendered.yaml:/etc/livekit.yaml:ro
    ports:
      - "7881:7881/tcp"
      - "50100-50200:50100-50200/udp"
    depends_on:
      - redis
    restart: unless-stopped

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: orep-backend
    env_file:
      - ../.env.production
    environment:
      JAVA_TOOL_OPTIONS: ${JAVA_OPTS}
      SERVER_PORT: 8080
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql:3306/${MYSQL_DATABASE}?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
      SPRING_DATASOURCE_USERNAME: root
      SPRING_DATASOURCE_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      SPRING_DATA_REDIS_HOST: redis
      SPRING_DATA_REDIS_PORT: 6379
      SPRING_DATA_REDIS_PASSWORD: ${REDIS_PASSWORD}
      SPRING_MAIL_HOST: ${MAIL_HOST}
      SPRING_MAIL_PORT: ${MAIL_PORT}
      SPRING_MAIL_USERNAME: ${MAIL_USERNAME}
      SPRING_MAIL_PASSWORD: ${MAIL_PASSWORD}
      OREP_JWT_SECRET: ${JWT_SECRET}
      OREP_EMAIL_FROM: ${MAIL_FROM}
      LIVEKIT_API_KEY: ${LIVEKIT_API_KEY}
      LIVEKIT_API_SECRET: ${LIVEKIT_API_SECRET}
      LIVEKIT_WS_URL: ${LIVEKIT_WS_URL}
      LIVEKIT_EGRESS_API_URL: http://livekit:7880
      LIVEKIT_EGRESS_S3_ENDPOINT: http://minio:9000
      LIVEKIT_EGRESS_S3_ACCESS_KEY: ${MINIO_ROOT_USER}
      LIVEKIT_EGRESS_S3_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      LIVEKIT_EGRESS_S3_BUCKET: ${MINIO_BUCKET_RECORDINGS}
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      MINIO_BUCKET: ${MINIO_BUCKET_RECORDINGS}
      RECORDING_MODE: bot
      RECORDING_BOT_URL: http://recording-bot:8091
      RECORDING_BOT_SECRET: ${RECORDING_BOT_SECRET}
      RECORDING_CALLBACK_BASE_URL: http://backend:8080
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_started
      livekit:
        condition: service_started
    restart: unless-stopped

  ai-scoring:
    build:
      context: ../ai-scoring
      dockerfile: Dockerfile
    container_name: orep-ai-scoring
    env_file:
      - ../.env.production
    environment:
      HOST: 0.0.0.0
      PORT: 8090
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      BACKEND_CALLBACK_URL: http://backend:8080/api/ai-score/callback
      CHAT_CALLBACK_URL: http://backend:8080/api/ai-chat/callback
    volumes:
      - ai_uploads:/app/uploads
    depends_on:
      - minio
      - backend
    restart: unless-stopped

  recording-bot:
    build:
      context: ../recording-bot
      dockerfile: Dockerfile
    container_name: orep-recording-bot
    env_file:
      - ../.env.production
    environment:
      LIVEKIT_URL: ws://livekit:7880
      LIVEKIT_API_KEY: ${LIVEKIT_API_KEY}
      LIVEKIT_API_SECRET: ${LIVEKIT_API_SECRET}
      BOT_PORT: 8091
      BACKEND_CALLBACK_BASE_URL: http://backend:8080
      RECORDING_BOT_SECRET: ${RECORDING_BOT_SECRET}
    volumes:
      - recording_bot_data:/app/recordings
    depends_on:
      - livekit
      - backend
      - minio
    restart: unless-stopped
    shm_size: "1gb"

  signaling:
    build:
      context: ../signaling
      dockerfile: Dockerfile
    container_name: orep-signaling
    environment:
      PORT: 3000
    restart: unless-stopped

  frontend-user:
    build:
      context: ../frontend/user
      dockerfile: Dockerfile
    container_name: orep-user
    restart: unless-stopped

  frontend-admin:
    build:
      context: ../frontend/admin
      dockerfile: Dockerfile
    container_name: orep-admin
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: orep-nginx
    env_file:
      - ../.env.production
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/conf.d/default.conf:ro
      - ../certs:/etc/nginx/certs:ro
    depends_on:
      - frontend-user
      - frontend-admin
      - backend
      - ai-scoring
      - signaling
      - livekit
    restart: unless-stopped

volumes:
  mysql_data:
  redis_data:
  minio_data:
  ai_uploads:
  recording_bot_data:
```

注意：

- Compose 中 `${变量名}` 来自 `.env.production`，执行命令时要加 `--env-file ../.env.production`。
- 如果 Docker Compose 无法替换 `env_file` 中的变量，请把 `.env.production` 复制为 `/opt/orep/deploy/.env`，或者执行时显式传 `--env-file`。
- `depends_on.condition` 对新版 Docker Compose 插件可用；如果你的版本不支持，去掉 condition，改用服务自身重试和手动观察日志。

---

## 10. LiveKit 生产配置

当前根目录 `livekit.yaml` 是本地开发配置，里面有：

```yaml
node_ip: 172.168.1.173
redis:
  address: 127.0.0.1:6379
```

生产环境不要直接用它。建议新建模板文件：

```bash
nano /opt/orep/deploy/livekit.prod.yaml
```

内容：

```yaml
port: 7880
bind_addresses:
  - "0.0.0.0"

rtc:
  tcp_port: 7881
  port_range_start: 50100
  port_range_end: 50200
  use_external_ip: true
  # 如果 use_external_ip 获取不到正确公网 IP，可改为：
  # node_ip: 你的服务器公网IP

keys:
  ${LIVEKIT_API_KEY}: ${LIVEKIT_API_SECRET}

redis:
  address: redis:6379
  password: ${REDIS_PASSWORD}

logging:
  level: info
```

重要：

- 生产浏览器连接地址使用 `wss://你的域名/livekit`。
- LiveKit 容器内部 HTTP 端口 `7880` 不对公网开放，由 Nginx 代理。
- 媒体端口 `7881/tcp` 和 `50100-50200/udp` 要对公网开放。
- 如果云服务器有 NAT 或弹性公网 IP，优先验证浏览器是否能拿到公网 ICE candidate。

LiveKit 配置文件本身不会像 Docker Compose 一样稳定替换 `${LIVEKIT_API_KEY}` 变量，所以启动前要用 `envsubst` 生成最终配置：

```bash
cd /opt/orep/deploy
set -a
. ../.env.production
set +a
envsubst < livekit.prod.yaml > livekit.rendered.yaml
chmod 600 livekit.rendered.yaml
```

上面第 9 节的 Compose 示例已经挂载 `livekit.rendered.yaml`。每次修改 LiveKit Key、Redis 密码或公网 IP 后，都要重新生成这个文件并重启 LiveKit：

```bash
docker compose --env-file ../.env.production -f docker-compose.prod.yml restart livekit
```

---

## 11. Nginx 生产配置

当前 `deploy/nginx.conf` 只监听 80。生产建议新建：

```bash
nano /opt/orep/deploy/nginx.prod.conf
```

内容：

```nginx
server {
    listen 80;
    server_name orep.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name orep.example.com;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    client_max_body_size 500M;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;

    location /admin/ {
        proxy_pass http://frontend-admin:80/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location /api/ai/ {
        proxy_pass http://ai-scoring:8090/api/ai/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 900s;
        client_max_body_size 500M;
    }

    location /api/ppt/ {
        proxy_pass http://ai-scoring:8090/api/ppt/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 900s;
        client_max_body_size 500M;
    }

    location /api/ {
        proxy_pass http://backend:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        client_max_body_size 500M;
    }

    location /uploads/ {
        proxy_pass http://backend:8080/uploads/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location /socket.io/ {
        proxy_pass http://signaling:3000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400s;
    }

    location /room/ {
        proxy_pass http://signaling:3000/room/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws-stomp {
        proxy_pass http://backend:8080/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    # LiveKit: 前端连接 wss://域名/livekit，LiveKit client 会请求 /livekit/rtc/v1。
    # 当前项目曾用路径重写解决 LiveKit Client 2.x /rtc/v1 与 LiveKit Server /rtc 的兼容问题。
    location /livekit/ {
        rewrite ^/livekit/rtc/v1(.*)$ /rtc$1 break;
        rewrite ^/livekit/(.*)$ /$1 break;

        proxy_pass http://livekit:7880;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 86400s;
    }

    location = /livekit {
        return 301 /livekit/;
    }

    location / {
        proxy_pass http://frontend-user:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

替换：

```nginx
server_name orep.example.com;
```

为你的真实域名。

证书放置：

```bash
cp fullchain.pem /opt/orep/certs/fullchain.pem
cp privkey.pem /opt/orep/certs/privkey.pem
chmod 600 /opt/orep/certs/privkey.pem
```

---

## 12. 后端生产配置如何覆盖

当前后端配置文件：

```text
backend/src/main/resources/application.yml
```

它适合本地开发，不建议直接改成生产固定值。Docker Compose 里可以用环境变量覆盖 Spring Boot 配置。

重点映射关系：

| application.yml 配置 | 生产环境变量 |
|---|---|
| `spring.datasource.url` | `SPRING_DATASOURCE_URL` |
| `spring.datasource.username` | `SPRING_DATASOURCE_USERNAME` |
| `spring.datasource.password` | `SPRING_DATASOURCE_PASSWORD` |
| `spring.data.redis.host` | `SPRING_DATA_REDIS_HOST` |
| `spring.data.redis.password` | `SPRING_DATA_REDIS_PASSWORD` |
| `orep.jwt.secret` | `OREP_JWT_SECRET` |
| `livekit.api-key` | `LIVEKIT_API_KEY` |
| `livekit.api-secret` | `LIVEKIT_API_SECRET` |
| `livekit.ws-url` | `LIVEKIT_WS_URL` |
| `minio.endpoint` | `MINIO_ENDPOINT` |
| `recording.bot.url` | `RECORDING_BOT_URL` |
| `recording.callback.base-url` | `RECORDING_CALLBACK_BASE_URL` |

上线建议把后端 `application.yml` 中的敏感默认值改成占位或环境变量形式，例如：

```yaml
spring:
  datasource:
    url: ${SPRING_DATASOURCE_URL:jdbc:mysql://localhost:3306/orep?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true}
    username: ${SPRING_DATASOURCE_USERNAME:root}
    password: ${SPRING_DATASOURCE_PASSWORD:12345678}
  data:
    redis:
      host: ${SPRING_DATA_REDIS_HOST:127.0.0.1}
      port: ${SPRING_DATA_REDIS_PORT:6379}
      password: ${SPRING_DATA_REDIS_PASSWORD:}

orep:
  jwt:
    secret: ${OREP_JWT_SECRET:dev-only-secret-change-me}

livekit:
  api-key: ${LIVEKIT_API_KEY:devkey-orep-local}
  api-secret: ${LIVEKIT_API_SECRET:dev-secret-change-me}
  ws-url: ${LIVEKIT_WS_URL:ws://127.0.0.1:7880}

minio:
  endpoint: ${MINIO_ENDPOINT:http://127.0.0.1:9000}
  access-key: ${MINIO_ACCESS_KEY:minioadmin}
  secret-key: ${MINIO_SECRET_KEY:minioadmin}
  bucket: ${MINIO_BUCKET:meeting-recordings}
```

如果暂时不改代码，也可以依赖 Compose 环境变量覆盖；但长期建议把 `application.yml` 清理干净，避免再次误传密钥。

---

## 13. 前端打包方法

### 13.1 用户端

本地或服务器均可构建。Dockerfile 已经定义：

```text
frontend/user/Dockerfile
```

手动构建命令：

```bash
cd /opt/orep/frontend/user
npm ci
npm run build
```

Docker 构建：

```bash
cd /opt/orep/deploy
docker compose --env-file ../.env.production -f docker-compose.prod.yml build frontend-user
```

生产访问后端时，用户端前端代码主要使用相对路径：

- `/api/...`
- `/api/livekit/token`
- `/livekit`

所以**不需要在前端代码里写死域名**，Nginx 代理配置正确即可。

### 13.2 管理端

手动构建：

```bash
cd /opt/orep/frontend/admin
npm ci
npm run build
```

Docker 构建：

```bash
cd /opt/orep/deploy
docker compose --env-file ../.env.production -f docker-compose.prod.yml build frontend-admin
```

管理端 `frontend/admin/src/api/request.js` 中 `baseURL: ''`，表示同源请求，生产也不需要写死域名。

### 13.3 Vite 配置是否需要改

`frontend/user/vite.config.js` 和 `frontend/admin/vite.config.js` 里的 proxy 只影响本地开发服务器，不影响 `npm run build` 后的生产静态文件。

但为了后续维护，建议把 `frontend/admin/vite.config.js` 中的：

```js
target: 'http://172.168.1.173:8080'
```

改成本地开发值：

```js
target: 'http://localhost:8080'
```

生产环境的域名交给 Nginx，不交给 Vite。

---

## 14. 后端打包方法

Dockerfile 已经定义：

```text
backend/Dockerfile
```

手动编译：

```bash
cd /opt/orep/backend
mvn clean package -DskipTests
```

Docker 构建：

```bash
cd /opt/orep/deploy
docker compose --env-file ../.env.production -f docker-compose.prod.yml build backend
```

启动后检查：

```bash
docker logs -f orep-backend
curl -k https://orep.example.com/api/auth/check
```

如果没有公开的 health API，可用登录接口或实际页面请求验证。

---

## 15. AI 服务打包和部署

AI 服务目录：

```text
ai-scoring/
```

Dockerfile 已经定义：

```text
ai-scoring/Dockerfile
```

依赖包括：

- FastAPI / Uvicorn
- ffmpeg
- DashScope / OpenAI-compatible SDK
- librosa / scipy / parselmouth
- python-pptx / PyMuPDF / reportlab / Pillow
- Playwright 相关能力

构建：

```bash
cd /opt/orep/deploy
docker compose --env-file ../.env.production -f docker-compose.prod.yml build ai-scoring
```

启动：

```bash
docker compose --env-file ../.env.production -f docker-compose.prod.yml up -d ai-scoring
```

检查：

```bash
docker logs -f orep-ai-scoring
curl -k https://orep.example.com/api/ai/health
curl -k https://orep.example.com/api/ppt/health
```

注意：

- `ai-scoring/.env` 不要直接作为生产配置上传。
- `MINIO_ENDPOINT` 在容器内应为 `minio:9000`，不是服务器公网域名。
- `BACKEND_CALLBACK_URL` 在容器内应为 `http://backend:8080/api/ai-score/callback`。
- 如果 PPT 生成需要浏览器渲染能力，而容器内 Playwright 浏览器缺失，需要在 Dockerfile 里补安装浏览器依赖。当前 Dockerfile 没有显式执行 `playwright install`，如遇到预览/截图失败，再加：

```dockerfile
RUN python -m playwright install --with-deps chromium
```

这会明显增加镜像体积。

---

## 16. 信令服务打包和部署

信令服务目录：

```text
signaling/
```

Dockerfile：

```text
signaling/Dockerfile
```

构建：

```bash
cd /opt/orep/deploy
docker compose --env-file ../.env.production -f docker-compose.prod.yml build signaling
```

检查：

```bash
docker logs -f orep-signaling
curl -k https://orep.example.com/socket.io/
```

说明：

- `signaling/server.js` 会尝试读取 `../certs`，但 Docker 容器内通常读不到。
- 生产建议让 signaling 在容器内跑 HTTP，由总 Nginx 统一提供 HTTPS。
- 浏览器访问的是 `https://域名/socket.io/`，Nginx 再转给 `http://signaling:3000/socket.io/`。

---

## 17. LiveKit 服务部署

LiveKit 不需要本项目自己打包，直接用官方镜像更好维护：

```bash
docker pull livekit/livekit-server:v1.9.12
```

部署由 `docker-compose.prod.yml` 中的 `livekit` 服务负责。

检查日志：

```bash
docker logs -f orep-livekit
```

检查 Nginx 代理：

```bash
curl -k https://orep.example.com/livekit/
```

浏览器会议页最终会连接：

```text
wss://orep.example.com/livekit
```

当前用户端代码位置：

```text
frontend/user/src/views/MeetingRoom.vue
```

关键逻辑：

```js
const connectUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/livekit`
```

所以生产环境重点不是改前端，而是 Nginx 必须正确代理 `/livekit/`。

---

## 18. 录制 Bot 部署

录制 Bot 目录：

```text
recording-bot/
```

Dockerfile：

```text
recording-bot/Dockerfile
```

构建：

```bash
cd /opt/orep/deploy
docker compose --env-file ../.env.production -f docker-compose.prod.yml build recording-bot
```

启动：

```bash
docker compose --env-file ../.env.production -f docker-compose.prod.yml up -d recording-bot
```

关键环境变量：

```bash
LIVEKIT_URL=ws://livekit:7880
LIVEKIT_API_KEY=生产 LiveKit API Key
LIVEKIT_API_SECRET=生产 LiveKit API Secret
BACKEND_CALLBACK_BASE_URL=http://backend:8080
RECORDING_BOT_SECRET=生产录制密钥
```

注意：

- 录制 Bot 使用 Puppeteer/Chromium，内存压力大。
- Compose 中建议设置 `shm_size: "1gb"`，否则 Chromium 可能崩溃。
- 4 核 16G 单机建议一次只允许 1 路录制。
- 如果录制失败，先看：

```bash
docker logs -f orep-recording-bot
docker logs -f orep-livekit
docker logs -f orep-backend
```

---

## 19. 一键启动

首次构建并启动：

```bash
cd /opt/orep/deploy
docker compose --env-file ../.env.production -f docker-compose.prod.yml build
docker compose --env-file ../.env.production -f docker-compose.prod.yml up -d
```

查看状态：

```bash
docker compose --env-file ../.env.production -f docker-compose.prod.yml ps
```

查看资源：

```bash
docker stats
```

查看日志：

```bash
docker compose --env-file ../.env.production -f docker-compose.prod.yml logs -f nginx
docker compose --env-file ../.env.production -f docker-compose.prod.yml logs -f backend
docker compose --env-file ../.env.production -f docker-compose.prod.yml logs -f ai-scoring
docker compose --env-file ../.env.production -f docker-compose.prod.yml logs -f livekit
```

---

## 20. 上线验收清单

### 20.1 基础访问

```bash
curl -I http://orep.example.com
curl -Ik https://orep.example.com
curl -Ik https://orep.example.com/admin/
```

预期：

- HTTP 80 自动跳转 HTTPS。
- HTTPS 证书有效。
- 用户端首页正常。
- 管理端页面正常。

### 20.2 后端

```bash
curl -k https://orep.example.com/api/auth/check
```

或直接在浏览器登录管理员账号。

### 20.3 AI 服务

```bash
curl -k https://orep.example.com/api/ai/health
curl -k https://orep.example.com/api/ppt/health
```

如果接口路径在实际代码中不同，以 `ai-scoring/main.py` 输出的路由为准。

### 20.4 LiveKit

浏览器进入会议页，检查：

- 能进入会议房间。
- 麦克风可开启。
- 摄像头可开启。
- 屏幕共享可开启。
- 两台不同网络设备能互相听到/看到。
- 浏览器控制台没有 WebSocket 404、ICE failed、DTLS failed 等错误。

服务器侧检查：

```bash
docker logs -f orep-livekit
```

如果能获取 token 但媒体不通，优先检查云安全组和系统防火墙的 UDP `50100-50200`。

### 20.5 录制

测试：

- 创建会议。
- 进入会议。
- 开始录制。
- 停止录制。
- 后台/用户端能看到录像。
- MinIO 中出现录像对象。

日志：

```bash
docker logs -f orep-recording-bot
docker logs -f orep-backend
docker logs -f orep-minio
```

### 20.6 管理端

检查：

- 管理员登录。
- 用户管理。
- 会议管理。
- 评分记录。
- 资源/PPT/录像相关页面。

---

## 21. 更新发布流程

### 21.1 更新前备份

备份数据库：

```bash
cd /opt/orep/deploy
mkdir -p /opt/orep/backups
docker exec orep-mysql mysqldump -uroot -p"${MYSQL_ROOT_PASSWORD}" orep > /opt/orep/backups/orep-$(date +%F-%H%M).sql
```

备份配置：

```bash
tar czf /opt/orep/backups/orep-config-$(date +%F-%H%M).tar.gz \
  /opt/orep/.env.production \
  /opt/orep/deploy/docker-compose.prod.yml \
  /opt/orep/deploy/nginx.prod.conf \
  /opt/orep/deploy/livekit.prod.yaml \
  /opt/orep/certs
```

### 21.2 上传新版本

```bash
scp orep-release-新日期.tar.gz user@服务器IP:/opt/orep/
ssh user@服务器IP
cd /opt/orep
tar xzf orep-release-新日期.tar.gz
```

### 21.3 重建指定服务

只更新前端：

```bash
cd /opt/orep/deploy
docker compose --env-file ../.env.production -f docker-compose.prod.yml build frontend-user frontend-admin
docker compose --env-file ../.env.production -f docker-compose.prod.yml up -d frontend-user frontend-admin nginx
```

只更新后端：

```bash
docker compose --env-file ../.env.production -f docker-compose.prod.yml build backend
docker compose --env-file ../.env.production -f docker-compose.prod.yml up -d backend
```

只更新 AI 服务：

```bash
docker compose --env-file ../.env.production -f docker-compose.prod.yml build ai-scoring
docker compose --env-file ../.env.production -f docker-compose.prod.yml up -d ai-scoring
```

---

## 22. 日常运维命令

查看容器：

```bash
docker ps
docker compose --env-file ../.env.production -f docker-compose.prod.yml ps
```

查看日志：

```bash
docker logs -f --tail=200 orep-nginx
docker logs -f --tail=200 orep-backend
docker logs -f --tail=200 orep-ai-scoring
docker logs -f --tail=200 orep-livekit
docker logs -f --tail=200 orep-recording-bot
```

重启服务：

```bash
docker restart orep-backend
docker restart orep-ai-scoring
docker restart orep-livekit
```

查看资源占用：

```bash
docker stats
free -h
df -h
htop
```

清理无用镜像：

```bash
docker image prune -f
docker builder prune -f
```

不要随便执行：

```bash
docker volume prune
```

它可能删除数据库、MinIO 等数据卷。

---

## 23. 建议后续优化

4 核 16G 单机上线后，建议按下面顺序优化：

1. 把所有密钥从代码和 Compose 明文中移走，统一用 `.env.production`。
2. 给 MySQL、Redis、MinIO、后端、AI 服务增加健康检查。
3. 给 AI PPT 生成和录制任务做并发限制与队列。
4. 给数据库和 MinIO 做每日自动备份。
5. 使用云厂商对象存储替代本机 MinIO，减轻磁盘压力。
6. 如果会议并发上升，把 LiveKit 单独拆到更高带宽服务器。
7. 如果 AI 任务变多，把 AI 服务单独拆到 8 核 32G 或 GPU/高 CPU 实例。
8. 接入日志轮转和监控告警，例如 Docker log rotate、Prometheus、Grafana 或云监控。

---

## 24. 最小上线执行顺序

按这个顺序做，最稳：

1. 购买 Ubuntu Server 24.04 LTS，4 核 16G，100GB+ SSD。
2. 域名 A 记录解析到服务器公网 IP。
3. 上传证书到 `/opt/orep/certs/fullchain.pem` 和 `/opt/orep/certs/privkey.pem`。
4. 安装 Docker Engine 和 Docker Compose 插件。
5. 上传 OREP 代码包到 `/opt/orep`。
6. 创建 `.env.production`，填入生产密钥和域名。
7. 创建 `docker-compose.prod.yml`、`nginx.prod.conf`、`livekit.prod.yaml`。
8. 开放安全组：80、443、7881/tcp、50100-50200/udp。
9. 执行 `docker compose build`。
10. 执行 `docker compose up -d`。
11. 验证用户端、管理端、登录、会议、LiveKit、录制、AI 服务。
12. 压测或至少模拟 2 个会议房间、1 路录制、1 个 AI 任务。
13. 做数据库和配置备份。
14. 再对外通知上线。

---

## 25. 本次判断依据

本次判断基于当前 OREP 项目中的实际文件：

- `README.md`：技术栈包含 Spring Boot 3.x、Java 21、Vue 3、MySQL、Redis、WebSocket、Docker Compose、Nginx。
- `deploy/docker-compose.yml`：已有 MySQL、Redis、backend、signaling、frontend-admin、frontend-user、nginx、MinIO、recording-bot、ai-scoring。
- `deploy/nginx.conf`：已有 `/admin/`、`/api/`、`/api/ai/`、`/socket.io/`、`/room/`、`/ws-stomp` 代理，但缺少 HTTPS 和 `/livekit`。
- `backend/src/main/resources/application.yml`：包含数据库、Redis、邮件、JWT、LiveKit、MinIO、录制配置。
- `frontend/user/src/views/MeetingRoom.vue`：LiveKit 连接使用同源 `/livekit`。
- `ai-scoring/Dockerfile` 和 `ai-scoring/requirements.txt`：AI 服务依赖较重，需要单独预留内存。
- `recording-bot/Dockerfile`：录制 Bot 依赖 Chromium/Puppeteer，需要单独预留内存和 `/dev/shm`。
- `livekit.yaml`：当前为本地开发配置，上线必须替换公网和 Redis 配置。

外部资料：

- Ubuntu 官方 Release 信息：Ubuntu 26.04 LTS 已于 2026-04 发布，Ubuntu 24.04 LTS 仍在 LTS 支持周期内。
- Docker 官方 Ubuntu 安装文档：Docker Engine 支持 Ubuntu 26.04 LTS、24.04 LTS、22.04 LTS 等版本。

# OREP Ubuntu Server 24.04 LTS 生产部署说明

适用域名：`www.qvm-onestar.cn`

本目录是 OREP 的生产发布包目录。你可以把整个 `deploy/` 上传到云服务器 `/opt/orep/deploy`，然后按本文档在一台全新的 Ubuntu Server 24.04 LTS 服务器上完成部署。

## 1. 发布包目录说明

```text
deploy/
├── .env.production.example          # 生产环境变量模板，复制成 .env.production 后填写真实值
├── deploy.sh                        # 生产部署脚本：渲染 LiveKit 配置、构建镜像、启动服务
├── docker-compose.release.yml       # 生产发布 Compose，总入口文件
├── OREP_Ubuntu24.04_LTS_部署说明.md  # 本文档
├── backend/                         # Java 后端发布目录
│   ├── Dockerfile
│   └── orep-backend-1.0.0.jar
├── frontend/
│   ├── user/                        # 用户端前端发布目录
│   │   ├── Dockerfile
│   │   ├── nginx-default.conf
│   │   └── dist/
│   └── admin/                       # 管理端前端发布目录
│       ├── Dockerfile
│       ├── nginx-default.conf
│       └── dist/
├── ai-service/                      # AI 评分 / AI PPT 服务发布目录
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── app/
├── recording-bot/                   # LiveKit 录制 Bot 服务
├── signaling/                       # Socket.IO 信令服务
├── livekit/
│   ├── livekit.prod.yaml            # LiveKit 配置模板
│   └── render-livekit-config.sh     # 根据 .env.production 生成 livekit.rendered.yaml
├── nginx/
│   └── nginx.conf                   # HTTPS、前后端、AI、LiveKit、WebSocket 统一反向代理
├── certs/
│   └── README.md                    # 证书放置说明
└── sql/                             # MySQL 初始化脚本
```

## 2. 服务器最低配置建议

当前 OREP 服务包括：用户端、管理端、Java 后端、AI 服务、LiveKit、录制 Bot、信令服务、MySQL、Redis、MinIO、Nginx。

`4 核 CPU / 16G 内存` 可以作为第一阶段单机上线配置，适合小规模试运行、内测、演示和低并发正式使用。需要注意：

- AI 评分、AI PPT、录制 Bot、LiveKit 同时工作时会明显吃 CPU 和内存。
- 同时开多个会议并录制时，4 核会比较紧。
- 建议先用 4 核 16G 上线，后续根据会议并发和 AI 任务数量升级到 8 核 32G 或拆分 AI / LiveKit。
- 系统盘建议不低于 100G；如果录制文件多，建议挂载独立数据盘。

## 3. Ubuntu Server 24.04 LTS 空系统准备

官方下载地址：

- Ubuntu Server 下载页：https://ubuntu.com/download/server
- Ubuntu 24.04 发布镜像页：https://releases.ubuntu.com/24.04/
- Docker Ubuntu 安装文档：https://docs.docker.com/engine/install/ubuntu/
- Docker Compose 插件文档：https://docs.docker.com/compose/install/linux/
- Node.js 下载页：https://nodejs.org/en/download/package-manager
- OpenJDK 安装说明：https://openjdk.org/install/
- LiveKit 自托管说明：https://docs.livekit.io/home/self-hosting/deployment/

生产服务器只部署本 `deploy/` 发布包时，核心依赖是 Docker、Docker Compose 插件、curl、gettext-base。Node.js、JDK、Maven 只在服务器上重新打包源码时才需要；本发布包已经包含前端 dist 和后端 jar，服务器一般不需要安装 Node.js/JDK/Maven。

### 3.1 更新系统

```bash
sudo apt update
sudo apt -y upgrade
sudo apt -y install ca-certificates curl gnupg lsb-release unzip tar vim ufw gettext-base
```

### 3.2 安装 Docker Engine 和 Compose 插件

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

验证：

```bash
docker --version
docker compose version
sudo docker run --rm hello-world
```

如果你希望当前用户不用每次加 `sudo`：

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 4. 域名、DNS 和服务器端口

### 4.1 DNS 解析

在域名控制台添加：

```text
主机记录：www
记录类型：A
记录值：你的服务器公网 IP
```

等待解析生效后验证：

```bash
dig www.qvm-onestar.cn +short
```

返回结果应为你的服务器公网 IP。

### 4.2 云服务器安全组

至少放行：

```text
TCP 22      SSH
TCP 80      HTTP，自动跳转 HTTPS
TCP 443     HTTPS，网站、API、WebSocket、LiveKit WSS
TCP 7881    LiveKit TCP fallback
UDP 50100-50200 LiveKit WebRTC UDP 媒体端口
```

如果云厂商安全组没放行 UDP `50100-50200`，会议语音视频可能连接失败或质量很差。

### 4.3 Ubuntu 防火墙

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 7881/tcp
sudo ufw allow 50100:50200/udp
sudo ufw enable
sudo ufw status
```

## 5. 上传 deploy 发布包

在本地把项目里的 `deploy/` 上传到服务器：

```bash
ssh root@你的服务器公网IP "mkdir -p /opt/orep"
scp -r deploy root@你的服务器公网IP:/opt/orep/
```

服务器上确认：

```bash
cd /opt/orep/deploy
ls
```

## 6. 配置 HTTPS 证书

把 `www.qvm-onestar.cn` 的证书放到：

```text
/opt/orep/deploy/certs/fullchain.pem
/opt/orep/deploy/certs/privkey.pem
```

要求：

- `fullchain.pem` 必须包含站点证书和中间证书链。
- `privkey.pem` 必须是申请证书时生成的私钥。
- 证书的 SAN / 绑定域名必须包含 `www.qvm-onestar.cn`。
- 浏览器必须信任证书链，否则 HTTPS 和 LiveKit 的 `wss://www.qvm-onestar.cn/livekit` 都会有风险。

如果证书厂商给的是多个文件，常见合并方式：

```bash
cat www.qvm-onestar.cn.crt intermediate.crt > /opt/orep/deploy/certs/fullchain.pem
cp www.qvm-onestar.cn.key /opt/orep/deploy/certs/privkey.pem
chmod 600 /opt/orep/deploy/certs/privkey.pem
```

证书文件名必须和 Nginx 配置一致：

```nginx
ssl_certificate     /etc/nginx/certs/fullchain.pem;
ssl_certificate_key /etc/nginx/certs/privkey.pem;
```

## 7. 配置生产环境变量

复制模板：

```bash
cd /opt/orep/deploy
cp .env.production.example .env.production
chmod 600 .env.production
vim .env.production
```

必须修改的关键项：

```bash
DOMAIN=www.qvm-onestar.cn
PUBLIC_IP=你的服务器公网IP

MYSQL_ROOT_PASSWORD=请改成强密码
REDIS_PASSWORD=请改成强密码
JWT_SECRET=请改成至少64位随机字符串

LIVEKIT_API_KEY=orep-prod-key
LIVEKIT_API_SECRET=请改成至少32位随机字符串
LIVEKIT_WS_URL=wss://www.qvm-onestar.cn/livekit

MINIO_ROOT_USER=orepminio
MINIO_ROOT_PASSWORD=请改成强密码

SPRING_MAIL_USERNAME=你的邮箱
SPRING_MAIL_PASSWORD=你的邮箱授权码
OREP_EMAIL_FROM=你的邮箱

DASHSCOPE_API_KEY=你的阿里云百炼DashScope Key
DEEPSEEK_API_KEY=你的DeepSeek Key
MINIMAX_API_KEY=你的MiniMax Key
PPT_TEXT_API_KEY=你的PPT文本模型Key
PPT_HTML_API_KEY=你的PPT HTML模型Key
PPT_VISION_API_KEY=你的PPT视觉模型Key
```

生成随机密钥可以用：

```bash
openssl rand -base64 48
```

邮箱如果使用 QQ 邮箱，`SPRING_MAIL_PASSWORD` 填邮箱授权码，不是邮箱登录密码。

## 8. 启动 OREP

执行：

```bash
cd /opt/orep/deploy
./deploy.sh
```

脚本会做这些事：

1. 检查 Docker / Docker Compose。
2. 检查 `.env.production`。
3. 检查证书文件。
4. 根据 `.env.production` 渲染 `livekit/livekit.rendered.yaml`。
5. 校验 Compose 配置。
6. 构建所有服务镜像。
7. 启动 OREP 全部服务。

手动命令等价于：

```bash
cd /opt/orep/deploy
./livekit/render-livekit-config.sh ./.env.production ./livekit/livekit.prod.yaml ./livekit/livekit.rendered.yaml
docker compose --env-file .env.production -f docker-compose.release.yml config
docker compose --env-file .env.production -f docker-compose.release.yml build --parallel
docker compose --env-file .env.production -f docker-compose.release.yml up -d
```

## 9. 访问地址

```text
用户端：https://www.qvm-onestar.cn/
管理端：https://www.qvm-onestar.cn/admin/
后端健康检查：https://www.qvm-onestar.cn/api/auth/check
LiveKit WSS：wss://www.qvm-onestar.cn/livekit
```

## 10. 验证命令

查看容器状态：

```bash
cd /opt/orep/deploy
docker compose --env-file .env.production -f docker-compose.release.yml ps
```

查看日志：

```bash
docker compose --env-file .env.production -f docker-compose.release.yml logs -f nginx
docker compose --env-file .env.production -f docker-compose.release.yml logs -f backend
docker compose --env-file .env.production -f docker-compose.release.yml logs -f ai-scoring
docker compose --env-file .env.production -f docker-compose.release.yml logs -f livekit
```

接口验证：

```bash
curl -k https://www.qvm-onestar.cn/api/auth/check
```

Nginx 配置验证：

```bash
docker exec orep-nginx nginx -t
```

LiveKit 配置确认：

```bash
sed -n '1,120p' /opt/orep/deploy/livekit/livekit.rendered.yaml
```

## 11. 本地重新打包方法

如果以后你改了代码，需要重新生成 `deploy/` 发布内容，可以在本地项目根目录执行。

### 11.1 用户端前端

```bash
cd frontend/user
npm ci
npm run build
cd ../..
rsync -a --delete frontend/user/dist/ deploy/frontend/user/dist/
```

### 11.2 管理端前端

```bash
cd frontend/admin
npm ci
npm run build
cd ../..
rsync -a --delete frontend/admin/dist/ deploy/frontend/admin/dist/
```

### 11.3 Java 后端

本地需要 JDK 21 和 Maven。

```bash
cd backend
JAVA_HOME=$(/usr/libexec/java_home -v 21) mvn -DskipTests -Dmaven.compiler.useIncrementalCompilation=false clean package
cd ..
cp backend/target/orep-backend-1.0.0.jar deploy/backend/orep-backend-1.0.0.jar
```

Linux 本地构建时，如果已经安装 `openjdk-21-jdk`：

```bash
cd backend
mvn -DskipTests -Dmaven.compiler.useIncrementalCompilation=false clean package
```

### 11.4 AI 服务

AI 服务是 Python/FastAPI 服务，发布包保留运行入口、`app/` 代码和 `requirements.txt`，由服务器 Docker 构建镜像：

```bash
rm -rf deploy/ai-service
mkdir -p deploy/ai-service
rsync -a ai-scoring/app deploy/ai-service/ \
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='.DS_Store' \
  --exclude='uploads/' --exclude='app/uploads/' \
  --exclude='app/services/ppt/agent/workspaces/' \
  --exclude='app/services/ppt/agent/.runtime/'
cp ai-scoring/main.py ai-scoring/requirements.txt ai-scoring/Dockerfile deploy/ai-service/
```

### 11.5 录制 Bot 和信令服务

```bash
rsync -a --delete recording-bot/ deploy/recording-bot/ \
  --exclude='node_modules/' --exclude='recordings/' --exclude='logs/' \
  --exclude='*.log' --exclude='.env' --exclude='.env.*' --exclude='.DS_Store'

rsync -a --delete signaling/ deploy/signaling/ \
  --exclude='node_modules/' --exclude='logs/' --exclude='*.log' \
  --exclude='.env' --exclude='.env.*' --exclude='certs/' --exclude='.DS_Store'
```

### 11.6 SQL 和 LiveKit

```bash
rsync -a --delete sql/ deploy/sql/
cp deploy/livekit.prod.yaml deploy/livekit/livekit.prod.yaml
cp deploy/render-livekit-config.sh deploy/livekit/render-livekit-config.sh
chmod +x deploy/livekit/render-livekit-config.sh
```

## 12. 更新上线

上传新的 `deploy/` 后，在服务器执行：

```bash
cd /opt/orep/deploy
./deploy.sh
```

只重启应用层，不动数据库数据卷：

```bash
docker compose --env-file .env.production -f docker-compose.release.yml up -d --build backend ai-scoring frontend-user frontend-admin nginx
```

重启 LiveKit 会议链路：

```bash
./livekit/render-livekit-config.sh ./.env.production ./livekit/livekit.prod.yaml ./livekit/livekit.rendered.yaml
docker compose --env-file .env.production -f docker-compose.release.yml up -d --build livekit recording-bot nginx
```

## 13. 停止和备份

停止全部服务：

```bash
docker compose --env-file .env.production -f docker-compose.release.yml down
```

注意：上面的命令不会删除 Docker volume。不要随便执行 `down -v`，否则 MySQL、Redis、MinIO 数据卷会被删除。

备份 MySQL：

```bash
mkdir -p /opt/orep/backups
docker exec orep-mysql mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" orep > /opt/orep/backups/orep_$(date +%F_%H%M%S).sql
```

备份 Docker volumes 建议使用云服务器快照或专门备份工具。

## 14. 常见问题

### 14.1 浏览器提示证书危险

检查：

- 证书是否覆盖 `www.qvm-onestar.cn`。
- `fullchain.pem` 是否包含完整中间证书链。
- 证书是否过期。
- 证书品牌是否仍被主流浏览器信任。

如果 HTTPS 不被浏览器信任，LiveKit 的 `wss://www.qvm-onestar.cn/livekit` 也可能失败。

### 14.2 页面能打开，但会议进不去

检查：

```bash
docker compose --env-file .env.production -f docker-compose.release.yml logs -f livekit nginx
```

重点确认：

- 云安全组是否放行 UDP `50100-50200`。
- `.env.production` 里的 `LIVEKIT_WS_URL` 是否为 `wss://www.qvm-onestar.cn/livekit`。
- `livekit/livekit.rendered.yaml` 里的 key 是否和后端环境变量一致。
- 服务器是否有公网 IP，或云厂商 NAT 是否影响 LiveKit 外部 IP 探测。

### 14.3 邮件验证码发不出去

检查：

```bash
docker compose --env-file .env.production -f docker-compose.release.yml logs -f backend
```

重点确认：

- `SPRING_MAIL_USERNAME` 是否为邮箱。
- `SPRING_MAIL_PASSWORD` 是否为邮箱授权码。
- `OREP_EMAIL_FROM` 是否和发件邮箱一致。
- 云服务器是否允许访问 SMTP 端口 `465`。

如果 JavaMail 在某些网络环境下和 SMTP 服务握手异常，可以临时把：

```bash
OREP_EMAIL_PYTHON_FALLBACK_ENABLED=true
```

然后重启后端：

```bash
docker compose --env-file .env.production -f docker-compose.release.yml up -d --build backend
```

### 14.4 AI 服务启动慢或构建慢

AI 服务依赖较多，首次构建会下载 Python 包、音频处理库和渲染依赖，时间较长是正常的。建议服务器能稳定访问 PyPI，或提前配置国内 PyPI 镜像。

### 14.5 MySQL 初始化脚本没有执行

MySQL 官方镜像只会在第一次创建空数据目录时执行 `/docker-entrypoint-initdb.d`。如果 volume 已经存在，后续修改 SQL 文件不会自动重新执行。

查看 volume：

```bash
docker volume ls | grep mysql
```

生产环境不要为了重新初始化随便删除 volume。需要变更表结构时，应写迁移 SQL 并手动执行。

## 15. 当前代码里域名相关的地方

本发布包已经按 `www.qvm-onestar.cn` 配好生产入口：

- `deploy/nginx/nginx.conf`：`server_name www.qvm-onestar.cn`，证书读取 `/etc/nginx/certs/fullchain.pem` 和 `/etc/nginx/certs/privkey.pem`。
- `deploy/.env.production.example`：`DOMAIN=www.qvm-onestar.cn`，`LIVEKIT_WS_URL=wss://www.qvm-onestar.cn/livekit`。
- `deploy/livekit/livekit.prod.yaml`：通过 `render-livekit-config.sh` 写入 LiveKit key、secret、Redis 密码等。
- 前端生产包使用同源接口路径，例如 `/api`、`/socket.io`、`/livekit`，不需要在前端代码里硬编码域名。

真正上线前，你只需要确认 `.env.production`、证书文件和 DNS 解析正确。

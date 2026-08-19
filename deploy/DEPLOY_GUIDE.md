# OREP 部署入口

当前 `deploy/` 已整理为可上传服务器的生产发布包目录，推荐阅读：

- `README.md`
- `OREP_Ubuntu24.04_LTS_部署说明.md`

生产部署使用：

- `docker-compose.release.yml`
- `.env.production.example`
- `deploy.sh`
- `nginx/nginx.conf`
- `livekit/livekit.prod.yaml`

首次部署简版命令：

```bash
cd /opt/orep/deploy
cp .env.production.example .env.production
vim .env.production
# 放置 certs/fullchain.pem 和 certs/privkey.pem
./deploy.sh
```

旧的 `docker-compose.yml`、`docker-compose.prod.yml`、`nginx.conf`、`nginx.prod.conf` 保留为历史配置参考；新的可交付发布包请以 `docker-compose.release.yml` 和本文档为准。

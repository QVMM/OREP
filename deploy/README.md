# OREP 生产发布包

域名：`www.jingsaidanao.com`

请先阅读：

- `OREP_Ubuntu24.04_LTS_部署说明.md`

服务器上推荐路径：

```bash
/opt/orep/deploy
```

首次部署：

```bash
cd /opt/orep/deploy
cp .env.production.example .env.production
vim .env.production
# 把证书放到 certs/fullchain.pem 和 certs/privkey.pem
./deploy.sh
```

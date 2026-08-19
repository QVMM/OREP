# 启发 Office — Collabora Online（WOPI）集成说明

**状态：** 开发中（替代已弃用的 ONLYOFFICE Community）  
**引擎：** Collabora Online Development Edition（MPL-2.0，可定制品牌）  
**协议：** WOPI Host 在 OREP Java 后端

## 架构

```text
浏览器 → 竞赛大脑前端（列表/权限/品牌壳）
       → iframe → Collabora cool.html
                    ↓ WOPI
                 OREP /api/wopi/files/{id}
                    ↓
                 本地文件 office/ + inspire_office_document
```

## 本地开发

```bash
# 1. 启动 Collabora（挂载 deploy/collabora/coolwsd.xml，含 style-src unsafe-inline）
docker rm -f orep-collabora 2>/dev/null
docker run -d --name orep-collabora -p 9980:9980 \
  -e username=admin -e password=S3cRet \
  -e aliasgroup1=http://host.docker.internal:8080 \
  -e DONT_GEN_SSL_CERT=true \
  -e 'extra_params=--o:ssl.enable=false --o:ssl.termination=false' \
  -v "$PWD/deploy/collabora/coolwsd.xml:/etc/coolwsd/coolwsd.xml:ro" \
  --cap-add MKNOD \
  --add-host=host.docker.internal:host-gateway \
  collabora/code:latest

# 2. 后端环境变量（全局配置，云端同样用 env，不要改代码里的默认值）
#    本地默认已写在 application.yml，一般只需保证 Collabora 容器在跑。
export OREP_COLLABORA_URL=http://127.0.0.1:9980/collabora          # 后端 discovery（须含 service_root）
export OREP_COLLABORA_PUBLIC_URL=http://127.0.0.1:5174              # 浏览器 iframe 基址（Vite 同源）
export OREP_WOPI_PUBLIC_BASE_URL=http://host.docker.internal:8080   # 容器回调 WOPI
# 可选：Vite 代理上游
export OREP_COLLABORA_PROXY_TARGET=http://127.0.0.1:9980

# 云端示例（docker-compose / .env.production）：
# OREP_COLLABORA_URL=http://collabora:9980/collabora
# OREP_COLLABORA_PUBLIC_URL=https://www.jingsaidanao.com/collabora
# OREP_WOPI_PUBLIC_BASE_URL=https://www.jingsaidanao.com

# 3. 重启前端 Vite（代理配置变更后必须重启）
# 4. 用户端：无痕窗口打开文档
open http://localhost:5174/inspire-office
```

**空白页**：多为 iframe 请求 `/browser/...` 被剥掉了 `/collabora` 前缀。Vite 代理必须 **保留** `/collabora` 前缀转发到 9980。

**去品牌失效时**：多半是浏览器仍缓存旧 `branding.js`。硬刷新或清空站点数据。

`deploy/collabora/coolwsd.xml` 要点：

- CSP 含 `style-src 'self' 'unsafe-inline'`
- **`home_mode.enable=true`**：关闭欢迎页与「请向我们提供您的反馈意见」类弹窗（连接/文档数上限 20/10，试点足够）
- **`allow_update_popup=false`**：关闭更新提示

`deploy/collabora/branding.css` 挂载覆盖官方 branding，**隐藏左上角 Collabora logo**、关于页 logo、加载 spinner 品牌图。

## 控制台日志说明

| 日志 | 是否阻塞编辑 | 说明 |
|------|--------------|------|
| CSP `style-src` 拦截 inline style | **会**（样式异常） | 已用 coolwsd.xml 修复；硬刷新后应消失 |
| `lc_*.svg` 404 | 否 | CODE 部分侧栏图标路径/主题缺失，核心编辑一般仍可用 |
| MetaMask / inpage.js | 否 | 浏览器钱包扩展，与产品无关 |
| Blocked autofocusing cross-origin | 否 | 父页与 Collabora 跨域 iframe 的浏览器策略 |
| Not a CODA app / TaskWorker | 否 | Collabora 正常日志 |

## 产品能力

| 项 | 说明 |
|----|------|
| 归属 | 个人 / 项目 / 团队（`project_team`） |
| 格式 | docx / xlsx / pptx（及常见 Office） |
| **上传弹窗** | 选择文件 + 归属（个人/项目/团队）；项目/团队须选团队 |
| **资源中心同步** | 项目/团队文档创建或上传时，复制一份到资源中心（演示→`content`，其它→`team`）；个人不同步；`resource_id` 回写 |
| **文档管理** | 打开 / 下载 / 重命名 / **迁移归属** / 同步资源中心 / 复制 / 删除（所有者） |

### 文档管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/api/inspire-office/documents/{id}` | 重命名 |
| PATCH | `/api/inspire-office/documents/{id}/location` | 迁移归属 `scope`+`teamId`，可选 `syncResource` |
| POST | `/api/inspire-office/documents/{id}/sync-resource` | 把当前内容再同步到资源中心 |
| POST | `/api/inspire-office/documents/{id}/duplicate` | 复制文档（默认可到个人） |
| GET | `/api/inspire-office/documents/{id}/download` | 下载当前文件 |
| DELETE | `/api/inspire-office/documents/{id}` | 软删除 |
| 协同 | Collabora 原生多人编辑（3–6 人试点）；**同文档多人打开**即协同 |
| **版本存档** | 每次协同保存自动快照；支持**手动存档**；可**恢复**（生成新版本） |
| **修订痕迹（文件内）** | Word：**Track Changes**。新建 docx 默认 `trackRevisions`。显示开关：同源 `sendUnoCommand` / `viewchanges-hidden|inline`，否则 `postMessage Send_UNO_Command` + `.uno:ShowTrackedChanges`（勿用 Action_Dispatch）。仅视图。作者名 = WOPI `UserFriendlyName` |
| **协同头像** | WOPI `UserExtraInfo.avatar` → `GET /api/wopi/avatars/{userId}`（与侧栏一致的橙底首字 SVG；URL 源取 `OREP_COLLABORA_PUBLIC_URL` 的 origin） |
| **分享链接** | 点分享图标弹出气泡预览邀请文案 →「确认复制」；`访问地址：` 后换行、URL 独占一行。域名取实时 origin。未登录带 `redirect`。对方需有权限 |
| **演示协同（pptx）** | Impress **无** Word 式修订。能力：多人同屏编辑、版本存档/恢复。新建 pptx 为 **16:9** 标题页+正文版式 |
| 业务侧操作审计 | **已不做**（改为文件内修订标记） |
| 品牌 | 产品壳为「启发 Office」 |

### 版本 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/inspire-office/documents/{id}/versions` | 版本列表 |
| POST | `/api/inspire-office/documents/{id}/versions` | 手动存档 |
| POST | `/api/inspire-office/documents/{id}/versions/{n}/restore` | 恢复 |

**边界：** 修订痕迹依赖 Writer 修订模型；Excel/PPT **无**等价 Track Changes，请用评论 + 版本存档。作者名取决于当前会话用户显示名。

## 与 ONLYOFFICE 差异

- 不依赖付费白标改 loader  
- 集成协议为 **WOPI**，非 OnlyOffice JWT editor-config  
- 开源许可证以 Collabora **MPL** 为准（改过的文件需按 MPL 合规）

# AI评分上传统一为5GB

## 背景

AI评分上传当前存在多层限制不一致：

- 前端把5GB作为普通上传与预处理的分界，而不是用户上限。
- 后端普通视频限制5GB，预处理源视频允许20GB。
- Spring multipart默认允许20GB。
- 线上Nginx只允许500MB，导致正式环境在到达后端前返回413。

本次将本地、后端和有效线上部署链路统一为同一套产品规则。

## 产品规则

- 路演视频最大5GB，支持MP4、WebM、MOV。
- 单个佐证材料最大200MB。
- 佐证材料合计最大1GB。
- 单次multipart请求包络最大7GB，用于容纳5GB视频、1GB材料及协议开销和安全余量。
- 上传最长允许2小时。

所有容量均使用1024进制计算：1GB = 1024 × 1024 × 1024字节。

## 前端

`VideoScoreUploadForm.vue` 在文件选择阶段执行校验：

1. 视频超过5GB时清空选择并提示“路演视频最大5GB，请压缩后上传”。
2. 单个材料超过200MB时拒绝本次材料选择并指出文件名。
3. 材料合计超过1GB时拒绝本次材料选择。
4. 上传区域在选择前明确展示视频与材料上限。
5. 不再把超过5GB的视频派发到预处理接口。
6. 413响应转换为明确的容量超限提示。

前端上传请求和Vite开发代理超时统一为2小时。

## 后端

- `AiScoreMediaAssetService`继续以5GB作为视频硬上限、200MB作为单个材料上限。
- `AiScoreMediaAssetService`在创建评分会话前校验材料合计不超过1GB。
- `AiScoreMediaPreprocessService`的源视频上限从20GB改为5GB，避免绕过统一规则。
- Spring `max-file-size`设置为5GB。
- Spring `max-request-size`和Tomcat表单请求上限设置为7GB。

预处理接口保留兼容性，但不再允许大于5GB的源视频。

## 线上代理

全局请求限制继续保持500MB，仅为`/api/ai-score/`增加更具体的代理规则：

- `client_max_body_size 7G`
- `proxy_request_buffering off`
- `proxy_http_version 1.1`
- `proxy_read_timeout 7200s`
- `proxy_send_timeout 7200s`
- `client_body_timeout 7200s`

需要同步的有效配置：

- `deploy/nginx/nginx.conf`：当前正式发布权威配置。
- `deploy/nginx.conf`、`deploy/nginx.prod.conf`：仍可被旧部署入口引用。
- `cloudrun/config/nginx.conf.template`
- `cloudrun/release/orep-cloudrun/config/nginx.conf.template`
- `dockerrun/config/nginx.conf.template`
- `windowsrun/config/nginx-orep.conf.template`
- `frontend/user/nginx-default.conf`：用户端容器直接代理API时的兜底配置。

不修改带日期的构建产物、`dist`目录或历史运行时配置归档。

## 错误处理

- 前端选择阶段的超限错误不发起网络请求。
- Nginx或Spring返回413时，页面提示“上传内容超过限制：视频最大5GB，单个材料最大200MB”。
- 后端业务校验仍返回具体文件限制信息。
- 上传失败后保留已选择的合法文件，方便用户压缩或调整材料后重试。

## 验证

- 前端契约测试覆盖5GB视频、200MB单材料、1GB材料总量、2小时超时和不再派发超5GB预处理。
- 后端测试覆盖预处理源视频5GB上限。
- 配置契约测试覆盖Spring 5GB/7GB和全部有效Nginx配置的专用AI评分上传规则。
- 运行用户端测试与生产构建。
- 运行后端相关测试。
- 使用`nginx -t`验证可用的Nginx配置；环境缺少Nginx时使用静态配置契约测试兜底。

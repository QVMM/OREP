# OREP Coding Task - 在线路演评审平台

## 构建完整项目，目录: /Users/liuyixing/项目/OREP

### 本地环境
- Java 21: /Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
- Maven 3.9.9: 下载安装 `brew install maven` 或用 wrapper
- MySQL 8.0: root/12345678, port 3306
- Redis: localhost:6379
- Node.js 22

### 第一步：后端 Spring Boot 项目

在 `backend/` 目录创建完整的 Spring Boot 3 项目：

**pom.xml 依赖：**
- spring-boot-starter-web
- spring-boot-starter-websocket
- mybatis-spring-boot-starter 3.x + mybatis-plus-boot-starter
- mysql-connector-java
- spring-boot-starter-data-redis
- spring-boot-starter-mail (发验证码)
- jjwt (JWT 认证: io.jsonwebtoken:jjwt-api/impl/jackson)
- lombok
- hutool-all (工具库)
- itextpdf / openpdf (PDF 生成)
- knife4j-openapi3 (API 文档, 可选)

**数据库 SQL (`sql/init.sql`)：**
根据 README.md 中的评分标准，建表包含：
1. tenant (租户/学校)
2. user (用户，带 tenant_id, role 字段)
3. meeting (会议，带 jitsi_room_id, meeting_code, meeting_password, status)
4. score_template (评分模板)
5. score_item (评分项，含 max_score)
6. score_record (评分记录，meeting_id + user_id 唯一)
7. score_detail (评分详情，每项分数+评论)
8. issue (问题跟踪)
9. email_verification (邮箱验证码)

**预置评分模板数据：**
按2025大赛评分标准INSERT score_template + score_item。

**实体类 (entity/)：**
所有表对应实体，使用 MyBatis-Plus 注解。

**Mapper (mapper/)：**
MyBatis-Plus 的 BaseMapper + 自定义 XML。

**Service 层：**
- AuthService: 登录/注册/验证码
- MeetingService: CRUD会议，生成meeting_code，管理状态
- ScoreService: 提交评分、计算总分、防重复
- IssueService: 问题自动生成、状态跟踪
- StatisticsService: 数据统计
- PdfService: 生成PDF报告

**Controller 层：**
所有 REST API 接口，JWT 认证拦截。

**Security:**
- JWT filter
- 多租户拦截器 (每个请求校验 tenant_id)
- 角色权限注解 @RequiresRole

**WebSocket:**
- 会议内实时消息
- 评分结果实时推送

**application.yml：**
- MySQL datasource
- Redis
- JWT secret
- Mail config (QQ邮箱 SMTP)
- 服务端口 8080

### 第二步：前端 Vue3 项目

**frontend/admin/ - 管理后台：**
- Vue 3 + Vite + Element Plus + Pinia + Vue Router + Axios
- 登录页
- Dashboard (统计概览)
- 用户管理 (CRUD, 角色分配)
- 会议管理 (创建/列表/详情)
- 评分模板管理
- 评分结果查看 + PDF导出
- 问题跟踪管理
- 数据分析图表 (ECharts)

**frontend/user/ - 用户端：**
- Vue 3 + Vite + Element Plus
- 登录/注册页 (邮箱验证码)
- 会议列表 (进入会议)
- 会议内页面:
  - WebRTC视频区域 (iframe嵌入或组件)
  - 倒计时 (60分钟)
  - 评分表单 (各项评分输入框 + 评论)
  - 评分结果展示
  - 聊天区域
  - 问题列表
- 个人中心
- 数据分析页面 (折线图: 分数趋势)

### 第三步：WebRTC 信令服务器

**signaling/ 目录：**
- Node.js + Express + Socket.IO
- 房间管理 (create/join/leave)
- WebRTC 信令 (offer/answer/ice-candidate)
- 屏幕共享支持
- 聊天消息转发
- 录制控制信令
- 端口 3000

### 第四步：Docker 部署

**deploy/docker-compose.yml：**
```yaml
services:
  mysql: mysql:8.0 (512MB)
  redis: redis:7-alpine (128MB)
  backend: Spring Boot (512MB)
  frontend-admin: nginx (64MB)
  frontend-user: nginx (64MB)
  signaling: Node.js (256MB)
  nginx: 反向代理 (64MB)
```

总计约 1.5GB，适合 2C4G 服务器。

**deploy/ 目录包含：**
- docker-compose.yml
- Dockerfile (backend)
- Dockerfile (frontend-admin)
- Dockerfile (frontend-user)
- Dockerfile (signaling)
- nginx.conf (统一入口，反代所有服务)
- deploy.sh (一键部署脚本)

### 重要约束
1. 所有代码必须能编译运行
2. 数据库密码用 root/12345678
3. 前端API地址用 /api 代理到后端
4. 信令服务用 /ws 代理
5. 代码注释用中文
6. 前端用 Composition API + `<script setup>`
7. 后端统一返回格式: { code: 200, message: "success", data: {} }

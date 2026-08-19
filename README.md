# OREP - 在线路演评审平台

## 项目概述
多租户（学校级）评审闭环平台，支持路演 → 评分 → 问题 → 改进 → 再路演。

## 技术栈
- **后端**: Spring Boot 3.x + Java 21 + MyBatis-Plus + JWT
- **前端**: Vue 3 + Vite + Element Plus + Pinia
- **数据库**: MySQL 8.0
- **缓存**: Redis
- **实时通信**: WebSocket + Socket.IO
- **视频会议**: 自研轻量 WebRTC（P2P + 信令服务器）
- **文件存储**: 本地存储（可扩展 MinIO）
- **部署**: Docker Compose + Nginx

## 项目结构
```
OREP/
├── backend/              # Spring Boot 后端
│   ├── src/main/java/com/orep/
│   │   ├── controller/   # REST API
│   │   ├── service/      # 业务逻辑
│   │   ├── mapper/       # MyBatis Mapper
│   │   ├── entity/       # 实体类
│   │   ├── dto/          # 数据传输对象
│   │   ├── config/       # 配置类
│   │   ├── security/     # JWT + 安全
│   │   ├── websocket/    # WebSocket 处理
│   │   └── util/         # 工具类
│   └── src/main/resources/
│       ├── mapper/       # XML Mapper
│       └── application.yml
├── frontend/
│   ├── admin/            # 管理后台前端
│   └── user/             # 用户前端
├── signaling/            # WebRTC 信令服务器 (Node.js + Socket.IO)
├── deploy/               # 部署配置
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── Dockerfile.*
└── sql/                  # 数据库脚本
```

## 评分标准（2025 世界职业院校技能大赛）

### 一、技能水平 (60分)
1. 操作规范性 (10分)
2. 技能熟练度 (15分)
3. 任务难易度 (15分)
4. 技术先进性 (15分)
5. 现场讲解效果 (5分)

### 二、职业素养 (10分)
1. 职业道德与行为规范 (4分)
2. 工匠精神 (3分)
3. 安全意识 (3分)

### 三、应用价值 (10分)
1. 实用性 (4分)
2. 经济性 (3分)
3. 可持续性 (3分)

### 四、团队合作 (10分)
1. 团队精神 (5分)
2. 沟通协作 (5分)

### 五、创新创意 (10分)
1. 创新意识 (4分)
2. 创新成效 (6分)

## 角色
- admin: 平台管理员
- school_admin: 学校管理员
- teacher: 教师（创建会议、评分）
- student: 学生（参与路演）
- reviewer: 评审员（评分）
- expert: 专家（指导+评分）

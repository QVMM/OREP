const express = require('express');
const http = require('http');
const https = require('https');
const fs = require('fs');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// 尝试加载 HTTPS 证书
const certDir = path.resolve(__dirname, '../certs');
let server;
if (fs.existsSync(path.join(certDir, 'cert.pem')) && fs.existsSync(path.join(certDir, 'key.pem'))) {
    const sslOptions = {
        cert: fs.readFileSync(path.join(certDir, 'cert.pem')),
        key: fs.readFileSync(path.join(certDir, 'key.pem'))
    };
    server = https.createServer(sslOptions, app);
    console.log('使用 HTTPS 模式');
} else {
    server = http.createServer(app);
    console.log('使用 HTTP 模式（未找到证书）');
}
const io = new Server(server, {
    cors: {
        origin: '*',
        methods: ['GET', 'POST']
    },
    maxHttpBufferSize: 10e6 // 10MB for file uploads
});

// 房间管理
const rooms = new Map();

io.on('connection', (socket) => {
    console.log(`[连接] ${socket.id}`);

    // 加入房间
    socket.on('join-room', (data) => {
        const { roomId, userId, username } = data;

        if (!rooms.has(roomId)) {
            rooms.set(roomId, new Map());
        }
        const room = rooms.get(roomId);
        room.set(socket.id, { userId, username, socketId: socket.id });

        socket.join(roomId);
        socket.roomId = roomId;
        socket.userId = userId;
        socket.username = username;

        console.log(`[加入房间] ${username} -> ${roomId}，当前人数: ${room.size}`);

        // 通知房间内其他人
        socket.to(roomId).emit('user-joined', {
            socketId: socket.id,
            userId,
            username
        });

        // 发送当前房间用户列表
        const users = Array.from(room.values()).filter(u => u.socketId !== socket.id);
        socket.emit('room-users', users);
    });

    // WebRTC信令：offer
    socket.on('offer', (data) => {
        const { to, offer } = data;
        io.to(to).emit('offer', {
            from: socket.id,
            offer,
            username: socket.username
        });
    });

    // WebRTC信令：answer
    socket.on('answer', (data) => {
        const { to, answer } = data;
        io.to(to).emit('answer', {
            from: socket.id,
            answer
        });
    });

    // WebRTC信令：ICE candidate
    socket.on('ice-candidate', (data) => {
        const { to, candidate } = data;
        io.to(to).emit('ice-candidate', {
            from: socket.id,
            candidate
        });
    });

    // 聊天消息
    socket.on('chat-message', (data) => {
        const { roomId, message, type } = data;
        io.to(roomId).emit('chat-message', {
            userId: socket.userId,
            username: socket.username,
            message,
            type: type || 'text',
            timestamp: new Date().toISOString()
        });
    });

    // 文件/图片发送
    socket.on('file-message', (data) => {
        const { roomId, fileName, fileData, fileType } = data;
        io.to(roomId).emit('file-message', {
            userId: socket.userId,
            username: socket.username,
            fileName,
            fileData,
            fileType,
            timestamp: new Date().toISOString()
        });
    });

    // 屏幕共享
    socket.on('screen-share-started', (data) => {
        const { roomId } = data;
        socket.to(roomId).emit('screen-share-started', {
            socketId: socket.id,
            username: socket.username
        });
    });

    socket.on('screen-share-stopped', (data) => {
        const { roomId } = data;
        socket.to(roomId).emit('screen-share-stopped', {
            socketId: socket.id
        });
    });

    // 静音状态
    socket.on('mute-status', (data) => {
        const { roomId, audioMuted, videoMuted } = data;
        socket.to(roomId).emit('user-mute-status', {
            socketId: socket.id,
            audioMuted,
            videoMuted
        });
    });

    // 录制控制（仅管理员）
    socket.on('recording-start', (data) => {
        const { roomId } = data;
        io.to(roomId).emit('recording-started', {
            startedBy: socket.username
        });
    });

    socket.on('recording-stop', (data) => {
        const { roomId } = data;
        io.to(roomId).emit('recording-stopped', {
            stoppedBy: socket.username
        });
    });

    // 断开连接
    socket.on('disconnect', () => {
        console.log(`[断开] ${socket.id}`);
        if (socket.roomId && rooms.has(socket.roomId)) {
            const room = rooms.get(socket.roomId);
            room.delete(socket.id);
            socket.to(socket.roomId).emit('user-left', {
                socketId: socket.id,
                username: socket.username
            });
            if (room.size === 0) {
                rooms.delete(socket.roomId);
            }
        }
    });
});

// 健康检查
app.get('/health', (req, res) => {
    res.json({ status: 'ok', rooms: rooms.size });
});

// 房间页面（用于iframe嵌入）
app.get('/room/:roomId', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'room.html'));
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`信令服务器运行在端口 ${PORT}`);
});

package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.entity.InspireOfficeDocument;
import com.orep.backend.entity.User;
import com.orep.backend.mapper.UserMapper;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class SdocCollabService {

    private static final String[] COLORS = {
            "#c43a12", "#2b579a", "#217346", "#6d28d9",
            "#b45309", "#0f766e", "#be185d", "#334155"
    };
    private static final long STALE_MS = 12_000;

    private final InspireOfficeService inspireOfficeService;
    private final UserMapper userMapper;
    private final SimpMessagingTemplate messaging;
    private final ObjectMapper objectMapper;

    /** documentId -> sessionId -> peer */
    private final ConcurrentHashMap<Long, ConcurrentHashMap<String, Peer>> rooms = new ConcurrentHashMap<>();
    /** documentId -> latest live snapshot (rev is monotonic in-process) */
    private final ConcurrentHashMap<Long, LiveDoc> liveDocs = new ConcurrentHashMap<>();

    public SdocCollabService(
            InspireOfficeService inspireOfficeService,
            UserMapper userMapper,
            SimpMessagingTemplate messaging,
            ObjectMapper objectMapper
    ) {
        this.inspireOfficeService = inspireOfficeService;
        this.userMapper = userMapper;
        this.messaging = messaging;
        this.objectMapper = objectMapper;
    }

    public Map<String, Object> join(Long documentId, Long userId, String sessionId) {
        inspireOfficeService.requireAccessible(documentId, userId);
        Peer peer = upsert(documentId, userId, sessionId, 0, 0, -1, 0, 0, "", false, false);
        broadcast(documentId);
        Map<String, Object> out = snapshot(documentId, sessionId, peer);
        LiveDoc live = liveDocs.get(documentId);
        out.put("rev", live == null ? 0L : live.rev);
        return out;
    }

    public Map<String, Object> heartbeat(
            Long documentId, Long userId, String sessionId,
            int from, int to, int block, int offset, int endOffset,
            String preview, boolean inProtect, boolean editing
    ) {
        inspireOfficeService.requireAccessible(documentId, userId);
        String safePreview = inProtect ? "仅教师可见" : clip(preview, 32);
        Peer peer = upsert(
                documentId, userId, sessionId,
                from, to, block, offset, endOffset,
                safePreview, inProtect, editing
        );
        broadcast(documentId);
        return snapshot(documentId, sessionId, peer);
    }

    public Map<String, Object> leave(Long documentId, Long userId, String sessionId) {
        inspireOfficeService.requireAccessible(documentId, userId);
        ConcurrentHashMap<String, Peer> room = rooms.get(documentId);
        if (room != null) {
            room.remove(sessionId);
            if (room.isEmpty()) rooms.remove(documentId);
        }
        broadcast(documentId);
        return Map.of("ok", true, "documentId", documentId);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> snapshotContent(Long documentId, Long userId) {
        inspireOfficeService.requireAccessible(documentId, userId);
        try {
            LiveDoc live = liveDocs.get(documentId);
            String raw;
            long rev;
            String sessionId;
            String updatedAt;
            if (live != null) {
                raw = objectMapper.writeValueAsString(Map.of("type", "doc", "content", live.content));
                rev = live.rev;
                sessionId = live.sessionId;
                updatedAt = live.updatedAt;
            } else {
                InspireOfficeDocument meta = inspireOfficeService.requireAccessible(documentId, userId);
                raw = inspireOfficeService.readSmartDocContent(documentId);
                rev = 0L;
                sessionId = "";
                updatedAt = meta.getUpdatedAt() == null ? "" : String.valueOf(meta.getUpdatedAt());
            }
            User viewer = userMapper.selectById(userId);
            String role = viewer != null && viewer.getRole() != null ? viewer.getRole() : "";
            if (!SmartDocProtect.canEditProtected(role)) {
                raw = SmartDocProtect.redact(raw, role);
            }
            Map<String, Object> doc = objectMapper.readValue(raw, Map.class);
            List<Object> blocks = doc.get("content") instanceof List<?> list
                    ? new ArrayList<>(list)
                    : new ArrayList<>();
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("documentId", documentId);
            payload.put("sessionId", sessionId);
            payload.put("rev", rev);
            payload.put("content", blocks);
            payload.put("contentUpdatedAt", updatedAt);
            return payload;
        } catch (IllegalArgumentException | SecurityException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("读取协同快照失败: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> syncContent(
            Long documentId,
            Long userId,
            String sessionId,
            List<Map<String, Object>> changes,
            Integer blockCount,
            List<Object> snapshot
    ) {
        inspireOfficeService.requireAccessible(documentId, userId);
        if (sessionId == null || !sessionId.matches("[A-Za-z0-9_-]{8,64}")) {
            throw new IllegalArgumentException("协同会话无效");
        }
        try {
            String raw = inspireOfficeService.readSmartDocContent(documentId);
            Map<String, Object> doc = objectMapper.readValue(raw, Map.class);
            List<Object> blocks = doc.get("content") instanceof List<?> list
                    ? new ArrayList<>(list)
                    : new ArrayList<>();
            if (snapshot != null) {
                blocks = new ArrayList<>(snapshot);
            } else if (changes != null) {
                for (Map<String, Object> change : changes) {
                    if (change == null) continue;
                    int index = change.get("index") instanceof Number n ? n.intValue() : -1;
                    Object node = change.get("node");
                    if (index < 0 || node == null || index >= blocks.size()) continue;
                    blocks.set(index, node);
                }
            }
            doc.put("type", "doc");
            doc.put("content", blocks);
            String out = objectMapper.writeValueAsString(doc);
            String updatedAt = inspireOfficeService.replaceSmartDocContent(documentId, userId, out);
            Map<String, Object> stored = objectMapper.readValue(
                    inspireOfficeService.readSmartDocContent(documentId),
                    Map.class
            );
            List<Object> storedBlocks = stored.get("content") instanceof List<?> list
                    ? new ArrayList<>(list)
                    : blocks;
            LiveDoc live = liveDocs.compute(documentId, (id, prev) -> new LiveDoc(
                    prev == null ? 1L : prev.rev + 1L,
                    sessionId,
                    storedBlocks,
                    updatedAt
            ));
            User viewer = userMapper.selectById(userId);
            String role = viewer != null && viewer.getRole() != null ? viewer.getRole() : "";
            List<Object> visible = storedBlocks;
            if (!SmartDocProtect.canEditProtected(role)) {
                String redacted = SmartDocProtect.redact(
                        objectMapper.writeValueAsString(Map.of("type", "doc", "content", storedBlocks)),
                        role
                );
                Map<String, Object> redactedDoc = objectMapper.readValue(redacted, Map.class);
                visible = redactedDoc.get("content") instanceof List<?> list
                        ? new ArrayList<>(list)
                        : storedBlocks;
            }
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("documentId", documentId);
            payload.put("sessionId", sessionId);
            payload.put("rev", live.rev);
            payload.put("content", visible);
            payload.put("contentUpdatedAt", updatedAt);
            Map<String, Object> broadcast = new LinkedHashMap<>(payload);
            broadcast.put("content", storedBlocks);
            messaging.convertAndSend("/topic/sdoc/" + documentId + "/sync", broadcast);
            return payload;
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("同步文档失败: " + e.getMessage());
        }
    }

    public Map<String, Object> peers(Long documentId, Long userId) {
        inspireOfficeService.requireAccessible(documentId, userId);
        return Map.of("documentId", documentId, "peers", listPeers(documentId));
    }

    @Scheduled(fixedDelay = 4000)
    public void sweep() {
        long now = Instant.now().toEpochMilli();
        rooms.forEach((docId, room) -> {
            boolean changed = room.entrySet().removeIf(e -> now - e.getValue().seenAt > STALE_MS);
            if (room.isEmpty()) rooms.remove(docId);
            if (changed) broadcast(docId);
        });
    }

    private Peer upsert(
            Long documentId, Long userId, String sessionId,
            int from, int to, int block, int offset, int endOffset,
            String preview, boolean inProtect, boolean editing
    ) {
        if (sessionId == null || !sessionId.matches("[A-Za-z0-9_-]{8,64}")) {
            throw new IllegalArgumentException("协同会话无效");
        }
        ConcurrentHashMap<String, Peer> room = rooms.computeIfAbsent(documentId, k -> new ConcurrentHashMap<>());
        Peer prev = room.get(sessionId);
        User user = userMapper.selectById(userId);
        String name = user != null && user.getUsername() != null && !user.getUsername().isBlank()
                ? user.getUsername().trim()
                : "用户" + userId;
        String role = user != null && user.getRole() != null ? user.getRole() : "";
        boolean emptyLoc = block < 0 && from == 0 && to == 0 && (preview == null || preview.isBlank());
        if (prev != null && emptyLoc) {
            Peer kept = new Peer(
                    userId, sessionId, name, role, colorOf(userId),
                    "/api/wopi/avatars/" + userId + "?v=4",
                    prev.from, prev.to, prev.block, prev.offset, prev.endOffset,
                    prev.preview, prev.inProtect, editing, Instant.now().toEpochMilli()
            );
            room.put(sessionId, kept);
            return kept;
        }
        Peer next = new Peer(
                userId,
                sessionId,
                name,
                role,
                colorOf(userId),
                "/api/wopi/avatars/" + userId + "?v=4",
                from,
                to,
                block,
                offset,
                endOffset,
                preview == null ? "" : preview,
                inProtect,
                editing,
                Instant.now().toEpochMilli()
        );
        room.put(sessionId, next);
        return next;
    }

    private void broadcast(Long documentId) {
        messaging.convertAndSend("/topic/sdoc/" + documentId + "/presence", Map.of(
                "documentId", documentId,
                "peers", listPeers(documentId)
        ));
    }

    private List<Map<String, Object>> listPeers(Long documentId) {
        ConcurrentHashMap<String, Peer> room = rooms.get(documentId);
        if (room == null) return List.of();
        long now = Instant.now().toEpochMilli();
        List<Map<String, Object>> out = new ArrayList<>();
        room.forEach((id, peer) -> {
            if (now - peer.seenAt <= STALE_MS) out.add(peer.toMap());
        });
        return out;
    }

    private Map<String, Object> snapshot(Long documentId, String sessionId, Peer self) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("documentId", documentId);
        m.put("sessionId", sessionId);
        m.put("self", self.toMap());
        m.put("peers", listPeers(documentId));
        return m;
    }

    static String colorOf(long userId) {
        return COLORS[Math.floorMod(userId, COLORS.length)];
    }

    private static String clip(String text, int max) {
        if (text == null) return "";
        String t = text.replaceAll("\\s+", " ").trim();
        if (t.length() <= max) return t;
        return t.substring(0, max) + "…";
    }

    record LiveDoc(long rev, String sessionId, List<Object> content, String updatedAt) {
    }

    record Peer(
            long userId,
            String sessionId,
            String name,
            String role,
            String color,
            String avatar,
            int from,
            int to,
            int block,
            int offset,
            int endOffset,
            String preview,
            boolean inProtect,
            boolean editing,
            long seenAt
    ) {
        Map<String, Object> toMap() {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("userId", userId);
            m.put("sessionId", sessionId);
            m.put("name", name);
            m.put("role", role);
            m.put("color", color);
            m.put("avatar", avatar);
            m.put("from", from);
            m.put("to", to);
            m.put("block", block);
            m.put("offset", offset);
            m.put("endOffset", endOffset);
            m.put("preview", preview);
            m.put("inProtect", inProtect);
            m.put("editing", editing);
            return m;
        }
    }
}

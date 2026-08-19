# Realtime Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a secure, persistent, realtime student notification center for teacher training reminders.

**Architecture:** A focused `NotificationService` owns reminder persistence, read state, REST views, and user-specific STOMP delivery. The existing teacher portal delegates reminder creation to that service, while a frontend notification client combines REST bootstrap/fallback with an authenticated `/user/queue/notifications` subscription.

**Tech Stack:** Java 21, Spring Boot 3.2, JdbcTemplate, STOMP/SockJS, JWT, Vue 3, Axios, `@stomp/stompjs`, Playwright

---

### Task 1: Notification persistence and ownership

**Files:**

- Create: `backend/src/main/java/com/orep/backend/service/NotificationService.java`
- Create: `backend/src/test/java/com/orep/backend/service/NotificationServiceTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/TeacherPortalService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/TeacherPortalServiceScopeTest.java`

- [ ] **Step 1: Write failing service tests**

Create Mockito-based tests covering:

```java
@Test
void listReturnsItemsAndGlobalUnreadCount() {
    when(jdbc.queryForList(contains("ORDER BY created_at DESC"), eq(7L), eq(21L)))
            .thenReturn(List.of(new LinkedHashMap<>(Map.of(
                    "id", 9L, "targetType", "TRAINING_CAMP",
                    "payloadJson", "{\"message\":\"请完成训练\"}",
                    "readAt", null
            ))));
    when(jdbc.queryForObject(contains("COUNT(*)"), eq(Integer.class), eq(7L), eq(21L)))
            .thenReturn(3);

    Map<String, Object> result = service.notifications(7L, 21L);

    assertEquals(3, result.get("unreadCount"));
    assertEquals("/training/today",
            ((List<Map<String, Object>>) result.get("items")).getFirst().get("targetPath"));
}

@Test
void markReadScopesUpdateToTenantAndRecipient() {
    service.markRead(7L, 21L, 9L);
    verify(jdbc).update(contains("tenant_id=? AND target_id=?"),
            any(), eq(9L), eq(7L), eq(21L));
}
```

- [ ] **Step 2: Run the tests and confirm failure**

Run:

```bash
cd backend
mvn -Dtest=NotificationServiceTest test
```

Expected: compilation failure because `NotificationService` does not exist.

- [ ] **Step 3: Implement `NotificationService`**

The service must expose:

```java
public Map<String, Object> notifications(Long tenantId, Long userId)
public Map<String, Object> markRead(Long tenantId, Long userId, Long notificationId)
public Map<String, Object> markAllRead(Long tenantId, Long userId)
public Map<String, Object> createReminder(
        Long tenantId,
        Long actorUserId,
        Long recipientUserId,
        String targetType,
        Map<String, Object> payload)
```

`createReminder` inserts `REMINDER_SENT` with a `GeneratedKeyHolder`, builds one normalized notification DTO, and returns it. `notifications` returns `{items, unreadCount}`; `markRead` and `markAllRead` update only rows matching tenant, recipient, and event type. `targetPath` is always `/training/today` for current reminder types.

- [ ] **Step 4: Add schema compatibility**

In `TeacherPortalService.ensureTables()`, add `read_at DATETIME NULL` to the create statement and a guarded:

```java
try {
    jdbc.execute("ALTER TABLE teacher_portal_event ADD COLUMN read_at DATETIME NULL AFTER payload_json");
} catch (Exception ignored) { }
```

- [ ] **Step 5: Delegate reminder creation**

Inject `NotificationService` into `TeacherPortalService`. Replace the reminder-specific `recordEvent(...)` call with:

```java
notificationService.createReminder(
        tenantId, userId, recipientId, targetType, payload);
```

Update `TeacherPortalServiceScopeTest` to provide a mocked `NotificationService`.

- [ ] **Step 6: Run service tests**

Run:

```bash
cd backend
mvn -Dtest=NotificationServiceTest,TeacherPortalServiceScopeTest test
```

Expected: all selected tests pass.

### Task 2: Secure notification REST API

**Files:**

- Modify: `backend/src/main/java/com/orep/backend/controller/NotificationController.java`
- Create: `backend/src/test/java/com/orep/backend/controller/NotificationControllerTest.java`

- [ ] **Step 1: Write failing controller tests**

Use standalone MockMvc to assert:

```java
mvc.perform(patch("/api/notifications/9/read")
        .requestAttr("tenantId", 7L)
        .requestAttr("userId", 21L))
   .andExpect(status().isOk())
   .andExpect(jsonPath("$.data.id").value(9));

mvc.perform(patch("/api/notifications/read-all")
        .requestAttr("tenantId", 7L)
        .requestAttr("userId", 21L))
   .andExpect(status().isOk())
   .andExpect(jsonPath("$.data.unreadCount").value(0));
```

- [ ] **Step 2: Run and confirm failure**

Run:

```bash
cd backend
mvn -Dtest=NotificationControllerTest test
```

Expected: compilation or 404 failures for the new API.

- [ ] **Step 3: Implement the controller endpoints**

Change the controller dependency from `TeacherPortalService` to `NotificationService`, return the notification envelope from `GET`, and add:

```java
@PatchMapping("/{id}/read")
public Result<Map<String, Object>> markRead(@PathVariable Long id, HttpServletRequest request)

@PatchMapping("/read-all")
public Result<Map<String, Object>> markAllRead(HttpServletRequest request)
```

- [ ] **Step 4: Run controller tests**

Run:

```bash
cd backend
mvn -Dtest=NotificationControllerTest test
```

Expected: all controller tests pass.

### Task 3: Authenticated user-specific STOMP delivery

**Files:**

- Create: `backend/src/main/java/com/orep/backend/config/WebSocketAuthChannelInterceptor.java`
- Modify: `backend/src/main/java/com/orep/backend/config/WebSocketConfig.java`
- Modify: `backend/src/main/java/com/orep/backend/service/NotificationService.java`
- Create: `backend/src/test/java/com/orep/backend/config/WebSocketAuthChannelInterceptorTest.java`

- [ ] **Step 1: Write failing authentication tests**

Build STOMP `CONNECT` messages with `StompHeaderAccessor` and assert:

```java
accessor.addNativeHeader("Authorization", "Bearer valid-token");
Message<?> authenticated = interceptor.preSend(message(accessor), channel);
assertEquals("21", StompHeaderAccessor.wrap(authenticated).getUser().getName());

accessor.addNativeHeader("Authorization", "Bearer invalid-token");
Message<?> anonymous = interceptor.preSend(message(accessor), channel);
assertNull(StompHeaderAccessor.wrap(anonymous).getUser());
```

- [ ] **Step 2: Run and confirm failure**

Run:

```bash
cd backend
mvn -Dtest=WebSocketAuthChannelInterceptorTest test
```

Expected: compilation failure because the interceptor does not exist.

- [ ] **Step 3: Implement authentication and broker configuration**

On STOMP `CONNECT`, parse the Bearer token with `JwtUtil`. For a valid token set:

```java
accessor.setUser(() -> String.valueOf(jwtUtil.getUserId(token)));
```

Configure:

```java
config.enableSimpleBroker("/topic", "/queue");
registration.interceptors(webSocketAuthChannelInterceptor);
```

Missing or invalid credentials remain anonymous and therefore cannot receive a user destination.

- [ ] **Step 4: Push after persistence**

Inject `SimpMessagingTemplate` into `NotificationService` and, only after a successful insert, call:

```java
messagingTemplate.convertAndSendToUser(
        String.valueOf(recipientUserId),
        "/queue/notifications",
        notification);
```

- [ ] **Step 5: Run realtime backend tests**

Run:

```bash
cd backend
mvn -Dtest=NotificationServiceTest,WebSocketAuthChannelInterceptorTest test
```

Expected: all selected tests pass and the service test verifies the exact user destination.

### Task 4: Frontend notification client

**Files:**

- Create: `frontend/user/src/services/notificationClient.js`
- Modify: `frontend/user/src/utils/websocket.js`
- Create: `frontend/user/tests/notification-center.spec.js`

- [ ] **Step 1: Write a failing Playwright contract**

Mock `GET /api/notifications` with:

```js
{
  code: 200,
  data: {
    unreadCount: 1,
    items: [{
      id: 9,
      title: '集训任务提醒',
      message: '请完成今日训练',
      isRead: false,
      targetPath: '/training/today',
      createdAt: '2026-07-23T10:00:00'
    }]
  }
}
```

Assert the bell badge shows `1`, the panel item is a button, clicking it calls
`PATCH /api/notifications/9/read`, and the URL becomes `/training/today`.

- [ ] **Step 2: Run and confirm failure**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/notification-center.spec.js
```

Expected: failure because the current topbar renders non-clickable articles and has no read request.

- [ ] **Step 3: Implement the client**

Export a focused API:

```js
export function useNotificationClient({
  onSnapshot,
  onRealtimeNotification,
  onConnectionChange
})
```

It must:

- fetch the REST envelope on start, focus, and explicit refresh;
- connect with the existing authenticated STOMP client;
- subscribe to `/user/queue/notifications`;
- refresh after reconnect to recover missed messages;
- expose `markRead(id)`, `markAllRead()`, `refresh()`, and `stop()`;
- unsubscribe and remove focus listeners on stop.

Update the shared WebSocket utility so repeated `connect` calls reuse one active client and subscriptions survive reconnect through stored callbacks.

- [ ] **Step 4: Run the focused frontend test**

Run the same Playwright command.

Expected: the REST, read, and navigation assertions pass.

### Task 5: Notification panel interaction and realtime presentation

**Files:**

- Modify: `frontend/user/src/components/workspace/WorkspaceTopbar.vue`
- Modify: `frontend/user/tests/notification-center.spec.js`

- [ ] **Step 1: Extend the failing UI contract**

Add assertions for:

- badge absent when `unreadCount` is zero;
- unread item has `is-unread`;
- “全部已读” calls `PATCH /api/notifications/read-all`;
- a simulated realtime callback inserts one item without duplication;
- REST failure shows “通知加载失败” and a retry button.

- [ ] **Step 2: Implement the panel states**

Replace notification `<article>` nodes with buttons. Add:

```vue
<button
  v-for="item in notifications"
  :key="item.id"
  class="workspace-message-item"
  :class="{ 'is-unread': !item.isRead }"
  type="button"
  @click="openNotification(item)"
>
```

The header shows unread count and “全部已读”. Loading, error, empty, and populated states are mutually exclusive. Realtime arrivals update the list by ID and use a four-second `ElNotification` only while the panel is closed.

- [ ] **Step 3: Implement optimistic read behavior**

`openNotification` updates local read state and unread count first, calls the read endpoint, then routes to the server-provided internal path. On API failure it refreshes without blocking navigation. `markAllRead` uses the same optimistic/refresh pattern.

- [ ] **Step 4: Run notification and existing student contracts**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test \
  tests/notification-center.spec.js \
  tests/student-prototype-contract.spec.js
```

Expected: all selected Playwright tests pass.

### Task 6: Full verification

**Files:**

- Verify only; no new production files.

- [ ] **Step 1: Run backend tests**

```bash
cd backend
mvn -Dtest=NotificationServiceTest,NotificationControllerTest,WebSocketAuthChannelInterceptorTest,TeacherPortalServiceScopeTest test
```

Expected: all selected tests pass.

- [ ] **Step 2: Build both applications**

```bash
cd backend && mvn -DskipTests package
cd ../frontend/user && npm run build
```

Expected: both builds finish successfully.

- [ ] **Step 3: Run frontend contracts**

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test \
  tests/notification-center.spec.js \
  tests/student-prototype-contract.spec.js
```

Expected: all selected tests pass.

- [ ] **Step 4: Manual end-to-end check**

With teacher and student sessions open:

1. Teacher sends one training reminder.
2. Student badge increments without refreshing.
3. Student opens the panel and sees the new reminder at the top.
4. Student clicks the reminder and arrives at `/training/today`.
5. Reloading keeps the notification read.
6. Disconnecting WebSocket and reopening the panel still retrieves the reminder through REST.

**Repository note:** `/Users/liuyixing/项目/OREP` is not a Git worktree, so commit steps are intentionally omitted.
